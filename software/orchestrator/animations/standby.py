"""Standby animation — sparse random LED sparkles.

Sparkles fade in, hold briefly, then fade out.
Color palette and density are configurable.
"""
import random
from grid import TOTAL


def render(frame: bytearray, time_ms: float, params: dict, state: dict):
    density = params["sparkle_density"]
    palette = params["color_palette"]
    fade_speed = params["fade_speed"]
    max_brightness = params["max_brightness"]
    spawn_rate = params["spawn_rate"]

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

        b = s["brightness"]
        c = s["color"]
        off = idx * 3
        frame[off] = int(c[0] * b)
        frame[off + 1] = int(c[1] * b)
        frame[off + 2] = int(c[2] * b)

    for idx in to_remove:
        del sparkles[idx]
