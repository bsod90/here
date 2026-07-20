"""Eyes — a hand-drawn pair of blinking eyes, played from baked frames.

Source: a 4K pencil-sketch video (Dream_1.mp4). Converted one-off with
ffmpeg + numpy — centre SQUARE crop (no aspect distortion), area-scaled
to the matrix, 38 frames @ 24 fps, seamless loop:

    ffmpeg -i Dream_1.mp4 \
        -vf "crop=2160:2160:840:0,scale=44:44:flags=area" \
        -f rawvideo -pix_fmt rgb24 eyes.rgb
    frames = np.fromfile("eyes.rgb", np.uint8).reshape(-1, 44, 44, 3)
    np.savez_compressed("animations/data/eyes.npz", frames=frames)

The sketch is dark-pencil-on-WHITE; played literally that would drive
~1,900 LEDs full white (≈190 W and a lot of glare on the playa night),
so by default the drawing is INVERTED — softly glowing eyes on a black
floor. Set `invert: False` under config.playground.eyes for the paper
look. Playback lerps between neighbouring frames, so slowing it down
(`speed`) stays smooth.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from grid import GRID, TOTAL


DEFAULTS = {
    "speed": 1.0,            # playback rate; 1.0 = the source's 24 fps loop
    "invert": True,          # glowing eyes on black (see module docstring)
    "black_point": 12.0,     # paper noise floor removed after inversion
    "gain": 1.5,             # stroke brightness boost (soft pencil greys)
    "color": [255, 255, 255],  # tint of the inverted drawing
    "brightness": 1.0,
    "fade_in_s": 1.5,        # gentle fade from black when the animation starts
}

_SRC_FPS = 24.0

_FRAMES: np.ndarray | None = None


def _frames() -> np.ndarray:
    global _FRAMES
    if _FRAMES is None:
        path = Path(__file__).parent / "data" / "eyes.npz"
        _FRAMES = np.load(path)["frames"].astype(np.float32)
    return _FRAMES


# Fallback state for callers that pass none.
_FALLBACK_STATE: dict = {}


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else _FALLBACK_STATE
    if "t0" not in st:
        st["t0"] = time_ms
    t = (time_ms - st["t0"]) / 1000.0

    fr = _frames()
    if fr.shape[1] != GRID or fr.shape[2] != GRID:
        frame[:] = bytes(TOTAL * 3)      # baked for a different grid → dark
        return

    # Fractional playback position with a lerp between neighbouring
    # frames — slow playback stays smooth instead of stepping at 24 fps.
    n = len(fr)
    pos = (t * _SRC_FPS * max(0.01, float(p["speed"]))) % n
    i0 = int(pos)
    f = pos - i0
    img = fr[i0] * (1.0 - f) + fr[(i0 + 1) % n] * f      # (GRID, GRID, 3)

    if p.get("invert", True):
        img = 255.0 - img
        bp = min(200.0, max(0.0, float(p["black_point"])))
        img = (img - bp) * (255.0 / (255.0 - bp))
        img = np.clip(img, 0.0, 255.0) * max(0.0, float(p["gain"]))
        tint = np.array(p.get("color") or [255, 255, 255], np.float32) / 255.0
        img = img * tint[None, None, :]

    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))
    img = np.clip(img * (float(p["brightness"]) * fade), 0, 255)
    frame[:] = img.astype(np.uint8).reshape(-1).tobytes()
