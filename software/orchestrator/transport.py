"""Multi-target LED transport — DDP only.

DDP (Distributed Display Protocol, port 4048) has proper multi-packet
framing so the receiver knows when a complete frame has arrived. We
used to also support DNRGB as a fallback, but in practice DDP is what
WLED handles correctly for the 1936-pixel matrix; DNRGB was removed.

DDP packet format (10-byte header + data):
  Byte 0:    Flags (VER1=0x40, PUSH=0x01, TIMECODE=0x10)
  Byte 1:    Sequence number (1-15, wraps)
  Byte 2:    Data type (0x01 = RGB, 8 bits per channel)
  Byte 3:    Source ID
  Bytes 4-7: Data offset (32-bit big-endian, in BYTES not LEDs)
  Bytes 8-9: Data length (16-bit big-endian, in bytes)
  Bytes 10+: RGB data
"""
import socket
import threading
import time
import logging
import urllib.request

import numpy as np

logger = logging.getLogger(__name__)

HEALTH_CHECK_INTERVAL = 5

# WS2811 full-white draw per LED — keep in sync with animation_engine's
# WATTS_PER_LED_FULL_WHITE (duplicated to avoid importing the engine here).
WATTS_PER_LED_FULL_WHITE = 0.1

# DDP constants
DDP_PORT = 4048
DDP_HEADER_SIZE = 10
DDP_MAX_DATA = 1440  # conservative max data per packet (fits in MTU)
DDP_FLAGS_VER1 = 0x40
DDP_FLAGS_PUSH = 0x01  # signals last packet of a frame
DDP_TYPE_RGB8 = 0x01
DDP_SOURCE_ID = 0x01


