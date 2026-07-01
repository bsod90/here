"""WLED-port primitives — faithful, vectorized reimplementations of the
FastLED / WLED math that the ported 2D effects lean on.

The HERE animations all share one render contract:

    render(frame, time_ms, params, state)

where `frame` is a `TOTAL*3` bytearray in RGB order, linear index
`row*GRID + col` (index 0 = top-left, see grid.py). Inside an effect we
work with a float image of shape **(rows, cols, 3)** and flush it with
`write_frame(frame, img)` at the end.

What lives here (so each effect file stays short and reads like the WLED
source it was ported from):

  * `sin8` / `cos8` / `sin16` / `cos16` — phase is 0..255 (resp. 0..65535)
    = one full turn, output 0..255 (resp. 0..65535), midpoint at half.
    Because every value only depends on the phase *modulo* its period,
    you can nest them in float without worrying about uint8 wraparound
    (e.g. Hiphotic's `sin8(cos8(..)+sin8(..))` is exact in float).
  * `beatsin8` / `beatsin16` — a `bpm`-rate sine oscillator anchored to a
    millisecond clock, matching FastLED's `*280>>16` beat timing so a
    port keeps the original's tempo.
  * `inoise8` / `inoise16` — 3D Perlin gradient noise, normalized to the
    same reduced 0..255 / 0..65535 span WLED's `inoise` produces. The
    *coordinate scale* matches WLED (divide raw args by 256 / 65536 to
    reach lattice units) so feature sizes land where the effect expects.
  * `from_palette` — `ColorFromPalette`: sample a gradient (our palettes,
    any number of anchors) at index 0..255 with optional brightness and
    the PALETTE_SOLID_WRAP seam-clip.
  * `blur2d` / `fade_to_black` / `gamma8` / `wu_splat` — the framebuffer
    helpers (separable blur, trail fade, gamma LUT, anti-aliased plot).
  * `XY`, `coords()`, `write_frame`, `get_buf` — geometry + buffer glue.

Everything is numpy-vectorized; 44×44 = 1936 px renders comfortably at
the engine's frame rate on the Pi.
"""
from __future__ import annotations

import numpy as np

from grid import GRID, TOTAL

# Matrix is square; expose rows/cols for clarity in ported code.
ROWS = COLS = GRID


# ── Geometry ────────────────────────────────────────────────────────
# Per-pixel integer coordinates as (rows, cols) meshgrids, computed once.
_YY, _XX = np.meshgrid(np.arange(ROWS), np.arange(COLS), indexing="ij")
_XX = _XX.astype(np.float32)        # column index per pixel
_YY = _YY.astype(np.float32)        # row index per pixel


def coords():
    """(X, Y) float meshgrids of shape (rows, cols) — column & row index."""
    return _XX, _YY


def XY(x: int, y: int) -> int:
    """WLED's row-major XY → linear index (wraps modulo, like Segment::XY)."""
    return (int(x) % COLS) + (int(y) % ROWS) * COLS


def write_frame(frame: bytearray, img: np.ndarray) -> None:
    """Flush an (rows, cols, 3) float image into the RGB byte frame."""
    np.clip(img, 0.0, 255.0, out=img)
    frame[:] = img.astype(np.uint8).reshape(-1).tobytes()


def get_buf(state: dict, key: str = "buf") -> np.ndarray:
    """Persistent (rows, cols, 3) float framebuffer kept in `state` — for
    trail effects (fadeToBlackBy / additive draws) that need last frame."""
    buf = state.get(key)
    if buf is None or buf.shape != (ROWS, COLS, 3):
        buf = np.zeros((ROWS, COLS, 3), dtype=np.float32)
        state[key] = buf
    return buf


# ── 8/16-bit trig (phase 0..255 / 0..65535 = full circle) ───────────
def sin8(theta) -> np.ndarray:
    """FastLED sin8: phase 0..255 = 2π, output 0..255 centered at ~128."""
    return 127.5 + 127.5 * np.sin(np.asarray(theta, dtype=np.float32) * (np.pi / 128.0))


def cos8(theta) -> np.ndarray:
    return sin8(np.asarray(theta, dtype=np.float32) + 64.0)


