"""SFX overlay layer — short-lived visual effects composited on top of the
main SynthAnimation render.

Each Sfx has:
  * `start_beat`, `duration_beats` — lifecycle window in beat-space
  * `is_done(beat)` — Scene prunes when True
  * `render(frame, grid, time_ms, params, beat)` — additive overlay on
    the already-rendered frame; should not zero existing pixels.

Color picker convention: every SFX takes a `color` palette-index 0..7
(rim, inner, outer, trail, color4, color5, color6, color7) so the user
can pick from any of the 8 palette slots.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

try:
    import numpy as np
except ImportError:   # pragma: no cover
    np = None


# Re-export from envelopes so SFX share the same easing vocabulary
# as actions + envelopes (single source of truth).
from .envelopes import EASE_TO_INTERP as _EASE_INTERP   # noqa: E402

_PALETTE_KEYS = [
    "rim_color", "inner_color", "outer_color", "trail_color",
    "color4", "color5", "color6", "color7",
]


_warned_color_idx_oob: set[int] = set()


def _pick_color(palette: dict, idx: int) -> "np.ndarray":
    """Return an (R, G, B) float32 array for palette slot `idx` (0..7).
    Falls back to white if the slot is missing. Out-of-range indices are
    clamped but the first occurrence per-idx is logged so silent palette
    confusion doesn't go unnoticed."""
    raw = int(idx)
    clamped = max(0, min(7, raw))
    if clamped != raw and raw not in _warned_color_idx_oob:
        import logging
        logging.getLogger(__name__).warning(
            "SFX color_idx %d out of range [0,7]; clamped to %d", raw, clamped)
        _warned_color_idx_oob.add(raw)
    key = _PALETTE_KEYS[clamped]
    return np.asarray(palette.get(key, [255, 255, 255]), dtype=np.float32)


