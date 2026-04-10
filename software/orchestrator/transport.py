"""Multi-target LED transport — DDP (Distributed Display Protocol) + DNRGB fallback.

DDP is the primary transport (port 4048). It has proper multi-packet framing
so the receiver knows when a complete frame has arrived.

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

logger = logging.getLogger(__name__)

HEALTH_CHECK_INTERVAL = 5

# DDP constants
DDP_PORT = 4048
DDP_HEADER_SIZE = 10
DDP_MAX_DATA = 1440  # conservative max data per packet (fits in MTU)
DDP_FLAGS_VER1 = 0x40
DDP_FLAGS_PUSH = 0x01  # signals last packet of a frame
DDP_TYPE_RGB8 = 0x01
DDP_SOURCE_ID = 0x01

# DNRGB constants (fallback)
DNRGB_PORT = 21324
DNRGB_PROTOCOL = 4
DNRGB_MAX_LEDS = 489


def _find_source_ip_for(target_ip: str) -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((target_ip, 1))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return ""


class UDPTransport:
    def __init__(self, targets: list[dict], config):
        self._config = config
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for t in targets:
            src = _find_source_ip_for(t.get("ip", "127.0.0.1"))
            if src and src != "127.0.0.1":
                try:
                    self._sock.bind((src, 0))
                    logger.info(f"UDP socket bound to {src} (for {t['ip']})")
                except OSError:
                    pass
                break
        self._lock = threading.Lock()
        self._targets = []
        self._seq = 0  # DDP sequence counter
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
            enabled = [(t["ip"].split("/")[0].strip(), t["port"]) for t in self._targets if t["enabled"]]

        if not enabled:
            return

        params = self._config.get("transport")
        protocol = params.get("protocol", "ddp")
        delay = params.get("inter_packet_ms", 0) / 1000.0

        if protocol == "ddp":
            self._send_ddp(frame, enabled, delay)
        else:
            self._send_dnrgb(frame, enabled, params, delay)

    def _send_ddp(self, frame: bytearray, targets, delay):
        """Send frame via DDP protocol (port 4048)."""
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
                except OSError:
                    pass

            offset += chunk
            if offset < total_bytes and delay > 0:
                time.sleep(delay)

    def _send_dnrgb(self, frame: bytearray, targets, params, delay):
        """Send frame via DNRGB protocol (port 21324). Fallback."""
        timeout = params.get("timeout", 255)
        max_leds = min(params.get("max_leds_per_packet", 489), DNRGB_MAX_LEDS)
        total_leds = len(frame) // 3

        packets = []
        led = 0
        while led < total_leds:
            chunk = min(max_leds, total_leds - led)
            pkt = bytearray(4 + chunk * 3)
            pkt[0] = DNRGB_PROTOCOL
            pkt[1] = timeout
            pkt[2] = (led >> 8) & 0xFF
            pkt[3] = led & 0xFF
            pkt[4:] = frame[led * 3:(led + chunk) * 3]
            packets.append(pkt)
            led += chunk

        for i, pkt in enumerate(packets):
            for ip, port in targets:
                try:
                    self._sock.sendto(pkt, (ip, port))
                except OSError:
                    pass
            if i < len(packets) - 1 and delay > 0:
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
