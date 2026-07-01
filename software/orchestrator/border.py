"""Floor-border LED strips.

Addressable WS2812/SK6812 strips lighting the platform's border — separate
from the 44×44 matrix (which is WLED over Ethernet). One strip per half;
each is wired to a Pi SPI MOSI pin and driven here.

Why SPI: bit-banging WS2812 from Linux userspace is too jittery, and the
PWM/PCM drivers (rpi_ws281x) collide with the Pi's analog audio — which this
installation needs for the meditation/ocean sound. SPI is hardware-timed and
touches neither. Each WS2812 bit is encoded as three SPI bits at 2.4 MHz
(1.25 µs/bit): a '1' → 110, a '0' → 100.

Pin map (Pi 4):
  * SPI0 MOSI = GPIO10  (enable: dtparam=spi=on        → /dev/spidev0.0)
  * SPI1 MOSI = GPIO20  (enable: dtoverlay=spi1-1cs    → /dev/spidev1.0)

The border is modelled as ONE logical ring (sum of all segment lengths) so
animations — especially the moving gradient — wrap seamlessly across both
halves; each physical strip just renders its slice of the ring.

Everything is intentionally SLOW and dim: this runs all night on battery, so
the animations are gentle and the default brightness is low (less LED current
= real power saving).
"""
from __future__ import annotations

import logging
import math
import threading
import time

import numpy as np

logger = logging.getLogger(__name__)

try:
    import spidev  # Pi-only
    HAS_SPIDEV = True
except ImportError:
    spidev = None
    HAS_SPIDEV = False


# ── WS2812-over-SPI bit encoding ────────────────────────────────────
_SPI_HZ = 2_400_000          # 3 SPI bits per WS2812 bit → 1.25 µs/bit
_RESET_BYTES = 42            # trailing zero bytes (>50 µs low latch)