def sin16(theta) -> np.ndarray:
    """phase 0..65535 = 2π, output −32767..32767."""
    return 32767.0 * np.sin(np.asarray(theta, dtype=np.float32) * (np.pi / 32768.0))


def cos16(theta) -> np.ndarray:
    return sin16(np.asarray(theta, dtype=np.float32) + 16384.0)


def triwave8(theta) -> np.ndarray:
    """FastLED triwave8: triangle 0..255 over phase 0..255."""
    t = np.asarray(theta, dtype=np.float32) % 256.0
    return np.where(t < 128.0, t * 2.0, (255.0 - t) * 2.0)


def scale8(v, s) -> np.ndarray:
    """FastLED scale8: v * s / 256."""
    return np.asarray(v, dtype=np.float32) * (np.asarray(s, dtype=np.float32) / 256.0)


# ── beatsin: bpm-rate oscillator on a ms clock ──────────────────────
def beat8(bpm: float, now_ms: float, tb: float = 0.0) -> float:
    """Sawtooth 0..255; one full ramp per beat (≈ 60000/bpm ms)."""
    return ((now_ms - tb) * bpm * 280.0 / 256.0) % 256.0


def beatsin8(bpm, now_ms, lo=0.0, hi=255.0, tb=0.0, phase=0.0):
    """sin8 oscillator at `bpm` beats/min, mapped into [lo, hi]."""
    s = sin8(beat8(bpm, now_ms, tb) + phase)           # 0..255
    return lo + s * (np.asarray(hi - lo, dtype=np.float32) / 256.0)


def beatsin16(bpm, now_ms, lo=0.0, hi=65535.0, tb=0.0, phase=0.0):
    beat = ((now_ms - tb) * bpm * 280.0 / 256.0) % 256.0
    s = sin8(beat + phase)                              # reuse 8-bit sine shape
    return lo + s * (np.asarray(hi - lo, dtype=np.float32) / 256.0)


def beatsin88(bpm88, now_ms, lo=0.0, hi=255.0, tb=0.0):
    """Oscillator with BPM given in Q8.8 fixed point (bpm = bpm88/256),
    as FastLED's beatsin88 — used by Juggle. Returns lo..hi."""
    cycles = (now_ms - tb) / 60000.0 * (bpm88 / 256.0)
    s = 0.5 + 0.5 * np.sin(2.0 * np.pi * cycles)
    return lo + (hi - lo) * s


# ── FastLED 3.6.0 noise (bit-exact) ─────────────────────────────────
# WLED's inoise is pure FastLED (built with FASTLED_NOISE_FIXED=1 /
# FASTLED_SCALE8_FIXED=1). Porting it FAITHFULLY matters — a generic float
# Perlin looks visibly different: FastLED uses an int8 gradient lattice and
# maps the result with `qadd8(raw+64, raw+64)` (a doubling + saturation),
# not a simple `+128`. The integer math below reproduces it exactly.
# 257-entry permutation table (last entry repeats p[0] so P(x+1) at x=255
# stays in range), accessed as P(x).
_P = np.array([
    151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225,
    140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 21, 10, 23, 190, 6, 148,
    247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 11, 32,
    57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175,
    74, 165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122,
    60, 211, 133, 230, 220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 143, 54,
    65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208, 89, 18, 169,
    200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3, 64,
    52, 217, 226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85, 212,
    207, 206, 59, 227, 47, 16, 58, 17, 182, 189, 28, 42, 223, 183, 170, 213,
    119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155, 167, 43, 172, 9,
    129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185, 112, 104,
    218, 246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191, 179, 162, 241,
    81, 51, 145, 235, 249, 14, 239, 107, 49, 192, 214, 31, 181, 199, 106, 157,
    184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150, 254, 138, 236, 205, 93,
    222, 114, 67, 29, 24, 72, 243, 141, 128, 195, 78, 66, 215, 61, 156, 180,
    151,
], dtype=np.int64)


def _scale8(i, s):
    return ((i * (1 + s)) >> 8) & 0xFF


def _scale16(i, s):
    return ((i * (1 + s)) >> 16) & 0xFFFF


