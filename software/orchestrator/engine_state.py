"""Co-objects for AnimationEngine.

Extracted from animation_engine.py so the engine itself stays focused on
the frame-loop and the mode dispatch. Each piece here owns one concern:

* `TransitionCoordinator` — tracks a (from → to) crossfade between modes,
  composes outgoing + incoming renders, and tells the engine when it's
  done.
* `PowerEstimator` — rolling-window average of the per-frame LED power
  draw plus a battery-runtime estimate.

Neither one knows about the FastAPI / config / transport / scale layers;
they take the few things they need as constructor arguments or method
parameters. That makes them testable without standing up the full engine.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from grid import FRAME_BYTES


# ── Transition coordinator ───────────────────────────────────────
class TransitionCoordinator:
    """Owns the (src, dst, t0_ms) crossfade state + the scratch layer
    buffer. The engine asks `render(time_ms, frame, render_mode_fn)` on
    every frame; the coordinator returns True if it claimed the frame
    (in which case the engine skips its normal render)."""

    def __init__(self,
                 fade_durations: Callable[[str | None], tuple[float, float]]):
        # `fade_durations` is the engine's mode-registry lookup, injected
        # to avoid a circular import. (engine knows registry → registry
        # would need to know engine if it imported the coordinator.)
        self._fade_durations = fade_durations
        self.src: str | None = None
        self.dst: str | None = None
        self.t0_ms: float = 0.0
        # Scratch buffer for compositing the incoming layer onto the
        # outgoing frame. One bytearray, reused every frame.
        self._layer = bytearray(FRAME_BYTES)

    def start(self, src: str | None, dst: str, t0_ms: float) -> None:
        self.src = src
        self.dst = dst
        self.t0_ms = t0_ms

    def clear(self) -> None:
        self.src = None
        self.dst = None

    @property
    def active(self) -> bool:
        return self.dst is not None

    def render(self, time_ms: float, frame: bytearray,
               render_mode: Callable[[str, bytearray, float, float | None, float | None], None]) -> bool:
        """Paint a crossfade frame if one is in flight.

        `render_mode(mode, dest_buffer, time_ms, fade_in, fade_out)` is
        provided by the engine — it dispatches the actual per-mode
        render into the supplied buffer.

        Returns True if we claimed the frame, False if the transition
        is over (caller should fall back to its normal render path)."""
        if self.dst is None:
            return False

        age_s = (time_ms - self.t0_ms) / 1000.0
        _, src_out_s = self._fade_durations(self.src)
        dst_in_s, _ = self._fade_durations(self.dst)
        total_s = max(src_out_s, dst_in_s)
        if total_s <= 0 or age_s >= total_s:
            self.clear()
            return False

        # Outgoing → main frame. Once its fade-out window ends the
        # output is zero anyway; clear instead of re-rendering.
        if self.src is not None and age_s < src_out_s:
            out_u = age_s / src_out_s
            render_mode(self.src, frame, time_ms, None, out_u)
        else:
            for i in range(len(frame)):
                frame[i] = 0

        # Incoming → scratch layer → additive composite onto frame.
        # Clamp fade_in to 1.0 instead of bailing once dst_in_s ends:
        # if the dst's fade-in is shorter than src's fade-out, we want
        # the new mode fully painted while the longer outgoing fade-out
        # plays out — otherwise the incoming vanishes for the remainder
        # then re-appears once the transition ends.
        in_u = min(1.0, age_s / dst_in_s) if dst_in_s > 0 else 1.0
        render_mode(self.dst, self._layer, time_ms, in_u, None)
        self._composite_additive(frame, self._layer, 1.0)
        return True

    @staticmethod
    def _composite_additive(dest: bytearray, layer: bytearray,
                            alpha: float) -> None:
        """dest += layer * alpha (saturating at 255). Numpy because the
        inner loop runs every frame for the duration of every crossfade."""
        if alpha <= 0:
            return
        main = np.frombuffer(dest, dtype=np.uint8).astype(np.int32)
        lay = np.frombuffer(layer, dtype=np.uint8).astype(np.int32)
        mixed = np.clip(main + (lay * alpha).astype(np.int32), 0, 255).astype(np.uint8)
        dest[:] = mixed.tobytes()


# ── Power estimator ─────────────────────────────────────────────
class PowerEstimator:
    """Rolling-window average of per-frame LED power draw.

    Caller pushes one `instant_watts` reading per rendered frame; the
    estimator computes the average over a sliding time window (default
    30 s) so the value the user sees on the status pill isn't twitching
    with every frame. `estimate()` packages the value into the dict the
    admin panel expects (`led_watts`, `total_watts`, `daily_wh`,
    `battery_days`)."""

    def __init__(self, system_idle_watts: float, battery_wh: float,
                 watts_per_led_full_white: float, total_leds: int,
                 window_s: float = 30.0):
        self._system_idle_w = system_idle_watts
        self._battery_wh = battery_wh
        self._watts_per_led_full_white = watts_per_led_full_white
        self._total_leds = total_leds  # used by tests; not required for now
        self._window_s = window_s
        self._samples: list[tuple[float, float]] = []   # (t, watts)
        self._led_watts = 0.0

    def push_frame_rgb_sum(self, rgb_sum: int, now: float) -> None:
        """Push one frame's RGB byte sum at monotonic time `now`. RGB
        sum is divided by (255 * 3) — equivalent to "how many LEDs
        would be at full white" — and multiplied by per-LED full-
        white wattage to get instantaneous draw."""
        instant_w = (rgb_sum / (255 * 3)) * self._watts_per_led_full_white
        self._samples.append((now, instant_w))
        cutoff = now - self._window_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.pop(0)
        if self._samples:
            self._led_watts = sum(w for _, w in self._samples) / len(self._samples)
        else:
            self._led_watts = instant_w

    @property
    def led_watts(self) -> float:
        return self._led_watts

    def estimate(self) -> dict:
        led_w = self._led_watts
        total_w = self._system_idle_w + led_w
        daily_wh = total_w * 24
        runtime_days = self._battery_wh / daily_wh if daily_wh > 0 else 999
        return {
            "led_watts": round(led_w, 1),
            "system_watts": round(self._system_idle_w, 1),
            "total_watts": round(total_w, 1),
            "daily_wh": round(daily_wh),
            "battery_days": round(runtime_days, 1),
        }
