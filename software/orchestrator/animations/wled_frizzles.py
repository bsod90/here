"""Frizzles — ported from WLED `mode_2DFrizzles`.

Eight additive dots, each on a slightly different beatsin frequency, trace
dense overlapping Lissajous curves over a lightly-fading, blurred buffer —
a lively scribble of light. The user earmarked this one for the "bench
wakes up" moment, so its defaults are a touch livelier.

Knobs (WLED 0..255):
  speed     — X frequency
  intensity — Y frequency
  custom1   — blur
"""
from __future__ import annotations

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "rainbow",
    "speed": 128,
    "intensity": 128,
    "custom1": 64,       # blur
    "brightness": 1.0,
    "fade_in_s": 1.5,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    w.fade_to_black(buf, 16)

    cols, rows = w.COLS, w.ROWS
    pal = palettes.as_array(p["palette"])
    sp = float(p["speed"]) / 8.0
    inten = float(p["intensity"]) / 8.0
    hue = w.beatsin8(12, now, 0, 255)
    color = w.from_palette(pal, float(hue), 255.0, wrap=False)
    for i in range(8, 0, -1):
        x = int(w.beatsin8(sp + i, now, 0, cols - 1))
        y = int(w.beatsin8(inten - i, now, 0, rows - 1))
        w.add_xy(buf, x, y, color)
    w.blur2d(buf, int(p["custom1"]) >> 3)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
