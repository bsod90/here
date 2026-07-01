"""Raindrops — rain falling down the matrix, drop by drop.

A side view of rain: bright drops fall from the top edge, each one a
short streak — brightest at its head with a fading tail — falling at
its own speed. When a drop reaches the bottom it lands with a tiny
splash that flattens out and fades. Drops differ in speed, length and
brightness, and arrive on an irregular rhythm, so it reads as honest
rain rather than a marching pattern.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.raindrops`.
"""
from __future__ import annotations

import random

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "rate": 5.0,             # drops per second (1 = sparse, 12 = downpour)
    "fall_speed": 14.0,      # how fast drops fall (LEDs per second)
    "speed_jitter": 0.4,     # how much speeds vary between drops (0 = uniform)
    "tail": 5.0,             # length of a drop's fading tail (LEDs)

    "color_drop": [120, 170, 230],   # the falling drop (cool rain blue)
    "color_splash": [170, 210, 255], # the little splash at the bottom
    "color_sky": [2, 4, 12],         # the near-dark background

    "splash": True,          # drops land with a tiny flattening splash
    "splash_life_s": 0.45,   # how long the splash lasts

    "fade_in_s": 1.5,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}

_MAX_DROPS = 60              # safety cap on simultaneous drops (render cost)


# Per-LED x/y coordinates, computed once (the grid never changes).
_X = None
_Y = None


def _geometry():
    global _X, _Y
    if _X is None:
        _X = np.empty(TOTAL, dtype=np.float32)
        _Y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            _X[i] = col
            _Y[i] = row
    return _X, _Y


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    # ── One-time init (state is reset on each trigger/play) ─────────
    if "t0" not in st:
        st["t0"] = time_ms
        st["last_ms"] = time_ms
        st["rng"] = random.Random()
        st["drops"] = []         # [{x, y, speed, tail, bright}]
        st["splashes"] = []      # [{x, born_s}]
        st["spawn_acc"] = 1.0    # first drop falls immediately
    rng: random.Random = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0
    dt = min(0.1, max(0.0, (time_ms - st["last_ms"]) / 1000.0))
    st["last_ms"] = time_ms

    speed0 = max(1.0, float(p["fall_speed"]))
    sj = min(1.0, max(0.0, float(p["speed_jitter"])))
    tail0 = max(1.0, float(p["tail"]))
    splash_life = max(0.1, float(p["splash_life_s"]))

    # ── Spawn drops at the top, irregular rhythm ─────────────────────
    st["spawn_acc"] += float(p["rate"]) * dt
    while st["spawn_acc"] >= 1.0 and len(st["drops"]) < _MAX_DROPS:
        st["spawn_acc"] -= 1.0 * rng.uniform(0.5, 1.5)
        st["drops"].append({
            "x": rng.uniform(0.5, GRID - 1.5),
            "y": -rng.uniform(0.0, 4.0),             # just above the top edge
            "speed": speed0 * (1.0 + sj * rng.uniform(-0.5, 0.8)),
            "tail": tail0 * rng.uniform(0.7, 1.3),
            "bright": rng.uniform(0.55, 1.0),
        })

    # ── Move drops; land → splash ────────────────────────────────────
    alive = []
    for d in st["drops"]:
        d["y"] += d["speed"] * dt
        if d["y"] - d["tail"] > GRID - 1:            # fully past the bottom
            continue
        if d["y"] >= GRID - 1 and p.get("splash") and "landed" not in d:
            d["landed"] = True
            st["splashes"].append({"x": d["x"], "born_s": t,
                                   "bright": d["bright"]})
        alive.append(d)
    st["drops"] = alive
    st["splashes"] = [s for s in st["splashes"]
                      if t - s["born_s"] < splash_life]

    # ── Render ───────────────────────────────────────────────────────
    sky = np.array(p["color_sky"], dtype=np.float32)
    rgb = np.tile(sky, (TOTAL, 1))
    drop_c = np.array(p["color_drop"], dtype=np.float32)
    splash_c = np.array(p["color_splash"], dtype=np.float32)

    for d in st["drops"]:
        # Streak: head at d.y, tail trailing above, one column wide.
        dx = x - d["x"]
        col_w = np.exp(-(dx * dx) / (2.0 * 0.55 * 0.55))
        behind = d["y"] - y                          # 0 at head, + above it
        along = np.where((behind >= 0.0) & (behind <= d["tail"]),
                         1.0 - behind / d["tail"], 0.0)
        # A touch of glow just below the head so motion looks smooth.
        head_glow = np.exp(-(behind * behind) / (2.0 * 0.6 * 0.6))
        streak = np.maximum(along ** 1.6, head_glow * 0.9) * col_w * d["bright"]
        a = np.clip(streak, 0.0, 1.0)[:, np.newaxis]
        rgb = rgb * (1.0 - a) + drop_c[np.newaxis, :] * a

    for s in st["splashes"]:
        u = (t - s["born_s"]) / splash_life          # 0 fresh → 1 gone
        # A small puddle of light on the bottom row, widening and fading.
        dx = x - s["x"]
        spread = 1.0 + 3.5 * u
        flat = np.exp(-(dx * dx) / (2.0 * spread * spread))
        row = np.exp(-((GRID - 1 - y) ** 2) / (2.0 * 0.7 * 0.7))
        a = np.clip(flat * row * (1.0 - u) * s["bright"], 0.0, 1.0)[:, np.newaxis]
        rgb = rgb * (1.0 - a) + splash_c[np.newaxis, :] * a

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
