"""4-petal flower animation for Nadia's Playground.

A pink flower whose four petals reach out toward the four corners of the
platform (but stop short of the edges), with a small glowing center. By
default the flower is static, held fully open (set `animate: true` to make
it breathe).

This module is intentionally self-contained and HEAVILY commented so it's
easy to tweak. Every visual knob lives in `DEFAULTS` below with a plain
explanation of what it does and which way to nudge it. The Playground
merges any overrides from `config.playground.flower` on top of these.

Geometry note: the grid is 44×44, center at (21.5, 21.5). The four
corners lie on the diagonals (45°, 135°, 225°, 315°), so with the default
`base_rotation_deg = 45` the petals point straight at the corners. A reach
of ~30 would touch the corners; smaller keeps the petals inside the matrix.
"""
from __future__ import annotations

import colorsys
import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
# Tweak these (or override via config.playground.flower). Each line says
# what it does and how to change the feel.
DEFAULTS = {
    # --- Shape ---
    "petals": 4,                 # number of petals (4 = toward the corners)
    "base_rotation_deg": 45.0,   # 45 aims petals AT the corners; 0 aims at the edges
    "petal_reach": 24.0,         # how far a petal stretches (≈30 hits the corners; smaller stays inside)
    "petal_width": 3.6,          # fatness of each petal (smaller = thinner = more gap between petals)
    "petal_base_width": 0.5,     # min width at base/tip so petals don't pinch to nothing
    "edge_cutoff": 0.22,         # dim glow below this is turned fully OFF (black) — bigger = sharper petals, more black gap
    "edge_light_amount": 0.06,   # how much LIGHTER the petal edges get (0 = flat color, 1 = white rim)

    # --- Petal color: a radial gradient from center → tip ---
    "color_center": [110, 0, 45],    # deep, saturated pink/magenta near the center
    "color_tip":    [8, 0, 115],     # deep, saturated blue out at the tips

    # --- Inner petal (off) ---
    "inner_petal": False,        # draw a narrow light petal inside each big petal
    "inner_reach_frac": 0.62,    # inner petal length as a fraction of the big petal
    "inner_width": 1.1,          # how narrow the inner petal is
    "inner_light_amount": 0.7,   # how light the inner petal is (0 = same color, 1 = white)

    # --- Timed sequence (the intro choreography) ---
    "sequence": True,            # true = play the timed intro below; false = just sit fully open & static
    "center_time_s": 2.0,        # how long ONLY the center shows before petals appear
    "grow_time_s": 1.5,          # how long the petals take to grow out from the center
    "grow_ease": "ease_out",     # growth curve: linear / ease_in / ease_out / ease_in_out / smooth
    "grow_stagger": 0.35,        # per-petal growth delay (0 = all together, 0.6 = very staggered)
    "hold_time_s": 2.0,          # how long the open flower holds still before it starts moving
    "rotate_speed_deg_s": 8.0,   # how fast it rotates once moving (8°/s = one full turn every 45s)
    "rotate_ramp_s": 5.0,        # ease the rotation up to speed over this long (0 = start abruptly)
    "center_fade_s": 1.5,        # how long the center takes to fade in at the very start

    # --- Inner glow pulse (only while the flower is turning) ---
    "pulse_amount": 0.35,        # how strongly the petals glow from inside (0 = no pulse, 1 = full white)
    "pulse_period_s": 3.0,       # seconds per glow pulse (bigger = slower, calmer)

    # --- Motion blur (smooths the rotation) ---
    "motion_blur": True,         # leave a short light trail behind moving petals (false = crisp, no trail)
    "blur_decay": 0.6,           # trail persistence per frame (0.4 = subtle, 0.8 = long dreamy trail)

    # --- Center / core ---
    "core_size": 1.6,            # radius of the glowing flower center (smaller = tighter dot)
    "core_brightness": 1.0,      # how bright the center glows (0 = no core)
    "core_color": [255, 210, 120],  # warm gold

    # --- Ambient life (a gentle, ALWAYS-ON filter over the whole sequence so
    #     the flower never sits perfectly still — most visible during the
    #     static hold before it starts to rotate). All slow + subtle. ---
    "ambient": True,                 # master on/off for everything below
    "ambient_shimmer": 0.30,         # spatial brightness twinkle depth (0=off, 0.5=strong)
    "ambient_shimmer_scale": 0.45,   # shimmer blob size (smaller number = bigger, softer blobs)
    "ambient_shimmer_speed": 1.1,    # how fast the shimmer drifts
    "ambient_sway_deg": 0.0,         # rocking of the whole bloom (degrees); 0 = off
    "ambient_sway_period_s": 9.0,    # seconds per sway cycle (bigger = slower)
    "ambient_warp": 0.04,            # petal undulation depth (radians of angular wobble)
    "ambient_warp_period_s": 10.0,   # seconds per undulation cycle
    "ambient_breath": 0.05,          # in/out breathing of the petals (fraction of reach)
    "ambient_breath_period_s": 8.0,  # seconds per breath

    # --- Overall ---
    "brightness": 1.0,           # master brightness multiplier (0–1+)
}


