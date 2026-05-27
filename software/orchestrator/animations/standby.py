"""Standby animation — sparse random LED sparkles.

Sparkles fade in, hold briefly, then fade out.
Color palette and density are configurable.
"""
from __future__ import annotations

import random
from grid import TOTAL


# How long the in/out crossfades take when transitioning to/from this
# animation. The animation engine reads these to drive a generic
# crossfade between any pair of animations.
FADE_IN_S = 4.0
FADE_OUT_S = 4.0


def _fade_multiplier(fade_in: float | None, fade_out: float | None) -> float:
    """Combined brightness multiplier from the engine-supplied fade
    progress. Standby's out-fade has a brief intensify peak at u≈0.4
    (room "wakes up") before dimming to zero — keeps the disappearance
    from feeling like a switch flick."""
    m = 1.0
    if fade_in is not None:
        # Sparkles fade in linearly with progress.
        m *= max(0.0, min(1.0, fade_in))
    if fade_out is not None:
        u = max(0.0, min(1.0, fade_out))
        peak = 1.7
        if u < 0.4:
            m *= 1.0 + (u / 0.4) * (peak - 1.0)
        else:
            m *= peak * max(0.0, 1.0 - (u - 0.4) / 0.6)
    return m


def render(frame: bytearray, time_ms: float, params: dict, state: dict,
           *, fade_in: float | None = None, fade_out: float | None = None):
    density = params["sparkle_density"]
    palette = params["color_palette"]
    fade_speed = params["fade_speed"]
    max_brightness = params["max_brightness"]
    spawn_rate = params["spawn_rate"]

    # During the out-fade's intensify window we increase spawn rate and
    # density a little so the "wake up" reads as a genuine swell, not
    # just brighter sparkles.
    if fade_out is not None:
        u = max(0.0, min(1.0, fade_out))
        if u < 0.4:
            intensify = u / 0.4
            spawn_rate = int(spawn_rate * (1.0 + intensify * 1.0))
            density = min(0.4, density * (1.0 + intensify * 0.8))

    mult = _fade_multiplier(fade_in, fade_out)

    # Initialize state on first call
    if "sparkles" not in state:
        state["sparkles"] = {}

    sparkles = state["sparkles"]
    max_active = int(TOTAL * density)

    # Spawn new sparkles
    if len(sparkles) < max_active:
        for _ in range(spawn_rate):
            idx = random.randint(0, TOTAL - 1)
            if idx not in sparkles:
                sparkles[idx] = {
                    "color": random.choice(palette),
                    "brightness": 0.0,
                    "phase": "up",
                }

    # Clear frame
    for i in range(len(frame)):
        frame[i] = 0

    # Update and render
    to_remove = []
    for idx, s in sparkles.items():
        if s["phase"] == "up":
            s["brightness"] += fade_speed * 2  # fade in faster
            if s["brightness"] >= max_brightness:
                s["brightness"] = max_brightness
                s["phase"] = "down"
        else:
            s["brightness"] -= fade_speed
            if s["brightness"] <= 0:
                to_remove.append(idx)
                continue

        b = s["brightness"] * mult
        if b <= 0:
            continue
        c = s["color"]
        off = idx * 3
        frame[off] = min(255, int(c[0] * b))
        frame[off + 1] = min(255, int(c[1] * b))
        frame[off + 2] = min(255, int(c[2] * b))

    for idx in to_remove:
        del sparkles[idx]
