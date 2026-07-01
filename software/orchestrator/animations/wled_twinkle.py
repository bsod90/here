"""Twinkle — ported verbatim from WLED `mode_twinkle` (1D mapped onto the
matrix the default way: index i → pixel (i%44, i//44)).

LEDs light at random positions and accumulate until a maximum count, then
all reset to a new random set — a field of slowly-fading twinkles. Each
lit pixel is colored by the palette at its position.

Knobs (WLED 0..255): speed = cycle time, intensity = how many on at once.
"""
from __future__ import annotations

import random

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "rainbow",
    "speed": 80,
    "intensity": 128,
    "brightness": 1.0,
    "fade_in_s": 1.5,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    flat = buf.reshape(TOTAL, 3)
    if "rng" not in st:
        st["rng"] = random.Random()
        st["aux0"] = 0
        st["aux1"] = st["rng"].randint(0, 0xFFFF)
        st["step"] = -1
    w.fade_out(buf, 224)

    speed = int(p["speed"])
    cycle_time = 20 + (255 - speed) * 5
    it = int(now // cycle_time)
    if it != st["step"]:
        max_on = 1 + int(p["intensity"]) * (TOTAL - 1) // 255
        if st["aux0"] >= max_on:
            st["aux0"] = 0
            st["aux1"] = st["rng"].randint(0, 0xFFFF)
        st["aux0"] += 1
        st["step"] = it

    pal = palettes.as_array(p["palette"])
    prng = st["aux1"]
    for _ in range(st["aux0"]):
        prng = ((prng * 2053) + 13849) & 0xFFFF
        j = (TOTAL * prng) >> 16
        hue = j * 255 / (TOTAL - 1)
        flat[j] = w.from_palette(pal, hue, 255.0, wrap=True)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
