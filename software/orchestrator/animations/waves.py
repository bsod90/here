"""Underwater — deep blue water with sunlight caustics playing through it.

What you see looking down (or around) underwater: everything is blue,
and ribbons of light — caustics, the bright webs the surface focuses
the sun into — wander, stretch, merge and split, never still and never
repeating. Here the water is a deep blue field and the caustic web is
drawn by warping space with layers of slow sine currents: the light
lines bend and flow exactly like the real thing.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.waves`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, GRID, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    "speed": 1.0,            # how fast the light web flows (1 = real lazy water)
    "scale": 26.0,           # rough size of the light cells in LEDs (bigger = broader,
                             # calmer web; smaller = busy little ripples)
    "complexity": 1.0,       # how irregular/busy the web is (more = more, smaller,
                             # more varied cells; less = bigger lazier cells)
    "warp": 1.0,             # how much the whole web folds & wanders (0 = stiller)

    # --- Water ---
    "color_deep": [0, 10, 45],       # the deep blue of the water itself
    "color_shallow": [0, 40, 75],    # a slightly lighter blue the water leans
                                     # toward where the light gathers

    # --- The light web (caustics) ---
    "light_color": [110, 200, 215],  # color of the focused light (soft cyan —
                                     # not white, so the contrast stays gentle)
    "light_amount": 0.75,    # how strong the light ribbons are (0 = none)
    "sharpness": 4.5,        # how thin/crisp the ribbons are (1 = broad washes,
                             # 5 = thin bright filaments)

    # --- The pool's edge ---
    "edge_softness": 3.0,    # how wide the fade-to-dark rim is (LEDs);
                             # 0 = hard square edge (the bare matrix look)
    "edge_waviness": 3.2,    # how far the shoreline swells in and out (LEDs)
    "edge_wave_speed": 1.0,  # how fast the shoreline undulates (1 = lazy)

    "fade_in_s": 2.5,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}


# Per-LED x/y coordinates, computed once (the grid never changes).
_X = None
_Y = None


def _geometry():
    global _X, _Y
    if _X is None:
        _X = np.empty(TOTAL, dtype=np.float32)
        _Y = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            _X[i] = col
            _Y[i] = row
    return _X, _Y


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    x, y = _geometry()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the fade-in always replays.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0 * float(p["speed"])

    scale = max(4.0, float(p["scale"]))
    k = 2.0 * math.pi / scale          # base spatial frequency
    cx = float(p["complexity"])
    warp = float(p["warp"])

    # ── Caustic web ──────────────────────────────────────────────────
    # Real caustics are NOT a grid — they're the contour lines of a slowly
    # heaving sheet of water, which gives irregular, ever-changing cells of
    # all different sizes. So instead of multiplying two sines (a warped
    # lattice — every cell the same), we build an organic HEIGHT FIELD from
    # several wave trains running at incommensurate angles and speeds (their
    # frequency ratios are irrational, so the pattern never tiles or repeats),
    # then light up its contour lines. Where the sheet is flat the cells are
    # big; where it's steep they crowd together — that variation is what reads
    # as "real water" rather than a regular mesh.

    # First fold the whole field with slow, low-frequency currents so the web
    # wanders and drifts (domain warp).
    xw = x + warp * 0.16 * scale * np.sin(y * k * 0.45 + 0.20 * t)
    yw = y + warp * 0.16 * scale * np.cos(x * k * 0.40 - 0.15 * t + 1.7)

    # Sum of wave trains: deliberately odd angles / freqs / drift speeds so no
    # two cells line up and the whole thing keeps reshuffling.
    waves = (
        # (angle rad, freq×, drift speed, phase)
        (0.40, 1.00,  0.21, 0.0),
        (1.25, 1.43, -0.17, 1.3),
        (2.10, 0.68,  0.13, 2.7),
        (2.95, 1.91, -0.27, 0.6),
        (3.85, 1.17,  0.19, 4.1),
        (5.20, 0.55, -0.11, 5.5),
    )
    height = np.zeros(TOTAL, dtype=np.float32)
    for ang, f, spd, ph in waves:
        proj = (math.cos(ang) * xw + math.sin(ang) * yw) * (k * f * cx)
        height += np.sin(proj + spd * t + ph)
    height /= len(waves)               # ~[-1, 1], but lumpy & non-separable

    # Light the contour lines of that height field — thin bright ribbons that
    # merge and split as the sheet heaves. `sharpness` thins them; the extra
    # `1.6×` band density keeps a few ribbons on screen at the default scale.
    web = np.abs(np.sin(height * cx * 4.0))
    web = (1.0 - web) ** max(0.5, float(p["sharpness"]))

    # ── Water + light ────────────────────────────────────────────────
    deep = np.array(p["color_deep"], dtype=np.float32)
    shallow = np.array(p["color_shallow"], dtype=np.float32)
    light = np.array(p["light_color"], dtype=np.float32)

    # The water itself leans a little lighter where light gathers…
    base_mix = np.clip(web * 1.6, 0.0, 1.0)[:, np.newaxis]
    rgb = deep[np.newaxis, :] * (1.0 - base_mix) + shallow[np.newaxis, :] * base_mix

    # …and the bright ribbons blend on top (never to full white).
    amount = min(1.0, max(0.0, float(p["light_amount"])))
    a = np.clip(web ** 1.5 * amount, 0.0, 1.0)[:, np.newaxis]
    rgb = rgb * (1.0 - a) + light[np.newaxis, :] * a

    # ── The pool's edge: soft and wavy ───────────────────────────────
    # A hard square boundary is what makes the floor read as "LED panel".
    # Fade the water to darkness over `edge_softness` LEDs before the
    # physical border, and undulate that shoreline with two slow
    # travelling waves so the lit region breathes like an organic pool —
    # the eye never finds the rectangle.
    soft = float(p["edge_softness"])
    if soft > 0.0:
        edge = np.minimum(np.minimum(x, GRID - 1 - x),
                          np.minimum(y, GRID - 1 - y))
        wav = float(p["edge_waviness"])
        if wav > 0.0:
            wt = float(p["edge_wave_speed"]) * t
            # Three wave trains at incommensurate frequencies: two short
            # ripples plus one long slow swell, so the shoreline visibly
            # LIVES — whole stretches breathe in and out — while each
            # individual movement stays lazy.
            wob = (0.45 * np.sin(x * 0.31 + y * 0.17 + 0.53 * wt)
                   + 0.30 * np.sin(y * 0.41 - x * 0.11 - 0.37 * wt + 2.1)
                   + 0.45 * np.sin((x + y) * 0.09 + 0.19 * wt + 4.0))
            edge = edge + wob * wav
        v = np.clip(edge / max(0.5, soft), 0.0, 1.0)
        rgb = rgb * (v * v * (3.0 - 2.0 * v))[:, np.newaxis]   # smoothstep

    # Gentle fade from black at the start.
    fade = min(1.0, (time_ms / 1000.0) / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
