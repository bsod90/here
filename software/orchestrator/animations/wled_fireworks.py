"""Fireworks 1D — ported verbatim from WLED `mode_exploding_fireworks`.

A flare rises from the floor, slows under gravity, and bursts into a shower
of sparks that arc up and fall, fading white→color→dark with a warm cooling
tail. Then a short pause, and another launches.

Knobs (WLED 0..255): speed = gravity, intensity = launch position spread,
blur = soften the burst.
"""
from __future__ import annotations

import math
import random

import numpy as np

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "rainbow",
    "speed": 128,        # gravity
    "intensity": 128,
    "blur": False,       # check3
    "brightness": 1.0,
    "fade_in_s": 0.5,
}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    cols, rows = w.COLS, w.ROWS
    if "rng" not in st:
        st["rng"] = random.Random()
        st["aux0"] = 0
        st["flare"] = {}
        st["sparks"] = []
        st["dg"] = 0.0
        st["nsparks"] = 0
    rng = st["rng"]
    pal = palettes.as_array(p["palette"])
    num_sparks = min(5 + (rows * cols) // 2, 200)

    w.fade_out(buf, 252)
    gravity = (-0.0004 - (int(p["speed"]) / 800000.0)) * rows
    flare = st["flare"]

    if st["aux0"] < 2:                                   # FLARE
        if st["aux0"] == 0:
            flare["pos"] = 0.0
            flare["posX"] = float(rng.randint(2, cols - 3))
            peak = 75 + rng.randint(0, 179)
            peak = (peak * (rows - 1)) >> 8
            flare["vel"] = math.sqrt(max(0.0, -2.0 * gravity * peak))
            flare["velX"] = (rng.randint(0, 8) - 4) / 64.0
            flare["col"] = 255.0
            st["aux0"] = 1
        if flare["vel"] > 12 * gravity:
            c = max(0.0, flare["col"])
            w.set_xy(buf, int(flare["posX"]), rows - int(flare["pos"]) - 1,
                     np.array([c, c, c], dtype=np.float32))
            flare["pos"] = min(max(flare["pos"] + flare["vel"], 0), rows - 1)
            flare["posX"] = min(max(flare["posX"] + flare["velX"], 0), cols - 1)
            flare["vel"] += gravity
            flare["col"] -= 2
        else:
            st["aux0"] = 2
    elif st["aux0"] < 4:                                 # EXPLODE
        nsparks = int(flare["pos"]) + rng.randint(0, 3)
        nsparks = max(4, min(nsparks, num_sparks))
        if st["aux0"] == 2:
            sparks = []
            for _ in range(1, nsparks):
                vel = (rng.randint(0, 20000) / 10000.0) - 0.9
                velX = (rng.randint(0, 20000) / 10000.0) - 1.0
                vel *= flare["pos"] / rows
                velX *= flare["posX"] / cols
                vel *= -gravity * 50
                sparks.append({"pos": flare["pos"], "posX": flare["posX"],
                               "vel": vel, "velX": velX, "col": 345.0,
                               "colIndex": rng.randint(0, 255)})
            st["sparks"] = sparks
            st["nsparks"] = nsparks
            st["dg"] = gravity / 2.0
            st["aux0"] = 3
        sparks = st["sparks"]
        if sparks and sparks[0]["col"] > 4:
            for s in sparks:
                s["pos"] += s["vel"]; s["posX"] += s["velX"]
                s["vel"] += st["dg"]; s["velX"] += st["dg"]
                if s["col"] > 3:
                    s["col"] -= 4
                if 0 < s["pos"] < rows and 0 <= s["posX"] < cols:
                    prog = s["col"]
                    spc = w.from_palette(pal, float(s["colIndex"]), 255.0, wrap=False)
                    if prog > 300:
                        c = w.color_blend(spc, np.array([255., 255., 255.], np.float32), (prog - 300) * 5)
                    elif prog > 45:
                        c = w.color_blend(np.zeros(3, np.float32), spc, prog - 45)
                        cool = (300 - prog) / 32.0
                        c = c.copy(); c[1] = max(0.0, c[1] - cool); c[2] = max(0.0, c[2] - cool * 2)
                    else:
                        c = np.zeros(3, np.float32)
                    w.set_xy(buf, int(s["posX"]), rows - int(s["pos"]) - 1, c)
            if p.get("blur"):
                w.blur2d(buf, 16)
            st["dg"] *= 0.8
        else:
            st["aux0"] = 6 + rng.randint(0, 9)
    else:                                               # WAIT
        st["aux0"] -= 1
        if st["aux0"] < 4:
            st["aux0"] = 0
    w.finalize(frame, buf.copy(), now / 1000.0, p)
