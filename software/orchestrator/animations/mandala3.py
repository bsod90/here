"""Mandala III — a sparse star lattice (more black, fewer lit LEDs).

The third sibling in the mandala family. Same bones as the other two
(polar symmetry, a crisp edge cutoff for real black between the shapes,
radius-flowing `_sinebow` color that slowly walks the wheel, gentle
breathing + counter-rotation + fade-in) — but deliberately SPARSE: built
from thin linework instead of filled petals, so most of the floor stays
dark and only fine glowing lines and nodes are lit.

Layers, all sharing one center:
  1. SPOKES — thin straight rays at the main symmetry, slowly turning,
  2. STAR   — a finer counter-rotating star of even thinner rays, twisted
              into a faint spiral so the two lattices re-interlock,
  3. RINGS  — one or two very thin concentric rings woven through,
  4. NODES  — small glowing beads where a ring crosses the spokes,
  5. CORE   — a small medallion at the very center.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS`; overrides come from
`config.playground.mandala3`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "symmetry": 9,           # how many spokes / star points (odd reads "starrier")
    "reach": 26.0,           # mandala radius in LEDs (~30 touches the corners)

    "rotate_speed_deg_s": 3.0,   # spoke layer turn speed
    "counter_rotate": True,      # star layer turns the OPPOSITE way

    "spoke_width": 14.0,     # thinness of the main spokes (bigger = thinner = more black)
    "star_width": 22.0,      # thinness of the fine counter-star (bigger = thinner)
    "star_amount": 0.7,      # strength of the fine star (0 = off)
    "spiral": 0.7,           # how much the star twists into a spiral (0 = straight)

    "rings": 2.0,            # how many thin concentric rings fit inside
    "ring_width": 12.0,      # thinness of the rings (bigger = thinner)
    "ring_amount": 0.6,      # strength of the rings (0 = off)

    "nodes": 9,              # glowing beads around the node ring (0 = off)
    "node_radius_frac": 0.6,     # where the node ring sits (fraction of reach)
    "node_size": 1.1,        # size of each bead (LEDs)
    "node_speed_deg_s": 3.0,     # node ring orbit speed (match spokes to sit on them)

    "hue_start": 0.80,       # starting hue on the wheel (0.80 ≈ purple/violet); the
                             # mandala begins here and slowly walks onward from it
    "color_speed": 2.0,      # palette walk speed (2 = full color wheel ~75 s)
    "hue_spread": 0.15,      # center → edge hue difference (small = the whole mandala
                             # stays one colour family, e.g. purple→pink)
    "saturation": 0.9,       # color richness (1 = fully saturated)

    "breathe": 0.06,         # gentle swelling of the whole mandala (0 = still)
    "breathe_period_s": 9.0, # seconds per breath
    "edge_cutoff": 0.40,     # dim glow below this is turned OFF — high here, so the
                             # thin lines stay thin and the floor stays mostly black

    "core_size": 1.8,        # radius of the glowing center medallion
    "core_brightness": 0.85, # how bright the center glows

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
    """Smooth vectorized rainbow: hue 0..1 → (N,3) RGB 0..255."""
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

    # ── Layer 1: thin straight spokes (main symmetry) ────────────────
    # |sin| raised to a high power makes very thin rays; the higher the
    # `spoke_width` exponent the thinner the line (so more black).
    sw = max(1.0, float(p["spoke_width"]))
    spokes = np.abs(np.sin(0.5 * m * (theta - rot))) ** sw
    spokes = spokes * np.sin(rn * math.pi)            # fade at center & rim

    # ── Layer 2: finer counter-rotating star, faintly spiralled ──────
    tw = 2.0 * math.pi * float(p["spiral"]) * rn
    stw = max(1.0, float(p["star_width"]))
    star = np.abs(np.sin(m * (theta - rot2) + tw)) ** stw
    star = star * np.sin(rn * math.pi) * float(p["star_amount"])

    # ── Layer 3: thin concentric rings ───────────────────────────────
    rw = max(1.0, float(p["ring_width"]))
    rings = (0.5 + 0.5 * np.sin(2.0 * math.pi * float(p["rings"]) * rn - 0.4 * rot)) ** rw
    rings = rings * np.sin(np.clip(rn * 1.1, 0.0, 1.0) * math.pi) * float(p["ring_amount"])

    # ── Layer 4: glowing nodes on a ring (sit on the spokes) ─────────
    n_node = max(0, int(p["nodes"]))
    nodes = np.zeros(TOTAL, dtype=np.float32)
    if n_node > 0:
        nr = float(p["node_radius_frac"]) * reach * breathe
        ns = max(0.4, float(p["node_size"]))
        orbit = math.radians(float(p["node_speed_deg_s"])) * t
        sector = 2.0 * math.pi / n_node
        da = np.mod(theta - orbit, sector) - sector / 2.0
        arc = nr * da                                 # distance along the ring
        rad = r - nr                                  # distance off the ring
        nodes = np.exp(-(arc * arc + rad * rad) / (2.0 * ns * ns))

    # ── Layer 5: glowing center medallion ───────────────────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) * float(p["core_brightness"])

    # Stack the line layers, hard cutoff for crisp dark space, then add the
    # bright point layers (nodes + core) ABOVE the cutoff so they always read.
    field = np.clip(spokes + star + rings, 0.0, 1.0)
    field = np.where(inside, field, 0.0)
    cut = min(0.95, max(0.0, float(p["edge_cutoff"])))
    field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)
    field = np.maximum(field, np.where(inside, nodes, 0.0))
    field = np.maximum(field, core)

    # ── Color: hue flows with radius, palette slowly cycles ─────────
    hue0 = float(p["hue_start"]) + t * float(p["color_speed"]) / 150.0
    hue = hue0 + float(p["hue_spread"]) * rn
    sat = min(1.0, max(0.0, float(p["saturation"])))
    color = _sinebow(hue, sat)

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = field[:, np.newaxis] * color * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
