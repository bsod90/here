"""Fireplace mode — heat field + blackbody palette + sharp flame tongues.

Pipeline per frame:
  1. **Base heat**   — radial falloff, hottest at the centre.
  2. **Turbulence**  — sum of moving sinusoids; gives the body constant
     flicker without going chaotic.
  3. **Flares**      — thin radial tongues that travel outward from the
     core. Each lives ~1 s with a quick attack + fade, with the hottest
     point at the tip (Tsoi "Zvezda po imeni солнце" energy).
  4. **Flicker**     — per-frame global multiplier for vertical breath.
  5. **Palette**     — heat (0..1) → blackbody-ish gradient
     (black → deep red → red → orange → yellow → white-yellow).
  6. **Embers**      — random pixels around the body, additive on top.

Numpy makes the per-frame field math cheap (≪1 ms on the Pi for 44×44).
"""
from __future__ import annotations

import math
import random
from typing import Any

import numpy as np

from grid import GRID


# ── Pixel coordinate precompute ─────────────────────────────────
_C = (GRID - 1) / 2.0
_DC = (np.arange(GRID, dtype=np.float32).reshape(1, GRID) - _C)
_DR = (np.arange(GRID, dtype=np.float32).reshape(GRID, 1) - _C)
_D = np.sqrt(_DR * _DR + _DC * _DC)
_THETA = np.arctan2(_DR, _DC)


# ── Heat → colour palette (256 entries, blackbody-ish) ──────────
# Each stop is (heat_value, (R, G, B)). The palette is interpolated
# linearly between adjacent stops, then frozen into a 256×3 LUT.
_PALETTE_STOPS = [
    (0.00, (  0,   0,   0)),
    (0.06, ( 18,   0,   0)),
    (0.14, ( 70,   3,   0)),
    (0.24, (140,  12,   0)),
    (0.36, (210,  35,   0)),
    (0.50, (250,  80,  10)),
    (0.64, (255, 140,  25)),
    (0.78, (255, 200,  60)),
    (0.90, (255, 235, 140)),
    (1.00, (255, 250, 220)),
]


def _build_palette() -> np.ndarray:
    lut = np.zeros((256, 3), dtype=np.uint8)
    stops = _PALETTE_STOPS
    for i in range(256):
        x = i / 255.0
        for j in range(len(stops) - 1):
            x0, c0 = stops[j]
            x1, c1 = stops[j + 1]
            if x0 <= x <= x1:
                f = (x - x0) / (x1 - x0)
                lut[i] = [int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)]
                break
    return lut


_PALETTE = _build_palette()


DEFAULT_PARAMS: dict[str, Any] = {
    # Body geometry. A soft filled disc — hottest core, fading to the rim.
    "core_radius":   6.0,
    "outer_radius": 14.0,
    "brightness":    1.0,
    # Slow "breath" of the whole ember — size + brightness gently swell and
    # settle. This is the calm, slowed-down pulse the look is built around.
    "pulse_amp":      0.12,    # fraction the radius swells at the peak
    "pulse_period_s": 9.0,     # seconds per full breath (bigger = slower)
    # Grain shimmer — a multi-frequency radial+angular wobble over the body
    # that gives the rough, vibrating "live coals" texture (borrowed from
    # the MIDI synth ring). Applied AFTER heat-smoothing so it stays crisp.
    "shimmer_amount": 0.35,    # 0 = smooth disc, higher = rougher grain
    "shimmer_speed":  0.45,    # how fast the grain churns (slow = calm)
    # Turbulence — slow heat noise that makes the body churn, not a flat disc.
    "turb_amp":      0.10,
    "turb_speed":    0.5,
    "flicker_amp":   0.025,
    "flicker_smoothing": 0.06,
    "heat_smoothing": 0.45,
    # Flares — tapered, curved tongues. OFF by default (flare_max=0): the
    # default look is the soft shimmering ember disc, not flame tongues.
    # Raise Max Flares in the Tune tab to bring them back. Range-style
    # params are gone: the spawner applies ±25 % jitter to each "mean".
    "flare_max":          0,
    "flare_spawn_hz":     2.0,
    "flare_speed_mean":  11.0,    # LED/s outward
    "flare_life_mean":    0.95,   # seconds
    "flare_reach_mean":  10.0,    # LEDs past outer_radius the tip can reach
    "flare_base_width":   0.20,   # radians — angular thickness at the rim
    "flare_tip_width":    0.04,   # radians — angular thickness at the tip
    "flare_curl_amp":     0.18,   # radians — peak centerline deviation
    "flare_curl_freq":    1.8,    # how many half-curves along the flame
    # Anchor point (× outer_radius) where the burst's base sits. 0.85 ≈
    # clearly inside the body but close to the rim, so the flame appears
    # to grow out of the fire rather than off its edge. 1.0 = on the rim;
    # < 0.7 buries the root deep in the body.
    "flare_inner_factor": 0.85,
    # Heat strength along the flame. Base sits near the body so it's
    # mostly orange; tip pop is a thin highlight.
    "flare_base_heat":    0.55,
    "flare_tip_heat":     0.35,
    # Rare detachment — chance a flare's base launches past the rim so
    # the tongue floats unattached (cf. real flames sometimes do).
    # Detached flares are scaled down so they read as quick sparks
    # rather than displaced full tongues.
    "flare_detach_prob":     0.08,
    "flare_detach_factor":   1.12,   # × outer_radius for the detached base
    # Embers — random sparks around the body. OFF by default for the clean
    # ember-disc look; raise Max Embers to add drifting sparks.
    "ember_max":          0,
    "ember_spawn_hz":     2.0,
    "ember_life_mean":    1.05,
    "ember_radius_mean": 16.5,
    "ember_color":      [255, 130, 30],
}


