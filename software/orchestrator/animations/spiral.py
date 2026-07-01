"""Spiral burst — segmented rays of blues and purples streaming from
the center, after Nadia's reference image.

A sunburst of many rays radiates from the center of the matrix, each
ray chopped into short blocks of color — electric blue, cyan, violet,
magenta, deep navy — separated by thin black gaps, like stacked paint
chips. The whole figure slowly TURNS, the rays curve into a gentle
spiral, and the color blocks stream slowly outward along each ray, so
the pattern keeps flowing out of the center forever.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.spiral`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "rays": 16,              # how many rays radiate from the center
    "ray_fill": 0.62,        # how much of each sector the ray fills
                             # (the rest is the black gap between rays)
    "segment_len": 4.0,      # length of one color block along a ray (LEDs)

    "rotate_speed_deg_s": 3.0,   # how fast the whole burst turns
    "twist": 0.12,           # how much the rays curve into a spiral
                             # (0 = straight sunburst, 1 = strongly wound)
    "flow_speed": 1.5,       # how fast the color blocks stream outward
                             # (LEDs per second; negative = stream inward)

    "shuffle_every_s": 0.0,  # > 0: every N seconds all blocks also jump to
                             # fresh colors (0 = colors only change by flowing)

    "brightness_center": 0.35,   # rays are dimmer near the center (like the
                                 # reference) and reach full brightness out wide
    "fade_in_s": 2.0,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}

# The paint-chip palette from the reference: blues, cyans, purples,
# magentas, and the occasional near-black navy block that reads as a
# "missing" chip and keeps the pattern lively.
_PALETTE = np.array([
    [25, 60, 230],       # electric blue
    [80, 150, 255],      # bright sky blue
    [130, 200, 255],     # pale cyan
    [105, 25, 215],      # violet
    [175, 55, 230],      # magenta-purple
    [10, 15, 90],        # deep navy (almost off)
    [45, 90, 240],       # royal blue
    [140, 70, 250],      # lavender
    [15, 35, 150],       # dark blue
    [200, 90, 235],      # bright orchid
], dtype=np.float32)


# Per-LED polar coordinates, computed once (the grid never changes).
_R = None
_THETA = None


def _geometry():
    global _R, _THETA
    if _R is None:
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - CENTER
            dy[i] = row - CENTER
        _R = np.sqrt(dx * dx + dy * dy)
        _THETA = np.arctan2(dy, dx)
    return _R, _THETA


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the fade-in always replays.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    n_rays = max(4, int(p["rays"]))
    seg_len = max(1.0, float(p["segment_len"]))
    rot = math.radians(float(p["rotate_speed_deg_s"])) * t
    twist = float(p["twist"]) * 0.12                 # radians of curl per LED

    # ── Which ray (and where in it) is each LED? ─────────────────────
    # Subtracting twist*r makes the spoke boundaries curl with radius —
    # that's what bends the sunburst into a spiral.
    sector = 2.0 * math.pi / n_rays
    a = np.mod(theta - rot - twist * r, sector) / sector   # 0..1 across sector
    # Ray mask with a slightly soft edge (hard cut shimmers at 44 px).
    fill = min(0.98, max(0.1, float(p["ray_fill"])))
    edge = 0.06
    ray = np.clip((fill / 2.0 - np.abs(a - 0.5)) / edge + 0.5, 0.0, 1.0)

    # Spoke index + block index → a stable pseudo-random color per block.
    spoke = np.floor((theta - rot - twist * r) / sector).astype(np.int64) % n_rays
    flow = float(p["flow_speed"]) * t
    block = np.floor((r - flow) / seg_len).astype(np.int64)
    epoch = 0
    if float(p["shuffle_every_s"]) > 0.0:
        epoch = int(t / float(p["shuffle_every_s"]))
    h = (spoke * 73856093 + block * 19349663 + epoch * 83492791)
    idx = np.mod(np.abs(h), len(_PALETTE))
    color = _PALETTE[idx]                            # (TOTAL, 3)

    # Thin black seams between blocks along the ray (the chip edges).
    in_block = np.mod(r - flow, seg_len) / seg_len   # 0..1 within a block
    seam = np.clip((np.minimum(in_block, 1.0 - in_block)) / 0.12, 0.0, 1.0)

    # Dimmer toward the center, full brightness out wide (per reference).
    bc = min(1.0, max(0.0, float(p["brightness_center"])))
    radial = bc + (1.0 - bc) * np.clip(r / (CENTER * 1.1), 0.0, 1.0)

    field = ray * seam * radial

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = field[:, np.newaxis] * color * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
