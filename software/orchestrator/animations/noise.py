"""White noise — a slowly shimmering, calming field of soft light.

Every LED gets its own quiet life: a blend of a few very slow waves at
frequencies and phases unique to that LED. Each one gently brightens
and dims on its own schedule, so the whole matrix shimmers like soft
static, candle-lit snow, or moonlight on water — never flashing, never
repeating, never moving in lockstep.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.noise`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "dim_level": 0.02,       # the floor — how bright a GLOWING LED is at its dimmest (0–1)
    "bright_level": 0.7,     # the ceiling — how bright the shimmering peaks get (0–1)
    "off_cutoff": 0.02,      # LEDs whose wave sits below this go COMPLETELY OFF —
                             # real black holes in the field for contrast (0 = none)
    "speed": 0.45,           # shimmer pace (1 = slow, calm; 2 = twice as lively)
    "tint": [235, 235, 210], # the color of the light — soft warm white with
                             # red ≤ green, so the dim shimmer floor can never
                             # quantize into red-dominant LEDs on the hardware
                             # (the old candle tint's dim tail rendered red)
    "softness": 6.5,         # >1 = most LEDs sit near the dim floor with bright
                             # ripples drifting through; 1 = even spread; <1 = mostly bright

    "fade_in_s": 3.0,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}


# Per-LED wave personalities, fixed once (seeded → same character every
# run): three slow waves per LED with random frequencies and phases.
_FREQS = None    # (TOTAL, 3) — cycles per second, all well under 1 Hz
_PHASES = None   # (TOTAL, 3)
_AMPS = None     # (TOTAL, 3) — each LED's mix of its three waves


def _waves():
    global _FREQS, _PHASES, _AMPS
    if _FREQS is None:
        rng = np.random.default_rng(7)
        # 0.04–0.22 Hz: one full brighten-dim swing takes ~5–25 seconds.
        _FREQS = rng.uniform(0.04, 0.22, size=(TOTAL, 3)).astype(np.float32)
        _PHASES = rng.uniform(0.0, 2.0 * math.pi, size=(TOTAL, 3)).astype(np.float32)
        amps = rng.uniform(0.4, 1.0, size=(TOTAL, 3)).astype(np.float32)
        _AMPS = amps / amps.sum(axis=1, keepdims=True)   # normalized mix
    return _FREQS, _PHASES, _AMPS


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    freqs, phases, amps = _waves()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the fade-in always replays.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    speed = float(p["speed"])

    # Each LED: a personal blend of three slow sines → -1..1, smooth.
    osc = np.sin(2.0 * math.pi * freqs * (t * speed) + phases)
    noise = (osc * amps).sum(axis=1)                 # -1..1 per LED

    # Map each LED's wave (-1..1) onto a brightness between the dim
    # floor and the bright ceiling. The softness curve keeps most LEDs
    # resting near the floor while gentle bright ripples drift through.
    v = (noise + 1.0) * 0.5                          # 0..1 per LED
    soft = max(0.1, float(p["softness"]))
    lo = float(p["dim_level"])
    hi = float(p["bright_level"])
    raw = v ** soft
    # Below the cutoff an LED goes fully OFF (true black, for contrast);
    # above it, brightness runs from the dim floor up to the ceiling.
    # As an LED's wave rises it turns on at the floor and climbs — the
    # on/off boundary keeps drifting around the matrix.
    cut = min(0.9, max(0.0, float(p["off_cutoff"])))
    scaled = np.clip((raw - cut) / max(1e-6, 1.0 - cut), 0.0, 1.0)
    level = np.where(raw > cut, lo + scaled * (hi - lo), 0.0)

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    tint = np.array(p["tint"], dtype=np.float32)
    rgb = level[:, np.newaxis] * tint[np.newaxis, :] \
        * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
