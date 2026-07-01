"""Fireflies — little wandering lights over a purple-haze gradient.

From Nadia's reference images: a smoky gradient that runs diagonally
across the matrix — near-black blue-violet in one corner melting
through deep purple into glowing pink in the opposite corner — with
small bright fireflies drifting through it.

The gradient itself MOVES: the dark and pink ends slowly slide along
the diagonal and the boundary between them breathes and marbles, so
the background feels like slow smoke. The fireflies wander randomly
(each one eases to a nearby spot, pauses, picks another — never in a
straight line, never together) and each one pulses with its own slow
blink, like real fireflies.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.fireflies`.
"""
from __future__ import annotations

import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    # --- Fireflies ---
    "flies": 22,             # how many fireflies wander the matrix
    "fly_size": 0.8,         # glow radius of one firefly (LEDs)
    "fly_speed": 1.0,        # how fast they drift (1 = lazy summer night)
    "blink_speed": 1.0,      # how fast they pulse bright/dim
    "fly_color": [255, 225, 245],    # warm white-pink spark

    # --- The purple haze behind them ---
    "color_dark": [6, 0, 28],        # near-black blue-violet corner
    "color_mid": [105, 12, 175],       # deep purple middle
    "color_pink": [240, 75, 195],    # glowing pink corner
    "bg_brightness": 0.65,    # how bright the haze is overall (0 = black bg,
                             # fireflies only)
    "drift_speed": 1.0,      # how fast the dark/pink ends slide along the
                             # diagonal (1 = a slow tide, ~1 min per sweep)

    "fade_in_s": 2.5,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}


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


def _new_target(rng: random.Random, x: float, y: float) -> tuple[float, float]:
    """A wander waypoint near the current spot (fireflies hop locally,
    they don't cross the whole matrix in one go)."""
    return (min(GRID - 2.0, max(1.0, x + rng.uniform(-7.0, 7.0))),
            min(GRID - 2.0, max(1.0, y + rng.uniform(-7.0, 7.0))))


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    n = max(1, int(p["flies"]))

    # ── One-time init (state is reset on each trigger/play) ─────────
    if "t0" not in st or len(st.get("flies", ())) != n:
        st["t0"] = time_ms
        st["last_ms"] = time_ms
        rng = st["rng"] = random.Random()
        flies = []
        for _ in range(n):
            fx = rng.uniform(1.0, GRID - 2.0)
            fy = rng.uniform(1.0, GRID - 2.0)
            flies.append({
                "x": fx, "y": fy,
                "tx": fx, "ty": fy,
                "pause": rng.uniform(0.0, 1.5),      # resting before first hop
                "freq": rng.uniform(0.10, 0.30),     # personal blink rhythm
                "phase": rng.uniform(0.0, 2.0 * math.pi),
                "bright": rng.uniform(0.6, 1.0),
            })
        st["flies"] = flies
    rng = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0
    dt = min(0.1, max(0.0, (time_ms - st["last_ms"]) / 1000.0))
    st["last_ms"] = time_ms

    # ── Move the fireflies: ease → arrive → pause → new hop ─────────
    speed = float(p["fly_speed"])
    ease = 1.0 - math.exp(-0.9 * speed * dt)
    for f in st["flies"]:
        if f["pause"] > 0.0:
            f["pause"] -= dt
        else:
            f["x"] += (f["tx"] - f["x"]) * ease
            f["y"] += (f["ty"] - f["y"]) * ease
            if abs(f["tx"] - f["x"]) < 0.6 and abs(f["ty"] - f["y"]) < 0.6:
                f["tx"], f["ty"] = _new_target(rng, f["x"], f["y"])
                f["pause"] = rng.uniform(0.2, 2.0)   # hover a moment

    # ── The purple haze: a moving diagonal gradient ──────────────────
    # Position along the diagonal (0 = one corner, 1 = the other), then
    # slide it back and forth slowly and marble the boundary so the
    # colors move like smoke, not like a ruler.
    drift = float(p["drift_speed"])
    diag = (x + y) / (2.0 * (GRID - 1))
    slide = 0.22 * math.sin(2.0 * math.pi * t * drift / 64.0)
    marble = 0.10 * np.sin(x / 9.0 - t * drift * 0.11) \
        * np.sin(y / 7.0 + t * drift * 0.09)
    g = np.clip(diag + slide + marble, 0.0, 1.0)

    dark = np.array(p["color_dark"], dtype=np.float32)
    mid = np.array(p["color_mid"], dtype=np.float32)
    pink = np.array(p["color_pink"], dtype=np.float32)
    lo = np.clip(g * 2.0, 0.0, 1.0)[:, np.newaxis]
    hi = np.clip(g * 2.0 - 1.0, 0.0, 1.0)[:, np.newaxis]
    rgb = dark[np.newaxis, :] * (1.0 - lo) + mid[np.newaxis, :] * lo
    rgb = rgb * (1.0 - hi) + pink[np.newaxis, :] * hi
    rgb = rgb * float(p["bg_brightness"])

    # ── The fireflies, glowing over the haze ─────────────────────────
    size = max(0.3, float(p["fly_size"]))
    blink_spd = float(p["blink_speed"])
    fly_c = np.array(p["fly_color"], dtype=np.float32)
    for f in st["flies"]:
        # Personal blink: mostly soft, swelling bright in pulses.
        blink = 0.5 + 0.5 * math.sin(2.0 * math.pi * f["freq"] * blink_spd * t
                                     + f["phase"])
        glow = f["bright"] * (0.15 + 0.85 * blink * blink)
        dx = x - f["x"]
        dy = y - f["y"]
        a = np.clip(np.exp(-(dx * dx + dy * dy) / (2.0 * size * size)) * glow,
                    0.0, 1.0)[:, np.newaxis]
        rgb = rgb * (1.0 - a) + fly_c[np.newaxis, :] * a

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
