"""Color blobs — a slow lava-lamp of drifting, color-shifting light.

The WHOLE matrix is always lit: a soft two-color wash slowly rotates
and re-colors across the full grid, and a handful of smaller, rounder
blobs wander on top of it. Each blob eases smoothly toward a random
nearby waypoint, picks a new one when it arrives, and slowly cycles
its color. Every so often ONE blob takes a long glide all the way
across the matrix, passing over the others (they take turns, in a
random order).

Blobs blend OVER what's beneath them (not additive), so a crossing
blob reads as a color sweeping across another, not as a white flash.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.blobs`.
"""
from __future__ import annotations

import colorsys
import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "blobs": 5,              # how many blobs wander around
    "blob_size": 4.0,        # softness radius of each blob in LEDs (smaller = tighter shapes)
    "size_breathe": 0.2,     # how much each blob slowly swells/shrinks (0 = fixed size)
    "blob_alpha": 0.9,       # how solidly a blob covers what's under it (1 = opaque center)

    "drift_speed": 2.5,      # how fast blobs ease around (1 = the original slow stroll)
    "step": 10.0,            # typical hop distance between wander waypoints (LEDs)
    "sweep_every_s": 12.0,   # roughly how often one blob glides across the whole matrix

    "color_speed": 2.0,      # how fast colors cycle (1 = full color wheel every ~2 min per blob)
    "saturation": 0.9,       # color richness (1 = fully saturated, 0 = white)

    # --- Background wash (keeps the whole matrix lit) ---
    "bg_brightness": 0.35,   # brightness of the full-matrix color wash (0 = black gaps again)
    "bg_color_speed": 2.0,   # how fast the wash re-colors (1 = slow, calm)

    "fade_in_s": 2.0,        # gentle fade from black when the animation starts
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


def _hsv(hue: float, sat: float) -> np.ndarray:
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, sat, 1.0)
    return np.array([r * 255.0, g * 255.0, b * 255.0], dtype=np.float32)


_MARGIN = 4.0  # keep waypoint targets this far inside the matrix edge


def _new_blob(rng: random.Random) -> dict:
    x = rng.uniform(_MARGIN, GRID - 1 - _MARGIN)
    y = rng.uniform(_MARGIN, GRID - 1 - _MARGIN)
    return {
        "x": x, "y": y,
        "tx": x, "ty": y,                       # current waypoint
        "hue": rng.random(),                    # starting color
        "hue_speed": rng.uniform(0.6, 1.4),     # personal color-cycling pace (×)
        "phase": rng.uniform(0.0, 2.0 * math.pi),
    }


# Fallback state for callers that pass none (keeps motion smooth anyway).
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()
    st = state if state is not None else _FALLBACK_STATE

    n = max(1, int(p["blobs"]))

    # ── One-time init (state is reset on each trigger/play) ─────────
    if "t0" not in st or len(st.get("blobs", ())) != n:
        st["t0"] = time_ms
        st["last_ms"] = time_ms
        st["rng"] = random.Random()
        st["blobs"] = [_new_blob(st["rng"]) for _ in range(n)]
        st["next_sweep_s"] = float(p["sweep_every_s"]) * 0.5
        st["last_sweeper"] = -1
    rng: random.Random = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0
    dt = min(0.1, max(0.0, (time_ms - st["last_ms"]) / 1000.0))
    st["last_ms"] = time_ms

    speed = float(p["drift_speed"])
    step = float(p["step"])
    sat = min(1.0, max(0.0, float(p["saturation"])))
    w_color = float(p["color_speed"]) / 120.0     # color wheels per second

    # ── Movement ─────────────────────────────────────────────────────
    # Every so often, ONE blob (random, taking turns) gets a waypoint on
    # the far side of the matrix — a long smooth glide across everyone.
    if t >= st["next_sweep_s"] and n > 1:
        idx = rng.randrange(n)
        while idx == st["last_sweeper"]:
            idx = rng.randrange(n)
        st["last_sweeper"] = idx
        b = st["blobs"][idx]
        hi = GRID - 1 - _MARGIN
        b["tx"] = min(hi, max(_MARGIN, 2.0 * CENTER - b["x"] + rng.uniform(-8, 8)))
        b["ty"] = min(hi, max(_MARGIN, 2.0 * CENTER - b["y"] + rng.uniform(-8, 8)))
        st["next_sweep_s"] = t + float(p["sweep_every_s"]) * rng.uniform(0.7, 1.3)

    # Each blob eases toward its waypoint (exponential approach: starts
    # moving, glides, slows into arrival — never a jump). On arrival it
    # picks a fresh random waypoint nearby.
    ease = 1.0 - math.exp(-0.18 * speed * dt)
    hi = GRID - 1 - _MARGIN
    for b in st["blobs"]:
        b["x"] += (b["tx"] - b["x"]) * ease
        b["y"] += (b["ty"] - b["y"]) * ease
        if abs(b["tx"] - b["x"]) < 1.2 and abs(b["ty"] - b["y"]) < 1.2:
            b["tx"] = min(hi, max(_MARGIN, b["x"] + rng.uniform(-step, step)))
            b["ty"] = min(hi, max(_MARGIN, b["y"] + rng.uniform(-step, step)))

    # ── Background wash: the whole matrix lit, slowly re-coloring ───
    # Two hues on opposite sides of the wheel, blended across a slowly
    # rotating direction — a soft gradient that never sits still and
    # never goes dark.
    w_bg = float(p["bg_color_speed"]) / 240.0
    hue_a = (0.62 + w_bg * t) % 1.0
    hue_b = (hue_a + 0.35) % 1.0
    ang = 2.0 * math.pi * t / 150.0               # gradient direction rotates ~2.5 min
    proj = ((x - CENTER) * math.cos(ang) + (y - CENTER) * math.sin(ang)) / GRID
    mix = (0.5 + 0.5 * np.sin(proj * math.pi * 2.0 + t * 0.05))[:, np.newaxis]
    c_a = _hsv(hue_a, sat * 0.9)
    c_b = _hsv(hue_b, sat * 0.9)
    rgb = (c_a[np.newaxis, :] * (1.0 - mix) + c_b[np.newaxis, :] * mix) \
        * float(p["bg_brightness"])

    # ── Blobs, composited OVER the background (and each other) ──────
    size = max(1.0, float(p["blob_size"]))
    breathe = float(p["size_breathe"])
    alpha = min(1.0, max(0.0, float(p["blob_alpha"])))
    for b in st["blobs"]:
        s = size * (1.0 + breathe * math.sin(t * 0.5 + b["phase"]))
        hue = (b["hue"] + w_color * b["hue_speed"] * t) % 1.0
        color = _hsv(hue, sat)
        dx = x - b["x"]
        dy = y - b["y"]
        a = (np.exp(-(dx * dx + dy * dy) / (2.0 * s * s)) * alpha)[:, np.newaxis]
        rgb = rgb * (1.0 - a) + color[np.newaxis, :] * a

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = np.clip(rgb * (float(p["brightness"]) * fade), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
