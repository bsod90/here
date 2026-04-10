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

from grid import TOTAL, DISTANCES, GRID_POSITIONS, CENTER


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


# Pre-compute numpy arrays once
_NP_DISTANCES = None
_NP_ANGLES = None

def _get_np_arrays():
    global _NP_DISTANCES, _NP_ANGLES
    if _NP_DISTANCES is None:
        _NP_DISTANCES = np.array(DISTANCES, dtype=np.float32)
        # Angle of each LED relative to grid center (for shimmer rotation)
        angles = []
        for row, col in GRID_POSITIONS:
            angles.append(math.atan2(row - CENTER, col - CENTER))
        _NP_ANGLES = np.array(angles, dtype=np.float32)
    return _NP_DISTANCES, _NP_ANGLES


def _render_numpy(frame: bytearray, time_ms: float, params: dict):
    min_r = params["min_radius"]
    max_r = params["max_radius"]
    rim_w = params["rim_width"]
    inner_blur = params["inner_blur"]
    outer_blur = params["outer_blur"]
    palettes = params.get("palettes", [])
    active = params.get("active_palette", 0)
    pal = palettes[active % len(palettes)] if palettes else {}
    rim_color = np.array(pal.get("rim_color", [120, 80, 255]), dtype=np.float32)
    inner_color = np.array(pal.get("inner_color", [40, 220, 220]), dtype=np.float32)
    outer_color = np.array(pal.get("outer_color", [200, 40, 180]), dtype=np.float32)
    trail_delay = params["trail_delay_ms"]
    trail_blur = params["trail_blur"]
    trail_opacity = params["trail_opacity"]
    trail_color = np.array(pal.get("trail_color", [80, 50, 200]), dtype=np.float32)
    brightness = params["brightness"]

    dist, angles = _get_np_arrays()

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

    # Composite base RGB
    rgb = (np.outer(rim_glow, rim_color)
           + np.outer(inner_glow, inner_color)
           + np.outer(outer_glow, outer_color)
           + np.outer(trail_glow, trail_color))

    # ── Per-point shimmer: hue/brightness wave rotating around the circle ──
    # Slow rotation (completes one cycle every ~12 seconds)
    shimmer_speed = time_ms * 0.0005
    # 3 overlapping sine waves at different frequencies for organic feel
    shimmer = (
        0.08 * np.sin(angles * 3 + shimmer_speed) +         # 3-fold symmetry
        0.05 * np.sin(angles * 5 - shimmer_speed * 1.3) +   # 5-fold, counter-rotating
        0.04 * np.sin(angles * 7 + shimmer_speed * 0.7)      # 7-fold, slow
    )
    # Hue shift: rotate between channels slightly
    hue_shift = 0.12 * np.sin(angles * 2 + shimmer_speed * 0.8)

    # Apply shimmer as brightness modulation + subtle hue rotation
    # Only shimmer pixels that are actually lit (avoid boosting black pixels)
    total_glow = rim_glow + inner_glow + outer_glow + trail_glow
    shimmer_mask = np.minimum(total_glow, 1.0)  # 0 where dark, 1 where lit

    brightness_mod = (1.0 + shimmer * shimmer_mask)[:, np.newaxis]
    rgb = rgb * brightness_mod

    # Subtle hue rotation: shift some R→B and B→R based on angular position
    hue_amount = (hue_shift * shimmer_mask)[:, np.newaxis]
    r_shift = rgb[:, 2:3] * hue_amount * 0.3   # steal from blue
    b_shift = rgb[:, 0:1] * hue_amount * 0.3   # steal from red
    rgb[:, 0:1] += r_shift - b_shift * 0.5
    rgb[:, 2:3] += b_shift - r_shift * 0.5

    # ── Spinning mask: creates illusion of circle rotation ──
    spin = params.get("spin", {})
    if spin.get("enabled", False):
        arms = max(1, spin.get("arms", 4))
        depth = spin.get("depth", 0.3)
        mode = spin.get("mode", "constant")

        if mode == "yoyo":
            # Use the breath velocity as spin drive, with inertia.
            # Compute instantaneous velocity from two nearby breath samples,
            # then use a persistent accumulator for smooth angle integration.
            yoyo_speed = spin.get("yoyo_speed", 1.0)
            dt = 16.0  # ~1 frame at 60fps, doesn't need to be exact

            reverse = spin.get("yoyo_reverse", True)

            # Current and previous breath values → velocity
            b_now = _breath_phase(time_ms, params)
            b_prev = _breath_phase(time_ms - dt, params)
            velocity = (b_now - b_prev) / dt * 1000  # breath units per second
            if not reverse:
                velocity = abs(velocity)  # always spin same direction

            # Use module-level accumulator for smooth integration
            if not hasattr(_render_numpy, '_yoyo_angle'):
                _render_numpy._yoyo_angle = 0.0
                _render_numpy._yoyo_vel = 0.0

            # Blend toward target velocity with inertia (smoothing factor)
            inertia = spin.get("yoyo_inertia", 0.995)
            _render_numpy._yoyo_vel = _render_numpy._yoyo_vel * inertia + velocity * (1 - inertia)

            # Integrate
            _render_numpy._yoyo_angle += _render_numpy._yoyo_vel * yoyo_speed * dt * 0.001

            spin_angle = _render_numpy._yoyo_angle * math.pi * 2
        else:
            # Constant speed
            speed = spin.get("constant_speed", 0.3)
            spin_angle = time_ms * 0.001 * speed * math.pi * 2

        # Mask: sinusoidal pattern around the circle with N arms
        spin_mask = np.sin(angles * arms + spin_angle)
        # Normalize to 0-1 range, then scale by depth
        spin_mod = 1.0 - depth * 0.5 * (1.0 + spin_mask)  # ranges from (1-depth) to 1
        # Apply only to lit pixels
        spin_mod = 1.0 - shimmer_mask * (1.0 - spin_mod)
        rgb = rgb * spin_mod[:, np.newaxis]

    rgb = np.clip(rgb * brightness, 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()


def _render_pure(frame: bytearray, time_ms: float, params: dict):
    min_r = params["min_radius"]
    max_r = params["max_radius"]
    rim_w = params["rim_width"]
    inner_blur = params["inner_blur"]
    outer_blur = params["outer_blur"]
    palettes = params.get("palettes", [])
    active = params.get("active_palette", 0)
    pal = palettes[active % len(palettes)] if palettes else {}
    rim_color = pal.get("rim_color", [120, 80, 255])
    inner_color = pal.get("inner_color", [40, 220, 220])
    outer_color = pal.get("outer_color", [200, 40, 180])
    trail_color = pal.get("trail_color", [80, 50, 200])
    trail_delay = params["trail_delay_ms"]
    trail_blur = params["trail_blur"]
    trail_opacity = params["trail_opacity"]
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
