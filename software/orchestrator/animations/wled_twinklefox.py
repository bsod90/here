"""Twinklefox — ported from WLED `mode_twinklefox` (Mark Kriegsman). 1D,
mapped onto the matrix the default way: index i → pixel (i%44, i//44).

Each pixel twinkles on its own slow schedule with a fast-attack / slow-
decay glow and an incandescent "cooling" that warms it toward red as it
fades. The per-pixel schedule comes from a fixed-seed PRNG (reset every
frame in the original), so we precompute each pixel's clock offset / speed
/ salt once and cache them — the animation then comes purely from time.

Knobs (WLED 0..255):
  speed     — twinkle speed (lower = slower, dreamier)
  intensity — twinkle density (how many are lit at once)
  cool      — incandescent warming on the decay (check1 inverted: on = warm)
"""
from __future__ import annotations

import numpy as np

from . import _wled as w
from grid import TOTAL
import palettes

DEFAULTS = {
    "palette": "fire",
    "speed": 40,         # slow, dreamy
    "intensity": 128,    # density
    "cool": True,        # incandescent warming
    "brightness": 1.0,
    "fade_in_s": 2.0,
}


def _precompute(state: dict):
    off = np.empty(TOTAL, np.int64)
    spd = np.empty(TOTAL, np.int64)
    uniq = np.empty(TOTAL, np.int64)
    prng = 11337
    for i in range(TOTAL):
        prng = (prng * 2053 + 1384) & 0xFFFF
        off[i] = prng
        prng = (prng * 2053 + 1384) & 0xFFFF
        spd[i] = ((((prng & 0xFF) >> 4) + (prng & 0x0F)) & 0x0F) + 0x08
        uniq[i] = prng >> 8
    state["_tf"] = (off, spd, uniq)
    return state["_tf"]


def _sin8i(x):
    return np.round(w.sin8(x)).astype(np.int64) & 0xFF


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    off, spd, uniq = st.get("_tf") or _precompute(st)

    speed = int(p["speed"])
    aux0 = (3 + ((255 - speed) >> 3)) if speed > 100 else (22 + ((100 - speed) >> 1))
    myclock = (((int(now) * spd) >> 3) + off) & 0xFFFFFFFF
    ticks = myclock // max(1, aux0)
    fast = ticks & 0xFF
    slow16 = ((ticks >> 8) + uniq) & 0xFFFF
    slow16 = (slow16 + _sin8i(slow16 & 0xFF)) & 0xFFFF
    slow16 = (slow16 * 2053 + 1384) & 0xFFFF
    slow8 = ((slow16 & 0xFF) + (slow16 >> 8)) & 0xFF

    density = (int(p["intensity"]) >> 5) + 1
    gate = ((slow8 & 0x0E) // 2) < density
    ph = fast.astype(np.float32)
    bright = np.where(ph < 86, ph * 3.0, 255.0 - ((ph - 86) + (ph - 86) / 2.0))
    bright = np.where(gate, np.clip(bright, 0.0, 255.0), 0.0)
    hue = ((slow8 - uniq) & 0xFF).astype(np.float32)

    pal = palettes.as_array(p["palette"])
    color = w.from_palette(pal, hue, bright, wrap=False)     # (TOTAL, 3)
    if p.get("cool", True):
        cool = np.where(fast >= 128, (fast - 128) >> 4, 0).astype(np.float32)
        color[:, 1] = np.maximum(color[:, 1] - cool, 0.0)
        color[:, 2] = np.maximum(color[:, 2] - cool * 2.0, 0.0)
    img = color.reshape(w.ROWS, w.COLS, 3).astype(np.float32)
    w.finalize(frame, img, now / 1000.0, p)
