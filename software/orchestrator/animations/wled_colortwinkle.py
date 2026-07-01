"""Colortwinkles — ported verbatim from WLED `mode_colortwinkle` (1D mapped
onto the matrix: index i → (i%44, i//44)).

Each pixel, once spawned, brightens itself up from a dim palette color to
full, then fades back to black on its own — a shimmer of self-cycling
twinkles. New ones spawn at random dark pixels.

Knobs (WLED 0..255): speed = fade speed, intensity = spawn rate.
"""
from __future__ import annotations

import random

import numpy as np

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "rainbow",
    "speed": 80,
    "intensity": 64,
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
        st["up"] = np.zeros(TOTAL, dtype=bool)      # per-pixel fade-up flag
    up = st["up"]
    rng = st["rng"]

    speed = int(p["speed"])
    fade_up = 8 + (speed >> 2)
    fade_down = 8 + (speed >> 3)

    # Fade-up pixels brighten (saturating); when a channel maxes, flip them
    # to fade-down. Fade-down pixels scale toward black.
    inc = np.floor(flat * fade_up / 256.0) + (flat > 0)        # nscale8_video
    up_new = np.minimum(flat + inc, 255.0)
    maxed = up & (up_new >= 255.0).any(axis=1)
    up[maxed] = False
    down_new = flat * ((255 - fade_down) / 256.0)
    flat[:] = np.where(up[:, None], up_new, down_new)

    # Spawn at random dark pixels.
    pal = palettes.as_array(p["palette"])
    for _ in range(TOTAL // 50 + 1):
        if rng.randint(0, 255) <= int(p["intensity"]):
            for _t in range(5):
                i = rng.randrange(TOTAL)
                if not flat[i].any():
                    flat[i] = w.from_palette(pal, rng.randint(0, 255), 64.0, wrap=False)
                    up[i] = True
                    break
    w.finalize(frame, buf.copy(), now / 1000.0, p)
