"""Crazy Bees — ported verbatim from WLED `mode_2Dcrazybees`.

A few "bees" fly in straight Bresenham lines toward random target points,
leaving fading trails; at each target a little 4-pixel flower blooms in the
bee's hue. When a bee arrives it picks a new target. Blurred + faded.

Knobs (WLED 0..255): speed = fly speed, intensity = blur.
"""
from __future__ import annotations

import random

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "rainbow",          # unused (bees use CHSV) — kept for UI uniformity
    "speed": 128,
    "intensity": 64,
    "brightness": 1.0,
    "fade_in_s": 1.0,
}

_FRAMETIME = 24.0


def _aimed(b, rng, cols, rows):
    b["aimX"] = rng.randrange(cols)
    b["aimY"] = rng.randrange(rows)
    b["hue"] = rng.randint(0, 255)
    b["dX"] = abs(b["aimX"] - b["posX"])
    b["dY"] = abs(b["aimY"] - b["posY"])
    b["sX"] = 1 if b["posX"] < b["aimX"] else -1
    b["sY"] = 1 if b["posY"] < b["aimY"] else -1
    b["err"] = b["dX"] - b["dY"]


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    buf = w.get_buf(st)
    cols, rows = w.COLS, w.ROWS
    n = min(5, (rows * cols) // 256 + 1)

    if "bees" not in st:
        rng = random.Random()
        st["rng"] = rng
        st["next"] = 0.0
        bees = []
        for _ in range(n):
            b = {"posX": rng.randrange(cols), "posY": rng.randrange(rows)}
            _aimed(b, rng, cols, rows)
            bees.append(b)
        st["bees"] = bees
    rng = st["rng"]

    if now > st["next"]:
        st["next"] = now + (_FRAMETIME * 16.0 / ((int(p["speed"]) >> 4) + 1))
        w.fade_to_black(buf, 32)
        for b in st["bees"]:
            col = w.chsv(b["hue"], 255, 255)
            w.add_xy(buf, b["aimX"] + 1, b["aimY"], col)
            w.add_xy(buf, b["aimX"], b["aimY"] + 1, col)
            w.add_xy(buf, b["aimX"] - 1, b["aimY"], col)
            w.add_xy(buf, b["aimX"], b["aimY"] - 1, col)
            if b["posX"] != b["aimX"] or b["posY"] != b["aimY"]:
                w.set_xy(buf, b["posX"], b["posY"], w.chsv(b["hue"], 60, 255))
                e2 = b["err"] * 2
                if e2 > -b["dY"]:
                    b["err"] -= b["dY"]; b["posX"] += b["sX"]
                if e2 < b["dX"]:
                    b["err"] += b["dX"]; b["posY"] += b["sY"]
            else:
                _aimed(b, rng, cols, rows)
        w.blur2d(buf, int(p["intensity"]) >> 4)
    w.finalize(frame, buf.copy(), now / 1000.0, p)