# ── State helpers ───────────────────────────────────────────────
def _ensure_state(state: dict) -> None:
    state.setdefault("flares", [])
    state.setdefault("embers", [])
    state.setdefault("last_t", None)
    state.setdefault("flicker", 0.0)


def _jitter(mean: float, frac: float = 0.25) -> float:
    return float(mean) * random.uniform(1.0 - frac, 1.0 + frac)


def _spawn_flare(t: float, p: dict) -> dict:
    detached = random.random() < float(p["flare_detach_prob"])
    # Detached flares are scaled down to look like brief sparks rather
    # than full tongues misplaced past the rim — that "out-of-place"
    # feel comes from a full-size flame floating without a body.
    if detached:
        life_scale  = 0.40
        reach_scale = 0.50
        width_scale = 0.55
    else:
        life_scale = reach_scale = width_scale = 1.0
    return {
        "angle":      random.uniform(0.0, 2 * math.pi),
        "speed":      _jitter(p["flare_speed_mean"]),
        "t0":         t,
        "duration":   _jitter(p["flare_life_mean"]) * life_scale,
        "reach":      _jitter(p["flare_reach_mean"]) * reach_scale,
        "base_width": _jitter(p["flare_base_width"]) * width_scale,
        "tip_width":  _jitter(p["flare_tip_width"])  * width_scale,
        "curl_amp":   _jitter(p["flare_curl_amp"]) * random.choice((-1.0, 1.0)),
        "curl_phase": random.uniform(0.0, 2 * math.pi),
        "curl_freq":  float(p["flare_curl_freq"]),
        "intensity":  random.uniform(0.75, 1.0),
        "detached":   detached,
    }


def _spawn_ember(t: float, p: dict) -> dict | None:
    r = _jitter(p["ember_radius_mean"])
    a = random.uniform(0.0, 2 * math.pi)
    er = int(round(_C + math.sin(a) * r))
    ec = int(round(_C + math.cos(a) * r))
    if not (0 <= er < GRID and 0 <= ec < GRID):
        return None
    return {"row": er, "col": ec, "t0": t,
            "duration": _jitter(p["ember_life_mean"])}


# Crossfade durations — read by the engine's generic transition logic.
FADE_IN_S = 5.0
FADE_OUT_S = 4.0


def _apply_fade(p: dict, fade_in: float | None, fade_out: float | None) -> None:
    """Mutate `p` in place: scale brightness + body geometry so the
    fire grows in / dies down rather than appearing/disappearing."""
    mult = 1.0
    if fade_in is not None:
        u = max(0.0, min(1.0, fade_in))
        # Brightness rises with eased progress; body grows from a small
        # core to its configured radius.
        grow = u ** 1.3
        mult *= 0.10 + grow * 0.90
        p["core_radius"] = float(p.get("core_radius", 5.0)) * (0.20 + grow * 0.80)
        p["outer_radius"] = float(p.get("outer_radius", 12.0)) * (0.30 + grow * 0.70)
        # Suppress flares early — they only start spawning past the
        # half-way mark so the rim is established first.
        if u < 0.5:
            p["flare_spawn_hz"] = 0.0
        else:
            p["flare_spawn_hz"] = float(p.get("flare_spawn_hz", 2.0)) * ((u - 0.5) / 0.5)
    if fade_out is not None:
        u = max(0.0, min(1.0, fade_out))
        shrink = max(0.0, 1.0 - u)
        mult *= shrink
        p["core_radius"] = float(p.get("core_radius", 5.0)) * (0.4 + shrink * 0.6)
        p["outer_radius"] = float(p.get("outer_radius", 12.0)) * (0.4 + shrink * 0.6)
        # No new flares or embers as the fire dies.
        if u > 0.3:
            p["flare_spawn_hz"] = 0.0
            p["ember_spawn_hz"] = 0.0
    p["brightness"] = float(p.get("brightness", 1.0)) * mult


