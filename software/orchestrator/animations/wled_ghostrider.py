"""Ghost Rider — ported from WLED `mode_2Dghostrider`.

A "ghost" (white dot) drives around the matrix on a slowly-curving path,
shedding a swarm of spark particles that shoot backward, age, and respawn —
all drawn anti-aliased over a fading, blurred buffer. Hypnotic motion.

Knobs (WLED 0..255):
  speed     — trail fade rate (higher = shorter, snappier trails)
  intensity — blur (glow softness)
"""
from __future__ import annotations

import math
import random

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "twilight",
    "speed": 64,
    "intensity": 80,     # blur
    "brightness": 1.0,
    "fade_in_s": 1.5,
}

_N = 64                  # LIGHTERS_AM
_WHITE = None


def _init(st):
    cols, rows = w.COLS, w.ROWS
    rng = random.Random()
    g = {
        "rng": rng,
        "gx": (cols / 2) * 10.0, "gy": (rows / 2) * 10.0,
        "angle": rng.randint(0, 359), "aspeed": rng.randint(0, 19) - 10,
        "vspeed": 5.0,
        "px": [], "py": [], "la": [], "lt": [], "reg": [],
        "next_ms": 0.0,
    }
    n = min(cols + rows, _N)
    for i in range(n):
        g["px"].append(g["gx"])
        g["py"].append(g["gy"] + i)
        g["la"].append(0)
        g["lt"].append(i * 2)
        g["reg"].append(False)
    g["n"] = n
    st["ghost"] = g
    return g


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    import numpy as np
    global _WHITE
    if _WHITE is None:
        _WHITE = np.array([255.0, 255.0, 255.0], dtype=np.float32)
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    g = st.get("ghost") or _init(st)
    cols, rows = w.COLS, w.ROWS
    pal = palettes.as_array(p["palette"])
    rng = g["rng"]

    if now > g["next_ms"]:
        g["next_ms"] = now + 1024.0 / (cols + rows)
        w.fade_to_black(buf, (int(p["speed"]) >> 2) + 64)
        w.wu_splat(buf, g["gx"] / 10.0, g["gy"] / 10.0, _WHITE)
        g["gx"] += g["vspeed"] * math.sin(math.radians(g["angle"]))
        g["gy"] += g["vspeed"] * math.cos(math.radians(g["angle"]))
        g["angle"] = (g["angle"] + g["aspeed"]) % 360
        if g["gx"] < 0: g["gx"] = (cols - 1) * 10.0
        if g["gx"] > (cols - 1) * 10.0: g["gx"] = 0.0
        if g["gy"] < 0: g["gy"] = (rows - 1) * 10.0
        if g["gy"] > (rows - 1) * 10.0: g["gy"] = 0.0
        for i in range(g["n"]):
            g["lt"][i] += rng.randint(5, 19)
            if (g["lt"][i] >= 255 or g["px"][i] <= 0 or g["px"][i] >= (cols - 1) * 10.0
                    or g["py"][i] <= 0 or g["py"][i] >= (rows - 1) * 10.0):
                g["reg"][i] = True
            if g["reg"][i]:
                g["px"][i] = g["gx"]
                g["py"][i] = g["gy"]
                g["la"][i] = (g["angle"] + rng.randint(0, 19) - 10) % 360
                g["lt"][i] = 0
                g["reg"][i] = False
            else:
                g["px"][i] += -7.0 * math.sin(math.radians(g["la"][i]))
                g["py"][i] += -7.0 * math.cos(math.radians(g["la"][i]))
            color = w.from_palette(pal, (256 - g["lt"][i]) % 256, 255.0, wrap=False)
            w.wu_splat(buf, g["px"][i] / 10.0, g["py"][i] / 10.0, color)
        w.blur2d(buf, int(p["intensity"]) >> 3)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
