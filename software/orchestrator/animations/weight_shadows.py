"""Weight-responsive shadow blobs.

Draws one soft glow under each scale leg, sized proportionally to that
leg's grams above its share of the occupancy threshold. Each blob is
small at threshold and grows modestly as more weight is applied — the
brief tells us "not by much, but still visible".

Inputs are read from the live scale snapshot each frame, so this stays
in lockstep with the readings shown in the admin panel.
"""
from __future__ import annotations

import math

from grid import GRID


def _falloff(d: float, radius: float) -> float:
    """Smooth cosine-shaped falloff, 0 outside `radius`, 1 at the centre."""
    if radius <= 0 or d >= radius:
        return 0.0
    x = d / radius
    # cos² falloff: gentle plateau in the middle, soft edges.
    return math.cos(x * math.pi / 2) ** 2


def render(frame: bytearray, time_ms: float, params: dict,
           scale_snapshot: dict | None, clear: bool = True):
    # `clear=True` keeps standalone-mode behaviour (paint on black).
    # `clear=False` is the overlay path — additively layered on top of
    # whatever the active mode just rendered.
    if clear:
        for i in range(len(frame)):
            frame[i] = 0

    if not scale_snapshot:
        return
    legs = scale_snapshot.get("legs") or []
    if len(legs) < 2:
        return

    color = params.get("color") or [255, 120, 30]
    brightness = float(params.get("brightness", 0.7))
    base_radius = float(params.get("base_radius", 3.0))
    max_radius = float(params.get("max_radius", 6.5))
    # Per-leg grams of *excess* above threshold that maps to max_radius.
    span_grams = float(params.get("span_grams", 60000.0))
    # Leg positions: prefer the flat `legN_row/col` fields (slider-friendly).
    # Fall back to the legacy `leg_positions: [[r,c],[r,c]]` array so old
    # configs keep working without migration.
    if "leg1_row" in params or "leg2_row" in params:
        positions = [
            [float(params.get("leg1_row", 14)), float(params.get("leg1_col", 14))],
            [float(params.get("leg2_row", 29)), float(params.get("leg2_col", 29))],
        ]
    else:
        positions = params.get("leg_positions") or [[14, 14], [29, 29]]

    # Threshold is in total grams; per-leg share is half (assumes weight is
    # roughly centred on the bench). Once the bench is occupied, blobs
    # become visible; below threshold we don't render anything.
    threshold_total = float(scale_snapshot.get("threshold_grams") or 0.0)
    per_leg_floor = threshold_total / 2.0

    for i in range(min(2, len(positions), len(legs))):
        grams = float(legs[i].get("grams") or 0.0)
        excess = grams - per_leg_floor
        if excess <= 0:
            continue
        norm = min(1.0, excess / max(span_grams, 1.0))
        radius = base_radius + norm * (max_radius - base_radius)

        row0, col0 = int(positions[i][0]), int(positions[i][1])
        # Bounding box keeps the per-frame cost ~O(radius²), not O(GRID²).
        bb = int(math.ceil(radius)) + 1
        r_start = max(0, row0 - bb)
        r_end   = min(GRID, row0 + bb + 1)
        c_start = max(0, col0 - bb)
        c_end   = min(GRID, col0 + bb + 1)

        for r in range(r_start, r_end):
            dr = r - row0
            for c in range(c_start, c_end):
                dc = c - col0
                # 3×3 hole under the physical leg — LEDs there are
                # obscured by the wood anyway, so skip the wasted draws.
                if abs(dr) <= 1 and abs(dc) <= 1:
                    continue
                d = math.sqrt(dr * dr + dc * dc)
                f = _falloff(d, radius) * brightness
                if f <= 0:
                    continue
                off = (r * GRID + c) * 3
                # Additive — if a future caller layers this on top of
                # something else, it will mix instead of stomp.
                nr = frame[off]     + int(color[0] * f)
                ng = frame[off + 1] + int(color[1] * f)
                nb = frame[off + 2] + int(color[2] * f)
                frame[off]     = nr if nr < 255 else 255
                frame[off + 1] = ng if ng < 255 else 255
                frame[off + 2] = nb if nb < 255 else 255
