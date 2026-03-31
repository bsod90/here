"""Breathing meditation animation — expanding/contracting circle rim.

Exact port of software/simulator/public/js/demo.js, extended with
4-phase timing: inhale → hold_top → exhale → hold_bottom.

Uses numpy for vectorized computation (30fps on RPi 4).
"""
import math

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from grid import TOTAL, DISTANCES


def _breath_phase(time_ms: float, params: dict) -> float:
    """Compute breath value (0=contracted, 1=expanded) using 4-phase timing.

    Phases: inhale (0→1) → hold_top (1) → exhale (1→0) → hold_bottom (0)
    Each phase duration is configurable in ms.
    Uses smooth cosine easing for inhale/exhale.
    """
    inhale = params["inhale_ms"]
    hold_top = params["hold_top_ms"]
    exhale = params["exhale_ms"]
    hold_bottom = params["hold_bottom_ms"]
    total = inhale + hold_top + exhale + hold_bottom

    if total <= 0:
        return 0.0

    t = time_ms % total

    if t < inhale:
        # Inhale: 0 → 1 (cosine ease)
        return (1 - math.cos(t / inhale * math.pi)) / 2
    t -= inhale

    if t < hold_top:
        # Hold at top
        return 1.0
    t -= hold_top

    if t < exhale:
        # Exhale: 1 → 0 (cosine ease)
        return (1 + math.cos(t / exhale * math.pi)) / 2
    # Hold at bottom
    return 0.0


def render(frame: bytearray, time_ms: float, params: dict):
    if HAS_NUMPY:
        _render_numpy(frame, time_ms, params)
    else:
        _render_pure(frame, time_ms, params)


# Pre-compute numpy distances array once
_NP_DISTANCES = None

def _get_np_distances():
    global _NP_DISTANCES
    if _NP_DISTANCES is None:
        _NP_DISTANCES = np.array(DISTANCES, dtype=np.float32)
    return _NP_DISTANCES


def _render_numpy(frame: bytearray, time_ms: float, params: dict):
    min_r = params["min_radius"]
    max_r = params["max_radius"]
    rim_w = params["rim_width"]
    inner_blur = params["inner_blur"]
    outer_blur = params["outer_blur"]
    rim_color = np.array(params["rim_color"], dtype=np.float32)
    inner_color = np.array(params["inner_color"], dtype=np.float32)
    outer_color = np.array(params["outer_color"], dtype=np.float32)
    trail_delay = params["trail_delay_ms"]
    trail_blur = params["trail_blur"]
    trail_opacity = params["trail_opacity"]
    trail_color = np.array(params["trail_color"], dtype=np.float32)
    brightness = params["brightness"]

    dist = _get_np_distances()

    # 4-phase breath
    breath = _breath_phase(time_ms, params)
    radius = min_r + breath * (max_r - min_r)

    # Trail: same but delayed
    trail_breath = _breath_phase(time_ms - trail_delay, params)
    trail_radius = min_r + trail_breath * (max_r - min_r)

    dfr = dist - radius
    dft = dist - trail_radius

    # Gaussians (vectorized)
    rim_glow = np.exp(-(dfr ** 2) / (2 * rim_w ** 2))

    inner_dist = np.maximum(0.0, -dfr)
    inner_glow = np.exp(-(inner_dist ** 2) / (2 * inner_blur ** 2)) * (dfr < 0)

    outer_dist = np.maximum(0.0, dfr)
    outer_glow = np.exp(-(outer_dist ** 2) / (2 * outer_blur ** 2)) * (dfr > 0)

    trail_glow = np.exp(-(dft ** 2) / (2 * trail_blur ** 2)) * trail_opacity

    # Composite RGB
    rgb = (np.outer(rim_glow, rim_color)
           + np.outer(inner_glow, inner_color)
           + np.outer(outer_glow, outer_color)
           + np.outer(trail_glow, trail_color))

    rgb = np.clip(rgb * brightness, 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()


def _render_pure(frame: bytearray, time_ms: float, params: dict):
    min_r = params["min_radius"]
    max_r = params["max_radius"]
    rim_w = params["rim_width"]
    inner_blur = params["inner_blur"]
    outer_blur = params["outer_blur"]
    rim_color = params["rim_color"]
    inner_color = params["inner_color"]
    outer_color = params["outer_color"]
    trail_delay = params["trail_delay_ms"]
    trail_blur = params["trail_blur"]
    trail_opacity = params["trail_opacity"]
    trail_color = params["trail_color"]
    brightness = params["brightness"]

    rim_denom = 2.0 * rim_w * rim_w
    inner_denom = 2.0 * inner_blur * inner_blur
    outer_denom = 2.0 * outer_blur * outer_blur
    trail_denom = 2.0 * trail_blur * trail_blur

    breath = _breath_phase(time_ms, params)
    radius = min_r + breath * (max_r - min_r)

    trail_breath = _breath_phase(time_ms - trail_delay, params)
    trail_radius = min_r + trail_breath * (max_r - min_r)

    for i in range(TOTAL):
        dist = DISTANCES[i]
        dfr = dist - radius
        dft = dist - trail_radius

        rim_glow = math.exp(-(dfr * dfr) / rim_denom)
        inner_glow = math.exp(-(dfr * dfr) / inner_denom) if dfr < 0 else 0.0
        outer_glow = math.exp(-(dfr * dfr) / outer_denom) if dfr > 0 else 0.0
        trail_glow = math.exp(-(dft * dft) / trail_denom) * trail_opacity

        r = (rim_glow * rim_color[0] + inner_glow * inner_color[0]
             + outer_glow * outer_color[0] + trail_glow * trail_color[0])
        g = (rim_glow * rim_color[1] + inner_glow * inner_color[1]
             + outer_glow * outer_color[1] + trail_glow * trail_color[1])
        b = (rim_glow * rim_color[2] + inner_glow * inner_color[2]
             + outer_glow * outer_color[2] + trail_glow * trail_color[2])

        off = i * 3
        frame[off] = min(255, int(r * brightness))
        frame[off + 1] = min(255, int(g * brightness))
        frame[off + 2] = min(255, int(b * brightness))
