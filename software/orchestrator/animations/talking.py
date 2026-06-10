"""Talking (soft glow) — for spoken segments of a guided meditation.

A calm central presence: one soft glow that swells and settles with a
slow, slightly organic rhythm (several out-of-sync sine waves, so it
never feels mechanical or metronome-like). Deliberately low-contrast
and almost still — the voice is the show, the floor just breathes
quietly underneath it.

Tweak via `config.playground.talking`.
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- The glow ---
    "radius": 7.0,           # average size of the glow (LEDs)
    "radius_wobble": 1.6,    # how much the size drifts around the average
    "softness": 1.0,         # >1 = blurrier edge, <1 = tighter ball

    # --- The "presence" rhythm (NOT a breath cue — just alive) ---
    "wobble_period_s": 7.0,  # main swell period; longer = sleepier
    "level_min": 0.55,       # dimmest point of the swell (0–1)
    "level_max": 0.9,        # brightest point of the swell (0–1)

    # --- Faint halo ring around the glow ---
    "halo": True,
    "halo_radius": 13.0,     # where the halo sits
    "halo_width": 3.0,       # how wide the halo band is
    "halo_brightness": 0.18, # very faint by default

    # --- Sound-wave shimmer: concentric waves radiating from the glow,
    # like the voice rippling across the floor. They breathe with the
    # same swell as the glow (louder presence = brighter waves). ---
    "shimmer_amount": 0.16,  # brightness of the waves (0 = off)
    "shimmer_spacing": 5.5,  # LEDs between wave crests
    "shimmer_speed": 3.0,    # LEDs per second the waves travel outward
    "shimmer_reach": 20.0,   # waves die out by this distance

    # --- Colors ---
    "color":      [120, 150, 255],   # cool calm blue
    "halo_color": [90, 80, 200],

    # --- Overall ---
    "brightness": 0.8,       # master brightness (0–1)
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

    # Organic level/size drift: three slow sines at unrelated periods.
    # Their sum wanders gently instead of pulsing on a fixed beat.
    period = max(0.5, float(p["wobble_period_s"]))
    w = (0.55 * np.sin(2.0 * np.pi * t / period)
         + 0.30 * np.sin(2.0 * np.pi * t / (period * 1.73) + 1.1)
         + 0.15 * np.sin(2.0 * np.pi * t / (period * 0.41) + 2.6))
    w = 0.5 + 0.5 * float(w) / 1.0            # ≈0..1, slow wander

    lo, hi = float(p["level_min"]), float(p["level_max"])
    level = lo + (hi - lo) * w
    radius = max(0.5, float(p["radius"]) + float(p["radius_wobble"]) * (w - 0.5) * 2.0)

    # Soft gaussian ball.
    sigma = radius * max(0.2, float(p["softness"]))
    glow = np.exp(-(d * d) / (2.0 * sigma * sigma)) * level
    rgb = glow[:, None] * np.array(p["color"], dtype=np.float32)

    # Sound-wave shimmer: additive concentric waves traveling outward.
    # The center stays calm (waves start past the glow's core) and the
    # wave brightness rides the same `level` swell as the glow, so it
    # reads as the voice radiating, not a separate effect.
    amt = float(p["shimmer_amount"])
    if amt > 0.0:
        spacing = max(1.0, float(p["shimmer_spacing"]))
        speed = float(p["shimmer_speed"])
        reach = max(radius + 1.0, float(p["shimmer_reach"]))
        wave = 0.5 + 0.5 * np.sin(2.0 * np.pi * (d - t * speed) / spacing)
        wave = wave * wave                          # crisper crests, darker troughs
        band = (np.clip((d - radius * 0.7) / radius, 0.0, 1.0)
                * np.clip((reach - d) / (reach * 0.45), 0.0, 1.0))
        rgb += (amt * level * wave * band)[:, None] \
            * np.array(p["color"], dtype=np.float32)

    # Faint halo ring, fixed in place (the still anchor around the swell).
    if p.get("halo"):
        hr = float(p["halo_radius"])
        hw = max(0.5, float(p["halo_width"]))
        halo = np.exp(-((d - hr) ** 2) / (2.0 * hw * hw)) * float(p["halo_brightness"])
        rgb += halo[:, None] * np.array(p["halo_color"], dtype=np.float32)

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
