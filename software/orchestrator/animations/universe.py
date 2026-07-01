"""Deep universe — a black sky full of shimmering colored stars.

The background is true black (LEDs off) — deep space. Scattered across
it is a constellation of stars: most are faint, a handful burn bright,
and they come in real star colors — blue-white giants, white and warm
yellow suns, gold, orange and ember-red dwarfs. Every star twinkles on
its own slow rhythm, the brightest few carry a soft halo, and once in
a while a shooting star streaks quietly across the dark.

The constellation is laid out fresh on every start, so the sky is
never the same twice.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.universe`.
"""
from __future__ import annotations

import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "stars": 110,            # how many stars in the sky (44×44 has 1,936 LEDs;
                             # ~110 reads as a rich but uncrowded night sky)
    "bright_stars": 7,       # how many of them are the BRIGHT ones (with halos)

    "twinkle_speed": 1.0,    # how fast stars shimmer (1 = slow night-sky twinkle)
    "twinkle_depth": 0.7,    # how deeply they dim between shimmers (0 = steady,
                             # 1 = all the way to dark and back)

    "shooting_stars": True,  # the occasional meteor
    "shoot_every_s": 25.0,   # roughly how often one streaks by (seconds)

    "fade_in_s": 3.0,        # the sky "comes out" gradually at the start
    "brightness": 1.0,       # master brightness multiplier
}

# Star colors — a real night-sky mix (hot blue → white → warm → ember),
# with weights: most stars are in the white/warm middle.
_STAR_COLORS = (
    ([165, 195, 255], 0.18),     # blue-white
    ([225, 235, 255], 0.22),     # white
    ([255, 244, 214], 0.22),     # warm white
    ([255, 214, 140], 0.16),     # gold
    ([255, 160, 80], 0.12),      # orange
    ([255, 95, 60], 0.06),       # ember red
    ([180, 140, 255], 0.04),     # a rare violet one — magic
)


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


def _pick_color(rng: random.Random) -> list[float]:
    roll = rng.random()
    acc = 0.0
    for color, w in _STAR_COLORS:
        acc += w
        if roll <= acc:
            return list(color)
    return list(_STAR_COLORS[1][0])


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    n = max(5, int(p["stars"]))
    n_bright = min(n, max(0, int(p["bright_stars"])))

    # ── One-time init: lay out the constellation ────────────────────
    if "t0" not in st or st.get("n") != n:
        st["t0"] = time_ms
        st["n"] = n
        rng = st["rng"] = random.Random()
        # Distinct LED per star (no two stars share a pixel).
        cells = rng.sample(range(TOTAL), n)
        st["idx"] = np.array(cells, dtype=np.int64)
        st["color"] = np.array([_pick_color(rng) for _ in range(n)],
                               dtype=np.float32)
        # Most stars faint, a few bright (power-law-ish brightness).
        st["base"] = (np.array([rng.random() for _ in range(n)],
                               dtype=np.float32) ** 2.2) * 0.75 + 0.08
        st["base"][:n_bright] = np.array(
            [rng.uniform(0.85, 1.0) for _ in range(n_bright)], dtype=np.float32)
        # Personal twinkle rhythms: frequency, phase, and a second
        # faster flicker layered on top.
        st["f1"] = np.array([rng.uniform(0.05, 0.20) for _ in range(n)],
                            dtype=np.float32)
        st["f2"] = st["f1"] * np.array([rng.uniform(2.3, 3.7) for _ in range(n)],
                                       dtype=np.float32)
        st["ph1"] = np.array([rng.uniform(0, 2 * math.pi) for _ in range(n)],
                             dtype=np.float32)
        st["ph2"] = np.array([rng.uniform(0, 2 * math.pi) for _ in range(n)],
                             dtype=np.float32)
        st["next_shoot"] = float(p["shoot_every_s"]) * rng.uniform(0.4, 1.0)
        st["shoot"] = None
    rng = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0

    # ── Twinkle ──────────────────────────────────────────────────────
    spd = float(p["twinkle_speed"])
    depth = min(1.0, max(0.0, float(p["twinkle_depth"])))
    w1 = np.sin(2.0 * math.pi * st["f1"] * spd * t + st["ph1"])
    w2 = np.sin(2.0 * math.pi * st["f2"] * spd * t + st["ph2"])
    shimmer = 0.5 + 0.5 * (0.7 * w1 + 0.3 * w2)      # 0..1 per star
    level = st["base"] * (1.0 - depth + depth * shimmer)

    rgb = np.zeros((TOTAL, 3), dtype=np.float32)
    np.maximum.at(rgb, st["idx"], st["color"] * level[:, np.newaxis])

    # Soft halos around the brightest stars.
    for k in range(n_bright):
        i = int(st["idx"][k])
        sx, sy = i % GRID, i // GRID
        dx = x - sx
        dy = y - sy
        halo = np.exp(-(dx * dx + dy * dy) / (2.0 * 1.1 * 1.1)) \
            * level[k] * 0.55
        rgb += halo[:, np.newaxis] * st["color"][k][np.newaxis, :]

    # ── The occasional shooting star ─────────────────────────────────
    if p.get("shooting_stars"):
        if st["shoot"] is None and t >= st["next_shoot"]:
            # Launch: a random straight line across the sky.
            ang = rng.uniform(0, 2 * math.pi)
            cx, cy = rng.uniform(10, GRID - 10), rng.uniform(10, GRID - 10)
            st["shoot"] = {"x0": cx - math.cos(ang) * 30, "y0": cy - math.sin(ang) * 30,
                           "dx": math.cos(ang), "dy": math.sin(ang),
                           "born_s": t, "speed": rng.uniform(38, 55)}
        sh = st["shoot"]
        if sh is not None:
            age = t - sh["born_s"]
            dist = sh["speed"] * age
            if dist > 75.0:                          # crossed the sky → done
                st["shoot"] = None
                st["next_shoot"] = t + float(p["shoot_every_s"]) * rng.uniform(0.6, 1.6)
            else:
                hx = sh["x0"] + sh["dx"] * dist
                hy = sh["y0"] + sh["dy"] * dist
                # Distance behind the head along the path → fading tail.
                rel = (x - hx) * sh["dx"] + (y - hy) * sh["dy"]   # ≤0 behind
                perp = -(x - hx) * sh["dy"] + (y - hy) * sh["dx"]
                behind = np.clip(-rel, 0.0, 9.0)
                tail = (1.0 - behind / 9.0) * np.exp(-(perp * perp) / (2.0 * 0.5 * 0.5))
                tail = np.where(rel <= 0.5, tail, 0.0) * 0.9
                rgb += tail[:, np.newaxis] * np.array([220, 230, 255],
                                                      dtype=np.float32)[np.newaxis, :]

    # The sky comes out gradually at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
