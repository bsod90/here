"""4-petal flower animation for Nadia's Playground.

A pink flower whose four petals reach out toward the four corners of the
platform (but stop short of the edges), with a small glowing center. By
default the flower is static, held fully open (set `animate: true` to make
it breathe).

This module is intentionally self-contained and HEAVILY commented so it's
easy to tweak. Every visual knob lives in `DEFAULTS` below with a plain
explanation of what it does and which way to nudge it. The Playground
merges any overrides from `config.playground.flower` on top of these.

Geometry note: the grid is 44×44, center at (21.5, 21.5). The four
corners lie on the diagonals (45°, 135°, 225°, 315°), so with the default
`base_rotation_deg = 45` the petals point straight at the corners. A reach
of ~30 would touch the corners; smaller keeps the petals inside the matrix.
"""
from __future__ import annotations

import colorsys
import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
# Tweak these (or override via config.playground.flower). Each line says
# what it does and how to change the feel.
DEFAULTS = {
    # --- Shape ---
    "petals": 4,                 # number of petals (4 = toward the corners)
    "base_rotation_deg": 45.0,   # 45 aims petals AT the corners; 0 aims at the edges
    "petal_reach": 23.0,         # how far a petal stretches (≈30 hits the corners; smaller stays inside)
    "petal_width": 3.6,          # fatness of each petal (smaller = thinner = more gap between petals)
    "petal_base_width": 0.5,     # min width at base/tip so petals don't pinch to nothing
    "edge_cutoff": 0.22,         # dim glow below this is turned fully OFF (black) — bigger = sharper petals, more black gap
    "edge_light_amount": 0.06,   # how much LIGHTER the petal edges get (0 = flat color, 1 = white rim)

    # --- Petal color: a radial gradient from center → tip ---
    "color_center": [110, 0, 45],    # deep, saturated pink/magenta near the center
    "color_tip":    [8, 0, 115],     # deep, saturated blue out at the tips

    # --- Inner petal (off) ---
    "inner_petal": False,        # draw a narrow light petal inside each big petal
    "inner_reach_frac": 0.62,    # inner petal length as a fraction of the big petal
    "inner_width": 1.1,          # how narrow the inner petal is
    "inner_light_amount": 0.7,   # how light the inner petal is (0 = same color, 1 = white)

    # --- Timed sequence (the intro choreography) ---
    "sequence": True,            # true = play the timed intro below; false = just sit fully open & static
    "center_time_s": 5.0,        # how long ONLY the center shows before petals appear
    "grow_time_s": 3.0,          # how long the petals take to grow out from the center
    "hold_time_s": 10.0,         # how long the open flower holds still before it starts moving
    "rotate_speed_deg_s": 8.0,   # how fast it rotates once moving (8°/s = one full turn every 45s)
    "center_fade_s": 1.5,        # how long the center takes to fade in at the very start

    # --- Center / core ---
    "core_size": 1.6,            # radius of the glowing flower center (smaller = tighter dot)
    "core_brightness": 1.0,      # how bright the center glows (0 = no core)
    "core_color": [255, 210, 120],  # warm gold

    # --- Overall ---
    "brightness": 1.0,           # master brightness multiplier (0–1+)
}


# Per-LED geometry, precomputed once (the grid never changes at runtime).
_R = None      # distance from center, per LED
_THETA = None  # angle from center, per LED (radians)


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


def _smoothstep(u: float) -> float:
    """Ease 0→1 with soft start and stop (no abrupt motion)."""
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _cycled_color(base_rgb, hue_offset: float):
    """Rotate a color around the color wheel by `hue_offset` (0..1)."""
    r, g, b = (c / 255.0 for c in base_rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + hue_offset) % 1.0
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return np.array([nr * 255.0, ng * 255.0, nb * 255.0], dtype=np.float32)


def _lighten(color, amount: float):
    """Blend a color toward white by `amount` (0 = unchanged, 1 = white)."""
    amount = min(1.0, max(0.0, amount))
    return color * (1.0 - amount) + 255.0 * amount