def _ease_sample(t: float, kind: str) -> float:
    """Sample an ease curve at normalized t in [0,1]."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if kind == "linear":
        return t
    if kind == "ease_in_quad":
        return t * t
    if kind == "ease_out_quad":
        return 1.0 - (1.0 - t) ** 2
    # cosine (default)
    return (1.0 - math.cos(t * math.pi)) * 0.5


@dataclass
class _SfxBase:
    start_beat: float
    duration_beats: float
    color_idx: int = 0
    ease: str = "linear"

    def progress(self, beat: float) -> float:
        if self.duration_beats <= 0:
            return 1.0
        return max(0.0, min(1.0, (beat - self.start_beat) / self.duration_beats))

    def is_done(self, beat: float) -> bool:
        return beat >= self.start_beat + self.duration_beats


@dataclass
class MeteorsSfx(_SfxBase):
    """N bright streaks flying diagonally across the grid. Each meteor
    has a head + short trail; lifetime is independent per meteor (some
    finish + respawn during the event)."""
    count: int = 6
    angle_deg: float = 35.0   # diagonal angle from horizontal
    _meteors: list = field(default_factory=list)

    def _spawn(self, grid, beat):
        # Start off one edge, fly toward opposite. Random vertical offset.
        diag = math.hypot(grid.center, grid.center) * 2.4
        angle = math.radians(self.angle_deg + random.uniform(-10, 10))
        speed = diag / max(0.4, self.duration_beats * 0.25)
        # Start outside left edge, random Y inside ±grid.center.
        sx = -grid.center * 1.4
        sy = random.uniform(-grid.center, grid.center)
        return {
            "x": sx, "y": sy,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "born_beat": beat,
        }

    def tick(self, dt_seconds, beat, grid):
        # Spawn missing meteors.
        while len(self._meteors) < self.count:
            self._meteors.append(self._spawn(grid, beat))
        # Move + cull off-grid.
        cull_dist = grid.center * 2.5
        for m in self._meteors:
            m["x"] += m["vx"] * dt_seconds
            m["y"] += m["vy"] * dt_seconds
        self._meteors = [m for m in self._meteors
                         if abs(m["x"]) < cull_dist and abs(m["y"]) < cull_dist]

    def render(self, frame, grid, time_ms, params, beat):
        if np is None: return
        palette = (params.get("palettes") or [{}])[0]   # SFX always use active
        # Use the actual active palette index if provided in params.
        palettes = params.get("palettes") or []
        if palettes:
            palette = palettes[0]   # the renderer already mixes per-frame; pick palette 0 baseline
        color = _pick_color(palette, self.color_idx)
        # Fade in then out across the SFX lifetime.
        t = self.progress(beat)
        amp = math.sin(t * math.pi)   # 0 → 1 → 0
        if amp <= 0.01:
            return
        dx_base = np.array([c - grid.center for _, c in grid.positions], dtype=np.float32)
        dy_base = np.array([r - grid.center for r, _ in grid.positions], dtype=np.float32)
        glow = np.zeros(grid.total, dtype=np.float32)
        head_sigma = 1.1
        for m in self._meteors:
            # Head
            dx = dx_base - m["x"]
            dy = dy_base - m["y"]
            head = np.exp(-(dx * dx + dy * dy) / (2.0 * head_sigma * head_sigma))
            glow += head * 1.4
            # Short tail behind the head (against velocity direction)
            for k in range(1, 5):
                back_x = m["x"] - m["vx"] * k * 0.04
                back_y = m["y"] - m["vy"] * k * 0.04
                bx = dx_base - back_x
                by = dy_base - back_y
                taper = (1.0 - k / 5.0) ** 1.5
                t_sig = head_sigma * (0.5 + 0.4 * taper)
                glow += np.exp(-(bx * bx + by * by) / (2.0 * t_sig * t_sig)) * taper
        glow = np.clip(glow * amp, 0.0, 1.5)
        arr = np.frombuffer(frame, dtype=np.uint8)[: grid.frame_bytes].reshape(grid.total, 3).astype(np.float32)
        arr = arr + np.outer(glow, color)
        np.clip(arr, 0, 255, out=arr)
        frame[: grid.frame_bytes] = arr.astype(np.uint8).tobytes()


_DUST_HISTORY: list[tuple[float, float]] = []


@dataclass
class DustPulseSfx(_SfxBase):
    """A cluster of scattered dots appears at a random location (kept a
    minimum distance from previous cluster centers), slowly dissolves
    out. Smaller than the standby sparkle but similar feel.

    Past cluster centers are tracked in a module-level history so each
    new DustPulseSfx instance can avoid placing on top of recent ones.
    """
    cluster_count: int = 28
    # cluster_radius controls Gaussian spread sigma = cluster_radius * 0.55.
    # Bumped 4.5 → 8.0 per user feedback ("more sparse, same number of
    # dots") — sigma goes from ~2.5 to ~4.4 LEDs, roughly doubling the
    # cluster footprint without changing dot count.
    cluster_radius: float = 8.0
    min_distance_from_last: float = 9.0
    cx: float = 0.0
    cy: float = 0.0
    _dots: list = field(default_factory=list)

    def _place_cluster(self, grid):
        half = grid.center * 0.85
        for _ in range(20):
            cx = random.uniform(-half, half)
            cy = random.uniform(-half, half)
            ok = True
            for (lx, ly) in _DUST_HISTORY[-3:]:
                if math.hypot(cx - lx, cy - ly) < self.min_distance_from_last:
                    ok = False
                    break
            if ok:
                self.cx, self.cy = cx, cy
                break
        else:
            self.cx, self.cy = 0.0, 0.0
        _DUST_HISTORY.append((self.cx, self.cy))
        if len(_DUST_HISTORY) > 10:
            _DUST_HISTORY.pop(0)
        # Scatter dots Gaussian around center.
        self._dots = []
        for _ in range(self.cluster_count):
            r = abs(random.gauss(0, self.cluster_radius * 0.55))
            theta = random.uniform(0, 2 * math.pi)
            jx = random.gauss(0, 0.4)   # tiny drift
            jy = random.gauss(0, 0.4)
            self._dots.append({
                "x": self.cx + r * math.cos(theta),
                "y": self.cy + r * math.sin(theta),
                "vx": jx, "vy": jy,
            })

    def tick(self, dt_seconds, beat, grid):
        if not self._dots:
            self._place_cluster(grid)
        # Brownian-ish drift.
        for d in self._dots:
            d["x"] += d["vx"] * dt_seconds
            d["y"] += d["vy"] * dt_seconds
            d["vx"] *= 0.92
            d["vy"] *= 0.92

    def render(self, frame, grid, time_ms, params, beat):
        if np is None: return
        palettes = params.get("palettes") or [{}]
        color = _pick_color(palettes[0], self.color_idx)
        # Fade in/out — peak around 25% of duration.
        t = self.progress(beat)
        interp = _EASE_INTERP.get(self.ease, "ease_out_quad")
        # Use ease curve for alpha — appears, then ease-out fades.
        peak_t = 0.2
        if t < peak_t:
            alpha = _ease_sample(t / peak_t, "linear")
        else:
            tail_t = (t - peak_t) / (1.0 - peak_t)
            alpha = 1.0 - _ease_sample(tail_t, interp.replace("ease_in_quad", "linear"))
        if alpha <= 0.01:
            return
        dx_base = np.array([c - grid.center for _, c in grid.positions], dtype=np.float32)
        dy_base = np.array([r - grid.center for r, _ in grid.positions], dtype=np.float32)
        glow = np.zeros(grid.total, dtype=np.float32)
        sigma = 0.7
        two_sig_sq = 2.0 * sigma * sigma
        for d in self._dots:
            dx = dx_base - d["x"]
            dy = dy_base - d["y"]
            glow += np.exp(-(dx * dx + dy * dy) / two_sig_sq)
        glow = np.clip(glow * alpha * 1.5, 0.0, 2.0)
        arr = np.frombuffer(frame, dtype=np.uint8)[: grid.frame_bytes].reshape(grid.total, 3).astype(np.float32)
        arr = arr + np.outer(glow, color)
        np.clip(arr, 0, 255, out=arr)
        frame[: grid.frame_bytes] = arr.astype(np.uint8).tobytes()


@dataclass
class FlashSfx(_SfxBase):
    """Full-screen flash of the chosen color, ease-curve-shaped alpha."""
    peak_alpha: float = 0.8   # cap flash top brightness at 80%

    def tick(self, dt_seconds, beat, grid):
        pass

    def render(self, frame, grid, time_ms, params, beat):
        if np is None: return
        palettes = params.get("palettes") or [{}]
        color = _pick_color(palettes[0], self.color_idx)
        t = self.progress(beat)
        # Triangle envelope shaped by the ease setting (alpha 0 → peak → 0).
        peak_t = 0.15
        if t < peak_t:
            alpha = _ease_sample(t / peak_t, _EASE_INTERP.get(self.ease, "linear"))
        else:
            tail = (t - peak_t) / (1.0 - peak_t)
            alpha = 1.0 - _ease_sample(tail, _EASE_INTERP.get(self.ease, "ease_out_quad"))
        alpha *= self.peak_alpha
        if alpha <= 0.01:
            return
        arr = np.frombuffer(frame, dtype=np.uint8)[: grid.frame_bytes].reshape(grid.total, 3).astype(np.float32)
        arr = arr + color[np.newaxis, :] * alpha
        np.clip(arr, 0, 255, out=arr)
        frame[: grid.frame_bytes] = arr.astype(np.uint8).tobytes()


@dataclass
class WipeSfx(_SfxBase):
    """Gradient wipe across the grid in a chosen direction. Brightest band
    sweeps from one edge to the other over the duration."""
    angle_deg: float = 0.0   # direction of the sweep
    band_width: float = 6.0  # in LED units (1σ of the band)

    def tick(self, dt_seconds, beat, grid):
        pass

    def render(self, frame, grid, time_ms, params, beat):
        if np is None: return
        palettes = params.get("palettes") or [{}]
        color = _pick_color(palettes[0], self.color_idx)
        t = self.progress(beat)
        # Eased position along the axis from min to max.
        eased = _ease_sample(t, _EASE_INTERP.get(self.ease, "cosine"))
        # Coordinate of band center, in LED units along the projection.
        full_span = grid.center * 2.2
        center_pos = -grid.center * 1.1 + eased * full_span
        # Project pixel coords onto axis.
        ax = math.cos(math.radians(self.angle_deg))
        ay = math.sin(math.radians(self.angle_deg))
        dx_base = np.array([c - grid.center for _, c in grid.positions], dtype=np.float32)
        dy_base = np.array([r - grid.center for r, _ in grid.positions], dtype=np.float32)
        proj = dx_base * ax + dy_base * ay
        # Gaussian band around center_pos.
        sigma = max(0.5, self.band_width)
        glow = np.exp(-((proj - center_pos) ** 2) / (2.0 * sigma * sigma))
        # Slight fade at the very start + end so the band doesn't pop in.
        envelope = 4.0 * t * (1.0 - t)   # peaks 1.0 at t=0.5
        envelope = max(0.0, min(1.0, envelope + 0.3))
        glow = glow * envelope * 1.6
        arr = np.frombuffer(frame, dtype=np.uint8)[: grid.frame_bytes].reshape(grid.total, 3).astype(np.float32)
        arr = arr + np.outer(glow, color)
        np.clip(arr, 0, 255, out=arr)
        frame[: grid.frame_bytes] = arr.astype(np.uint8).tobytes()
