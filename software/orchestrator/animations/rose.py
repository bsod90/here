"""Rose — a rose seen from above, unwrapping its petals and wrapping
them back, forever.

The rose is built from several WHORLS (rings of petals): a wide outer
whorl, then smaller whorls nested inside, each rotated so its petals
sit in the gaps of the one outside it — like a real rose. Inner whorls
are pinker, outer whorls deeper red, and every petal has a softly
lightened rim so the layers read separately.

The cycle: a closed bud → the OUTER petals unfurl first, then each
inner whorl follows → the open rose holds, slowly turning → then the
petals fold back in (innermost first, the exact reverse) → a short rest
as a bud → and it blooms again.

Self-contained and heavily commented, like the rest of Nadia's garden.
Every knob lives in `DEFAULTS` with a plain explanation; overrides come
from `config.playground.rose`.
"""
from __future__ import annotations

import math

import numpy as np

from grid import GRID_POSITIONS, CENTER, TOTAL


# ── Tunable knobs ───────────────────────────────────────────────────
DEFAULTS = {
    # --- The bloom cycle (seconds) ---
    "open_s": 7.0,           # how long the unwrapping takes
    "hold_open_s": 4.0,      # how long the rose stays fully open
    "close_s": 7.0,          # how long the wrapping-back takes
    "hold_closed_s": 3.0,    # how long it rests as a closed bud
    "stagger": 0.45,         # how much the whorls take turns (0 = all petals
                             # move together, 0.7 = strongly one-after-another)

    # --- Shape ---
    "reach": 24.0,           # radius of the open rose (~30 touches the corners)
    "bud_size": 4.5,         # radius of the closed bud
    "petal_width": 4.2,      # width of the outer petals when open
    "rotate_speed_deg_s": 1.5,   # slow turning of the whole rose

    # --- Color ---
    "color_outer": [80, 0, 6],       # very dark, saturated red of the outermost petals
    "color_inner": [255, 120, 155],  # light pink at the heart — pops against
                                     # the dark outer petals
    "edge_light": 0.12,      # how much lighter each petal's rim is (separates layers)
    "heart_color": [220, 140, 80],   # tiny warm glow at the very center
    "heart_size": 1.1,       # radius of that glow

    "edge_cutoff": 0.18,     # dim glow below this is turned OFF — keeps the
                             # space around the rose truly black
    "fade_in_s": 1.5,        # gentle fade from black when the animation starts
    "brightness": 1.0,       # master brightness multiplier
}

# Whorl layout: (petal count, fraction of full reach, rotation offset).
# Offsets put each whorl's petals into the gaps of the whorl outside it.
_WHORLS = (
    (7, 1.00, 0.0),          # outer
    (6, 0.72, 0.5),
    (5, 0.48, 0.25),
    (4, 0.30, 0.65),         # innermost
)


# Per-LED polar coordinates, computed once (the grid never changes).
_R = None
_THETA = None


def _geometry():
    global _R, _THETA
    if _R is None:
        dx = np.empty(TOTAL, dtype=np.float32)
        dy = np.empty(TOTAL, dtype=np.float32)
        for i, (row, col) in enumerate(GRID_POSITIONS):
            dx[i] = col - CENTER
            dy[i] = row - CENTER
        _R = np.sqrt(dx * dx + dy * dy)
        _THETA = np.arctan2(dy, dx)
    return _R, _THETA


