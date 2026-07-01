"""Plasma Ball — ported from WLED `mode_2DPlasmaball`.

Crackling plasma filaments: two 1D noise fields warp a set of diagonal /
edge "lightning" bands that ripple and re-form. Additive over a fading
buffer so the filaments leave soft trails. Defaults are tuned slower and
smoother than stock (the user's note) — gentle for meditation.

Knobs (WLED 0..255):
  speed     — filament drift rate
  custom1   — fade / trail length (lower = longer trails)
  custom2   — blur (smoothness)
"""
from __future__ import annotations

import numpy as np

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "lava",
    "speed": 90,         # slower than stock for a calm crackle
    "custom1": 24,       # fade (>>2 → small = long trails)
    "custom2": 160,      # blur (>>5 → smoothing)
    "brightness": 1.0,
    "fade_in_s": 2.0,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    w.fade_to_black(buf, int(p["custom1"]) >> 2)

    cols, rows = w.COLS, w.ROWS
    t = (now * 8.0) / max(1.0, 256.0 - float(p["speed"]))
    i = np.arange(cols)
    j = np.arange(rows)
    # Per-column and per-row noise displacements (integer map, like WLED).
    tv_col = w.inoise8(i * 30, np.full(cols, t), np.full(cols, t)).astype(np.int64)
    tm_col = (tv_col * (cols - 1)) // 255
    tv_row = w.inoise8(np.full(rows, t), j * 30, np.full(rows, t)).astype(np.int64)
    tm_row = (tv_row * (rows - 1)) // 255

    I, J = np.meshgrid(i, j)                     # (rows, cols)
    TMrow = tm_row[:, None]                      # depends on row j
    TMcol = tm_col[None, :]                      # depends on col i
    x = I + TMrow - cols // 2
    y = J + TMcol - cols // 2
    cx = I + TMrow
    cy = J + TMcol
    band = ((np.abs(x - y) < 2) |
            (np.abs(cols - 1 - x - y) < 2) |
            (cols - cx == 0) | (cols - 1 - cx == 0) |
            (rows - cy == 0) | (rows - 1 - cy == 0))

    pal = palettes.as_array(p["palette"])
    hue = w.beat8(5.0, now)                       # slow hue cycle
    bright = tv_col[None, :].astype(np.float32) * np.ones((rows, 1), dtype=np.float32)
    col = w.from_palette(pal, np.full((rows, cols), hue, np.float32), bright, wrap=False)
    buf += col * band[..., None]
    np.minimum(buf, 255.0, out=buf)
    w.blur2d(buf, int(p["custom2"]) >> 5)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