class UDPTransport:
    def __init__(self, targets: list[dict], config):
        self._config = config
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Don't bind to a specific interface — let the OS route each packet.
        # This way localhost targets keep working even if the WLED interface goes down.
        self._lock = threading.Lock()
        self._targets = []
        self._seq = 0  # DDP sequence counter
        # Cached gamma LUT: 256 FLOAT levels for the configured exponent,
        # rebuilt lazily when it changes — plus fixed per-pixel dither
        # offsets for the final 8-bit rounding (see _apply_gamma).
        self._gamma_exp = None
        self._gamma_lut = None
        self._dither_noise = None
        # Power limiter (ABL): current dim scale + last-frame stats for
        # the admin panel. Attack is instant, release glides — see
        # _limiter_scale.
        self._limit_scale = 1.0
        self._limit_t = 0.0
        self._limit_state = {"enabled": False, "max_watts": 0.0,
                             "watts": 0.0, "zone_watts": [0.0, 0.0],
                             "watts_out": 0.0, "scale": 1.0}
        self.update_targets(targets)

        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()

    def update_targets(self, targets: list[dict]):
        with self._lock:
            self._targets = [
                {
                    "name": t.get("name", "Unknown"),
                    "ip": t["ip"],
                    "port": t["port"],
                    "enabled": t.get("enabled", True),
                    "status": "unknown",
                }
                for t in targets
            ]

    def get_targets(self) -> list[dict]:
        with self._lock:
            return [t.copy() for t in self._targets]

    def send_frame(self, frame: bytearray):
        with self._lock:
            enabled = [
                (t["ip"].split("/")[0].strip(), t["port"])
                for t in self._targets if t["enabled"]
            ]

        if not enabled:
            return

        tcfg = self._config.get("transport") or {}
        frame = self._shape_output(frame, tcfg)
        delay = tcfg.get("inter_packet_ms", 0) / 1000.0
        self._send_ddp(frame, enabled, delay)

    def _shape_output(self, frame: bytearray, tcfg: dict):
        """Gamma + power limiter on the outgoing DDP bytes (hardware path
        only — the simulator frame stays raw). Both run in FLOAT with a
        single dither/quantize pass at the end."""
        try:
            exp = float(tcfg.get("gamma", 1.0))
        except (TypeError, ValueError):
            exp = 1.0
        lin = None
        if exp > 1.001:
            if exp != self._gamma_exp:
                self._gamma_lut = np.array(
                    [(i / 255.0) ** exp * 255.0 for i in range(256)],
                    dtype=np.float32)
                self._gamma_exp = exp
            lin = self._gamma_lut[np.frombuffer(frame, dtype=np.uint8)]

        # Power limiter — measured on the POST-gamma values, since those
        # are the duty cycles the LEDs actually draw current at.
        vals = (lin if lin is not None
                else np.frombuffer(frame, dtype=np.uint8))
        scale = self._limiter_scale(vals, tcfg.get("power_limit") or {})
        if scale < 0.9995:
            if lin is None:
                lin = np.frombuffer(frame, dtype=np.uint8).astype(np.float32)
            lin = lin * scale

        if lin is None:
            return frame
        return self._quantize(lin)

    def _limiter_scale(self, vals, pl: dict) -> float:
        """ABL-style auto power limiter. The matrix is fed as two
        electrically independent panels (2 WLED pins, first/second half
        of the frame), so the budget is enforced PER PANEL at half the
        total each: a bright scene concentrated on one panel pulls its
        whole draw through that panel's wiring and browns it out (random-
        color glitching) even when the total looks safe. The frame is
        scaled uniformly by the worst panel's overshoot, so the image
        only dims — it never changes balance. Attack is instant (protect
        the supply NOW); release glides back up over `release_s` so the
        limiter itself never pumps or flickers."""
        zones = max(1, int(pl.get("zones", 2)))
        zone_watts = [float(z.sum()) / (255.0 * 3.0) * WATTS_PER_LED_FULL_WHITE
                      for z in np.array_split(np.asarray(vals, dtype=np.float32),
                                              zones)]
        watts = sum(zone_watts)
        worst = max(zone_watts)
        enabled = bool(pl.get("enabled", False))
        try:
            max_w = float(pl.get("max_watts", 150.0))
        except (TypeError, ValueError):
            max_w = 150.0
        max_w = max(1.0, max_w)
        zone_budget = max_w / zones
        now = time.monotonic()
        dt = max(0.0, min(0.2, now - self._limit_t))
        self._limit_t = now
        if not enabled or worst <= 0.0:
            self._limit_scale = 1.0
        else:
            needed = min(1.0, zone_budget / worst)
            if needed < self._limit_scale:
                self._limit_scale = needed
            else:
                try:
                    release_s = max(0.05, float(pl.get("release_s", 0.7)))
                except (TypeError, ValueError):
                    release_s = 0.7
                self._limit_scale = min(needed,
                                        self._limit_scale + dt / release_s)
        scale = self._limit_scale
        self._limit_state = {
            "enabled":    enabled,
            "max_watts":  round(max_w, 1),
            "watts":      round(watts, 1),
            "zone_watts": [round(w, 1) for w in zone_watts],
            "watts_out":  round(watts * scale, 1),
            "scale":      round(scale, 3),
        }
        return scale

    def limiter_state(self) -> dict:
        """Last-frame limiter snapshot for the admin panel."""
        return dict(self._limit_state)

    def _quantize(self, lin):
        """Float → DDP bytes with a fixed per-pixel spatial dither.

        The old integer translation table collapsed the dark range into a
        handful of output levels, so slow fades (playground crossfades,
        mode transitions) stepped visibly: every pixel of the same value
        jumped a level at the same instant, frame-wide. Giving each pixel
        its own constant quantization threshold spreads the jumps through
        the fade (a fine spatial ripple instead of a step), while static
        content stays byte-identical frame to frame — the offsets never
        change over time, so nothing flickers."""
        noise = self._dither_noise
        if noise is None or noise.shape != lin.shape:
            # ONE offset per PIXEL, shared by its three channels — so the
            # rounding can't shift hue. Per-subpixel offsets turned dim
            # warm tones into lone pure-red LEDs (r rounded up where g/b
            # rounded down, permanently, since the offsets are fixed).
            px = np.random.default_rng(1234).random(
                (lin.shape[0] + 2) // 3).astype(np.float32)
            noise = np.repeat(px, 3)[: lin.shape[0]]
            self._dither_noise = noise
        out = np.clip(np.floor(lin + noise), 0, 255)
        return bytearray(out.astype(np.uint8).tobytes())

    def _apply_gamma(self, frame: bytearray, exp):
        """Gamma-only path (no limiter) — kept for tests and the on-Pi
        verification scripts that compare raw vs corrected bytes."""
        return self._shape_output(frame, {"gamma": exp})

    def _send_ddp(self, frame: bytearray, targets, delay):
        total_bytes = len(frame)
        self._seq = (self._seq % 15) + 1  # sequence 1-15

        offset = 0
        while offset < total_bytes:
            chunk = min(DDP_MAX_DATA, total_bytes - offset)
            is_last = (offset + chunk >= total_bytes)

            header = bytearray(DDP_HEADER_SIZE)
            header[0] = DDP_FLAGS_VER1 | (DDP_FLAGS_PUSH if is_last else 0)
            header[1] = self._seq
            header[2] = DDP_TYPE_RGB8
            header[3] = DDP_SOURCE_ID
            # Offset in bytes (32-bit big-endian)
            header[4] = (offset >> 24) & 0xFF
            header[5] = (offset >> 16) & 0xFF
            header[6] = (offset >> 8) & 0xFF
            header[7] = offset & 0xFF
            # Length in bytes (16-bit big-endian)
            header[8] = (chunk >> 8) & 0xFF
            header[9] = chunk & 0xFF

            packet = header + frame[offset:offset + chunk]

            for ip, _ in targets:
                try:
                    self._sock.sendto(packet, (ip, DDP_PORT))
                except Exception:
                    pass

            offset += chunk
            if offset < total_bytes and delay > 0:
                time.sleep(delay)

    def _health_loop(self):
        while self._running:
            with self._lock:
                targets = [(i, t.copy()) for i, t in enumerate(self._targets)]

            for i, t in targets:
                old_status = t["status"]
                status = self._check_health(t["ip"], t["port"])
                with self._lock:
                    if i < len(self._targets):
                        self._targets[i]["status"] = status
                if status != old_status:
                    logger.info(f"Target '{t['name']}' ({t['ip']}): {old_status} -> {status}")

            time.sleep(HEALTH_CHECK_INTERVAL)

    @staticmethod
    def _check_health(ip: str, port: int) -> str:
        clean_ip = ip.split("/")[0].strip()
        for url in [f"http://{clean_ip}/json", f"http://{clean_ip}:3000/"]:
            try:
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=3)
                resp.read(64)
                resp.close()
                return "online"
            except Exception:
                continue
        return "offline"

    def stop(self):
        self._running = False