def _smoothstep(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _openness(t: float, p: dict) -> float:
    """Master open/close value (0 = bud, 1 = fully open) — loops forever:
    open → hold open → close → hold closed → …"""
    open_s = max(0.1, float(p["open_s"]))
    hold_o = max(0.0, float(p["hold_open_s"]))
    close_s = max(0.1, float(p["close_s"]))
    hold_c = max(0.0, float(p["hold_closed_s"]))
    period = open_s + hold_o + close_s + hold_c
    tc = t % period
    if tc < open_s:
        return _smoothstep(tc / open_s)
    tc -= open_s
    if tc < hold_o:
        return 1.0
    tc -= hold_o
    if tc < close_s:
        return 1.0 - _smoothstep(tc / close_s)
    return 0.0


def _whorl_field(r, theta, m: int, rot: float, reach: float,
                 width: float) -> np.ndarray:
    """0..1 intensity of one ring of m petals pointing outward from the
    center, with rounded leaf shapes. Max over the petals."""
    reach = max(0.8, reach)
    field = np.zeros(TOTAL, dtype=np.float32)
    for k in range(m):
        direction = rot + k * (2.0 * math.pi / m)
        da = np.mod(theta - direction + math.pi, 2.0 * math.pi) - math.pi
        along = r * np.cos(da)
        across = r * np.sin(da)
        norm = along / reach
        inside = (norm >= 0.0) & (norm <= 1.0)
        long_prof = np.clip(np.sin(np.clip(norm, 0.0, 1.0) * math.pi),
                            0.0, None) ** 0.8
        half_w = width * (0.35 + 0.65 * long_prof)
        lat = np.exp(-(across * across) / (2.0 * half_w * half_w))
        petal = np.where(inside, long_prof * lat, 0.0).astype(np.float32)
        field = np.maximum(field, petal)
    return field


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    r, theta = _geometry()

    # Anchor the clock to the start of this run (state is reset on each
    # trigger/play) so the bloom always starts from the bud.
    if state is not None:
        if "t0" not in state:
            state["t0"] = time_ms
        time_ms = time_ms - state["t0"]
    t = time_ms / 1000.0

    u = _openness(t, p)                              # 0 bud → 1 open
    stagger = min(0.9, max(0.0, float(p["stagger"])))
    rot0 = math.radians(float(p["rotate_speed_deg_s"])) * t

    full_reach = float(p["reach"])
    bud = float(p["bud_size"])
    width_open = float(p["petal_width"])

    c_out = np.array(p["color_outer"], dtype=np.float32)
    c_in = np.array(p["color_inner"], dtype=np.float32)
    edge_light = float(p["edge_light"])
    cut = min(0.9, max(0.0, float(p["edge_cutoff"])))

    n_whorls = len(_WHORLS)
    rgb = np.zeros((TOTAL, 3), dtype=np.float32)

    # Outer whorl first; inner whorls composite on top of it.
    for w, (m, frac, off) in enumerate(_WHORLS):
        # Whorl take-their-turn timing: the OUTER whorl leads the
        # unwrapping; when closing (u falling back down) the inner ones
        # tuck in first — automatically, by running the same map backward.
        lag = stagger * (w / max(1, n_whorls - 1))
        uw = _smoothstep(min(1.0, max(0.0, u * (1.0 + stagger) - lag)))

        # Closed: tucked at bud radius, narrow. Open: full spread.
        reach_w = bud * (0.5 + 0.5 * frac) + (full_reach * frac - bud * (0.5 + 0.5 * frac)) * uw
        width_w = (1.1 + (width_open * (0.45 + 0.55 * frac) - 1.1) * uw)

        # Each whorl sits in the gaps of the previous one and turns at a
        # whisper different speed, so the layers slide subtly.
        rot_w = rot0 * (1.0 + 0.12 * w) + off * (2.0 * math.pi / m)

        field = _whorl_field(r, theta, m, rot_w, reach_w, width_w)
        # Crisp petal edges + real black between (per whorl, so inner
        # petals still cover outer ones cleanly).
        field = np.clip((field - cut) / (1.0 - cut), 0.0, 1.0)

        # Whorl color: deep red outside → pink at the heart, with a
        # lighter rim on every petal.
        wf = w / max(1, n_whorls - 1)
        base = c_out * (1.0 - wf) + c_in * wf
        edge_t = ((1.0 - field) * edge_light)[:, np.newaxis]
        color = base[np.newaxis, :] * (1.0 - edge_t) + 255.0 * edge_t

        a = field[:, np.newaxis]
        rgb = rgb * (1.0 - a) + color * a

    # Tiny warm heart at the very center.
    hs = max(0.1, float(p["heart_size"]))
    heart = np.exp(-(r * r) / (2.0 * hs * hs))[:, np.newaxis]
    heart_c = np.array(p["heart_color"], dtype=np.float32)[np.newaxis, :]
    rgb = rgb * (1.0 - heart) + heart_c * heart

    # Gentle fade from black at the start.
    fade = min(1.0, t / max(0.01, float(p["fade_in_s"])))

    rgb = rgb * (float(p["brightness"]) * fade)
    frame[:] = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