# Per-LED geometry, precomputed once (the grid never changes at runtime).
_R = None      # distance from center, per LED
_THETA = None  # angle from center, per LED (radians)
_X = None      # x offset from center, per LED (for the ambient shimmer field)
_Y = None      # y offset from center, per LED


def _geometry():
    global _R, _THETA, _X, _Y
    if _R is None:
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - CENTER
            dy[i] = row - CENTER
        _R = np.sqrt(dx * dx + dy * dy)
        _THETA = np.arctan2(dy, dx)
        _X, _Y = dx, dy
    return _R, _THETA


def _smoothstep(u: float) -> float:
    """Ease 0→1 with soft start and stop (no abrupt motion)."""
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _ease(u: float, mode: str) -> float:
    """Easing curves for the petal growth, so the reveal reads organic
    instead of a flat linear wipe. `ease_out` (the default) makes the petals
    reach out fast then settle gently into place — a natural bloom."""
    u = min(1.0, max(0.0, u))
    if mode == "linear":
        return u
    if mode == "ease_in":                       # slow start, accelerate
        return u * u * u
    if mode == "ease_out":                      # fast start, decelerate (bloom)
        return 1.0 - (1.0 - u) ** 3
    if mode == "ease_in_out":                   # Perlin smootherstep (stronger S)
        return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)
    return u * u * (3.0 - 2.0 * u)              # "smooth" (smoothstep) fallback


def _cycled_color(base_rgb, hue_offset: float):
    """Rotate a color around the color wheel by `hue_offset` (0..1)."""
    r, g, b = (c / 255.0 for c in base_rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + hue_offset) % 1.0
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
    return np.array([nr * 255.0, ng * 255.0, nb * 255.0], dtype=np.float32)


def _lighten(color, amount: float):
    """Blend a color toward white by `amount` (0 = unchanged, 1 = white)."""
    amount = min(1.0, max(0.0, amount))
    return color * (1.0 - amount) + 255.0 * amount


