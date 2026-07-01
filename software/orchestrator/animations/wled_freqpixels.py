"""Freqpixels — ported verbatim from WLED `mode_freqpixels` (1D mapped onto
the matrix: index i → (i%44, i//44)).

Sound-reactive in WLED; HERE has no live audio, so a synthetic dominant
frequency (slow sweep) and magnitude (slow swell) drive it. Random pixels
light in a color set by the "frequency", brightened by the "magnitude",
over a fading field — a slow chromatic sparkle.

Knobs (WLED 0..255): speed = fade rate, intensity = starting color + count.
"""
from __future__ import annotations

import math
import random

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "twilight",
    "speed": 80,
    "intensity": 128,
    "brightness": 1.0,
    "fade_in_s": 1.5,
}

_MAX_FREQ_LOG10 = 4.04238


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    flat = buf.reshape(TOTAL, 3)
    if "rng" not in st:
        st["rng"] = random.Random()
        st["call"] = 0
    rng = st["rng"]
    st["call"] += 1

    # Synthetic audio: a slow frequency sweep + a slow magnitude swell.
    fft_peak = 100.0 + float(w.beatsin8(7, now, 0, 255)) / 255.0 * 3500.0
    my_mag = float(w.beatsin8(11, now, 20, 200))
    speed, intensity = int(p["speed"]), int(p["intensity"])

    fade_rate = max(1, min(255, (speed * speed) * 255 // 65535))
    delay = (256 - speed) // 64
    if delay <= 1 or (st["call"] % delay) == 0:
        w.fade_out(buf, fade_rate)

    pix_col = (math.log10(fft_peak) - 1.78) * 255.0 / (_MAX_FREQ_LOG10 - 1.78)
    if fft_peak < 61.0:
        pix_col = 0.0
    pal = palettes.as_array(p["palette"])
    color = w.from_palette(pal, (intensity + pix_col) % 256.0, 255.0, wrap=True)
    for _ in range(intensity // 32 + 1):
        loc = rng.randrange(TOTAL)
        flat[loc] = color * (my_mag / 255.0)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
