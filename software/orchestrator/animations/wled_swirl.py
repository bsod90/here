"""Squared Swirl — ported from WLED `mode_2Dsquaredswirl`.

Mark Kriegsman's classic: three dots wander on independent beatsin
oscillators and are drawn additively in slowly-cycling palette colors.
A persistent fade + blur each frame smears them into flowing ribbons of
light. A lovely slow "beginning" texture.

Knobs (WLED 0..255):
  custom3   — blur (swirliness / smear length, 0..31)
"""
from __future__ import annotations

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "dusk",
    "custom3": 16,       # blur (0..31)
    "brightness": 1.0,
    "fade_in_s": 2.5,
}

_BORDER = 2


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)

    w.fade_to_black(buf, 24)
    w.blur2d(buf, int(p["custom3"]) >> 1)
    cols, rows = w.COLS, w.ROWS
    pal = palettes.as_array(p["palette"])
    i = int(w.beatsin8(19, now, _BORDER, cols - _BORDER))
    j = int(w.beatsin8(22, now, _BORDER, cols - _BORDER))
    k = int(w.beatsin8(17, now, _BORDER, cols - _BORDER))
    m = int(w.beatsin8(18, now, _BORDER, rows - _BORDER))
    n = int(w.beatsin8(15, now, _BORDER, rows - _BORDER))
    q = int(w.beatsin8(20, now, _BORDER, rows - _BORDER))
    w.add_xy(buf, i, m, w.from_palette(pal, now / 29.0 % 256.0, 255.0, wrap=False))
    w.add_xy(buf, j, n, w.from_palette(pal, now / 41.0 % 256.0, 255.0, wrap=False))
    w.add_xy(buf, k, q, w.from_palette(pal, now / 73.0 % 256.0, 255.0, wrap=False))
    w.finalize(frame, buf.copy(), now / 1000.0, p)
