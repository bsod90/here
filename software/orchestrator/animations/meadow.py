"""Night meadow — tiny flowers sprouting across the floor.

Small five-petal flowers appear at random spots, bloom for a while,
sway gently, and melt away — a few alive at any moment, never
symmetric, never centered. The flower-world cousin of the standby
stars: quiet, ambient, doesn't demand attention. Ideal under a voice
or as a chill backdrop.

Tweak via `config.playground.meadow`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, GRID, TOTAL

DEFAULTS = {
    # --- Population ---
    "max_flowers": 5,        # how many can be alive at once
    "spawn_rate": 0.30,      # average new flowers per second (when room)
    "margin": 6,             # flowers keep this far from the floor edge

    # --- One flower's life ---
    "bloom_s": 3.0,          # unfold from nothing
    "hold_s": 9.0,           # fully open, swaying
    "fade_s": 4.0,           # melt away
    "size": 3.2,             # petal reach of one little flower (LEDs)
    "petals": 5,
    "sway_amount": 0.18,     # radians of gentle rotation wobble
    "sway_speed": 0.7,       # wobbles per second

    # --- Colors (picked per flower, round-robin + jitter) ---
    "palette": [
        [255, 150, 190],     # pink
        [180, 130, 255],     # lilac
        [255, 200, 120],     # buttercup
        [140, 220, 255],     # pale blue
    ],
    "center_color": [255, 240, 200],

    # --- Overall ---
    "base_glow": 0.03,       # whisper of green-blue ground so it's never void
    "base_color": [10, 30, 25],
    "brightness": 0.8,
}

_X = None
_Y = None


def _geometry():
    global _X, _Y
    if _X is None:
        x = np.empty(TOTAL, dtype=np.float32)
        y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            x[i] = col
            y[i] = row
        _X, _Y = x, y
    return _X, _Y


def _spawn(p, time_ms, count):
    m = float(p["margin"])
    return {
        "x": float(np.random.uniform(m, GRID - 1 - m)),
        "y": float(np.random.uniform(m, GRID - 1 - m)),
        "born": time_ms,
        "rot": float(np.random.uniform(0, 2 * math.pi)),
        "sway_phase": float(np.random.uniform(0, 2 * math.pi)),
        "color": list((p["palette"] or DEFAULTS["palette"])[count % len(p["palette"] or DEFAULTS["palette"])]),
        "scale": float(np.random.uniform(0.8, 1.2)),
    }


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    if state is None:
        state = {}
    if "flowers" not in state:
        state["flowers"] = []
        state["last_ms"] = time_ms
        state["spawned"] = 0
    t = time_ms / 1000.0
    dt = max(0.0, (time_ms - state["last_ms"]) / 1000.0)
    state["last_ms"] = time_ms

    life_total = float(p["bloom_s"]) + float(p["hold_s"]) + float(p["fade_s"])
    flowers = state["flowers"]
    flowers[:] = [f for f in flowers
                  if (time_ms - f["born"]) / 1000.0 < life_total]

    # Spawn: probabilistic — but never an empty meadow (the first flower
    # appears the moment the clip starts, so triggering it shows life
    # immediately).
    if len(flowers) < int(p["max_flowers"]):
        if not flowers or np.random.random() < float(p["spawn_rate"]) * dt:
            flowers.append(_spawn(p, time_ms, state["spawned"]))
            state["spawned"] += 1

    # Faint ground wash.
    rgb = np.ones((TOTAL, 3), dtype=np.float32) \
        * np.array(p["base_color"], dtype=np.float32)[None, :] * float(p["base_glow"])

    petals = max(3, int(p["petals"]))
    center_color = np.array(p["center_color"], dtype=np.float32)
    for f in flowers:
        age = (time_ms - f["born"]) / 1000.0
        # Life envelope: bloom in → hold → fade out.
        if age < float(p["bloom_s"]):
            u = age / max(0.01, float(p["bloom_s"]))
            env = u * u * (3 - 2 * u)
        elif age < float(p["bloom_s"]) + float(p["hold_s"]):
            env = 1.0
        else:
            u = (age - float(p["bloom_s"]) - float(p["hold_s"])) / max(0.01, float(p["fade_s"]))
            env = max(0.0, 1.0 - u)
        if env <= 0.0:
            continue
        size = float(p["size"]) * f["scale"] * (0.4 + 0.6 * env)
        rot = f["rot"] + float(p["sway_amount"]) * math.sin(
            2.0 * math.pi * float(p["sway_speed"]) * t + f["sway_phase"])
        dx = x - f["x"]
        dy = y - f["y"]
        rl = np.sqrt(dx * dx + dy * dy)
        th = np.arctan2(dy, dx)
        # A tiny rosette: radial gaussian shaped by cos(petals·θ).
        rose = (0.55 + 0.45 * np.cos(petals * (th - rot)))
        body = np.exp(-(rl * rl) / (2.0 * size * size)) * rose * env
        heart = np.exp(-(rl * rl) / (2.0 * (size * 0.3) ** 2)) * env
        rgb += body[:, None] * np.array(f["color"], dtype=np.float32)
        rgb += heart[:, None] * center_color * 0.6

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