# ── Main render ─────────────────────────────────────────────────
def render(frame: bytearray, time_ms: float, params: dict, state: dict,
           *, fade_in: float | None = None, fade_out: float | None = None):
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    if fade_in is not None or fade_out is not None:
        _apply_fade(p, fade_in, fade_out)
    _ensure_state(state)

    t = time_ms / 1000.0
    last_t = state["last_t"]
    dt = (t - last_t) if last_t is not None else 0.0
    state["last_t"] = t

    # Slow breath of the whole ember — gently swells size + brightness.
    pulse_amp = float(p["pulse_amp"])
    period = max(0.1, float(p["pulse_period_s"]))
    pulse = math.sin(2.0 * math.pi * t / period)        # -1..1
    radius_mult = 1.0 + pulse_amp * pulse
    pulse_bright = 1.0 + 0.5 * pulse_amp * pulse

    inner = float(p["core_radius"]) * radius_mult
    outer = float(p["outer_radius"]) * radius_mult

    # MIDI-tab "voice shimmer": a multi-frequency wobble of the *radial
    # coordinate*, so the ember rim vibrates and the body shows fine moving
    # grain — the same rough texture as the synth ring (which uses high
    # angular frequencies: angles×11/17/5). Perturbing the radius itself
    # (not just brightness) is what gives the characteristic vibrating look.
    # The radial terms (sin(_D·…)) add grain to the interior, not just the
    # rim. Time is kept slow so the fireplace stays calm.
    shimmer_amount = float(p["shimmer_amount"])
    d_eff = _D
    if shimmer_amount > 0.001:
        ss = t * float(p["shimmer_speed"])
        wobble = (0.55 * np.sin(_THETA * 11.0 + ss * 1.3) +
                  0.30 * np.sin(_THETA * 17.0 - ss * 1.8) +
                  0.20 * np.sin(_THETA * 5.0  + ss * 2.6) +
                  0.40 * np.sin(_D * 3.3 - _THETA * 7.0 - ss * 1.0) +
                  0.25 * np.sin(_D * 5.7 + ss * 1.5))
        d_eff = _D - wobble * (shimmer_amount * 2.0)   # LED-unit perturbation

    # 1) Base radial heat: 1 at the centre, ~0 at outer.
    heat = np.clip(1.0 - (d_eff - inner * 0.25) / (outer - inner * 0.25 + 1e-6),
                   0.0, 1.0).astype(np.float32)
    # Slight squash so the body has volume, not a flat disc.
    heat = heat ** 1.15

    # 2) Turbulence — sum of moving sinusoids. Stronger inside the body
    # so the outer ring stays calm and the centre churns.
    ts = float(p["turb_speed"])
    turb = (
        np.sin(_D * 0.30 + t * 3.0 * ts) * 0.55 +
        np.sin(_THETA * 3.0 + t * 2.2 * ts) * 0.40 +
        np.sin(_D * 0.65 - _THETA * 2.0 + t * 4.3 * ts) * 0.35 +
        np.sin(_D * 1.10 + _THETA * 5.0 - t * 5.8 * ts) * 0.22
    )
    heat += p["turb_amp"] * turb * np.sqrt(np.clip(heat, 0.0, 1.0))

    # 3) Flares — thin tongues shooting outward.
    flares = [f for f in state["flares"] if (t - f["t0"]) < f["duration"]]
    spawn_p = float(p["flare_spawn_hz"]) * max(dt, 0.0)
    while len(flares) < int(p["flare_max"]) and random.random() < spawn_p:
        flares.append(_spawn_flare(t, p))
        spawn_p *= 0.4  # diminishing returns within one frame
    state["flares"] = flares

    inner_factor = float(p["flare_inner_factor"])
    detach_factor = float(p["flare_detach_factor"])
    base_heat = float(p["flare_base_heat"])
    tip_heat = float(p["flare_tip_heat"])

    for f in flares:
        age = t - f["t0"]
        u = age / max(f["duration"], 0.001)         # 0..1 over the flame's life
        # Asymmetric envelope: fast attack to ~35 %, slower fade.
        env = (u / 0.35) if u < 0.35 else max(0.0, 1.0 - (u - 0.35) / 0.65)
        env *= f["intensity"]
        if env <= 0:
            continue

        # Base anchored at the rim (or further out if detached). tip_r
        # is the distance from centre to the leading edge.
        anchor = outer * (detach_factor if f["detached"] else inner_factor)
        tip_r = anchor + f["speed"] * age
        max_r = outer + f["reach"]
        tip_r = min(tip_r, max_r)
        if tip_r <= anchor:
            continue

        # Normalized position along the flame (0 at base, 1 at tip).
        span = max(tip_r - anchor, 0.5)
        in_range = (_D >= anchor) & (_D <= tip_r * 1.03)
        along = np.where(in_range, np.clip((_D - anchor) / span, 0.0, 1.0), 0.0)

        # Curved centerline: angle bends with position along the flame.
        # The asymmetric ±curl_amp + random phase keeps each flame's
        # snake unique; without this we'd get straight ballistic streaks.
        center_angle = (f["angle"]
                        + f["curl_amp"]
                        * np.sin(along * f["curl_freq"] + f["curl_phase"]))
        da = _THETA - center_angle
        da = np.mod(da + math.pi, 2 * math.pi) - math.pi

        # Tapered width: wide at the base, sharpening toward the tip.
        # `along**1.6` keeps the base broad before tapering away near
        # the head — closer to a real flame than a linear narrowing.
        bw = float(f["base_width"])
        tw = float(f["tip_width"])
        width_at = bw + (tw - bw) * (along ** 1.6)
        width_at = np.maximum(width_at, 0.015)
        ang_g = np.exp(-(da * da) / (2.0 * width_at * width_at))
        ang_g = np.where(in_range, ang_g, 0.0)

        # Radial intensity: bright base fading toward the tip + a thin
        # pop at the very head so the tip flicks brighter.
        body_profile = base_heat * (1.0 - 0.55 * along)
        tip_pop = tip_heat * np.exp(-((along - 0.93) ** 2) / (2.0 * 0.05 ** 2))

        heat += ang_g * (body_profile + tip_pop) * env

    # 4) Smoothed flicker — low-pass a per-frame random target so the
    # global brightness drifts organically instead of going TV-static at
    # 30 fps. `flicker_smoothing` is the lerp rate toward each frame's
    # new target; smaller = slower, more cinematic breath.
    target = (random.random() - 0.5) * 2.0 * float(p["flicker_amp"])
    alpha = float(p["flicker_smoothing"])
    state["flicker"] = (1.0 - alpha) * float(state["flicker"]) + alpha * target
    heat *= 1.0 + state["flicker"]

    # 5) Temporal smoothing of the heat field. Without this each pixel's
    # heat value can jump across palette band boundaries every frame —
    # reads as "epileptic" colour shimmer even though the underlying
    # field is moving slowly.
    sm = float(p["heat_smoothing"])
    prev = state.get("heat_prev")
    if sm > 0 and prev is not None and prev.shape == heat.shape:
        heat = sm * prev + (1.0 - sm) * heat
    state["heat_prev"] = heat.copy()

    # 6) Palette LUT lookup (slow breath also modulates brightness).
    heat = np.clip(heat * float(p["brightness"]) * pulse_bright, 0.0, 1.0)
    idx = (heat * 255).astype(np.uint8)
    pixels = _PALETTE[idx]                      # (GRID, GRID, 3) uint8

    # 7) Embers — additive on top of the palette.
    embers = [em for em in state["embers"] if (t - em["t0"]) < em["duration"]]
    spawn_p = float(p["ember_spawn_hz"]) * max(dt, 0.0)
    while len(embers) < int(p["ember_max"]) and random.random() < spawn_p:
        em = _spawn_ember(t, p)
        if em is not None:
            embers.append(em)
        spawn_p *= 0.35
    state["embers"] = embers

    ec = p["ember_color"]
    pix_f = pixels.astype(np.int16)
    for em in embers:
        u = (t - em["t0"]) / max(em["duration"], 0.001)
        i = (u / 0.12) if u < 0.12 else max(0.0, 1.0 - (u - 0.12) / 0.88)
        i *= float(p["brightness"])
        if i <= 0:
            continue
        r, c = em["row"], em["col"]
        pix_f[r, c, 0] += int(ec[0] * i)
        pix_f[r, c, 1] += int(ec[1] * i)
        pix_f[r, c, 2] += int(ec[2] * i)
    np.clip(pix_f, 0, 255, out=pix_f)
    pixels = pix_f.astype(np.uint8)

    # 8) Blit into the bytearray frame buffer.
    frame[:] = pixels.tobytes()
