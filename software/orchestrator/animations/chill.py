"""Chill (aurora) — for free-floating / music-only meditation segments.

Slow sheets of color drift diagonally across the floor like an aurora:
two translucent waves at different angles and speeds slide over each
other, blending their colors where they cross. Nothing is centered and
nothing repeats on an obvious beat — it's weather, not a pattern.

Tweak via `config.playground.chill`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- Wave A ---
    "angle_a_deg": 25.0,     # direction the first sheet drifts (degrees)
    "speed_a": 0.05,         # sheets per second (tiny = glacial)
    "scale_a": 16.0,         # LEDs per sheet (bigger = broader bands)
    "color_a": [20, 180, 160],    # teal

    # --- Wave B ---
    "angle_b_deg": 115.0,
    "speed_b": 0.035,
    "scale_b": 22.0,
    "color_b": [110, 40, 220],    # violet

    # --- The slow sway: both angles drift back and forth a little ---
    "sway_deg": 18.0,        # how far the directions wander (0 = locked)
    "sway_period_s": 47.0,   # how long one wander takes

    # --- Overall ---
    "base_glow": 0.06,       # faint floor wash so it never goes fully black
    "brightness": 0.7,       # master brightness (0–1) — chill should be dim
}

_X = None
_Y = None


def _geometry():
    global _X, _Y
    if _X is None:
        x = np.empty(TOTAL, dtype=np.float32)
        y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            x[i] = col - CENTER
            y[i] = row - CENTER
        _X, _Y = x, y
    return _X, _Y


def _sheet(x, y, t, angle_deg, sway_deg, sway_period, speed, scale):
    """One drifting wave sheet: brightness 0..1 per LED."""
    sway = math.radians(sway_deg) * math.sin(2.0 * math.pi * t / max(1.0, sway_period))
    a = math.radians(angle_deg) + sway
    along = x * math.cos(a) + y * math.sin(a)        # position along drift axis
    phase = along / max(1.0, scale) - t * speed
    v = 0.5 + 0.5 * np.sin(phase * 2.0 * np.pi)
    return (v * v).astype(np.float32)                # square → soft dark gaps


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    t = time_ms / 1000.0

    a = _sheet(x, y, t, float(p["angle_a_deg"]), float(p["sway_deg"]),
               float(p["sway_period_s"]), float(p["speed_a"]), float(p["scale_a"]))
    b = _sheet(x, y, t, float(p["angle_b_deg"]), -float(p["sway_deg"]),
               float(p["sway_period_s"]) * 1.31, float(p["speed_b"]), float(p["scale_b"]))

    ca = np.array(p["color_a"], dtype=np.float32)
    cb = np.array(p["color_b"], dtype=np.float32)
    rgb = a[:, None] * ca[None, :] + b[:, None] * cb[None, :]

    # Faint constant wash so the floor reads "on" even between sheets.
    glow = float(p["base_glow"])
    rgb += glow * (ca + cb)[None, :] * 0.5

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
