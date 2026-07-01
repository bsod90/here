"""Noise 2D — ported from WLED `mode_2Dnoise`.

The simplest of the noise family: every pixel is just the active palette
sampled by 3D Perlin noise. `scale` sets the blob size, `speed` scrolls
the noise field in time. Vectorized over the whole 44×44 grid in one
numpy call, so it's cheap (the original was flagged "pricy" on the ESP —
not an issue here).

Knobs mirror WLED's sliders (0..255) so ports stay faithful:
  speed     — how fast the field drifts (z-scroll rate)
  intensity — feature SCALE; small = big smooth blobs, large = grainy
"""
from __future__ import annotations

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "ocean",
    "speed": 40,         # 0..255 (drift rate)
    "intensity": 30,     # 0..255 (scale; +2 → units/pixel)
    "brightness": 1.0,
    "fade_in_s": 2.0,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)

    pal = palettes.as_array(p["palette"])
    X, Y = w.coords()
    scale = float(p["intensity"]) + 2.0
    # z-scroll: WLED uses now/(16 - speed/16); keep the shape, guard the
    # divisor so high speed stays sane.
    z = now / max(0.5, 16.0 - float(p["speed"]) / 16.0)
    hue = w.inoise8(X * scale, Y * scale, z)          # (rows, cols) 0..255
    img = w.from_palette(pal, hue, 255.0, wrap=False)
    w.finalize(frame, img, now / 1000.0, p)
