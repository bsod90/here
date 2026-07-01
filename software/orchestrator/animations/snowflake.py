"""Snowflake — one intricate flake, slowly transforming between three
different snowflake designs.

A six-fold symmetric snowflake sits centered on the matrix. It does not
move — instead its SHAPE slowly changes: every branch, arm and the
central plate glides from one design to the next (a classic dendrite →
a feathery fern → a broad stellar plate → back), each design holding
for a while before melting into the next. Because the change is a true
morph (the same branches sliding, growing, shrinking), it reads as one
living crystal, not a slideshow.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.snowflake`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "hold_s": 8.0,           # how long each snowflake design holds its shape
    "morph_s": 6.0,          # how long the melt from one design to the next takes

    "tint": [185, 220, 255], # the ice color (cool blue-white)
    "tint_variation": 0.5,   # each design leans its own way around this tint
                             # (0 = all identical color, 1 = clearly different)

    "sparkle": 0.25,         # faint shimmering along the crystal (0 = steady)
    "edge_cutoff": 0.30,     # dim glow below this goes OFF — crisp crystal edges

    "fade_in_s": 2.0,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}

# ── The three designs ────────────────────────────────────────────────
# Each design: (arm_reach, arm_width, plate_radius, branches) where
# branches = 4 × (position along the arm 0..1, length, width, angle°).
# All three have the SAME structure (4 branches), so every number can
# glide smoothly to its counterpart in the next design.
_DESIGNS = (
    # 1. Classic dendrite — long slim arms, big branches near the tips.
    (21.0, 0.75, 2.8, ((0.42, 5.5, 0.65, 58.0),
                       (0.60, 7.5, 0.70, 56.0),
                       (0.78, 8.5, 0.75, 54.0),
                       (0.93, 4.5, 0.60, 50.0))),
    # 2. Feathery fern — branches all along the arm, evenly stepped.
    (18.5, 0.85, 4.2, ((0.30, 5.0, 0.65, 62.0),
                       (0.50, 6.0, 0.65, 60.0),
                       (0.70, 6.5, 0.65, 58.0),
                       (0.88, 4.5, 0.60, 56.0))),
    # 3. Stellar plate — broad hex heart, short arms, tip ornaments.
    (15.5, 1.00, 6.5, ((0.55, 3.0, 0.80, 64.0),
                       (0.74, 4.5, 0.80, 60.0),
                       (0.90, 6.0, 0.85, 55.0),
                       (0.99, 2.5, 0.70, 48.0))),
)
# Per-design tint lean: (toward-blue, neutral, toward-violet).
_DESIGN_LEAN = ((-25, 0, 25), (10, 10, 0), (15, -15, 30))


# Per-LED folded snowflake coordinates, computed once.
_ALONG = None    # distance along the nearest arm axis
_LAT = None      # perpendicular distance from that axis (≥ 0, mirrored)
_R = None


def _geometry():
    """Fold the grid into one 30° wedge of 6-fold mirror symmetry: every
    LED gets (along, lat) coordinates relative to the nearest of the six
    arm axes. Drawing ONE arm + branches then appears 6× mirrored."""
    global _ALONG, _LAT, _R
    if _ALONG is None:
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - CENTER
            dy[i] = row - CENTER
        _R = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)
        sector = math.pi / 3.0                       # 60° per arm
        a = np.mod(theta, sector)
        a = np.minimum(a, sector - a)                # mirror fold → 0..30°
        _ALONG = _R * np.cos(a)
        _LAT = _R * np.sin(a)
    return _ALONG, _LAT, _R


def _lerp(a: float, b: float, u: float) -> float:
    return a + (b - a) * u


def _smoothstep(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _flake_field(along, lat, r, reach, arm_w, plate_r, branches) -> np.ndarray:
    """Draw the snowflake (one folded wedge → appears 6-fold mirrored).
    Returns 0..1 intensity per LED."""
    # Main arm: a slim ridge along the axis, tapering toward the tip.
    taper = np.clip(1.0 - along / reach, 0.0, 1.0) ** 0.35
    arm = np.exp(-(lat * lat) / (2.0 * arm_w * arm_w)) * taper
    arm = np.where(along <= reach, arm, 0.0)
    field = arm.astype(np.float32)

    # Side branches: short ridges leaving the arm at an angle, mirrored
    # automatically by the fold.
    for (pos, length, b_w, ang_deg) in branches:
        d0 = pos * reach
        b = math.radians(ang_deg)
        # Branch direction in (along, lat) space.
        ca, sa = math.cos(b), math.sin(b)
        rel_a = along - d0
        s = rel_a * ca + lat * sa                    # distance along branch
        q = -rel_a * sa + lat * ca                   # distance across branch
        b_taper = np.clip(1.0 - s / max(0.3, length), 0.0, 1.0) ** 0.5
        br = np.exp(-(q * q) / (2.0 * b_w * b_w)) * b_taper
        br = np.where((s >= 0.0) & (s <= length), br, 0.0)
        field = np.maximum(field, br.astype(np.float32))

    # Central plate: a soft hex-ish heart (round is close enough at 44px,
    # the folded arms already give it a hex silhouette).
    plate = np.clip((plate_r - r) / 1.6 + 1.0, 0.0, 1.0)
    field = np.maximum(field, plate.astype(np.float32))
    return field


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    along, lat, r = _geometry()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the cycle always starts from design 1.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    hold = max(0.5, float(p["hold_s"]))
    morph = max(0.5, float(p["morph_s"]))
    seg = hold + morph
    n_d = len(_DESIGNS)
    cycle_pos = t % (seg * n_d)
    i = int(cycle_pos // seg)                        # current design
    j = (i + 1) % n_d                                # the one it melts into
    tc = cycle_pos - i * seg
    u = _smoothstep((tc - hold) / morph) if tc > hold else 0.0

    # ── Interpolate every shape number between design i and j ───────
    (re_a, aw_a, pl_a, br_a) = _DESIGNS[i]
    (re_b, aw_b, pl_b, br_b) = _DESIGNS[j]
    reach = _lerp(re_a, re_b, u)
    arm_w = _lerp(aw_a, aw_b, u)
    plate = _lerp(pl_a, pl_b, u)
    branches = tuple(tuple(_lerp(a, b, u) for a, b in zip(ba, bb))
                     for ba, bb in zip(br_a, br_b))

    field = _flake_field(along, lat, r, reach, arm_w, plate, branches)

    # Crisp crystal edges, black background.
    cut = min(0.9, max(0.0, float(p["edge_cutoff"])))
    field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)

    # Faint shimmer along the crystal (slow, spatial — like ice catching
    # light), never strobing.
    spark = float(p["sparkle"])
    if spark > 0.0:
        tw = 0.5 + 0.5 * np.sin(r * 1.7 + t * 0.9) * np.sin(lat * 2.3 - t * 0.7)
        field = field * (1.0 - spark + spark * tw)

    # ── Color: the ice tint, leaning per design ─────────────────────
    tint = np.array(p["tint"], dtype=np.float32)
    var = min(1.0, max(0.0, float(p["tint_variation"])))
    lean_a = np.array(_DESIGN_LEAN[i], dtype=np.float32)
    lean_b = np.array(_DESIGN_LEAN[j], dtype=np.float32)
    color = tint + (lean_a * (1.0 - u) + lean_b * u) * var

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = field[:, np.newaxis] * color[np.newaxis, :] \
        * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