def _petal_field(r, theta, reach: float, width: float, base_w: float,
                 n_petals: int, base_rot: float, spin: float, cutoff: float,
                 opens):
    """Intensity (0..1) of an `n_petals` flower. Returns one value per LED.
    Each petal is leaf-shaped: narrow at the base, fat in the middle, tapering
    to a soft tip. Anything dimmer than `cutoff` is turned fully off (black) so
    petals have crisp edges with real black space between them.

    `opens` is a per-petal open amount (0..1). The petal GROWS BY SCALING: at
    open<1 it's a smaller but COMPLETE petal — proper rounded tip, still rooted
    at the core — that grows to full size at open=1. (Not an outward reveal,
    which sliced the tip mid-petal and looked like an unfolding mask.)"""
    field = np.zeros(TOTAL, dtype=np.float32)
    for k in range(n_petals):
        o = float(opens[k]) if k < len(opens) else 1.0
        if o <= 0.001:
            continue
        # Scale the whole petal (length + width) by its open amount so it stays
        # in proportion — a small complete petal that grows.
        cur_reach = max(0.5, reach * o)
        cur_width = width * o
        cur_base = base_w * o

        direction = base_rot + spin + k * (2.0 * math.pi / n_petals)
        da = np.mod(theta - direction + math.pi, 2.0 * math.pi) - math.pi
        along = r * np.cos(da)      # distance ALONG the petal axis
        across = r * np.sin(da)     # distance to the SIDE of the axis

        norm = along / cur_reach                    # 0 at center → 1 at tip
        inside = (norm >= 0.0) & (norm <= 1.0)
        long_prof = np.sin(np.clip(norm, 0.0, 1.0) * math.pi)
        half_w = np.maximum(cur_base + cur_width * long_prof, 0.25)
        lat_prof = np.exp(-(across * across) / (2.0 * half_w * half_w))
        this_petal = np.where(inside, long_prof * lat_prof, 0.0).astype(np.float32)
        field = np.maximum(field, this_petal)
    # Hard cutoff: kill the dim halo so the gaps between petals are truly
    # black, then re-stretch what's left back to full brightness.
    cutoff = min(0.95, max(0.0, cutoff))
    field = np.clip((field - cutoff) / (1.0 - cutoff), 0.0, 1.0)
    return field


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()

    n_petals = max(1, int(p["petals"]))
    base_rot = math.radians(float(p["base_rotation_deg"]))
    base_w = float(p["petal_base_width"])
    full_reach = float(p["petal_reach"])

    # ── Sequence timing ──────────────────────────────────────────────
    # Stamp the start on the first frame of a run; `state` is reset by the
    # Playground on each (re)trigger / play, so the sequence replays from
    # the top every time the flower starts.
    if p.get("sequence") and state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        elapsed = (time_ms - state["t0"]) / 1000.0

        center_end = float(p["center_time_s"])
        grow_end = center_end + float(p["grow_time_s"])
        hold_end = grow_end + float(p["hold_time_s"])

        ease_mode = str(p.get("grow_ease", "ease_out"))
        stagger = max(0.0, min(0.9, float(p.get("grow_stagger", 0.35))))
        if elapsed < center_end:
            petal_opens = [0.0] * n_petals          # center only
        elif elapsed < grow_end:
            # Per-petal growth, each delayed a little so they bloom in sequence.
            g = (elapsed - center_end) / max(0.01, float(p["grow_time_s"]))
            span = max(0.01, 1.0 - stagger)         # each petal's own duration
            petal_opens = []
            for k in range(n_petals):
                off = (k / (n_petals - 1)) * stagger if n_petals > 1 else 0.0
                petal_opens.append(_ease((g - off) / span, ease_mode))
        else:
            petal_opens = [1.0] * n_petals          # fully open (hold + rotate)

        # Rotation kicks in after the hold (colors stay fixed). Ease the
        # angular VELOCITY up from 0 → full over `rotate_ramp_s` so it glides
        # into motion instead of lurching. The angle is the integral of that
        # ramp, so it stays continuous (spin = 0 exactly at hold_end).
        move_t = max(0.0, elapsed - hold_end)
        v = float(p["rotate_speed_deg_s"])
        ramp = max(0.0, float(p.get("rotate_ramp_s", 5.0)))
        if move_t < ramp and ramp > 0.0:
            spin_deg = v * move_t * move_t / (2.0 * ramp)      # ½·v·t²/ramp
        else:
            spin_deg = v * (move_t - ramp / 2.0)               # full speed
        spin = math.radians(spin_deg)
        core_fade = min(1.0, elapsed / max(0.01, float(p["center_fade_s"])))
    else:
        # Static: fully open, no motion.
        petal_opens = [1.0] * n_petals
        spin, core_fade, move_t = 0.0, 1.0, 0.0
    open_amt = max(petal_opens) if petal_opens else 0.0

    # ── Ambient life ─────────────────────────────────────────────────
    # A slow, always-on filter so the bloom subtly breathes even while it's
    # held still: `sway` rocks the whole flower, `warp` makes the petals
    # undulate (a serpentine angular wobble that varies along each petal),
    # and `breath` lets the reach expand/contract a touch. The brightness
    # shimmer is applied at the very end (after motion blur). Everything is
    # keyed off absolute time so it runs through every stage of the sequence.
    amb = bool(p.get("ambient"))
    t_s = time_ms / 1000.0
    reach_eff = full_reach
    theta_eff = theta
    if amb:
        sway = math.radians(float(p["ambient_sway_deg"]))
        spin += sway * math.sin(2.0 * math.pi * t_s
                                / max(0.5, float(p["ambient_sway_period_s"])))
        breath = float(p["ambient_breath"])
        reach_eff = full_reach * (1.0 + breath * math.sin(
            2.0 * math.pi * t_s / max(0.5, float(p["ambient_breath_period_s"]))))
        warp = float(p["ambient_warp"])
        if warp != 0.0:
            theta_eff = theta + warp * np.sin(
                r * 0.18 + 2.0 * math.pi * t_s
                / max(0.5, float(p["ambient_warp_period_s"])))

    # ── Petals ───────────────────────────────────────────────────────
    rgb = np.zeros((TOTAL, 3), dtype=np.float32)
    if open_amt > 0.001:
        cutoff = float(p["edge_cutoff"])

        # Radial color gradient: pink near the center → blue at the tips.
        c_center = np.array(p["color_center"], dtype=np.float32)
        c_tip = np.array(p["color_tip"], dtype=np.float32)
        frac = np.clip(r / reach_eff, 0.0, 1.0)[:, np.newaxis]
        grad_color = c_center[np.newaxis, :] * (1.0 - frac) + c_tip[np.newaxis, :] * frac

        # Big petal, with edges blended a little lighter for a soft rim.
        petal = _petal_field(r, theta_eff, reach_eff, float(p["petal_width"]),
                             base_w, n_petals, base_rot, spin, cutoff, petal_opens)
        edge_t = ((1.0 - petal) * float(p["edge_light_amount"]))[:, np.newaxis]
        petal_color = grad_color * (1.0 - edge_t) + 255.0 * edge_t

        # Inner glow pulse — only while the flower is turning. A slow,
        # soft wave of light breathes through the BODY of each petal
        # (strongest along the petal's spine, none at the edges). It
        # eases in over the first couple of seconds of rotation so the
        # hold → turn handoff doesn't pop.
        pulse_amount = float(p["pulse_amount"])
        if move_t > 0.0 and pulse_amount > 0.0:
            period = max(0.5, float(p["pulse_period_s"]))
            osc = (1.0 - math.cos(2.0 * math.pi * move_t / period)) / 2.0
            ramp = min(1.0, move_t / 2.0)
            # `petal**2` concentrates the glow inside the petal body.
            w = (petal * petal * (pulse_amount * ramp * osc))[:, np.newaxis]
            petal_color = petal_color * (1.0 - w) + 255.0 * w

        rgb += petal[:, np.newaxis] * petal_color

        # Narrow, lighter inner petal nested inside (off by default).
        if p.get("inner_petal"):
            inner = _petal_field(r, theta_eff, reach_eff * float(p["inner_reach_frac"]),
                                 float(p["inner_width"]), base_w, n_petals,
                                 base_rot, spin, cutoff, petal_opens)
            inner_color = _lighten(c_center, float(p["inner_light_amount"]))
            a = inner[:, np.newaxis]
            rgb = rgb * (1.0 - a) + inner_color[np.newaxis, :] * a

    # ── Glowing center core (fades in at the very start) ──────────────
    core_size = max(0.1, float(p["core_size"]))
    core = np.exp(-(r * r) / (2.0 * core_size * core_size)) * float(p["core_brightness"]) * core_fade
    rgb += core[:, np.newaxis] * np.array(p["core_color"], dtype=np.float32)

    # ── Motion blur ────────────────────────────────────────────────
    # Each frame keeps a dimmed ghost of the previous one (`blur_decay`
    # per frame), so the trailing edge of a turning petal fades out
    # smoothly instead of stepping LED by LED. Static parts are
    # unaffected (the ghost is never brighter than the live pixel).
    # To remove the effect entirely: set "motion_blur" to False.
    if p.get("motion_blur") and state is not None:
        decay = min(0.95, max(0.0, float(p["blur_decay"])))
        prev = state.get("_blur")
        if prev is not None and prev.shape == rgb.shape:
            rgb = np.maximum(rgb, prev * decay)
        state["_blur"] = rgb

    # ── Ambient shimmer ──────────────────────────────────────────────
    # A soft, slowly drifting spatial brightness twinkle over whatever is lit
    # (petals + core). Multiplicative, so black gaps stay black. Applied AFTER
    # motion blur so it stays crisp instead of smearing into the trail, and
    # AFTER the blur store so it never accumulates frame-to-frame.
    if amb:
        shimmer = float(p["ambient_shimmer"])
        if shimmer > 0.0:
            sc = float(p["ambient_shimmer_scale"])
            sp = float(p["ambient_shimmer_speed"])
            field = (np.sin(_X * sc + t_s * sp * 0.7)
                     + np.sin(_Y * sc * 0.8 - t_s * sp * 0.5)
                     + np.sin((_X + _Y) * sc * 0.6 + t_s * sp * 0.9)) / 3.0
            rgb = rgb * (1.0 + shimmer * field)[:, np.newaxis]

    rgb = np.clip(rgb * float(p["brightness"]), 0, 255).astype(np.uint8)
    frame[:] = rgb.tobytes()
