"""Mandala — an intricate, slowly turning, color-shifting mandala.

Built from four stacked layers, all sharing one center:
  1. PETALS — a ring of pointed petals (the main symmetry),
  2. RINGS — concentric circles woven through the petals,
  3. WEAVE — a finer spiral lattice at double symmetry, counter-rotating,
  4. CORE — a small glowing medallion at the very center.

The petals and the weave turn in OPPOSITE directions, very slowly, so
the pattern keeps re-interlocking — that's what makes it feel alive and
intricate rather than a static stencil. Color flows by radius (center
and edge are different hues) and the whole palette slowly walks around
the color wheel. A gentle breath swells the whole mandala in and out.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.mandala`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "symmetry": 8,           # how many petals / spokes (6, 8, 12 are classic)
    "reach": 26.0,           # mandala radius in LEDs (~30 touches the corners)

    "rotate_speed_deg_s": 3.0,   # petal layer turn speed (3°/s = full turn in 2 min)
    "counter_rotate": True,      # weave layer turns the OPPOSITE way (more intricate)

    "rings": 3.0,            # how many concentric rings fit inside the mandala
    "detail": 1.0,           # strength of the fine woven lattice (0 = off, 2 = busy)
    "spiral": 1.0,           # how much the weave twists into a spiral (0 = straight spokes)

    "color_speed": 2.0,      # palette walk speed (1 = full color wheel ~2.5 min,
                             # 2 = ~75 s)
    "hue_spread": 0.45,      # how different center vs edge colors are (0 = one color,
                             # 1 = full rainbow from center to edge)
    "saturation": 0.9,       # color richness (1 = fully saturated)

    "breathe": 0.06,         # gentle swelling of the whole mandala (0 = still)
    "breathe_period_s": 9.0, # seconds per breath
    "edge_cutoff": 0.18,     # dim glow below this is turned OFF — crisper lines,
                             # real black between the shapes

    "core_size": 2.0,        # radius of the glowing center medallion
    "core_brightness": 0.9,  # how bright the center glows

    "fade_in_s": 2.0,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}


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


def _sinebow(h: np.ndarray, sat: float) -> np.ndarray:
    """Smooth vectorized rainbow: hue 0..1 → (N,3) RGB 0..255. Saturation
    blends toward white."""
    r = np.cos(math.pi * (h % 1.0)) ** 2
    g = np.cos(math.pi * ((h % 1.0) - 1.0 / 3.0)) ** 2
    b = np.cos(math.pi * ((h % 1.0) - 2.0 / 3.0)) ** 2
    rgb = np.stack([r, g, b], axis=1) * 255.0
    return rgb * sat + 255.0 * (1.0 - sat)


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

    m = max(2, int(p["symmetry"]))
    reach = float(p["reach"])

    # Gentle whole-mandala breathing (scales the radius).
    breathe = 1.0 + float(p["breathe"]) * math.sin(
        2.0 * math.pi * t / max(0.5, float(p["breathe_period_s"])))
    rn = np.clip(r / (reach * breathe), 0.0, 1.0)     # 0 center → 1 edge
    inside = rn < 1.0

    rot = math.radians(float(p["rotate_speed_deg_s"])) * t
    rot2 = -rot if p.get("counter_rotate") else rot

    # ── Layer 1: petals (main symmetry, slowly turning) ─────────────
    # |sin| sharpened → pointed petals; brightest at mid-radius.
    petals = np.abs(np.sin(0.5 * m * (theta - rot))) ** 3.0
    petals = petals * np.sin(rn * math.pi)

    # ── Layer 2: concentric rings woven through ─────────────────────
    rings = (0.5 + 0.5 * np.sin(2.0 * math.pi * float(p["rings"]) * rn
                                - 0.4 * rot)) ** 3.0
    rings = rings * np.sin(np.clip(rn * 1.15, 0.0, 1.0) * math.pi)

    # ── Layer 3: fine counter-rotating spiral weave ──────────────────
    # Double symmetry + a radial twist → a lattice that re-interlocks
    # with the petals as the two layers turn against each other.
    twist = 2.0 * math.pi * float(p["spiral"]) * rn
    weave = np.abs(np.sin(m * (theta - rot2) + twist)) ** 5.0
    weave = weave * np.sin(rn * math.pi) * 0.6 * float(p["detail"])

    # ── Layer 4: glowing center medallion ───────────────────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) \
        * float(p["core_brightness"])

    # Stack the layers (capped at 1), then a hard cutoff for crisp dark
    # linework between the shapes.
    field = np.clip(0.62 * petals + 0.55 * rings + weave, 0.0, 1.0)
    field = np.where(inside, field, 0.0)
    cut = min(0.9, max(0.0, float(p["edge_cutoff"])))
    field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)
    field = np.maximum(field, core)

    # ── Color: hue flows with radius, palette slowly cycles ─────────
    hue0 = t * float(p["color_speed"]) / 150.0
    hue = hue0 + float(p["hue_spread"]) * rn
    sat = min(1.0, max(0.0, float(p["saturation"])))
    color = _sinebow(hue, sat)

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = field[:, np.newaxis] * color * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
