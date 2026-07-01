"""Rain — raindrops striking the surface, each one rippling out.

The matrix is the ground (or a pond) in the rain, seen from above.
Drops land at random moments and random spots: each one flashes as a
tiny splash, then spreads into a thin ring that grows and fades — and
the next drop is already landing somewhere else. Heavier or lighter
rain is one knob. The surface between drops stays pure black so the
ripples carry all the light.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.rain`.
"""
from __future__ import annotations

import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "rate": 0.9,             # drops per second (0.5 = sparse drizzle, 8 = downpour)
    "ripple_life_s": 8.8,    # how long one ripple lives, splash → faded out
    "ripple_size": 9.0,      # how far a ripple spreads before it dies (LEDs)
    "ring_width": 1.3,       # thickness of the ripple ring (LEDs)

    # Each ripple draws its colour from this cold palette and is rendered as a
    # gradient (a different palette colour at the centre vs. the spreading
    # edge), so the surface shimmers through blues and purples instead of one
    # flat blue. Add/replace entries to retune — all kept cold on purpose.
    "palette": [
        [70, 150, 215],   # rain blue
        [40,  90, 205],   # deeper blue
        [95,  70, 205],   # indigo / purple
        [55, 175, 200],   # teal-cyan
        [130, 80, 210],   # violet
    ],
    "color_ripple": [90, 140, 200],  # fallback if palette is emptied
    "color_splash": [200, 220, 255], # the first instant of impact (brighter)
    "color_ground": [0, 0, 0],       # between drops: pure black (no backlight)

    "size_jitter": 0.45,     # how much drop sizes vary (0 = all identical,
                             # 1 = from tiny to double-size)

    "fade_in_s": 2.0,        # gentle fade from black when the animation starts
    "start_delay_s": 0.0,    # hold pure black this long before the rain begins
                             # (the post-meditation rest screen uses it to leave
                             # a quiet dark moment after the breathing fades out)
    "brightness": 1.0,       # master brightness multiplier
}

_MAX_DROPS = 40              # safety cap on simultaneous ripples (render cost)


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


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    # ── One-time init (state is reset on each trigger/play) ─────────
    if "t0" not in st:
        st["t0"] = time_ms
        st["last_ms"] = time_ms
        st["rng"] = random.Random()
        st["drops"] = []         # [{x, y, born_s, size}]
        st["spawn_acc"] = 0.6    # a little head start: first drops land at once
    rng: random.Random = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0
    dt = min(0.1, max(0.0, (time_ms - st["last_ms"]) / 1000.0))
    st["last_ms"] = time_ms

    # Quiet hold: stay black until the delay has passed; no drops spawn,
    # so the first one lands only once the fade-in is underway.
    delay = max(0.0, float(p.get("start_delay_s", 0.0)))
    if t < delay:
        frame[:] = bytes(len(frame))
        return
    t -= delay

    life = max(0.3, float(p["ripple_life_s"]))
    base_size = float(p["ripple_size"])
    jitter = min(1.0, max(0.0, float(p["size_jitter"])))

    # Cold colour palette (np arrays). Each drop gets two indices → a gradient.
    pal = [np.array(c, dtype=np.float32) for c in
           (p["palette"] or [p["color_ripple"]])]
    npal = len(pal)

    # ── Spawn new drops (random timing, Poisson-ish) ─────────────────
    st["spawn_acc"] += float(p["rate"]) * dt
    while st["spawn_acc"] >= 1.0 and len(st["drops"]) < _MAX_DROPS:
        st["spawn_acc"] -= 1.0 * rng.uniform(0.6, 1.4)   # irregular rhythm
        ci = rng.randrange(npal)
        # The edge colour is a *different* palette entry from the centre, so
        # every ripple is a two-tone gradient (and neighbours differ).
        co = (ci + rng.randint(1, npal - 1)) % npal if npal > 1 else ci
        st["drops"].append({
            "x": rng.uniform(1.0, GRID - 2.0),
            "y": rng.uniform(1.0, GRID - 2.0),
            "born_s": t,
            "size": base_size * (1.0 + jitter * rng.uniform(-0.6, 1.0)),
            "ci": ci,
            "co": co,
        })
    # Drop the dead ones.
    st["drops"] = [d for d in st["drops"] if t - d["born_s"] < life]

    # ── Render ───────────────────────────────────────────────────────
    ground = np.array(p["color_ground"], dtype=np.float32)
    rgb = np.tile(ground, (TOTAL, 1))

    splash_c = np.array(p["color_splash"], dtype=np.float32)
    width = max(0.4, float(p["ring_width"]))

    for d in st["drops"]:
        u = (t - d["born_s"]) / life                 # 0 fresh → 1 gone
        dx = x - d["x"]
        dy = y - d["y"]
        r2 = dx * dx + dy * dy

        # The ring expands fast at first, then eases (like real ripples),
        # fading as it goes.
        radius = d["size"] * math.sqrt(u)
        r = np.sqrt(r2)
        ring = np.exp(-((r - radius) ** 2) / (2.0 * width * width))
        ring = ring * (1.0 - u) ** 1.4

        # The first instant: a small bright splash at the impact point.
        if u < 0.12:
            splash = math.cos(u / 0.12 * math.pi * 0.5)   # 1 → 0
            dot = np.exp(-r2 / (2.0 * 1.1 * 1.1)) * splash
            a = dot[:, np.newaxis]
            rgb = rgb * (1.0 - a) + splash_c[np.newaxis, :] * a

        # Per-ripple colour gradient: centre colour → edge colour across the
        # radius, and the gradient sweeps outward as the ring grows — so each
        # ripple shifts hue through the cold palette while it spreads.
        c_in = pal[d["ci"] % npal]
        c_out = pal[d["co"] % npal]
        g = np.clip(r / max(d["size"], 1.0), 0.0, 1.0)[:, np.newaxis]
        col = c_in[np.newaxis, :] * (1.0 - g) + c_out[np.newaxis, :] * g
        a = ring[:, np.newaxis]
        rgb = rgb * (1.0 - a) + col * a

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
