"""Dark Flower — the shimmering border with a breathing bloom inside.

A clone of Border (shimmer) (animations/borderglow.py) plus a breathing
circle in the middle. The same multi-frequency shimmer wobble that
vibrates the border's inner edge also perturbs the bloom's rim, so the
circle reads as a slowly breathing flower with soft, living petals
inside a glowing frame. Frame and bloom sample the SAME spinning palette
wheel, so they always agree on colour — together: a dark flower.

The wobble math is the MIDI engine's shimmer, verbatim (see borderglow):
  rough = 0.55·sin(11θ + 23t) + 0.30·sin(17θ − 31t) + 0.20·sin(5θ + 47t)

Knobs (WLED-style 0..255, tunable live in the playground):
  speed     — shimmer speed (same 1/10-of-MIDI pace as the border)
  intensity — shimmer amount over the constant ~30% floor
  custom1   — border width in LEDs (≈ width/16)
  custom2   — colour-wheel spin speed (0 = frozen)
  custom3   — breath pace (0 = ~14 s per breath, 255 = ~4 s)
"""
from __future__ import annotations

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL
from . import _wled as w
import palettes


DEFAULTS = {
    "palette": "dusk",       # pinks/violets — flower-ish by default
    "speed": 128,            # shimmer speed — 128 ≈ MIDI's shimmer at 1/10 pace
    "intensity": 178,        # shimmer amount — ≈ a held note's full wobble
    "custom1": 64,           # border width: /16 → 4 LEDs
    "custom2": 40,           # spin: ≈ 0.5 colour-wheel turns per minute
    "custom3": 96,           # breath pace: ≈ one breath every ~10 s
    "brightness": 1.0,
    "fade_in_s": 2.0,
}

# From the border: brightness of the frame at full amount, and the
# constant shimmer floor the MIDI engine always applies.
_BORDER_INTENSITY = 0.65
_BLOOM_INTENSITY = 0.85
_SHIMMER_FLOOR = 0.30

# The bloom breathes between these radii (LEDs) — snug inside the border.
_R_MIN, _R_MAX = 4.5, 13.5

# Per-LED geometry, computed once.
_ANGLE = None
_EDGE = None
_DIST = None


def _geometry():
    global _ANGLE, _EDGE, _DIST
    if _ANGLE is None:
        half = (GRID - 1) / 2.0
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - half
            dy[i] = row - half
        _ANGLE = np.arctan2(dy, dx).astype(np.float32)
        # Chebyshev distance from the nearest edge (border) and radial
        # distance from the centre (bloom).
        _EDGE = (half - np.maximum(np.abs(dx), np.abs(dy))).astype(np.float32)
        _DIST = np.sqrt(dx * dx + dy * dy).astype(np.float32)
    return _ANGLE, _EDGE, _DIST


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    angle, edge, dist = _geometry()

    # Knobs → quantities (identical mappings to borderglow).
    speed_mult = 0.01 + (float(p["speed"]) / 255.0) * 0.2
    shim = min(1.0, _SHIMMER_FLOOR + float(p["intensity"]) / 255.0)
    width = max(1.0, float(p["custom1"]) / 16.0)
    spin_rpm = (float(p["custom2"]) / 255.0) * 3.0
    breath_s = 14.0 - (float(p["custom3"]) / 255.0) * 10.0   # 14 s … 4 s

    # One shared shimmer field: the border's inner edge and the bloom's
    # rim wobble in sync — they read as one organism.
    ts = now * 0.001 * speed_mult
    rough = (0.55 * np.sin(angle * 11.0 + ts * 23.0)
             + 0.30 * np.sin(angle * 17.0 - ts * 31.0)
             + 0.20 * np.sin(angle * 5.0 + ts * 47.0))

    # One shared palette wheel, slowly spinning.
    b_rot = 2.0 * np.pi * spin_rpm * (now / 60000.0)
    idx = (((angle + b_rot) / (2.0 * np.pi)) % 1.0) * 256.0
    pal = palettes.as_array(p["palette"])
    color = w.from_palette(pal, idx, 255.0, wrap=False)

    # ── The frame: borderglow's edge band, verbatim ──────────────────
    width_eff = np.maximum(0.5, width * (1.0 + shim * 0.6 * rough))
    edge_bright = np.clip(1.0 - edge / width_eff, 0.0, 1.0)
    img = color * (edge_bright * _BORDER_INTENSITY)[:, np.newaxis]

    # ── The bloom: a breathing disc with a shimmering, petal-like rim ─
    breath = 0.5 - 0.5 * np.cos(2.0 * np.pi * (now / 1000.0) / breath_s)
    r = _R_MIN + (_R_MAX - _R_MIN) * breath
    r_pet = r * (1.0 + 0.18 * shim * rough)      # the petals
    rim = np.clip((r_pet - dist) / 1.5, 0.0, 1.0)          # soft edge
    depth = 0.55 + 0.45 * np.clip(1.0 - dist / np.maximum(r_pet, 1e-3),
                                  0.0, 1.0)                 # brighter core
    img = img + color * (rim * depth * _BLOOM_INTENSITY)[:, np.newaxis]

    w.finalize(frame, img, now / 1000.0, p)