def _ease8(t):
    t = t & 0xFF
    j = np.where(t & 0x80, 255 - t, t)
    jj2 = _scale8(j, j) << 1
    return np.where(t & 0x80, 255 - jj2, jj2)


def _ease16(t):
    t = t & 0xFFFF
    j = np.where(t & 0x8000, 65535 - t, t)
    jj2 = _scale16(j, j) << 1
    return np.where(t & 0x8000, 65535 - jj2, jj2)


def _grad8(h, x, y, z):
    h = h & 0xF
    u = np.where(h & 8, y, x)
    v = np.where(h < 4, y, np.where((h == 12) | (h == 14), x, z))
    u = np.where(h & 1, -u, u)
    v = np.where(h & 2, -v, v)
    return (u >> 1) + (v >> 1) + (u & 1)            # avg7


def _grad16(h, x, y, z):
    h = h & 0xF
    u = np.where(h < 8, x, y)
    v = np.where(h < 4, y, np.where((h == 12) | (h == 14), x, z))
    u = np.where(h & 1, -u, u)
    v = np.where(h & 2, -v, v)
    return (u >> 1) + (v >> 1) + (u & 1)            # avg15


def _lerp7by8(a, b, frac):
    scaled = _scale8(np.abs(b - a) & 0xFF, frac)
    return np.where(b > a, a + scaled, a - scaled)


def _lerp15by16(a, b, frac):
    scaled = _scale16(np.abs(b - a) & 0xFFFF, frac)
    return np.where(b > a, a + scaled, a - scaled)


def _as_int(v, mask):
    return (np.asarray(v).astype(np.int64)) & mask


def _inoise8_raw(x, y, z):
    """int8 −64..+64 (FastLED inoise8_raw 3D)."""
    x = _as_int(x, 0xFFFF); y = _as_int(y, 0xFFFF); z = _as_int(z, 0xFFFF)
    x, y, z = np.broadcast_arrays(x, y, z)
    P = _P
    X = (x >> 8) & 0xFF; Y = (y >> 8) & 0xFF; Z = (z >> 8) & 0xFF
    A = (P[X] + Y) & 0xFF
    AA = (P[A] + Z) & 0xFF; AB = (P[A + 1] + Z) & 0xFF
    B = (P[X + 1] + Y) & 0xFF
    BA = (P[B] + Z) & 0xFF; BB = (P[B + 1] + Z) & 0xFF
    u = _ease8(x & 0xFF); v = _ease8(y & 0xFF); w = _ease8(z & 0xFF)
    xx = ((x & 0xFF) >> 1) & 0x7F
    yy = ((y & 0xFF) >> 1) & 0x7F
    zz = ((z & 0xFF) >> 1) & 0x7F
    N = 0x80
    X1 = _lerp7by8(_grad8(P[AA], xx, yy, zz), _grad8(P[BA], xx - N, yy, zz), u)
    X2 = _lerp7by8(_grad8(P[AB], xx, yy - N, zz), _grad8(P[BB], xx - N, yy - N, zz), u)
    X3 = _lerp7by8(_grad8(P[AA + 1], xx, yy, zz - N), _grad8(P[BA + 1], xx - N, yy, zz - N), u)
    X4 = _lerp7by8(_grad8(P[AB + 1], xx, yy - N, zz - N), _grad8(P[BB + 1], xx - N, yy - N, zz - N), u)
    Y1 = _lerp7by8(X1, X2, v)
    Y2 = _lerp7by8(X3, X4, v)
    return _lerp7by8(Y1, Y2, w)


