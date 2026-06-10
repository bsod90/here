"""Wind-down (settle) — for the closing segment of a guided meditation.

The opposite of "welcome": dim rings drift INWARD and sink into a warm
ember at the center, like the session folding itself up. On top of the
inward drift the whole field slowly loses energy in long "settling"
cycles — each swell a little softer than a steady pulse would be, so it
reads as coming to rest rather than breathing.

Tweak via `config.playground.winddown`.
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- Motion (mirrors welcome.py, but inward) ---
    "ring_spacing": 8.0,     # LEDs between ring crests
    "drift_speed": 0.3,      # rings per second drifting INWARD (small = sleepy)
    "ring_softness": 2.6,    # higher = softer swells

    # --- Settle rhythm ---
    "settle_period_s": 11.0, # long slow swells of overall energy
    "settle_depth": 0.35,    # how much each swell dips (0 = steady)

    # --- Shape ---
    "reach": 19.0,           # how far the light extends from center
    "edge_softness": 7.0,    # gentle fade at the rim
    "ember_size": 2.4,       # the warm core that everything sinks into
    "ember_brightness": 0.9,

    # --- Colors: dusk palette, warm middle → deep blue edge ---
    "color_center": [255, 140, 60],    # ember orange
    "color_edge":   [30, 30, 120],     # deep night blue
    "ember_color":  [255, 170, 90],

    # --- Overall ---
    "brightness": 0.65,      # master brightness — wind-down stays low
}

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

    # Rings drifting inward: phase INCREASES with time so crests move
    # toward the center (compare welcome.py, where it decreases).
    spacing = max(1.0, float(p["ring_spacing"]))
    phase = d / spacing + t * float(p["drift_speed"])
    rings = 0.5 + 0.5 * np.sin(phase * 2.0 * np.pi)
    rings = rings ** max(0.5, float(p["ring_softness"]))

    # Long settle swells: a sine whose dips are stretched (cubed) so the
    # field spends more time low than high — losing energy, not pulsing.
    period = max(1.0, float(p["settle_period_s"]))
    s = 0.5 + 0.5 * np.sin(2.0 * np.pi * t / period)
    settle = 1.0 - float(p["settle_depth"]) * (1.0 - float(s) ** 3)

    reach = max(1.0, float(p["reach"]))
    soft = max(0.5, float(p["edge_softness"]))
    envelope = np.clip((reach - d) / soft, 0.0, 1.0)

    field = rings * envelope * settle

    c0 = np.array(p["color_center"], dtype=np.float32)
    c1 = np.array(p["color_edge"], dtype=np.float32)
    frac = np.clip(d / reach, 0.0, 1.0)[:, None]
    color = c0[None, :] * (1.0 - frac) + c1[None, :] * frac
    rgb = field[:, None] * color

    # The ember everything sinks into — steady, not part of the swell,
    # so there's always a still point to rest the eyes on.
    ember_size = max(0.1, float(p["ember_size"]))
    ember = np.exp(-(d * d) / (2.0 * ember_size * ember_size)) * float(p["ember_brightness"])
    rgb += ember[:, None] * np.array(p["ember_color"], dtype=np.float32)

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
