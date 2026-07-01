"""Soft mandala — perfectly symmetric nested petal bloom.

A softer sibling of the first mandala. No thin lines, no web — broad,
filled, glowing shapes with perfect mirror symmetry:

  1. OUTER COROLLA — a ring of wide soft petals, slowly turning,
  2. INNER COROLLA — a smaller petal ring nested between the outer
     petals, turning the OPPOSITE way, in a slightly different hue,
  3. RING BANDS — wide soft rings of light breathing through the body,
  4. CORE — a warm glowing center.

Everything is smooth and filled (gaussian / cosine shapes — nothing
sharp). Color flows by radius, the inner corolla carries its own hue
accent, and the palette slowly walks around the color wheel.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.kaleido`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "symmetry": 8,           # petals per corolla (6/8/10/12)
    "reach": 26.0,           # mandala radius in LEDs (~30 touches the corners)

    "rotate_speed_deg_s": 2.5,   # outer corolla turn speed (2.5°/s ≈ 2.4 min per turn)
    "inner_speed_ratio": -0.7,   # inner corolla speed vs outer (negative = opposite way)
    "inner_scale": 0.55,     # inner corolla size as a fraction of the outer

    "petal_softness": 2.2,   # petal edge softness (1 = very wide & overlapping,
                             # 4 = slimmer petals with more dark between)
    "rings": 2.5,            # how many soft ring bands breathe through the body
    "ring_amount": 0.35,     # how visible the ring bands are (0 = none)
    "ring_drift": 1.0,       # rings slowly slide outward (0 = still, negative = inward)

    "color_speed": 1.0,      # palette walk speed (1 = full color wheel ~2.5 min)
    "hue_spread": 0.35,      # center → edge hue difference (1 = full rainbow)
    "inner_hue_offset": 0.12,    # inner corolla's hue accent vs the outer
    "saturation": 0.9,       # color richness (1 = fully saturated)

    "breathe": 0.05,         # gentle swelling of the whole mandala (0 = still)
    "breathe_period_s": 10.0,    # seconds per breath
    "edge_cutoff": 0.06,     # tiny cutoff so the background stays black but
                             # edges remain soft (bigger = crisper, harder look)

    "core_size": 2.4,        # radius of the glowing center
    "core_brightness": 0.95, # how bright the center glows

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


def _corolla(theta: np.ndarray, rn: np.ndarray, m: int, rot: float,
             softness: float, peak_rn: float) -> np.ndarray:
    """One soft petal ring: m wide cosine petals around the circle,
    brightest at `peak_rn` of the (normalized) radius, fading smoothly
    to zero at the center and the rim. Fully mirror-symmetric."""
    angular = (0.5 + 0.5 * np.cos(m * (theta - rot))) ** softness
    radial = np.exp(-((rn - peak_rn) ** 2) / (2.0 * 0.22 ** 2))
    return angular * radial


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()

    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    m = max(2, int(p["symmetry"]))
    reach = float(p["reach"])

    # Gentle whole-mandala breathing.
    breathe = 1.0 + float(p["breathe"]) * math.sin(
        2.0 * math.pi * t / max(0.5, float(p["breathe_period_s"])))
    rn = np.clip(r / (reach * breathe), 0.0, 1.0)
    inside = rn < 1.0

    rot = math.radians(float(p["rotate_speed_deg_s"])) * t
    rot_in = rot * float(p["inner_speed_ratio"])
    soft = max(0.5, float(p["petal_softness"]))

    # ── Layer 1: outer corolla (wide soft petals) ────────────────────
    outer = _corolla(theta, rn, m, rot, soft, peak_rn=0.72)

    # ── Layer 2: inner corolla — nested between the outer petals,
    # counter-rotating, smaller.
    half = math.pi / m                                # half-petal offset
    inner_rn = np.clip(rn / max(0.1, float(p["inner_scale"])), 0.0, 1.5)
    inner = _corolla(theta, inner_rn, m, rot_in + half, soft, peak_rn=0.75)

    # ── Layer 3: soft ring bands breathing through the body ─────────
    drift = float(p["ring_drift"]) * t / 18.0
    ringband = (0.5 + 0.5 * np.sin(2.0 * math.pi * float(p["rings"]) * rn
                                   - drift * 2.0 * math.pi)) ** 2.0
    ringband = ringband * np.sin(rn * math.pi) * float(p["ring_amount"])

    # ── Layer 4: glowing core ────────────────────────────────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) \
        * float(p["core_brightness"])

    # Stack the body softly (capped at 1) with only a tiny cutoff so the
    # background is black but every edge stays a smooth glow.
    field = np.clip(0.85 * outer + ringband, 0.0, 1.0)
    field = np.where(inside, field, 0.0)
    cut = min(0.9, max(0.0, float(p["edge_cutoff"])))
    field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)
    inner_a = np.where(rn < 1.0, np.clip(inner, 0.0, 1.0), 0.0)

    # ── Color ────────────────────────────────────────────────────────
    hue0 = t * float(p["color_speed"]) / 150.0
    sat = min(1.0, max(0.0, float(p["saturation"])))
    body_rgb = _sinebow(hue0 + float(p["hue_spread"]) * rn, sat)
    inner_rgb = _sinebow(hue0 + float(p["inner_hue_offset"])
                         + float(p["hue_spread"]) * rn * 0.5, sat)
    core_rgb = _sinebow(np.full(TOTAL, hue0, dtype=np.float32), sat * 0.4)

    rgb = field[:, np.newaxis] * body_rgb
    # Inner corolla and core blend softly OVER the body.
    a_in = inner_a[:, np.newaxis]
    rgb = rgb * (1.0 - a_in) + inner_rgb * a_in
    a_core = np.clip(core, 0.0, 1.0)[:, np.newaxis]
    rgb = rgb * (1.0 - a_core) + core_rgb * a_core

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