def _inoise16_raw3(x, y, z):
    x = _as_int(x, 0xFFFFFFFF); y = _as_int(y, 0xFFFFFFFF); z = _as_int(z, 0xFFFFFFFF)
    x, y, z = np.broadcast_arrays(x, y, z)
    P = _P
    X = (x >> 16) & 0xFF; Y = (y >> 16) & 0xFF; Z = (z >> 16) & 0xFF
    A = (P[X] + Y) & 0xFF
    AA = (P[A] + Z) & 0xFF; AB = (P[A + 1] + Z) & 0xFF
    B = (P[X + 1] + Y) & 0xFF
    BA = (P[B] + Z) & 0xFF; BB = (P[B + 1] + Z) & 0xFF
    u = _ease16(x & 0xFFFF); v = _ease16(y & 0xFFFF); w = _ease16(z & 0xFFFF)
    xx = ((x & 0xFFFF) >> 1) & 0x7FFF
    yy = ((y & 0xFFFF) >> 1) & 0x7FFF
    zz = ((z & 0xFFFF) >> 1) & 0x7FFF
    N = 0x8000
    X1 = _lerp15by16(_grad16(P[AA], xx, yy, zz), _grad16(P[BA], xx - N, yy, zz), u)
    X2 = _lerp15by16(_grad16(P[AB], xx, yy - N, zz), _grad16(P[BB], xx - N, yy - N, zz), u)
    X3 = _lerp15by16(_grad16(P[AA + 1], xx, yy, zz - N), _grad16(P[BA + 1], xx - N, yy, zz - N), u)
    X4 = _lerp15by16(_grad16(P[AB + 1], xx, yy - N, zz - N), _grad16(P[BB + 1], xx - N, yy - N, zz - N), u)
    Y1 = _lerp15by16(X1, X2, v)
    Y2 = _lerp15by16(X3, X4, v)
    return _lerp15by16(Y1, Y2, w)


def _inoise16_raw2(x, y):
    x = _as_int(x, 0xFFFFFFFF); y = _as_int(y, 0xFFFFFFFF)
    x, y = np.broadcast_arrays(x, y)
    P = _P
    X = (x >> 16) & 0xFF; Y = (y >> 16) & 0xFF
    A = (P[X] + Y) & 0xFF; AA = P[A]; AB = P[A + 1]
    B = (P[X + 1] + Y) & 0xFF; BA = P[B]; BB = P[B + 1]
    u = _ease16(x & 0xFFFF); v = _ease16(y & 0xFFFF)
    xx = ((x & 0xFFFF) >> 1) & 0x7FFF
    yy = ((y & 0xFFFF) >> 1) & 0x7FFF
    N = 0x8000
    X1 = _lerp15by16(_grad16(P[AA], xx, yy, 0), _grad16(P[BA], xx - N, yy, 0), u)
    X2 = _lerp15by16(_grad16(P[AB], xx, yy - N, 0), _grad16(P[BB], xx - N, yy - N, 0), u)
    return _lerp15by16(X1, X2, v)


def inoise8(x, y=0, z=0) -> np.ndarray:
    """FastLED inoise8 (3D): args 8.8 (lattice cell 256). Output 0..255.
    `n += 64` is int8 then `qadd8(n,n)` treats n as uint8 — the `& 0xFF`
    reproduces that reinterpret (so a strongly-negative raw saturates to
    255, exactly like the firmware)."""
    n = (_inoise8_raw(x, y, z) + 64) & 0xFF
    return np.minimum(n + n, 255).astype(np.float32)


def inoise8_raw(x, y=0, z=0) -> np.ndarray:
    """Signed FastLED inoise8_raw (−64..+64) — for bump/height maps."""
    return _inoise8_raw(x, y, z).astype(np.float32)


def inoise16(x, y=0, z=None) -> np.ndarray:
    """FastLED inoise16. Two args → 2D form (+17308,×484>>8); three →
    3D form (+19052,×440>>8). Output 0..65535."""
    if z is None:
        out = ((_inoise16_raw2(x, y) + 17308) * 484) >> 8
    else:
        out = ((_inoise16_raw3(x, y, z) + 19052) * 440) >> 8
    return np.clip(out, 0, 65535).astype(np.float32)


# ── Palette sampling (ColorFromPalette) ─────────────────────────────
def from_palette(pal: np.ndarray, index, brightness=255.0,
                 wrap: bool = True) -> np.ndarray:
    """Sample a gradient `pal` (k,3) cyclically at `index` (0..255, any
    shape) → (..., 3) float RGB. `brightness` scales 0..255. `wrap=True`
    replicates PALETTE_SOLID_WRAP (clip the wrap seam by ×240/256)."""
    idx = np.asarray(index, dtype=np.float32)
    if wrap:
        idx = idx * (240.0 / 256.0)
    k = len(pal)
    u = (idx % 256.0) / 256.0 * k
    i0 = np.floor(u).astype(np.int32) % k
    i1 = (i0 + 1) % k
    f = (u - np.floor(u))[..., np.newaxis]
    col = pal[i0] * (1.0 - f) + pal[i1] * f
    b = np.asarray(brightness, dtype=np.float32)
    if b.ndim:
        b = b[..., np.newaxis]
    return col * (b / 255.0)


