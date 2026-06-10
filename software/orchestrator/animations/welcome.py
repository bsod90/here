"""Welcome (bloom) — for the opening segment of a guided meditation.

Warm rings of light drift slowly OUTWARD from the center, like ripples
greeting whoever just sat down. The whole thing blooms up from darkness
over the first few seconds (so a timeline clip starting on "welcome,
take a seat…" feels like the floor is waking up to meet the voice).

Tweak via `config.playground.welcome` — every knob below says which way
to nudge it.
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- Motion ---
    "ring_spacing": 7.0,     # LEDs between ring crests (bigger = fewer, wider rings)
    "drift_speed": 0.45,     # rings per second drifting outward (smaller = calmer)
    "ring_softness": 2.2,    # 1 = crisp rings, 3+ = soft swells

    # --- Bloom-in (plays once when the clip starts) ---
    "bloom_s": 4.0,          # seconds to bloom from dark to full

    # --- Shape ---
    "reach": 20.0,           # how far the light extends from center (≈22 = full floor)
    "edge_softness": 6.0,    # how gently it fades out at `reach`
    "core_size": 3.0,        # radius of the warm center glow
    "core_brightness": 0.8,  # 0 = no core, 1 = full

    # --- Color: center → edge gradient ---
    "color_center": [255, 190, 110],   # warm gold near the middle
    "color_edge":   [150, 70, 220],    # soft violet toward the rim
    "core_color":   [255, 220, 160],

    # --- Overall ---
    "brightness": 0.9,       # master brightness (0–1)
}

# Per-LED distance from center, precomputed once.
_D = None


def _geometry():
    global _D
    if _D is None:
        d = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            d[i] = np.hypot(col - CENTER, row - CENTER)
        _D = d
    return _D


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    d = _geometry()
    t = time_ms / 1000.0

    # One-time bloom from darkness; `state` is reset on every (re)trigger
    # or timeline play, so the bloom replays each time the clip starts.
    bloom = 1.0
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        elapsed = (time_ms - state["t0"]) / 1000.0
        u = min(1.0, elapsed / max(0.01, float(p["bloom_s"])))
        bloom = u * u * (3.0 - 2.0 * u)           # smoothstep ease

    # Rings drifting outward: phase decreases with time so crests move
    # away from the center.
    spacing = max(1.0, float(p["ring_spacing"]))
    phase = d / spacing - t * float(p["drift_speed"])
    rings = 0.5 + 0.5 * np.sin(phase * 2.0 * np.pi)
    rings = rings ** max(0.5, float(p["ring_softness"]))

    # Radial envelope: full near the center, easing to dark at `reach`.
    reach = max(1.0, float(p["reach"]))
    soft = max(0.5, float(p["edge_softness"]))
    envelope = np.clip((reach - d) / soft, 0.0, 1.0)

    field = rings * envelope

    # Color gradient center → edge.
    c0 = np.array(p["color_center"], dtype=np.float32)
    c1 = np.array(p["color_edge"], dtype=np.float32)
    frac = np.clip(d / reach, 0.0, 1.0)[:, None]
    color = c0[None, :] * (1.0 - frac) + c1[None, :] * frac
    rgb = field[:, None] * color

    # Warm core glow on top.
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(d * d) / (2.0 * core_size * core_size)) * float(p["core_brightness"])
    rgb += core[:, None] * np.array(p["core_color"], dtype=np.float32)

    rgb = np.clip(rgb * (float(p["brightness"]) * bloom), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
