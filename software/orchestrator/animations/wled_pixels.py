"""Pixels — ported verbatim from WLED `mode_pixels` (1D mapped onto the
matrix: index i → (i%44, i//44)).

A sound-reactive effect in WLED; HERE has no live audio, so it's driven by
a gentle synthetic "volume" (a slow sine swell, matching WLED's BeatSin
sound simulation). Random pixels light, colored from a rolling history of
the volume and brightened by the current level, over a fading field.

Knobs (WLED 0..255): speed = fade rate, intensity = number of pixels.
"""
from __future__ import annotations

import random

import numpy as np

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "ocean",
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
        st["vals"] = np.zeros(32, np.float32)
    rng = st["rng"]

    # Synthetic volume (WLED BeatSin sim: volumeSmth ≈ fftResult[8]).
    vol = float(w.beatsin8(13, now, 0, 255))
    st["vals"][int(now) % 32] = vol
    w.fade_out(buf, 64 + int(p["speed"]) // 2)

    pal = palettes.as_array(p["palette"])
    for i in range(int(p["intensity"]) // 8):
        loc = rng.randrange(TOTAL)
        col = w.from_palette(pal, (st["vals"][i % 32] + i * 4) % 256.0, 255.0, wrap=True)
        flat[loc] = col * (vol / 255.0)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