def _petal_field(r, theta, reach: float, width: float, base_w: float,
                 n_petals: int, base_rot: float, spin: float, cutoff: float,
                 grow_len: float):
    """Intensity (0..1) of an `n_petals` flower with petals of the given
    reach + width. Returns one value per LED. Leaf-shaped: narrow at the
    base, fat in the middle, tapering to the tip. Anything dimmer than
    `cutoff` is turned fully off (black) so petals have crisp edges with
    real black space between them.

    `grow_len` reveals the petal outward from the center: only the part of
    the (full-shape) petal within `grow_len` of the center is shown, with a
    soft growing tip. Pass a value ≥ reach to show the whole petal. This is
    a pure outward reveal — the petal never changes shape as it grows."""
    reach = max(0.5, reach)
    soft = 1.5  # softness of the growing tip (LEDs)
    field = np.zeros(TOTAL, dtype=np.float32)
    for k in range(n_petals):
        direction = base_rot + spin + k * (2.0 * math.pi / n_petals)
        da = np.mod(theta - direction + math.pi, 2.0 * math.pi) - math.pi
        along = r * np.cos(da)      # distance ALONG the petal axis
        across = r * np.sin(da)     # distance to the SIDE of the axis

        norm = along / reach                        # 0 at center → 1 at tip
        inside = (norm >= 0.0) & (norm <= 1.0)
        long_prof = np.sin(np.clip(norm, 0.0, 1.0) * math.pi)
        half_w = base_w + width * long_prof
        lat_prof = np.exp(-(across * across) / (2.0 * half_w * half_w))
        reveal = np.clip((grow_len - along) / soft, 0.0, 1.0)  # outward wipe
        this_petal = np.where(inside, long_prof * lat_prof * reveal, 0.0).astype(np.float32)
        field = np.maximum(field, this_petal)
    # Hard cutoff: kill the dim halo so the gaps between petals are truly
    # black, then re-stretch what's left back to full brightness.
    cutoff = min(0.95, max(0.0, cutoff))
    field = np.clip((field - cutoff) / (1.0 - cutoff), 0.0, 1.0)
    return field


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()

    n_petals = max(1, int(p["petals"]))
    base_rot = math.radians(float(p["base_rotation_deg"]))
    base_w = float(p["petal_base_width"])
    full_reach = float(p["petal_reach"])

    # ── Sequence timing ──────────────────────────────────────────────
    # Stamp the start on the first frame of a run; `state` is reset by the
    # Playground on each (re)trigger / play, so the sequence replays from
    # the top every time the flower starts.
    if p.get("sequence") and state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        elapsed = (time_ms - state["t0"]) / 1000.0

        center_end = float(p["center_time_s"])
        grow_end = center_end + float(p["grow_time_s"])
        hold_end = grow_end + float(p["hold_time_s"])

        if elapsed < center_end:
            open_amt = 0.0                      # center only
        elif elapsed < grow_end:
            open_amt = _smoothstep((elapsed - center_end) / max(0.01, float(p["grow_time_s"])))
        else:
            open_amt = 1.0                      # fully open (hold + rotate)

        # Rotation kicks in after the hold (colors stay fixed).
        move_t = max(0.0, elapsed - hold_end)
        spin = math.radians(float(p["rotate_speed_deg_s"]) * move_t)
        core_fade = min(1.0, elapsed / max(0.01, float(p["center_fade_s"])))
    else:
        # Static: fully open, no motion.
        open_amt, spin, core_fade = 1.0, 0.0, 1.0

    # ── Petals ───────────────────────────────────────────────────────
    rgb = np.zeros((TOTAL, 3), dtype=np.float32)
    if open_amt > 0.001:
        cutoff = float(p["edge_cutoff"])
        # Grow as a pure outward reveal: the petal keeps its full shape and
        # is simply unveiled from the center out. `+3` so a fully-open petal
        # is revealed all the way to its tip (and a little beyond).
        grow_len = open_amt * (full_reach + 3.0)

        # Radial color gradient: pink near the center → blue at the tips.
        c_center = np.array(p["color_center"], dtype=np.float32)
        c_tip = np.array(p["color_tip"], dtype=np.float32)
        frac = np.clip(r / full_reach, 0.0, 1.0)[:, np.newaxis]
        grad_color = c_center[np.newaxis, :] * (1.0 - frac) + c_tip[np.newaxis, :] * frac

        # Big petal, with edges blended a little lighter for a soft rim.
        petal = _petal_field(r, theta, full_reach, float(p["petal_width"]),
                             base_w, n_petals, base_rot, spin, cutoff, grow_len)
        edge_t = ((1.0 - petal) * float(p["edge_light_amount"]))[:, np.newaxis]
        petal_color = grad_color * (1.0 - edge_t) + 255.0 * edge_t
        rgb += petal[:, np.newaxis] * petal_color

        # Narrow, lighter inner petal nested inside (off by default).
        if p.get("inner_petal"):
            inner = _petal_field(r, theta, full_reach * float(p["inner_reach_frac"]),
                                 float(p["inner_width"]), base_w, n_petals,
                                 base_rot, spin, cutoff, grow_len)
            inner_color = _lighten(c_center, float(p["inner_light_amount"]))
            a = inner[:, np.newaxis]
            rgb = rgb * (1.0 - a) + inner_color[np.newaxis, :] * a

    # ── Glowing center core (fades in at the very start) ──────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) * float(p["core_brightness"]) * core_fade
    rgb += core[:, np.newaxis] * np.array(p["core_color"], dtype=np.float32)

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