def _build_lut() -> list[bytes]:
    """One colour byte (8 bits) → 24 SPI bits (3 bytes), MSB first."""
    lut = []
    for byte in range(256):
        bits = 0
        for i in range(8):
            bit = (byte >> (7 - i)) & 1
            bits = (bits << 3) | (0b110 if bit else 0b100)
        lut.append(bytes(((bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF)))
    return lut


_LUT = _build_lut()
# Flat 256×3 byte table for fast vectorised encoding.
_LUT_NP = np.frombuffer(b"".join(_LUT), dtype=np.uint8).reshape(256, 3)

# Strip byte order → column permutation applied to an (n,3) RGB array. Strips
# vary: standard WS2812 is GRB, but WS2811/SK6812 variants use others. Picked
# in the UI so colours can be matched by eye.
COLOR_ORDERS = {
    "RGB": (0, 1, 2), "RBG": (0, 2, 1), "GRB": (1, 0, 2),
    "GBR": (1, 2, 0), "BRG": (2, 0, 1), "BGR": (2, 1, 0),
}

# Mild gamma so low brightness still shows colour nicely.
_GAMMA = np.array([int(((i / 255.0) ** 2.2) * 255.0 + 0.5)
                   for i in range(256)], dtype=np.uint8)


class _SpiStrip:
    """One physical strip on an SPI bus. No-ops cleanly if SPI is absent
    (dev laptop, or the overlay not enabled yet) so the rest still runs."""

    def __init__(self, bus: int, dev: int, num: int) -> None:
        self.bus, self.dev, self.num = bus, dev, int(num)
        self._spi = None
        if HAS_SPIDEV and self.num > 0:
            try:
                s = spidev.SpiDev()
                s.open(bus, dev)
                s.max_speed_hz = _SPI_HZ
                s.mode = 0
                self._spi = s
                logger.info("border: opened /dev/spidev%d.%d (%d px)",
                            bus, dev, self.num)
            except Exception as e:
                logger.warning("border: /dev/spidev%d.%d unavailable: %s",
                               bus, dev, e)
                self._spi = None

    @property
    def ok(self) -> bool:
        return self._spi is not None

    def show(self, rgb: np.ndarray, order: str = "GRB") -> None:
        """rgb: (num, 3) uint8 in RGB order. Re-orders to the strip's native
        byte order (configurable — strips vary) and encodes over SPI."""
        if self._spi is None:
            return
        perm = COLOR_ORDERS.get(order, COLOR_ORDERS["GRB"])
        wire = rgb[:, perm]
        enc = _LUT_NP[wire.reshape(-1)].reshape(-1)   # (num*9,) SPI bytes
        buf = bytes(enc) + b"\x00" * _RESET_BYTES
        try:
            try:
                self._spi.writebytes2(buf)            # handles big buffers
            except AttributeError:
                for i in range(0, len(buf), 4096):
                    self._spi.writebytes(buf[i:i + 4096])
        except Exception:
            logger.exception("border: SPI write failed")

    def close(self) -> None:
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass
            self._spi = None


# ── Palette helpers ─────────────────────────────────────────────────
# Named presets so the UI can offer "pick a palette". All kept calm.
PALETTE_PRESETS: dict[str, list[list[int]]] = {
    "cold":    [[80, 120, 255], [40, 90, 205], [95, 70, 205], [55, 175, 200]],
    "ocean":   [[10, 80, 160], [20, 140, 180], [40, 200, 190], [10, 60, 120]],
    "ember":   [[180, 60, 20], [220, 110, 30], [120, 30, 10], [200, 80, 25]],
    "forest":  [[30, 120, 60], [80, 170, 70], [20, 90, 80], [120, 180, 90]],
    "dusk":    [[180, 70, 120], [110, 60, 180], [60, 50, 160], [210, 110, 90]],
    "mono":    [[180, 180, 200], [90, 90, 120], [220, 220, 235], [50, 50, 70]],
}


def _pal_array(palette) -> np.ndarray:
    pal = palette if palette else PALETTE_PRESETS["cold"]
    return np.array(pal, dtype=np.float32)


def _pal_lerp(pal: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Sample a cyclic gradient through `pal` at fractional positions u∈[0,1).
    u: (n,) → returns (n,3)."""
    k = len(pal)
    x = (u % 1.0) * k
    i0 = np.floor(x).astype(int) % k
    i1 = (i0 + 1) % k
    f = (x - np.floor(x))[:, None]
    return pal[i0] * (1.0 - f) + pal[i1] * f


# ── Animations ──────────────────────────────────────────────────────
# Each: (t_s, n, p, rng) -> (n,3) float RGB 0..255  (brightness applied later).
# `p` is the resolved border config; `speed`∈[0,1] scales every rate so the
# whole thing stays slow. `t_s` is seconds since the animation (re)started.

def _color(p) -> np.ndarray:
    c = p.get("color") or [80, 120, 255]
    return np.array(c, dtype=np.float32)


def _spd(p) -> float:
    # Geometric speed dial centred on the "liked" pulse rate (2.0) at 50%:
    #   0%   → 1.0  (half  speed)
    #   50%  → 2.0  (the calibrated default)
    #   100% → 4.0  (double speed)
    s = max(0.0, min(1.0, float(p.get("speed", 0.5))))
    return 2.0 ** (2.0 * s)


def anim_solid(t, n, p, rng):
    return np.tile(_color(p), (n, 1))


def anim_pulse(t, n, p, rng):
    # Whole border breathes one colour between ~25% and 100%.
    s = _spd(p)
    env = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * 0.5 * s))
    return np.tile(_color(p) * env, (n, 1))


def anim_gradient_orbit(t, n, p, rng):
    # The selected palette as a gradient wrapped around the ring, slowly
    # rotating — the "moving gradient" the border was made for.
    pal = _pal_array(p.get("palette"))
    s = _spd(p)
    u = (np.arange(n) / max(1, n)) + t * 0.03 * s
    return _pal_lerp(pal, u)


def anim_comet(t, n, p, rng):
    # A soft bright head drifts around a near-dark ring, long fading tail;
    # the head colour slowly cycles through the palette.
    pal = _pal_array(p.get("palette"))
    s = _spd(p)
    head = (t * 0.05 * s) % 1.0 * n
    idx = np.arange(n)
    d = (idx - head) % n                    # distance behind the head
    tail = np.exp(-d / (n * 0.22))          # fade along the ring
    col = _pal_lerp(pal, np.array([t * 0.02 * s]))[0]
    base = pal[0] * 0.04                     # faint resting glow
    return base[None, :] * (1 - tail[:, None]) + col[None, :] * tail[:, None]


def anim_breathe_wander(t, n, p, rng):
    # The whole ring is one colour that slowly wanders through the palette,
    # with a gentle brightness breath on top.
    pal = _pal_array(p.get("palette"))
    s = _spd(p)
    col = _pal_lerp(pal, np.array([t * 0.015 * s]))[0]
    env = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 0.35 * s))
    return np.tile(col * env, (n, 1))


def anim_wave(t, n, p, rng):
    # A slow sine brightness wave of the chosen colour travelling around.
    s = _spd(p)
    idx = np.arange(n)
    phase = idx / max(1, n) * 2 * math.pi * 2.0 - t * 0.6 * s
    env = (0.15 + 0.85 * (0.5 + 0.5 * np.sin(phase)))[:, None]
    return _color(p)[None, :] * env


def anim_twinkle(t, n, p, rng):
    # Sparse, slow twinkles in palette colours over a dim base. Persistent
    # per-pixel phase lives in p["_tw"] (seeded once).
    pal = _pal_array(p.get("palette"))
    s = _spd(p)
    st = p.setdefault("_tw", {})
    if st.get("n") != n:
        st["n"] = n
        st["phase"] = rng.random(n).astype(np.float32) * 1000.0
        st["rate"] = (0.15 + 0.5 * rng.random(n)).astype(np.float32)
        st["hue"] = rng.random(n).astype(np.float32)
    tw = 0.5 + 0.5 * np.sin(st["phase"] + t * st["rate"] * 0.6 * s)
    tw = np.clip((tw - 0.55) / 0.45, 0.0, 1.0) ** 2     # mostly dark, rare peaks
    cols = _pal_lerp(pal, st["hue"])
    base = pal[0] * 0.05
    return base[None, :] * (1 - tw[:, None]) + cols * tw[:, None]


def anim_aurora(t, n, p, rng):
    # Overlapping slow sine bands of palette colours drifting at different
    # rates — a soft aurora shimmer.
    pal = _pal_array(p.get("palette"))
    s = _spd(p)
    idx = np.arange(n) / max(1, n)
    out = np.zeros((n, 3), dtype=np.float32)
    wsum = np.zeros(n, dtype=np.float32)
    for j in range(len(pal)):
        k = 1.0 + j                                   # each band a bit tighter
        w = 0.5 + 0.5 * np.sin(2 * math.pi * (idx * k + t * (0.02 + 0.012 * j) * s))
        w = w ** 2
        out += pal[j][None, :] * w[:, None]
        wsum += w
    return out / np.maximum(wsum[:, None], 1e-3)


ANIMATIONS = {
    "solid":          anim_solid,
    "pulse":          anim_pulse,
    "gradient_orbit": anim_gradient_orbit,
    "comet":          anim_comet,
    "breathe_wander": anim_breathe_wander,
    "wave":           anim_wave,
    "twinkle":        anim_twinkle,
    "aurora":         anim_aurora,
}


class BorderController:
    def __init__(self, config) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._strips: list[_SpiStrip] = []
        self._total = 0
        self._running = False
        self._thread = None
        self._t0 = 0.0
        self._rng = np.random.default_rng(1234)
        self._anim_params: dict = {}     # scratch for stateful anims (twinkle)
        self._build_strips()

    # ── Config ──────────────────────────────────────────────
    def _cfg(self) -> dict:
        return (self._config.get("border") or {})

    def enabled(self) -> bool:
        return bool(self._cfg().get("enabled"))

    def _build_strips(self) -> None:
        with self._lock:
            for s in self._strips:
                s.close()
            self._strips = []
            for seg in (self._cfg().get("segments") or []):
                spec = str(seg.get("spi", "1.0"))
                try:
                    bus, dev = (int(x) for x in spec.split("."))
                except ValueError:
                    bus, dev = 1, 0
                self._strips.append(_SpiStrip(bus, dev, seg.get("num", 0)))
            self._total = sum(s.num for s in self._strips)

    def reload(self) -> None:
        """Re-open strips after a segment change."""
        self._build_strips()
        self._anim_params = {}

    # ── Render loop ─────────────────────────────────────────
    def start(self) -> None:
        self._running = True
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="border")
        self._thread.start()
        logger.info("border controller started (enabled=%s, %d px across %d strip(s))",
                    self.enabled(), self._total, len(self._strips))

    def stop(self) -> None:
        self._running = False

    def render_frame(self, t_s: float, n: int, cfg: dict) -> np.ndarray:
        """Pure render → (n,3) uint8 RGB, brightness + gamma applied. Public
        so it's unit-testable without any SPI hardware."""
        name = cfg.get("animation", "pulse")
        fn = ANIMATIONS.get(name, anim_pulse)
        p = dict(cfg)
        p.update(self._anim_params)          # carry persistent anim state
        rgb = fn(t_s, n, p, self._rng)
        # persist any state the anim stashed under private keys (e.g. _tw)
        for k, v in p.items():
            if k.startswith("_"):
                self._anim_params[k] = v
        bright = max(0.0, min(1.0, float(cfg.get("brightness", 0.5))))
        rgb = np.clip(rgb, 0, 255) * bright
        out = rgb.astype(np.uint8)
        return _GAMMA[out]

    def _loop(self) -> None:
        cleared = False
        while self._running:
            cfg = self._cfg()
            fps = max(1.0, min(120.0, float(cfg.get("fps", 60))))
            if not cfg.get("enabled") or self._total <= 0:
                if not cleared:
                    self._blackout()
                    cleared = True
                time.sleep(0.2)
                continue
            cleared = False
            try:
                t_s = time.monotonic() - self._t0
                frame = self.render_frame(t_s, self._total, cfg)
                self._push(frame)
            except Exception:
                logger.exception("border: render error")
            time.sleep(1.0 / fps)

    def _push(self, frame: np.ndarray) -> None:
        order = self._cfg().get("color_order", "GRB")
        with self._lock:
            off = 0
            for s in self._strips:
                s.show(frame[off:off + s.num], order)
                off += s.num

    def _blackout(self) -> None:
        with self._lock:
            for s in self._strips:
                if s.num > 0:
                    s.show(np.zeros((s.num, 3), dtype=np.uint8))

    # ── Status (for the admin route) ────────────────────────
    def status(self) -> dict:
        with self._lock:
            strips = [{"spi": f"{s.bus}.{s.dev}", "num": s.num, "ok": s.ok}
                      for s in self._strips]
        return {
            "total": self._total,
            "strips": strips,
            "hardware": any(st["ok"] for st in strips),
            "animations": list(ANIMATIONS.keys()),
            "palettes": PALETTE_PRESETS,
            "color_orders": list(COLOR_ORDERS.keys()),
        }
