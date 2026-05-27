"""Breathing meditation animation — expanding/contracting circle rim.

Exact port of software/simulator/public/js/demo.js, extended with
4-phase timing: inhale → hold_top → exhale → hold_bottom.

Vectorized with numpy for 30fps on RPi 4.
"""
from __future__ import annotations

import math

import numpy as np

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


FADE_IN_S = 16.5
FADE_OUT_S = 7.5

# Heartbeat phase parameters. The first chunk of the fade-in is a slow
# 60 bpm lub-dub pulse rather than a single growing breath — gives the
# emergence a "waking up" feel and matches the user's mental model of
# how the circle should appear.
_HEART_FRAC      = 0.40         # first 40% of fade-in is the heartbeat
_HEART_PERIOD_MS = 1000.0       # exactly 60 bpm
_HEART_R_BASE    = 3.0          # rest radius (LEDs)
_HEART_R_AMP     = 0.40         # peak excursion above rest — subtle
_LUB_CENTER_MS   = 110.0
_LUB_SIGMA_MS    = 55.0
_DUB_CENTER_MS   = 360.0
_DUB_SIGMA_MS    = 70.0
_DUB_AMP         = 0.50


def _heartbeat_envelope(time_ms: float) -> float:
    """Two-peak ('lub-dub') Gaussian pulse within each 1 s window.
    Returns 0..1; rest of the period is 0 (the long quiet between
    beats)."""
    t = time_ms % _HEART_PERIOD_MS
    lub = math.exp(-((t - _LUB_CENTER_MS) ** 2)
                   / (2.0 * _LUB_SIGMA_MS * _LUB_SIGMA_MS))
    dub = _DUB_AMP * math.exp(
        -((t - _DUB_CENTER_MS) ** 2)
        / (2.0 * _DUB_SIGMA_MS * _DUB_SIGMA_MS))
    return min(1.0, lub + dub)


def _apply_fade(params: dict, fade_in: float | None,
                fade_out: float | None, time_ms: float) -> dict:
    """Mutate a copy of `params` to encode the fade-in / fade-out state.
    Returns the modified dict (caller can then call render with it)."""
    p = dict(params)
    min_r = float(p.get("min_radius", 3.0))
    max_r = float(p.get("max_radius", 17.0))
    brightness = float(p.get("brightness", 1.0))

    if fade_in is not None:
        u = max(0.0, min(1.0, fade_in))
        if u < _HEART_FRAC:
            # Phase 1 — 60 bpm heartbeat. Setting min_radius == max_radius
            # means the breathing renderer's breath_phase math has no
            # range to lerp through, so the circle sits at whatever
            # radius we pass; the actual motion comes from this
            # heartbeat envelope, not from the breath cycle.
            pulse = _heartbeat_envelope(time_ms)
            r = _HEART_R_BASE + _HEART_R_AMP * pulse
            p["min_radius"] = r
            p["max_radius"] = r
            uu = u / _HEART_FRAC
            # Brightness ramps from 0 to ~85% across the heartbeat
            # phase so the first beats are barely-there glimmers and
            # the last beats are clearly visible.
            p["brightness"] = brightness * 0.85 * (uu ** 1.2)
        else:
            # Phase 2 — the natural breath cycle takes over at the
            # configured full radii. No "slow grow toward full" — that
            # read as a reluctant half-expansion; the user wants the
            # first real inhale to be a real inhale. We still ramp
            # brightness up the last 15% so the heartbeat → breath
            # handoff doesn't pop.
            POST_HEART_BRIGHT_RAMP = 0.10
            bramp = min(1.0, (u - _HEART_FRAC) / POST_HEART_BRIGHT_RAMP)
            p["brightness"] = brightness * (0.85 + 0.15 * bramp)
            # min_radius / max_radius are left at their configured
            # values so the breath cycle plays full-amplitude.

    if fade_out is not None:
        # Smooth continuous shrink. CRITICAL: do NOT override the
        # inhale/hold/exhale timings — those changes cause an instant
        # phase jump because the breath cycle's modulo math depends on
        # total_cycle. By leaving timing alone, the circle keeps
        # breathing at the same tempo as we toggle the transition; only
        # its scale tapers down. Brightness fades with a slightly
        # slower curve so a small dim circle remains visible for a beat
        # before disappearing entirely.
        u = max(0.0, min(1.0, fade_out))
        shrink = 1.0 - u
        p["min_radius"] = min_r * shrink
        p["max_radius"] = max_r * shrink
        p["brightness"] = brightness * (shrink ** 0.6)
    return p


