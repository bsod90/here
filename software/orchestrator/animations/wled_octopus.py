"""Octopus — ported from WLED `mode_2Doctopus`.

A rotating radial swirl: per-pixel polar coordinates (angle, radius about
an adjustable center) feed a nested-sine field that spins outward, colored
by the palette in concentric rings. The polar map is precomputed once and
cached in `state` (recomputed only if the center offset changes).

Knobs (WLED 0..255):
  speed     — swirl rotation rate
  custom1/2 — center offset X / Y (128 = centered)
  custom3   — number of spiral arms ("Legs", 0..31)
"""
from __future__ import annotations

import numpy as np

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "twilight",
    "speed": 40,         # 0..255
    "custom1": 128,      # center X offset
    "custom2": 128,      # center Y offset
    "custom3": 8,        # legs (0..31)
    "brightness": 1.0,
    "fade_in_s": 2.0,
}


def _polar(off_x: int, off_y: int):
    cols, rows = w.COLS, w.ROWS
    mapp = 180.0 / max(cols, rows)
    cx = (cols / 2) + ((off_x - 128) * cols) / 255.0
    cy = (rows / 2) + ((off_y - 128) * rows) / 255.0
    X, Y = w.coords()
    dx = X - cx
    dy = Y - cy
    angle = (40.7436 * np.arctan2(dy, dx)) % 256.0     # 0..255 over a turn
    radius = np.sqrt(dx * dx + dy * dy) * mapp
    return angle.astype(np.float32), radius.astype(np.float32)


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)

    ox, oy = int(p["custom1"]), int(p["custom2"])
    if st.get("_off") != (ox, oy):
        st["angle"], st["radius"] = _polar(ox, oy)
        st["_off"] = (ox, oy)
        st["step"] = 0.0
    angle, radius = st["angle"], st["radius"]
    st["step"] = st.get("step", 0.0) + float(p["speed"]) / 32.0 + 1.0
    step = st["step"]

    legs = float(p["custom3"]) / 4.0 + 1.0
    inten = w.sin8(w.sin8((angle * 4.0 - radius) / 4.0 + step / 2.0)
                   + radius - step + angle * legs)
    inten = (inten * inten) / 255.0                    # contrast (squared, /255)
    pal = palettes.as_array(p["palette"])
    img = w.from_palette(pal, step / 2.0 - radius, inten, wrap=True)
    w.finalize(frame, img, now / 1000.0, p)
