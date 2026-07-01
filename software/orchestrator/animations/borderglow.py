"""Border (shimmer) — the MIDI engine's glowing border, shimmer always on.

Ported from the border-glow layer in scene/animations/synth.py: a soft
gradient band hugging the platform's edge, coloured by a palette wheel
that slowly spins around the perimeter. In the MIDI engine the "Shimmer"
event roughens the border's inner edge with a multi-frequency radial
wobble while a note is held — that vibrating, liquid edge is the look
this module keeps running continuously (no MIDI needed).

The wobble math is copied verbatim from synth.py so it reads the same:
  rough = 0.55·sin(11θ + 23t) + 0.30·sin(17θ − 31t) + 0.20·sin(5θ + 47t)
  width_eff = width · (1 + shim · 0.6 · rough)

Knobs (WLED-style 0..255, tunable live in the playground):
  speed     — shimmer speed (vibrato rate; 128 ≈ the MIDI default)
  intensity — shimmer amount ON TOP of the MIDI engine's constant ~30%
              baseline (0 = the border's own gentle roughness,
              255 = full held-note vibrato)
  custom1   — border width in LEDs (≈ width/16, MIDI's border is 4 px)
  custom2   — colour-wheel spin speed (0 = frozen)
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL
from . import _wled as w
import palettes


DEFAULTS = {
    "palette": "lava",       # angular colour wheel (lava ≈ the MIDI swatch)
    "speed": 128,            # shimmer speed — 128 ≈ MIDI's shimmer at 1/10 pace
    "intensity": 178,        # shimmer amount — ≈ a held note's full wobble
    "custom1": 64,           # width: /16 → 4 LEDs, same as the MIDI border
    "custom2": 40,           # spin: ≈ 0.5 colour-wheel turns per minute
    "brightness": 1.0,
    "fade_in_s": 2.0,
}

# From synth.py — the border's brightness at amount=1, and the constant
# shimmer floor the MIDI engine always applies to the border.
_BASE_INTENSITY = 0.65
_SHIMMER_FLOOR = 0.30

# Per-LED geometry, computed once (matches synth.py's _geometry_for, but
# centered symmetrically so all four edges sit at edge-distance 0).
_ANGLE = None
_EDGE = None


def _geometry():
    global _ANGLE, _EDGE
    if _ANGLE is None:
        half = (GRID - 1) / 2.0
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - half
            dy[i] = row - half
        _ANGLE = np.arctan2(dy, dx).astype(np.float32)
        # Chebyshev distance from the nearest edge (0 at the rim).
        _EDGE = (half - np.maximum(np.abs(dx), np.abs(dy))).astype(np.float32)
    return _ANGLE, _EDGE


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    angle, edge = _geometry()

    # Knobs → the synth.py quantities. The wobble clock runs ~10x slower
    # than the MIDI engine's — at MIDI pace the always-on shimmer read
    # as a frantic vibration rather than a liquid edge.
    speed_mult = 0.01 + (float(p["speed"]) / 255.0) * 0.2     # 0.01..0.21, 128≈0.11
    shim = min(1.0, _SHIMMER_FLOOR + float(p["intensity"]) / 255.0)
    width = max(1.0, float(p["custom1"]) / 16.0)               # LEDs
    spin_rpm = (float(p["custom2"]) / 255.0) * 3.0             # 0..3 rev/min

    # Shimmer — the exact multi-frequency roughness from synth.py's
    # border layer: perturbs the local border WIDTH per pixel, so the
    # inner edge vibrates instead of the brightness flickering.
    ts = now * 0.001 * speed_mult
    rough = (0.55 * np.sin(angle * 11.0 + ts * 23.0)
             + 0.30 * np.sin(angle * 17.0 - ts * 31.0)
             + 0.20 * np.sin(angle * 5.0 + ts * 47.0))
    width_eff = np.maximum(0.5, width * (1.0 + shim * 0.6 * rough))
    edge_bright = np.clip(1.0 - edge / width_eff, 0.0, 1.0)

    # Colour wheel around the perimeter, slowly spinning. Sampled from
    # the palette cyclically (from_palette lerps the last anchor back
    # into the first) so there's no seam at ±π.
    b_rot = 2.0 * np.pi * spin_rpm * (now / 60000.0)
    idx = (((angle + b_rot) / (2.0 * np.pi)) % 1.0) * 256.0
    pal = palettes.as_array(p["palette"])
    color = w.from_palette(pal, idx, 255.0, wrap=False)

    img = color * (edge_bright * _BASE_INTENSITY)[:, np.newaxis]
    w.finalize(frame, img, now / 1000.0, p)
