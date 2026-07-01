"""Disco — a color-tile dance floor with a sweeping spotlight.

The matrix becomes a classic light-up dance floor: a grid of square
tiles in hot neon colors. On every beat a bunch of tiles flip to new
colors with a little flash, then settle until their next turn. A soft
spotlight sweeps round and round over the floor like the glint of a
mirror ball. No strobing — it pulses on the beat but never flashes the
whole floor at once.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.disco`.
"""
from __future__ import annotations

import math
import random

import numpy as np

from grid import GRID_POSITIONS, GRID, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "bpm": 122.0,            # the beat — tiles flip in time with this
    "tile_size": 4,          # tile edge in LEDs (4 → an 11×11 tile floor)
    "change_fraction": 0.28, # what share of tiles flip color on each beat
    "flash": 0.45,           # how hard a freshly-flipped tile flashes (0 = none)
    "grout": 0.6,            # brightness of the thin seams between tiles
                             # (1 = invisible seams, 0.4 = strong grid look)

    "spotlight": 0.4,        # strength of the sweeping mirror-ball beam (0 = off)
    "spotlight_speed_deg_s": 50.0,   # how fast the beam circles the floor

    "base_brightness": 0.75, # tiles' resting brightness between flashes
    "fade_in_s": 1.0,        # quick fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}

# Hot neon dance-floor palette.
_PALETTE = np.array([
    [255, 0, 110],       # hot pink
    [0, 200, 255],       # electric cyan
    [255, 200, 0],       # gold
    [170, 0, 255],       # purple
    [0, 255, 110],       # neon green
    [255, 80, 0],        # orange
    [40, 60, 255],       # club blue
    [255, 0, 30],        # red
], dtype=np.float32)


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

    tile = max(2, int(p["tile_size"]))
    n_side = math.ceil(GRID / tile)
    n_tiles = n_side * n_side

    # ── One-time init (state is reset on each trigger/play) ─────────
    if "t0" not in st or st.get("tile") != tile:
        st["t0"] = time_ms
        st["tile"] = tile
        rng = st["rng"] = random.Random()
        st["colors"] = _PALETTE[
            np.array([rng.randrange(len(_PALETTE)) for _ in range(n_tiles)])]
        st["glow"] = np.zeros(n_tiles, dtype=np.float32)
        st["beat"] = -1
        # Per-LED tile index (depends only on tile size).
        st["tile_idx"] = (np.floor(y / tile) * n_side
                          + np.floor(x / tile)).astype(np.int64)
        # Seam mask: thin darker lines where tiles meet.
        on_seam = (np.mod(x, tile) < 0.5) | (np.mod(y, tile) < 0.5)
        st["seam"] = np.where(on_seam, 1.0, 0.0).astype(np.float32)
        st["last_ms"] = time_ms
    rng = st["rng"]
    t = (time_ms - st["t0"]) / 1000.0
    dt = min(0.1, max(0.0, (time_ms - st["last_ms"]) / 1000.0))
    st["last_ms"] = time_ms

    # ── The beat: flip a batch of tiles to fresh colors ──────────────
    beat = int(t * float(p["bpm"]) / 60.0)
    if beat != st["beat"]:
        st["beat"] = beat
        n_flip = max(1, int(n_tiles * float(p["change_fraction"])))
        idx = rng.sample(range(n_tiles), n_flip)
        for i in idx:
            st["colors"][i] = _PALETTE[rng.randrange(len(_PALETTE))]
        st["glow"][idx] = 1.0                        # fresh tiles flash…
    st["glow"] *= math.exp(-dt * 5.0)                # …and settle quickly

    # ── Compose the floor ────────────────────────────────────────────
    base = float(p["base_brightness"])
    level = base + float(p["flash"]) * st["glow"]    # per tile
    rgb = st["colors"][st["tile_idx"]] * level[st["tile_idx"]][:, np.newaxis]

    # Thin seams between tiles.
    grout = min(1.0, max(0.0, float(p["grout"])))
    rgb = rgb * (1.0 - st["seam"] * (1.0 - grout))[:, np.newaxis]

    # ── The mirror-ball spotlight, circling the floor ────────────────
    spot = float(p["spotlight"])
    if spot > 0.0:
        ang = math.radians(float(p["spotlight_speed_deg_s"])) * t
        sx = CENTER + math.cos(ang) * CENTER * 0.62
        sy = CENTER + math.sin(ang) * CENTER * 0.62
        dx = x - sx
        dy = y - sy
        beam = np.exp(-(dx * dx + dy * dy) / (2.0 * 7.0 * 7.0)) * spot
        rgb = rgb * (1.0 + beam[:, np.newaxis])      # brightens what it passes

    # Quick fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
