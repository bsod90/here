"""Mood flower (shimmering petals) — Nadia's flower, alive for hours.

Not a new shape but a new skin: the existing 4-petal flower with the
MIDI-style shimmer rippling along the petal edges, while the palette
drifts very slowly around the color wheel (rose → violet → teal and
back, minutes per full cycle). Cheap, endless, made for long
unscripted stretches.

The flower geometry comes from animations/flower.py — shape overrides
go under the `flower` sub-dict. Tweak via `config.playground.moodflower`.
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL
from animations import flower as _flower

DEFAULTS = {
    # --- Shape overrides on top of flower.py DEFAULTS ---
    "flower": {
        "sequence": True,            # keeps the slow opening + rotation
        "rotate_speed_deg_s": 4.0,   # lazier spin than the stock flower
        "hold_time_s": 6.0,
    },

    # --- The mood cycle ---
    "cycle_period_s": 240.0, # one full trip around the color wheel (4 min)

    # --- Shimmer (same family as the fireplace / MIDI wobble) ---
    "shimmer_amount": 0.30,  # 0 = off, 0.5 = very lively
    "shimmer_speed": 0.5,    # how fast the shimmer crawls

    # --- Overall ---
    "brightness": 1.0,
}

_D = None
_THETA = None


def _geometry():
    global _D, _THETA
    if _D is None:
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - CENTER
            dy[i] = row - CENTER
        _D = np.sqrt(dx * dx + dy * dy)
        _THETA = np.arctan2(dy, dx)
    return _D, _THETA


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    d, theta = _geometry()
    t = time_ms / 1000.0

    # ── Hue-cycled flower: rotate the stock palette around the wheel
    # before rendering, so the gradient math stays inside flower.py.
    hue = (t / max(1.0, float(p["cycle_period_s"]))) % 1.0
    fparams = {**(p.get("flower") or {})}
    base = {**_flower.DEFAULTS, **fparams}
    for key in ("color_center", "color_tip", "core_color"):
        fparams[key] = _flower._cycled_color(base[key], hue).tolist()
    _flower.render(frame, time_ms, {**DEFAULTS["flower"], **fparams}, state)

    # ── Shimmer: the multi-sine radius wobble from the MIDI look,
    # applied as a brightness ripple over the rendered petals.
    amt = float(p["shimmer_amount"])
    if amt > 0.0:
        ss = t * float(p["shimmer_speed"])
        wobble = (0.55 * np.sin(theta * 11.0 + ss * 1.3)
                  + 0.30 * np.sin(theta * 17.0 - ss * 1.8)
                  + 0.20 * np.sin(theta * 5.0 + ss * 2.6)
                  + 0.25 * np.sin(d * 5.7 + ss * 1.5))
        mult = (1.0 + amt * 0.5 * wobble)[:, None]
        px = np.frombuffer(frame, dtype=np.uint8).astype(np.float32).reshape(TOTAL, 3)
        px = np.clip(px * mult * float(p["brightness"]), 0, 255).astype(np.uint8)
        frame[:] = px.tobytes()
