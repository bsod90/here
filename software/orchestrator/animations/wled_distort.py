"""Distortion Waves — ported from WLED `mode_2Ddistortionwaves`.

The original combines a nested-cosine "distort" field with a moving radial
wave (distance² from a wandering center) to make slow, warped, interfering
bands. WLED paints those into three independent, fully-saturated RGB
channels — which on hardware reads as harsh, high-contrast rainbow. Here we
keep the warped-band MOTION but recolor it through one of our soft palettes
(default `dusk` — muted rose/purple/indigo), blending two phase-shifted
lookups so the bands keep gentle multi-tone life without the contrast.

Knobs (WLED 0..255):
  speed     — wave drift / oscillator rate  (mapped /32 → 0..7)
  intensity — spatial frequency ("scale")    (mapped /32 → 0..7)
  palette   — which soft colour set to flow through
"""
from __future__ import annotations

import numpy as np

import palettes

from . import _wled as w

DEFAULTS = {
    "palette": "dusk",   # soft, low-contrast by default (try pastel / lava / cold)
    "speed": 48,         # 0..255 → /32 = 1
    "intensity": 64,     # 0..255 → /32 = 2 (scale)
    "blue_off": True,    # turn OFF (black) the blue/indigo pixels, leaving only the
                         # warm bands lit — a warm pattern on black
    "blue_off_soft": 40.0,   # how gradual the blue→off cutoff is (bigger = softer edge)
    "brightness": 0.9,
    "fade_in_s": 2.5,
}


# The whole effect is driven by `strip.now`; divide the animation clock to
# slow it down uniformly (1000× slower than stock — a glacial drift).
_TIME_DIV = 1000.0


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    real = w.elapsed(st, time_ms)
    now = real / _TIME_DIV               # slowed animation clock

    speed = float(p["speed"]) / 32.0
    scale = max(1.0, float(p["intensity"]) / 32.0)
    wgt = 2.0
    a = now / 32.0
    a2 = a / 2.0
    a3 = a / 3.0
    X, Y = w.coords()
    # Moving centers (one per channel) — beatsin8 × scale.
    cx = float(w.beatsin8(10 - speed, now, 0, w.COLS - 1)) * scale
    cy = float(w.beatsin8(12 - speed, now, 0, w.ROWS - 1)) * scale
    cx1 = float(w.beatsin8(13 - speed, now, 0, w.COLS - 1)) * scale
    cy1 = float(w.beatsin8(15 - speed, now, 0, w.ROWS - 1)) * scale
    cx2 = float(w.beatsin8(17 - speed, now, 0, w.COLS - 1)) * scale
    cy2 = float(w.beatsin8(14 - speed, now, 0, w.ROWS - 1)) * scale
    xoffs = (X + 1.0) * scale          # xoffs accumulates `scale` per column
    yoffs = (Y + 1.0) * scale

    x8 = X * 8.0
    y8 = Y * 8.0
    rdist = w.cos8(w.cos8(x8 + a) + w.cos8(y8 - a2) + a3) / 2.0
    gdist = w.cos8(w.cos8(x8 - a2) + w.cos8(y8 + a3) + a + 32.0) / 2.0
    bdist = w.cos8(w.cos8(x8 + a3) + w.cos8(y8 - a) + a2 + 64.0) / 2.0

    valR = rdist + wgt * (a - ((xoffs - cx) ** 2 + (yoffs - cy) ** 2) / 128.0)
    valG = gdist + wgt * (a2 - ((xoffs - cx1) ** 2 + (yoffs - cy1) ** 2) / 128.0)
    valB = bdist + wgt * (a3 - ((xoffs - cx2) ** 2 + (yoffs - cy2) ** 2) / 128.0)

    # Recolor the warped fields through a soft palette instead of dumping them
    # straight into saturated R/G/B. Two phase-shifted indices are blended so
    # the bands keep some multi-tone movement while staying gentle and
    # low-contrast.
    pal = palettes.as_array(p["palette"])
    idx_a = w.cos8(valR)
    idx_b = w.cos8(valG + 110.0)
    img = (0.6 * w.from_palette(pal, idx_a, 255.0, wrap=True)
           + 0.4 * w.from_palette(pal, idx_b, 255.0, wrap=True)).astype(np.float32)

    # Turn off the blue LEDs: where blue overtakes red the pixel fades to black,
    # so only the warm (rose/coral) bands stay lit. The ramp over `blue_off_soft`
    # keeps the edge gentle instead of a hard cut.
    if p.get("blue_off", True):
        warmth = img[..., 0] - img[..., 2]          # red minus blue
        soft = max(1.0, float(p.get("blue_off_soft", 40.0)))
        mask = np.clip(warmth / soft, 0.0, 1.0)
        img = img * mask[..., np.newaxis]

    w.finalize(frame, img, real / 1000.0, p)
