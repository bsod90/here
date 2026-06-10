"""Water lily (flower on a pond) — a flower with rippling water.

Nadia's 4-petal flower floats at the center while, every several
seconds, a soft ring ripples outward across the whole floor as if a
drop touched the water; the flower brightens just a touch as each
ripple passes. A transition / chill texture that combines the flower
with full-floor motion.

The flower itself is rendered by animations/flower.py (static, fully
open); this module adds the pond. Tweak via `config.playground.waterlily`
— flower-shape overrides go under its `flower` sub-dict.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL
from animations import flower as _flower

DEFAULTS = {
    # --- The lily (overrides applied on top of flower.py DEFAULTS) ---
    "flower": {
        "sequence": False,           # always fully open, floating still
        "petal_reach": 14.0,         # smaller than the full-floor flower
        "color_center": [200, 40, 90],
        "color_tip":    [120, 20, 140],
        "core_color":   [255, 220, 140],
        "brightness": 0.9,
    },

    # --- Ripples ---
    "ripple_period_s": 9.0,  # a new drop lands this often
    "ripple_speed": 4.0,     # LEDs per second outward
    "ripple_width": 1.8,     # thickness of the ring
    "ripple_brightness": 0.4,# how bright a fresh ring is (it fades going out)
    "ripple_color": [70, 130, 220],   # moonlit water blue
    "concurrent": 2,         # rings in flight at once (staggered)

    # --- The pond ---
    "pond_glow": 0.06,       # faint base water so the floor reads as a pond
    "pond_color": [10, 35, 70],
    "bob_amount": 0.12,      # how much the lily brightens as a ripple passes

    # --- Overall ---
    "brightness": 1.0,
}

_D = None


def _distmap():
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
    d = _distmap()
    t = time_ms / 1000.0

    # ── The lily, via the existing flower renderer ──────────────────
    fparams = {**DEFAULTS["flower"], **(p.get("flower") or {})}
    _flower.render(frame, time_ms, fparams, None)
    lily = np.frombuffer(frame, dtype=np.uint8).astype(np.float32).reshape(TOTAL, 3)

    # ── Ripples: staggered rings expanding from the center ──────────
    period = max(1.0, float(p["ripple_period_s"]))
    speed = max(0.1, float(p["ripple_speed"]))
    width = max(0.3, float(p["ripple_width"]))
    max_d = float(np.max(d)) + width
    rings = np.zeros(TOTAL, dtype=np.float32)
    bob = 0.0
    lily_edge = float(fparams.get("petal_reach", 14.0))
    for k in range(max(1, int(p["concurrent"]))):
        phase_t = (t + k * period / max(1, int(p["concurrent"]))) % period
        radius = phase_t * speed
        if radius > max_d:
            continue
        fade = max(0.0, 1.0 - radius / max_d)      # rings die out at the rim
        rings += np.exp(-((d - radius) ** 2) / (2.0 * width * width)) * fade
        # The lily bobs as a ring crosses its petals.
        bob += math.exp(-((radius - lily_edge) ** 2) / (2.0 * 2.5 ** 2)) * fade

    rgb = lily * (1.0 + float(p["bob_amount"]) * bob)
    rgb += (rings * float(p["ripple_brightness"]))[:, None] \
        * np.array(p["ripple_color"], dtype=np.float32)

    # Faint standing water everywhere.
    rgb += float(p["pond_glow"]) * np.array(p["pond_color"], dtype=np.float32)[None, :]

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
