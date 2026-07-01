"""Sun Radiation — ported from WLED `mode_2DSunradiation`.

A roiling solar surface: a moving Perlin height-field is bump-mapped with a
radial "specular" highlight (where the surface normal points outward), then
colored through the fire/black-body ramp. Warm and slow — a sun breathing.
Ignores the palette (uses HeatColor), so there's no palette knob.

Knobs (WLED 0..255):
  speed     — surface variance / feature frequency
  intensity — overall brightness of the heat
"""
from __future__ import annotations

import numpy as np

from . import _wled as w

DEFAULTS = {
    "speed": 60,         # variance
    "intensity": 128,    # brightness
    "brightness": 1.0,
    "fade_in_s": 2.5,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    cols, rows = w.COLS, w.ROWS

    some = float(p["speed"]) / 4.0
    t = now / 4.0
    # Height field over a +1 border so central differences stay in range.
    # `inoise8_raw/2` is stored in a uint8 in the firmware, so negative
    # values wrap — replicate that (it's part of the roiling look).
    jj, ii = np.meshgrid(np.arange(rows + 2), np.arange(cols + 2), indexing="ij")
    raw = w.inoise8_raw(ii * some, jj * some, t)
    bump = (np.trunc(raw / 2.0).astype(np.int64)) & 0xFF     # uint8 (rows+2, cols+2)

    nx = bump[1:-1, 2:] - bump[1:-1, :-2]                     # ∂/∂x  (rows, cols)
    ny = bump[2:, 1:-1] - bump[:-2, 1:-1]                     # ∂/∂y
    X, Y = w.coords()
    vlx = X - cols / 2.0
    vly = Y - rows / 2.0
    # abs8 truncates to int8 BEFORE the abs — where the bump byte wraps
    # (noise zero-crossings) the ±~224 jump must read as a small int8,
    # or the heat crushes to 0 and draws a black contour across the sun.
    difx = w.abs8(vlx * 7.0 - nx)
    dify = w.abs8(vly * 7.0 - ny)
    col = 255.0 - (difx * difx + dify * dify) / 8.0
    col = np.clip(col, 0.0, 255.0)
    divisor = 3.0 - float(p["intensity"]) / 128.0
    img = w.heat_color(col / max(0.1, divisor)).astype(np.float32)
    w.finalize(frame, img, now / 1000.0, p)
