"""Sunrise — night turning to morning, with the sun climbing the matrix.

A one-way sunrise, played bottom-to-top: it starts as deep night (the
sky nearly black, a faint cold glow at the bottom edge — the horizon),
then the horizon warms through rose and fire-orange, and the sun
itself rises from below the bottom edge — first a glow, then the disc
climbing slowly with a warm halo — until the whole sky settles into a
soft golden morning and holds there.

By default the sunrise takes ~50 seconds and then HOLDS at morning
(nice on the timeline: put it under the part of the recording where
the meditation "wakes up"). Set "loop": true to make it fade back to
night and rise again, forever.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.sunrise`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "rise_s": 50.0,          # how long night → full morning takes
    "loop": False,           # true = sink back to night and rise again forever;
                             # false = hold at morning once risen
    "night_hold_s": 6.0,     # (loop only) how long to rest in night between rises

    "sun_size": 3.6,         # radius of the sun disc (LEDs)
    "sun_glow": 1.0,         # strength of the warm halo around the sun

    "brightness": 1.0,       # master brightness multiplier
}

# The sky through the sunrise: (phase 0..1, top-of-sky color, horizon color).
# Phases between stops are blended smoothly.
_SKY_STOPS = (
    (0.00, (3, 3, 18),    (12, 9, 40)),      # deep night
    (0.30, (12, 9, 48),   (132, 40, 66)),    # first light — rose on the horizon
    (0.55, (30, 20, 84),  (232, 92, 48)),    # dawn fire
    (0.80, (62, 62, 152), (255, 152, 64)),   # the sun breaks the horizon
    (1.00, (92, 142, 215),(255, 205, 115)),  # golden morning
)


# Per-LED x/y coordinates, computed once (the grid never changes).
_X = None
_Y = None

# Static per-LED dither offsets (seeded, computed once). Added before
# quantizing to 8 bits: each LED rounds at its own fixed threshold, so
# the smooth sky gradient dissolves into invisible noise instead of
# visible color bands — and because the offsets never change, nothing
# flickers. (This is what made the dark sky "disco" on the real pebbles:
# at LED values of 1–5, plain rounding turns a smooth gradient into
# patches of different hues that pop step by step as the sky shifts.)
_DITHER = None


def _dither():
    global _DITHER
    if _DITHER is None:
        rng = np.random.default_rng(3)
        _DITHER = rng.uniform(0.0, 1.0, size=(TOTAL, 1)).astype(np.float32)
    return _DITHER


def _geometry():
    global _X, _Y
    if _X is None:
        _X = np.empty(TOTAL, dtype=np.float32)
        _Y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            _X[i] = col
            _Y[i] = row
    return _X, _Y


def _sky_colors(u: float) -> tuple[np.ndarray, np.ndarray]:
    """Top + horizon colors at sunrise phase `u`, blended between stops."""
    for k in range(len(_SKY_STOPS) - 1):
        u0, top0, hor0 = _SKY_STOPS[k]
        u1, top1, hor1 = _SKY_STOPS[k + 1]
        if u <= u1 or k == len(_SKY_STOPS) - 2:
            w = min(1.0, max(0.0, (u - u0) / max(1e-6, u1 - u0)))
            top = np.array(top0, dtype=np.float32) * (1 - w) \
                + np.array(top1, dtype=np.float32) * w
            hor = np.array(hor0, dtype=np.float32) * (1 - w) \
                + np.array(hor1, dtype=np.float32) * w
            return top, hor
    return (np.array(_SKY_STOPS[-1][1], dtype=np.float32),
            np.array(_SKY_STOPS[-1][2], dtype=np.float32))


def _smoothstep(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the sunrise always starts from night.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    rise = max(5.0, float(p["rise_s"]))
    if p.get("loop"):
        # night → rise → morning → sink back → short night rest → again.
        period = rise * 2.0 + float(p["night_hold_s"])
        tc = t % period
        if tc < rise:
            u = _smoothstep(tc / rise)
        elif tc < rise * 2.0:
            u = _smoothstep(1.0 - (tc - rise) / rise)
        else:
            u = 0.0
    else:
        u = _smoothstep(t / rise)                    # one way, then hold

    # ── Sky: vertical gradient, horizon at the BOTTOM edge ──────────
    top_c, hor_c = _sky_colors(u)
    yn = y / (GRID - 1)                              # 0 top → 1 bottom
    # Horizon light pools near the bottom (steeper than linear).
    wgt = (yn ** 1.7)[:, np.newaxis]
    rgb = top_c[np.newaxis, :] * (1.0 - wgt) + hor_c[np.newaxis, :] * wgt

    # ── The sun: climbs from below the bottom edge ───────────────────
    # It starts peeking at u≈0.45 and sits ~2/3 up by full morning.
    sun_u = _smoothstep(min(1.0, max(0.0, (u - 0.45) / 0.55)))
    if sun_u > 0.0:
        sun_y = (GRID + 5.0) - sun_u * (GRID + 5.0 - 15.0)   # 49 → 15
        sun_r = max(0.5, float(p["sun_size"]))
        dx = x - (GRID - 1) / 2.0
        dy = y - sun_y
        d = np.sqrt(dx * dx + dy * dy)
        # Sun color warms from deep orange at the horizon to gold aloft.
        sun_c = np.array([255, 120, 40], dtype=np.float32) * (1.0 - sun_u) \
            + np.array([255, 225, 150], dtype=np.float32) * sun_u
        # Warm halo first (additive)…
        glow = np.exp(-(d * d) / (2.0 * (sun_r * 2.6) ** 2)) \
            * 0.55 * float(p["sun_glow"]) * sun_u
        rgb += glow[:, np.newaxis] * sun_c[np.newaxis, :]
        # …then the disc itself (composited over the sky).
        disc = np.clip((sun_r - d) / 1.1 + 1.0, 0.0, 1.0)[:, np.newaxis]
        rgb = rgb * (1.0 - disc) + sun_c[np.newaxis, :] * disc

    rgb = rgb * float(p["brightness"])
    # Randomized-but-static rounding (see _dither above) — kills the
    # banding/shimmer in the dark sky on the physical LEDs.
    frame[:] = np.clip(np.floor(rgb + _dither()), 0, 255).astype(np.uint8).tobytes()
