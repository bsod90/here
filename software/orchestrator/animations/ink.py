"""Ink in water — colored drops diffusing through dark water.

The matrix is the water: black (LEDs off). Every so often a drop of
colored ink lands somewhere and slowly SPREADS — fast at first, then
slower and slower (like real diffusion). Its edge is not a circle: a
set of slowly-drifting waves bends the outline, so the shape keeps
changing as it grows — bulging one way, thinning another. As the drop
ages its solid center thins out, leaving a soft drifting ring of ink
that finally dissolves to nothing. Drops are staggered, so there's
always ink alive somewhere, each drop its own color.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.ink`.
"""
from __future__ import annotations

import colorsys
import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "drops": 3,              # how many ink drops can be alive at once
    "drop_life_s": 22.0,     # how long one drop lives, birth → fully dissolved
    "max_radius": 14.0,      # how far a drop spreads before dissolving (LEDs)
    "edge_width": 2.2,       # softness of the ink's outer edge (LEDs)

    "wobble": 0.35,          # how UN-round the drops are (0 = perfect circles, 0.6 = wild)
    "evolve_speed": 1.0,     # how fast the shape morphs while spreading (2 = livelier)
    "drift": 2.5,            # how far a drop's center slowly drifts, like a current (LEDs)

    "saturation": 0.95,      # ink color richness (1 = fully saturated)
    "fill": 1.0,             # how solid a fresh drop's center is (0 = rings only)

    "fade_in_s": 1.5,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}


# Per-LED x/y coordinates, computed once (the grid never changes).
_X = None
_Y = None


def _geometry():
    global _X, _Y
    if _X is None:
        _X = np.empty(TOTAL, dtype=np.float32)
        _Y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            _X[i] = col
            _Y[i] = row
    return _X, _Y


def _new_drop(rng: random.Random, born_s: float,
              avoid: list[tuple[float, float]] | None = None) -> dict:
    """One ink drop: where it lands, its color, and the 'personality' of
    its wobbly outline (3 wave harmonics with random sizes + speeds).
    `avoid` = centers of the other live drops — we sample several landing
    spots and keep the one farthest from all of them, so drops don't
    land on top of each other."""
    margin = 8.0
    cx = cy = None
    best = -1.0
    for _ in range(12):
        px = rng.uniform(margin, GRID - 1 - margin)
        py = rng.uniform(margin, GRID - 1 - margin)
        d = min((math.hypot(px - ax, py - ay) for ax, ay in (avoid or [])),
                default=1e9)
        if d > best:
            best, cx, cy = d, px, py
    return {
        "born": born_s,
        "cx": cx,
        "cy": cy,
        "hue": rng.random(),
        # Outline waves: (how many lobes, how strong, how fast it drifts)
        "waves": [(rng.choice([2, 3, 3, 4, 5]),
                   rng.uniform(0.5, 1.0),
                   rng.uniform(-0.6, 0.6))
                  for _ in range(3)],
        # Slow current pushing the drop: direction + personal pace.
        "drift_ang": rng.uniform(0.0, 2.0 * math.pi),
        "drift_pace": rng.uniform(0.6, 1.4),
    }


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    n = max(1, int(p["drops"]))
    life = max(2.0, float(p["drop_life_s"]))

    # ── One-time init (state is reset on each trigger/play) ─────────
    # Drops are staggered: the first lands right away, the next a third
    # of a life later, and so on — so the water is never empty and never
    # all-new at once.
    if "t0" not in st or len(st.get("drops", ())) != n:
        st["t0"] = time_ms
        st["rng"] = random.Random()
        st["drops"] = []
        for k in range(n):
            taken = [(d["cx"], d["cy"]) for d in st["drops"]]
            st["drops"].append(_new_drop(st["rng"], born_s=k * life / n,
                                         avoid=taken))
    rng: random.Random = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0

    max_r = float(p["max_radius"])
    edge_w = max(0.5, float(p["edge_width"]))
    wobble = float(p["wobble"])
    evolve = float(p["evolve_speed"])
    drift = float(p["drift"])
    sat = min(1.0, max(0.0, float(p["saturation"])))
    fill_amt = float(p["fill"])

    rgb = np.zeros((TOTAL, 3), dtype=np.float32)
    for d in st["drops"]:
        age = t - d["born"]
        if age < 0.0:
            continue                       # hasn't landed yet
        if age >= life:                    # fully dissolved → a new drop lands
            taken = [(o["cx"], o["cy"]) for o in st["drops"] if o is not d]
            d.update(_new_drop(rng, born_s=t + rng.uniform(0.0, 0.15 * life),
                               avoid=taken))
            continue
        u = age / life                     # 0 = just landed, 1 = gone

        # Diffusion: radius grows like sqrt(time) — quick bloom, then
        # slower and slower, the way real ink spreads.
        radius = max(0.6, max_r * math.sqrt(u))

        # The drop's center drifts slowly with the "current".
        slide = drift * u * d["drift_pace"]
        cx = d["cx"] + slide * math.cos(d["drift_ang"])
        cy = d["cy"] + slide * math.sin(d["drift_ang"])

        dx = x - cx
        dy = y - cy
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)

        # Wobbly, evolving outline: each LED's "edge distance" is bent
        # by a few slow waves around the drop, drifting at their own
        # speeds — the shape never stops changing.
        bend = np.zeros(TOTAL, dtype=np.float32)
        for (lobes, amp, spd) in d["waves"]:
            bend += amp * np.sin(lobes * theta + spd * evolve * age)
        local_r = radius * (1.0 + wobble * bend / 3.0)
        local_r = np.maximum(0.5, local_r)

        norm = r / local_r                 # 0 center → 1 at the wobbly edge

        # Ink body: a solid center that THINS as the drop ages (the ink
        # disperses), plus a soft edge ring that carries the shape. A
        # young drop is filled wall-to-wall; the hollowing creeps in
        # gradually as it spreads.
        hollow = 0.8 + 2.2 * u             # how sharply the fill decays w/ age
        center_fill = np.exp(-norm * norm * hollow) * fill_amt * (1.0 - u * 0.85)
        # The edge ring DEVELOPS as the ink disperses: a young drop is a
        # solid blot with a soft edge; the bright outline emerges with age.
        ring_amp = 0.25 + 0.60 * u
        ring = np.exp(-((r - local_r) ** 2) / (2.0 * edge_w * edge_w)) * ring_amp
        body = np.maximum(center_fill, ring)

        # Birth ramp (drop "lands" over ~0.8 s) and final dissolve.
        ramp_in = min(1.0, age / 0.8)
        dissolve = 1.0 - max(0.0, (u - 0.65) / 0.35) ** 1.5
        body *= ramp_in * max(0.0, dissolve)

        # Ink color, very slowly shifting while it spreads.
        hue = (d["hue"] + 0.04 * u) % 1.0
        cr, cg, cb = colorsys.hsv_to_rgb(hue, sat, 1.0)
        color = np.array([cr * 255.0, cg * 255.0, cb * 255.0], dtype=np.float32)

        rgb += body[:, np.newaxis] * color

    # Gentle fade from black at the start of the whole animation.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = np.clip(rgb * (float(p["brightness"]) * fade), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
