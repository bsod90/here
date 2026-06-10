"""Lotus (unfolding layers) — a ceremonial opening flower.

A bud that opens in layers: the inner ring of petals unfolds first,
then a wider ring rotated half a petal between them, then a third —
each layer a deeper shade, each opening a little after the previous.
Once fully open the whole lotus barely breathes. Built for the
welcome/opening segment of a guided meditation: the layer-by-layer
reveal gives ~20–30 s of choreography to speak over.

Tweak via `config.playground.lotus`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL

DEFAULTS = {
    # --- Layers ---
    "layers": 3,             # petal rings, inner → outer
    "petals": 6,             # petals per ring (rings are offset half a petal)
    "reach": 20.0,           # how far the OUTER ring stretches
    "inner_reach_frac": 0.45,# inner ring length as a fraction of `reach`
    "petal_width": 3.0,      # fatness of the outer-ring petals
    "edge_cutoff": 0.18,     # dim halo below this goes black (crisper petals)

    # --- The unfolding choreography ---
    "core_fade_s": 2.0,      # the golden center fades in first
    "layer_stagger_s": 4.0,  # delay between one ring starting and the next
    "layer_open_s": 5.0,     # how long each ring takes to unfold
    "breathe_amount": 0.02,  # once open: reach sways ±2% …
    "breathe_period_s": 9.0, # … this slowly

    # --- Colors: inner ring light, outer ring deep ---
    "color_inner": [255, 170, 200],   # pale pink (innermost ring)
    "color_outer": [140, 30, 150],    # deep magenta-violet (outermost)
    "core_color":  [255, 215, 130],   # warm gold center
    "core_size": 1.8,
    "core_brightness": 1.0,

    # --- Overall ---
    "brightness": 0.95,
}

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


def _smoothstep(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _ring_field(r, theta, reach, width, petals, rotation, cutoff, reveal):
    """Intensity 0..1 of one ring of leaf-shaped petals, revealed outward
    from the center by `reveal` (0..1 of its reach)."""
    field = np.zeros(TOTAL, dtype=np.float32)
    grow_len = reveal * (reach + 3.0)
    for k in range(petals):
        direction = rotation + k * (2.0 * math.pi / petals)
        da = np.mod(theta - direction + math.pi, 2.0 * math.pi) - math.pi
        along = r * np.cos(da)
        across = r * np.sin(da)
        norm = along / reach
        inside = (norm >= 0.0) & (norm <= 1.0)
        long_prof = np.sin(np.clip(norm, 0.0, 1.0) * math.pi)
        half_w = 0.5 + width * long_prof
        lat_prof = np.exp(-(across * across) / (2.0 * half_w * half_w))
        wipe = np.clip((grow_len - along) / 1.5, 0.0, 1.0)
        petal = np.where(inside, long_prof * lat_prof * wipe, 0.0).astype(np.float32)
        field = np.maximum(field, petal)
    field = np.clip((field - cutoff) / (1.0 - cutoff), 0.0, 1.0)
    return field


def render(frame: bytearray, time_ms: float, params: dict,
           state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()
    t = time_ms / 1000.0

    # Choreography clock — restarts whenever the clip (re)triggers.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        elapsed = (time_ms - state["t0"]) / 1000.0
    else:
        elapsed = 1e9                              # previews: fully open

    layers = max(1, int(p["layers"]))
    petals = max(1, int(p["petals"]))
    reach = float(p["reach"])
    stagger = float(p["layer_stagger_s"])
    open_s = max(0.01, float(p["layer_open_s"]))
    core_fade = _smoothstep(elapsed / max(0.01, float(p["core_fade_s"])))

    # Gentle breathing once things are open.
    breathe = 1.0 + float(p["breathe_amount"]) * math.sin(
        2.0 * math.pi * t / max(1.0, float(p["breathe_period_s"])))

    # Ring geometry: reach grows inner → outer; width scales with reach.
    fracs = np.linspace(float(p["inner_reach_frac"]), 1.0, layers)
    c_in = np.array(p["color_inner"], dtype=np.float32)
    c_out = np.array(p["color_outer"], dtype=np.float32)

    rgb = np.zeros((TOTAL, 3), dtype=np.float32)
    # Paint outer ring first so inner rings layer on top of it.
    for k in reversed(range(layers)):
        start = float(p["core_fade_s"]) + k * stagger
        reveal = _smoothstep((elapsed - start) / open_s)
        if reveal <= 0.001:
            continue
        ring_reach = reach * fracs[k] * breathe
        width = float(p["petal_width"]) * (0.55 + 0.45 * fracs[k])
        rotation = (k % 2) * math.pi / petals      # alternate half-petal offset
        field = _ring_field(r, theta, ring_reach, width, petals, rotation,
                            float(p["edge_cutoff"]), reveal)
        mix = k / max(1, layers - 1)
        color = c_in * (1.0 - mix) + c_out * mix
        a = field[:, None]
        rgb = rgb * (1.0 - a) + color[None, :] * a

    # Golden core, first to appear.
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) \
        * float(p["core_brightness"]) * core_fade
    rgb += core[:, None] * np.array(p["core_color"], dtype=np.float32)

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
