"""Shared named color palettes — "our palettes".

A palette is a small list of RGB anchors (0..255). Effects sample it as a
*cyclic gradient* (see animations/_wled.from_palette), so 4–6 anchors give
a smooth looping wash. These are the calm, on-brand gradients the border
already uses, plus a handful of WLED-flavored ones the ported 2D effects
want (aurora curtains, embers, twilight, …).

Kept deliberately small and dependency-free so both border.py and the
animation modules can import it without pulling in numpy at import time
(the array conversion is lazy, in `as_array`).
"""
from __future__ import annotations

# name → list of [r, g, b] anchors. Order = gradient order (wraps).
PALETTES: dict[str, list[list[int]]] = {
    # ── The border's calm set (kept in sync) ───────────────────────
    "cold":     [[80, 120, 255], [40, 90, 205], [95, 70, 205], [55, 175, 200]],
    "ocean":    [[10, 80, 160], [20, 140, 180], [40, 200, 190], [10, 60, 120]],
    "ember":    [[180, 60, 20], [220, 110, 30], [120, 30, 10], [200, 80, 25]],
    "forest":   [[30, 120, 60], [80, 170, 70], [20, 90, 80], [120, 180, 90]],
    "dusk":     [[180, 70, 120], [110, 60, 180], [60, 50, 160], [210, 110, 90]],
    "mono":     [[180, 180, 200], [90, 90, 120], [220, 220, 235], [50, 50, 70]],

    # ── WLED-flavored meditation gradients ─────────────────────────
    # Aurora curtains — the classic green→yellow→red northern-lights ramp.
    "aurora":   [[0, 40, 10], [0, 140, 30], [60, 220, 40], [200, 230, 30],
                 [240, 120, 20], [120, 20, 30]],
    # Warm fire bed — black-red-orange-yellow-white.
    "fire":     [[0, 0, 0], [120, 20, 0], [220, 70, 0], [255, 160, 20],
                 [255, 230, 140]],
    # Soft sunset wash.
    "sunset":   [[40, 20, 80], [150, 50, 90], [230, 110, 70], [250, 180, 90],
                 [255, 220, 150]],
    # Twilight — deep blue to violet to rose, very calm.
    "twilight": [[20, 25, 70], [60, 40, 130], [120, 60, 160], [190, 90, 150],
                 [240, 160, 150]],
    # Spring meadow — fresh greens with a bloom of pink/gold.
    "spring":   [[40, 130, 80], [110, 190, 90], [200, 230, 120],
                 [240, 200, 120], [230, 140, 170]],
    # Full rainbow (for playful effects that want the whole wheel).
    "rainbow":  [[255, 0, 0], [255, 160, 0], [200, 220, 0], [0, 200, 60],
                 [0, 120, 220], [80, 40, 200], [200, 0, 160]],
    # Pastel — low-saturation dream tones.
    "pastel":   [[200, 180, 230], [180, 220, 220], [230, 210, 180],
                 [220, 190, 210], [190, 210, 235]],
    # Lava lamp — magenta/purple/teal drift.
    "lava":     [[200, 30, 120], [120, 30, 180], [40, 60, 200],
                 [30, 160, 180], [120, 40, 160]],
}

NAMES: list[str] = list(PALETTES.keys())
DEFAULT = "cold"


def get(name) -> list[list[int]]:
    """Anchor list for a palette name (falls back to the default)."""
    if isinstance(name, (list, tuple)) and name:
        return [list(c) for c in name]          # already an anchor list
    return PALETTES.get(name, PALETTES[DEFAULT])


def as_array(name):
    """Anchors as a float32 (k, 3) numpy array — imported lazily."""
    import numpy as np
    return np.array(get(name), dtype=np.float32)
