"""Dandelion (letting go) — for the wind-down of a guided meditation.

A silvery seed-head glows at the center; every few seconds a couple of
seeds detach, drift outward on a slightly curling breeze, and fade
before reaching the edge. The head slowly thins as the clip runs —
"with every breath out, let something go."

Tweak via `config.playground.dandelion`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- The seed head ---
    "head_radius": 6.0,      # size of the fluffy ball
    "dot_density": 0.45,     # fraction of LEDs inside the head that sparkle
    "deplete_s": 90.0,       # how long until the head has visibly thinned out
    "min_density": 0.12,     # the head never empties completely

    # --- Seeds ---
    "spawn_period_s": 2.4,   # a puff of seeds releases this often
    "seeds_per_puff": 2,     # how many seeds per puff
    "seed_speed": 3.2,       # LEDs per second outward
    "seed_life_s": 5.5,      # how long a seed lives before fading out
    "seed_curl": 0.35,       # sideways wobble of the drift (0 = straight)
    "seed_size": 1.0,        # glow radius of one seed
    "max_seeds": 14,         # hard cap on simultaneous seeds

    # --- Colors ---
    "head_color": [215, 220, 255],    # silvery white
    "seed_color": [255, 255, 240],
    "core_color": [255, 200, 120],    # tiny warm heart of the flower
    "core_size": 1.2,
    "core_brightness": 0.5,

    # --- Overall ---
    "brightness": 0.85,
}

_R = None
_X = None
_Y = None
_DOTS = None     # static per-LED random values → which LEDs are "seeds"


def _geometry():
    global _R, _X, _Y, _DOTS
    if _R is None:
        x = np.empty(TOTAL, dtype=np.float32)
        y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            x[i] = col - CENTER
            y[i] = row - CENTER
        _X, _Y = x, y
        _R = np.sqrt(x * x + y * y)
        _DOTS = np.random.RandomState(7).rand(TOTAL).astype(np.float32)
    return _R, _X, _Y, _DOTS


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, x, y, dots = _geometry()
    if state is None:
        state = {}
    if "t0" not in state:
        state["t0"] = time_ms
        state["seeds"] = []
        state["last_spawn"] = time_ms
    elapsed = (time_ms - state["t0"]) / 1000.0

    # ── Spawn puffs of seeds ────────────────────────────────────────
    seeds = state["seeds"]
    if (time_ms - state["last_spawn"]) / 1000.0 >= float(p["spawn_period_s"]):
        state["last_spawn"] = time_ms
        for _ in range(int(p["seeds_per_puff"])):
            if len(seeds) >= int(p["max_seeds"]):
                break
            seeds.append({
                "angle": float(np.random.uniform(0, 2 * math.pi)),
                "born": time_ms,
                "speed": float(p["seed_speed"]) * float(np.random.uniform(0.8, 1.25)),
                "curl_phase": float(np.random.uniform(0, 2 * math.pi)),
            })
    # Drop the dead ones.
    life = max(0.5, float(p["seed_life_s"]))
    seeds[:] = [s for s in seeds if (time_ms - s["born"]) / 1000.0 < life]

    # ── The head: speckled ball that thins out over the session ────
    head_r = max(1.0, float(p["head_radius"]))
    density = max(float(p["min_density"]),
                  float(p["dot_density"])
                  * (1.0 - elapsed / max(1.0, float(p["deplete_s"]))))
    falloff = np.clip(1.0 - r / head_r, 0.0, 1.0)
    head = np.where(dots < density, falloff, 0.0).astype(np.float32)
    # A faint even fluff under the speckles so the ball reads as a ball.
    head += falloff * falloff * 0.15

    rgb = head[:, None] * np.array(p["head_color"], dtype=np.float32)

    # Tiny warm heart.
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) * float(p["core_brightness"])
    rgb += core[:, None] * np.array(p["core_color"], dtype=np.float32)

    # ── Drifting seeds ──────────────────────────────────────────────
    seed_color = np.array(p["seed_color"], dtype=np.float32)
    sigma = max(0.4, float(p["seed_size"]))
    for s in seeds:
        age = (time_ms - s["born"]) / 1000.0
        dist = head_r * 0.7 + s["speed"] * age
        ang = s["angle"] + float(p["seed_curl"]) * math.sin(age * 1.7 + s["curl_phase"]) * 0.5
        sx = dist * math.cos(ang)
        sy = dist * math.sin(ang)
        # Fade in fast, fade out over the last third of its life.
        env = min(1.0, age / 0.3) * min(1.0, (life - age) / (life * 0.35))
        if env <= 0.0:
            continue
        d2 = (x - sx) ** 2 + (y - sy) ** 2
        glow = np.exp(-d2 / (2.0 * sigma * sigma)) * env
        rgb += glow[:, None] * seed_color

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
