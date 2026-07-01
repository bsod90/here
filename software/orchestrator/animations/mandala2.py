"""Mandala II — a second mandala: twin pinwheels with a ring of pearls.

A sibling of the first mandala, built from different ingredients so the
two feel related but distinct:

  1. OUTER PINWHEEL — curved spiral petals sweeping one way,
  2. INNER PINWHEEL — a smaller, fewer-petaled pinwheel curving the
     OPPOSITE way, nested at the heart,
  3. PEARLS — a ring of glowing beads orbiting slowly between the two
     pinwheels, like a rosary being told,
  4. HALO — a thin scalloped ring of light around the outside,
  5. CORE — a soft glowing center.

Color flows by radius and the palette slowly walks the color wheel
(same family as the first mandala). The two pinwheels re-interlock
endlessly; the pearls give the eye something to follow.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.mandala2`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "petals": 10,            # petals on the outer pinwheel
    "inner_petals": 5,       # petals on the inner, counter-turning pinwheel
    "reach": 27.0,           # mandala radius in LEDs (~30 touches the corners)

    "rotate_speed_deg_s": 4.0,   # outer pinwheel turn speed
    "inner_speed_ratio": -1.4,   # inner speed vs outer (negative = opposite way)
    "twist": 1.2,            # how strongly the petals curve into a spiral
                             # (0 = straight spokes, 2 = tightly wound)

    "pearls": 12,            # how many beads orbit between the pinwheels
    "pearl_radius_frac": 0.52,   # where the bead ring sits (fraction of reach)
    "pearl_size": 1.3,       # size of each bead (LEDs)
    "pearl_speed_deg_s": -6.0,   # beads orbit (negative = against the outer wheel)

    "halo": 0.5,             # brightness of the thin scalloped outer ring (0 = off)

    "color_speed": 2.0,      # palette walk speed (2 = full color wheel ~75 s,
                             # same pace Nadia chose for the first mandala)
    "hue_spread": 0.45,      # center → edge hue difference (1 = full rainbow)
    "saturation": 0.9,       # color richness (1 = fully saturated)

    "breathe": 0.06,         # gentle swelling of the whole mandala (0 = still)
    "breathe_period_s": 9.0, # seconds per breath
    "edge_cutoff": 0.18,     # dim glow below this is turned OFF — crisp shapes

    "core_size": 2.0,        # radius of the glowing center
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

    m = max(2, int(p["petals"]))
    m_in = max(2, int(p["inner_petals"]))
    reach = float(p["reach"])

    # Gentle whole-mandala breathing.
    breathe = 1.0 + float(p["breathe"]) * math.sin(
        2.0 * math.pi * t / max(0.5, float(p["breathe_period_s"])))
    rn = np.clip(r / (reach * breathe), 0.0, 1.0)
    inside = rn < 1.0

    rot = math.radians(float(p["rotate_speed_deg_s"])) * t
    rot_in = rot * float(p["inner_speed_ratio"])
    twist = float(p["twist"]) * 2.0 * math.pi

    # ── Layer 1: outer pinwheel (curved spiral petals) ───────────────
    outer = np.abs(np.sin(0.5 * m * (theta - rot) + twist * rn * 0.5)) ** 3.0
    outer = outer * np.clip(np.sin(rn * math.pi), 0.0, None)

    # ── Layer 2: inner pinwheel, curving the other way ───────────────
    inner = np.abs(np.sin(0.5 * m_in * (theta - rot_in) - twist * rn * 0.8)) ** 2.5
    inner = inner * np.exp(-((rn - 0.28) ** 2) / (2.0 * 0.16 ** 2))

    # ── Layer 3: the orbiting pearls ─────────────────────────────────
    n_pearl = max(1, int(p["pearls"]))
    pr = float(p["pearl_radius_frac"]) * reach * breathe
    ps = max(0.4, float(p["pearl_size"]))
    orbit = math.radians(float(p["pearl_speed_deg_s"])) * t
    # Angular distance to the NEAREST pearl, turned into arc length.
    sector = 2.0 * math.pi / n_pearl
    da = np.mod(theta - orbit, sector) - sector / 2.0
    arc = pr * da                                     # distance along the ring
    rad = r - pr                                      # distance off the ring
    pearls = np.exp(-(arc * arc + rad * rad) / (2.0 * ps * ps))

    # ── Layer 4: thin scalloped halo ─────────────────────────────────
    halo = np.exp(-((rn - 0.93) ** 2) / (2.0 * 0.035 ** 2)) \
        * (0.55 + 0.45 * np.sin(m * theta + rot * 2.0)) * float(p["halo"])

    # ── Layer 5: glowing core ────────────────────────────────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) \
        * float(p["core_brightness"])

    # Stack + crisp cutoff (pearls and core ride above the cutoff).
    field = np.clip(0.62 * outer + 0.6 * inner + halo, 0.0, 1.0)
    field = np.where(inside, field, 0.0)
    cut = min(0.9, max(0.0, float(p["edge_cutoff"])))
    field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)
    field = np.maximum(field, np.where(inside, pearls, 0.0))
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