# ── Session phases ────────────────────────────────────────────
# A "breathing session" walks through several sub-phases over time.
# Each phase has a timing knob in config (breathing.session.*) and a
# matching visual stub here. Today the engine only renders whichever
# phase the user picks via `preview_phase` — full orchestration (auto
# progression on a timer + audio cues) will land later.
PHASES = ("auto", "fade_in", "intro_voice", "loop",
          "outro_voice", "chill", "fade_out")

# Chill (post-meditation): slightly slower than the fade-in heartbeat
# and a bit more visible — 50 bpm, ~1.5 LED amplitude.
_CHILL_PERIOD_MS = 1200.0       # 50 bpm
_CHILL_R_BASE    = 4.0
_CHILL_R_AMP     = 1.5
_CHILL_LUB_CENTER_MS = 130.0
_CHILL_LUB_SIGMA_MS  = 70.0
_CHILL_DUB_CENTER_MS = 420.0
_CHILL_DUB_SIGMA_MS  = 85.0
_CHILL_DUB_AMP       = 0.50


def _chill_envelope(time_ms: float) -> float:
    t = time_ms % _CHILL_PERIOD_MS
    lub = math.exp(-((t - _CHILL_LUB_CENTER_MS) ** 2)
                   / (2.0 * _CHILL_LUB_SIGMA_MS * _CHILL_LUB_SIGMA_MS))
    dub = _CHILL_DUB_AMP * math.exp(
        -((t - _CHILL_DUB_CENTER_MS) ** 2)
        / (2.0 * _CHILL_DUB_SIGMA_MS * _CHILL_DUB_SIGMA_MS))
    return min(1.0, lub + dub)


def _apply_chill(p: dict, time_ms: float) -> dict:
    """Replace the breath cycle with a 50 bpm heartbeat for the chill
    phase. Same min == max trick as fade-in's heartbeat so the
    breath_phase math is bypassed."""
    p = dict(p)
    pulse = _chill_envelope(time_ms)
    r = _CHILL_R_BASE + _CHILL_R_AMP * pulse
    p["min_radius"] = r
    p["max_radius"] = r
    return p


def _apply_voice_shimmer(p: dict, time_ms: float) -> dict:
    """Subtle global brightness modulation — gives the room a faint
    'speaking' presence during intro / outro audio prompts without
    overpowering the voice. Two slow sines beating against each other
    so the shimmer feels organic, not mechanical."""
    p = dict(p)
    t = time_ms / 1000.0
    base = float(p.get("brightness", 1.0))
    shimmer = (
        0.04 * math.sin(t * 0.55)
        + 0.025 * math.sin(t * 1.10 + 1.1)
    )
    p["brightness"] = base * (1.0 + shimmer)
    return p


def render(frame: bytearray, time_ms: float, params: dict,
           *, fade_in: float | None = None, fade_out: float | None = None,
           phase: str | None = None):
    if fade_in is not None or fade_out is not None:
        params = _apply_fade(params, fade_in, fade_out, time_ms)
    # Session phase overrides — only honored outside of explicit
    # fade-in/fade-out so the transitions still own the visual when
    # they're in flight.
    elif phase == "intro_voice" or phase == "outro_voice":
        params = _apply_voice_shimmer(params, time_ms)
    elif phase == "chill":
        params = _apply_chill(params, time_ms)
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
            if not hasattr(render, '_yoyo_angle'):
                render._yoyo_angle = 0.0
                render._yoyo_vel = 0.0

            # Blend toward target velocity with inertia (smoothing factor)
            inertia = spin.get("yoyo_inertia", 0.995)
            render._yoyo_vel = render._yoyo_vel * inertia + velocity * (1 - inertia)

            # Integrate
            render._yoyo_angle += render._yoyo_vel * yoyo_speed * dt * 0.001

            spin_angle = render._yoyo_angle * math.pi * 2
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
