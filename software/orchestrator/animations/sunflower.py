"""Sunflower (phyllotaxis spiral) — hypnotic breathing geometry.

Dots arranged exactly like the seeds of a real sunflower head (each new
seed rotated by the golden angle, radius growing with the square root of
its index), slowly rotating as one body while a brightness wave travels
along the spiral from the center to the rim and back. Mesmerizing in a
way rings and grids never are — built for breathing / deep-focus
segments. `wave_period_s` can be matched to an inhale+exhale cycle.

Tweak via `config.playground.sunflower`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, GRID, TOTAL

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))    # ≈ 137.5°

DEFAULTS = {
    # --- The seed lattice ---
    "seed_count": 220,       # how many dots in the head
    "spread": 1.40,          # radius of seed i = spread * sqrt(i)
    "max_radius": 21.0,      # seeds beyond this are clipped (off-floor)

    # --- Motion ---
    "rotate_deg_s": 0.75,    # whole-head rotation (slow drift). Halved from
                             # 1.5: at the rim a seed crossed one LED in ~2 s
                             # — dots popped in/out visibly fast out there,
                             # while the near-static inner seeds read fine.
    "wave_period_s": 8.0,    # one full center→rim→center brightness wave
    "wave_cycles": 2.5,      # how many wave crests live on the spiral at once
    "wave_floor": 0.18,      # dimmest a seed gets (0 = fully off between waves)

    # --- Colors: soft lavender heart → violet rim ---
    # (Was a golden heart, but the gold→violet blend passed through
    # muddy pink-reds midway and its dim tail rendered as red LEDs on
    # the hardware. All-purple keeps blue dominant at every radius —
    # no red-leaning pixel anywhere, in the sim or on the floor.)
    "color_center": [200, 165, 240],
    "color_rim":    [190, 70, 210],

    # --- Overall ---
    "brightness": 0.9,
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
    t = time_ms / 1000.0

    n = max(8, int(p["seed_count"]))
    i = np.arange(n, dtype=np.float32)
    radius = float(p["spread"]) * np.sqrt(i)
    keep = radius <= float(p["max_radius"])
    i, radius = i[keep], radius[keep]

    rot = math.radians(float(p["rotate_deg_s"])) * t
    theta = i * GOLDEN_ANGLE + rot
    sx = CENTER + radius * np.cos(theta)
    sy = CENTER + radius * np.sin(theta)

    # Brightness wave traveling along the spiral (i.e. outward, since
    # radius grows with index).
    period = max(0.5, float(p["wave_period_s"]))
    cycles = float(p["wave_cycles"])
    phase = cycles * (i / max(1.0, float(len(i)))) - t / period
    floor = float(p["wave_floor"])
    w = floor + (1.0 - floor) * (0.5 + 0.5 * np.sin(2.0 * np.pi * phase)) ** 2

    # Bilinear splat of every seed into a GRID×GRID intensity image —
    # vectorized, no per-seed python loop.
    img = np.zeros((GRID, GRID), dtype=np.float32)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    fx = (sx - x0).astype(np.float32)
    fy = (sy - y0).astype(np.float32)
    for dx_, dy_, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                          (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xs, ys = x0 + dx_, y0 + dy_
        ok = (xs >= 0) & (xs < GRID) & (ys >= 0) & (ys < GRID)
        np.add.at(img, (ys[ok], xs[ok]), (w * wgt)[ok])

    field = np.clip(img.reshape(TOTAL), 0.0, 1.0)

    # Color by distance from center: gold heart → violet rim.
    d = _distmap()
    c0 = np.array(p["color_center"], dtype=np.float32)
    c1 = np.array(p["color_rim"], dtype=np.float32)
    frac = np.clip(d / float(p["max_radius"]), 0.0, 1.0)[:, None]
    color = c0[None, :] * (1.0 - frac) + c1[None, :] * frac

    rgb = np.clip(field[:, None] * color * float(p["brightness"]),
                  0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