def abs8(v) -> np.ndarray:
    """FastLED abs8: the argument is truncated to int8 FIRST, then abs'd.
    That truncation matters — e.g. a byte-wrap jump of −224 reads as
    int8(+32), so |·| stays small where a plain abs() would explode
    (Sun Radiation's black-contour bug)."""
    v8 = ((np.asarray(v).astype(np.int64) + 128) & 0xFF) - 128
    return np.abs(v8).astype(np.float32)


def heat_color(temp) -> np.ndarray:
    """FastLED HeatColor: 0..255 → black→red→orange→yellow→white (...,3)."""
    t = np.clip(np.asarray(temp, dtype=np.float32), 0, 255)
    t192 = (t * 191.0 / 256.0).astype(np.int32)
    ramp = ((t192 & 0x3F) << 2).astype(np.float32)
    r = np.where(t192 & 0x80, 255.0, np.where(t192 & 0x40, 255.0, ramp))
    g = np.where(t192 & 0x80, 255.0, np.where(t192 & 0x40, ramp, 0.0))
    b = np.where(t192 & 0x80, ramp, 0.0)
    return np.stack([r, g, b], axis=-1)


def chsv(h, s=255, v=255) -> np.ndarray:
    """FastLED `hsv2rgb_rainbow` (CHSV→CRGB) — the warped-yellow rainbow WLED
    actually uses (NOT a textbook HSV). h/s/v 0..255 → (...,3) float 0..255."""
    h = np.asarray(h, dtype=np.int64) & 0xFF
    sec = (h >> 5).astype(np.int64)                 # which of 8 segments
    offset8 = (h & 0x1F) << 3
    third = _scale8(offset8, 256 // 3)              # 0..85
    two3 = _scale8(offset8, (256 * 2) // 3)         # 0..170
    z = np.zeros_like(h)
    r = np.select(
        [sec == 0, sec == 1, sec == 2, sec == 3, sec == 4, sec == 5, sec == 6, sec == 7],
        [255 - third, 171 + z, 171 - two3, z, z, third, 85 + third, 170 + third])
    g = np.select(
        [sec == 0, sec == 1, sec == 2, sec == 3, sec == 4, sec == 5, sec == 6, sec == 7],
        [third, 85 + third, 170 + third, 255 - third, 171 - two3, z, z, z])
    b = np.select(
        [sec == 0, sec == 1, sec == 2, sec == 3, sec == 4, sec == 5, sec == 6, sec == 7],
        [z, z, z, third, 85 + two3, 255 - third, 171 - third, 85 - third])
    r = r.astype(np.float32); g = g.astype(np.float32); b = b.astype(np.float32)
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if np.any(s < 255):
        desat = 255.0 - s
        desat = desat * desat / 256.0              # scale8_video-ish
        sc = (255.0 - desat) / 256.0
        floor = desat
        r = r * sc + floor; g = g * sc + floor; b = b * sc + floor
    if np.any(v < 255):
        vv = (v * v) / 256.0 / 255.0
        r = r * vv; g = g * vv; b = b * vv
    return np.stack([r, g, b], axis=-1)


def hsv(h, s=255.0, v=255.0) -> np.ndarray:
    """Alias kept for callers — FastLED rainbow HSV."""
    return chsv(h, s, v)


# ── Framebuffer helpers ─────────────────────────────────────────────
def fade_to_black(buf: np.ndarray, fade: float) -> None:
    """fadeToBlackBy(fade): multiply every pixel by (255-fade)/256 in place."""
    buf *= (255.0 - float(fade)) / 256.0


def fade_out(buf: np.ndarray, rate: float) -> None:
    """Segment::fade_out toward black — `mappedRate = 1/(((255-rate)>>1)+1.1)`
    with a guaranteed ≥1 step so trails fully clear. In place."""
    r = (255 - int(rate)) >> 1
    mapped = 1.0 / (r + 1.1)
    buf -= buf * mapped + (buf > 0.0)
    np.clip(buf, 0.0, 255.0, out=buf)


def qsub8(v, s):
    return np.maximum(np.asarray(v, dtype=np.float32) - s, 0.0)


def qadd8(v, s):
    return np.minimum(np.asarray(v, dtype=np.float32) + s, 255.0)


def color_blend(c1, c2, blend) -> np.ndarray:
    """color_blend(c1,c2,blend/255) — c1,c2 are (3,) or (...,3); blend 0..255."""
    t = np.asarray(blend, dtype=np.float32) / 255.0
    if np.ndim(t):
        t = t[..., np.newaxis]
    return c1 * (1.0 - t) + c2 * t


def blur2d(buf: np.ndarray, amount: float, smear: bool = False) -> None:
    """Separable 3-tap blur, in place — faithful to FastLED blur2D weights
    (keep + 2·seep ≈ 1, slight energy loss). `amount` 0..255."""
    amount = max(0.0, min(255.0, float(amount)))
    if amount <= 0.0:
        return
    keep = 255.0 if smear else (255.0 - amount)
    seep = (amount / 4.0 if smear else amount / 2.0) / 256.0
    keep /= 256.0
    for axis in (0, 1):                       # rows then cols
        left = np.zeros_like(buf)
        right = np.zeros_like(buf)
        if axis == 0:
            left[1:, :, :] = buf[:-1, :, :]
            right[:-1, :, :] = buf[1:, :, :]
        else:
            left[:, 1:, :] = buf[:, :-1, :]
            right[:, :-1, :] = buf[:, 1:, :]
        buf[:] = keep * buf + seep * (left + right)


_GAMMA = (np.linspace(0.0, 1.0, 256) ** 2.4 * 255.0).astype(np.float32)


def gamma8(v) -> np.ndarray:
    """WLED gamma curve (≈2.4) on a 0..255 value (clamped)."""
    idx = np.clip(np.asarray(v, dtype=np.float32), 0, 255).astype(np.int32)
    return _GAMMA[idx]


def add_xy(buf: np.ndarray, x: int, y: int, color: np.ndarray) -> None:
    """Saturating additive plot (addPixelColorXY); out-of-range dropped."""
    if 0 <= x < COLS and 0 <= y < ROWS:
        buf[y, x] = np.minimum(buf[y, x] + color, 255.0)


def set_xy(buf: np.ndarray, x: int, y: int, color: np.ndarray) -> None:
    """Overwrite plot (setPixelColorXY); out-of-range dropped."""
    if 0 <= x < COLS and 0 <= y < ROWS:
        buf[y, x] = color


def elapsed(state: dict, time_ms: float) -> float:
    """Milliseconds since this effect (re)started — `strip.now` analogue.
    Anchored to the first frame so intros/fades replay on each trigger."""
    if "t0" not in state:
        state["t0"] = time_ms
    return time_ms - state["t0"]


def finalize(frame: bytearray, img: np.ndarray, now_s: float, p: dict) -> None:
    """Apply master brightness + a gentle fade-from-black at the start,
    then flush to the byte frame. Shared by every ported effect."""
    img *= float(p.get("brightness", 1.0))
    fi = float(p.get("fade_in_s", 1.5))
    if fi > 0.0:
        img *= min(1.0, now_s / fi)
    write_frame(frame, img)


def wu_splat(buf: np.ndarray, x: float, y: float, color: np.ndarray) -> None:
    """Anti-aliased additive plot at sub-pixel (x, y) — bilinear into the
    4 surrounding pixels (FastLED wu_pixel), saturating."""
    x0 = int(np.floor(x))
    y0 = int(np.floor(y))
    fx = x - x0
    fy = y - y0
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                        (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        px, py = x0 + dx, y0 + dy
        if 0 <= px < COLS and 0 <= py < ROWS:
            buf[py, px] = np.minimum(buf[py, px] + color * wgt, 255.0)
