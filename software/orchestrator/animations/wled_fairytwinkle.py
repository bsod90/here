"""Fairytwinkle — ported verbatim from WLED `mode_fairytwinkle` (1D mapped
onto the matrix: index i → (i%44, i//44)).

Every pixel runs its own slow rise/hold/fall lamp cycle with a stable,
deterministic per-pixel hue — a calm field of fairy lights breathing in and
out of existence (no random flicker; the whole field is recomputed each
frame from each lamp's phase).

Knobs (WLED 0..255): speed = cycle speed, intensity = how lit the field is.
"""
from __future__ import annotations

import numpy as np

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "pastel",
    "speed": 80,
    "intensity": 128,
    "brightness": 1.0,
    "fade_in_s": 1.5,
}


def _init(st):
    rng = np.random.default_rng()
    st["rng"] = rng
    st["start"] = np.zeros(TOTAL, np.int64)
    st["dur"] = np.zeros(TOTAL, np.int64)
    st["on"] = np.zeros(TOTAL, bool)
    # Stable per-pixel hue via the PRNG walk (deterministic every frame).
    hues = np.empty(TOTAL, np.int64)
    prng = 5100
    for f in range(TOTAL):
        last = prng
        diff = 0
        while diff < 0x4000:
            prng = ((prng * 2053) + 1384) & 0xFFFF
            diff = abs(prng - last)
        hues[f] = prng >> 8
    st["hues"] = hues


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    if "rng" not in st:
        _init(st)
    rng, start, dur, on = st["rng"], st["start"], st["dur"], st["on"]

    speed, intensity = int(p["speed"]), int(p["intensity"])
    rise_fall = 400 + (255 - speed) * 3
    max_dur = rise_fall // 100 + ((255 - intensity) >> 2) + 13 + ((255 - intensity) >> 1)
    now16 = int(now) & 0xFFFF

    state_time = (now16 - start) & 0xFFFF
    flip = state_time > dur * 100
    if flip.any():
        idx = np.where(flip)[0]
        init = dur[idx] == 0
        on[idx] = ~on[idx]
        on_now = on[idx]
        lim_on = max(1, 12 + ((255 - intensity) >> 1))
        lim_off = max(1, 3 + ((255 - speed) >> 6))
        new_dur = np.where(
            on_now,
            rise_fall // 100 + ((255 - intensity) >> 2) + rng.integers(0, lim_on, idx.size) + 1,
            rise_fall // 100 + rng.integers(0, lim_off, idx.size) + 1)
        start[idx] = now16
        if init.any():
            sub = np.where(init)[0]
            start[idx[sub]] = (now16 - rise_fall) & 0xFFFF
            new_dur[sub] = rise_fall // 100 + rng.integers(0, lim_on, sub.size) + 5
        dur[idx] = new_dur
        state_time = (now16 - start) & 0xFFFF

    dur[:] = np.where(on & (dur > max_dur), max_dur, dur)
    state_time = np.minimum(state_time, rise_fall)
    fadeprog = 255 - (state_time * 255) // rise_fall
    g = w.gamma8(fadeprog)
    bri = np.where(on, 255.0 - g, g)

    pal = palettes.as_array(p["palette"])
    colors = w.from_palette(pal, st["hues"], 255.0, wrap=False)
    img = (colors * (bri[:, None] / 255.0)).reshape(w.ROWS, w.COLS, 3).astype(np.float32)
    w.finalize(frame, img, now / 1000.0, p)
