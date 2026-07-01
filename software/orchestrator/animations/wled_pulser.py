"""Pulser — ported from WLED `mode_2DPulser`.

A single bright dot sweeps horizontally while its vertical position is the
sum of three sine harmonics — a bouncing comet that smears into a glowing
ribbon via a light fade + blur. Nice slow "intro" texture.

Knobs (WLED 0..255):
  speed     — sweep rate
  intensity — trail length + glow (fade & blur amount)
"""
from __future__ import annotations

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "cold",
    "speed": 80,
    "intensity": 160,    # trail/glow
    "brightness": 1.0,
    "fade_in_s": 2.0,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)

    inten = int(p["intensity"])
    w.fade_to_black(buf, 8 - (inten >> 5))
    cols, rows = w.COLS, w.ROWS
    a = now / max(1.0, 18.0 - float(p["speed"]) / 16.0)
    x = int(a / 14.0) % cols
    s = float(w.sin8(a * 5.0) + w.sin8(a * 4.0) + w.sin8(a * 2.0))   # 0..765
    y = int((rows - 1) - s / 765.0 * (rows - 1))
    pal = palettes.as_array(p["palette"])
    color = w.from_palette(pal, y / max(1, rows - 1) * 255.0, 255.0, wrap=False)
    w.set_xy(buf, x, y, color)
    w.blur2d(buf, inten >> 4)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
