"""BeatClock — converts wall-clock time to musical beats.

The clock anchors beat 0 at a monotonic-time origin. Changing BPM preserves
the current beat phase (so a transition mid-flight doesn't jump).

Phase correction (gradual drift, not snap):
  When a tap or "Set 1" arrives, the engine doesn't immediately reset t0 —
  it queues a `_phase_correction` (in beats) that bleeds off over ~1.5 s of
  ticks. Each frame's `tick(dt_seconds)` applies a fraction of the remaining
  correction; the playhead briefly runs slightly fast (or slow) until the
  error is consumed. We cap the negative step so the playhead never reverses.

`reset_phase` is kept as a hard snap for emergency / programmatic use; the
admin UI no longer exposes it.
"""
from __future__ import annotations

import math
import threading
import time


# Time constant for gradual phase drift, in seconds. After 1.0 s ~63% of any
# pending correction is consumed; after 3.0 s ~95% is.
_CORRECTION_TAU_S = 1.0
# Large correction requests (e.g. tapping "Set 1" several beats away from
# loop_pos = 0) get most of their delta applied as a snap; only this much
# residual is left as smooth drift. Stops the playhead from "stalling"
# (capped at slow forward motion) for seconds.
_DRIFT_RESIDUAL_BEATS = 0.5
# Negative correction (slow-down) is bounded so the playhead never reverses.
# Higher = more aggressive slow-down. 0.5 means the playhead still moves at
# 50% of natural speed during a correction, which feels like a slight tempo
# wobble rather than a freeze.
_NEG_CAP_RATIO = 0.5


class BeatClock:
    def __init__(self, bpm: float = 120.0):
        self._bpm = float(bpm)
        self._t0_seconds = time.monotonic()
        self._phase_correction = 0.0
        # Pause support — `now_beat()` returns the frozen value while
        # paused so the UI playhead doesn't drift away from the scene
        # state (which is also frozen by Scene.pause()).
        self._paused: bool = False
        self._frozen_beat: float = 0.0
        self._lock = threading.Lock()

    @property
    def bpm(self) -> float:
        return self._bpm

    @property
    def seconds_per_beat(self) -> float:
        return 60.0 / self._bpm if self._bpm > 0 else 0.0

    @property
    def phase_correction(self) -> float:
        """Beats of drift still queued (may be negative)."""
        return self._phase_correction

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        with self._lock:
            if not self._paused:
                self._frozen_beat = self._raw_now_beat()
                self._paused = True

    def resume(self) -> None:
        with self._lock:
            if self._paused:
                # Shift t0 so the resume picks up at the frozen beat —
                # no jump in beat space, just continues from there.
                self._t0_seconds = time.monotonic() - self._frozen_beat * 60.0 / self._bpm
                self._paused = False

    def _raw_now_beat(self) -> float:
        if self._bpm <= 0:
            return 0.0
        return (time.monotonic() - self._t0_seconds) * self._bpm / 60.0

    def now_beat(self) -> float:
        """Fractional beats since the last phase reset. Frozen while paused."""
        if self._paused:
            return self._frozen_beat
        return self._raw_now_beat()

    def beat_at(self, monotonic_t_seconds: float) -> float:
        """Beat value that `now_beat()` would have reported AT
        `monotonic_t_seconds` (for compensating client-side tap latency)."""
        if self._bpm <= 0:
            return 0.0
        return (monotonic_t_seconds - self._t0_seconds) * self._bpm / 60.0

    def set_bpm(self, bpm: float) -> None:
        bpm = max(1.0, min(400.0, float(bpm)))
        with self._lock:
            beat_now = self.now_beat()
            self._bpm = bpm
            self._t0_seconds = time.monotonic() - beat_now * 60.0 / bpm

    def reset_phase(self) -> None:
        """Hard snap. Prefer `request_phase_correction` for gradual drift."""
        with self._lock:
            self._t0_seconds = time.monotonic()
            self._phase_correction = 0.0

    def request_phase_correction(self, delta_beats: float) -> None:
        """Queue a gradual drift of `delta_beats` beats.

        For large deltas (> `_DRIFT_RESIDUAL_BEATS`), most of it is applied
        immediately as a t0 snap — only the residual is queued for smooth
        drift. This prevents the playhead from stalling at the cap for
        several seconds when the requested correction is large.
        """
        with self._lock:
            delta = float(delta_beats)
            if abs(delta) > _DRIFT_RESIDUAL_BEATS:
                sign = 1.0 if delta > 0 else -1.0
                snap_beats = delta - sign * _DRIFT_RESIDUAL_BEATS
                # Shift t0 to apply the bulk instantly.
                # +snap_beats means now_beat increases by that amount.
                self._t0_seconds -= snap_beats * 60.0 / self._bpm
                delta = sign * _DRIFT_RESIDUAL_BEATS
            self._phase_correction += delta

    def tick(self, dt_seconds: float) -> None:
        """Apply a fraction of any pending phase correction. Called once per
        engine frame BEFORE reading `now_beat` for rendering."""
        with self._lock:
            if abs(self._phase_correction) < 1e-6:
                self._phase_correction = 0.0
                return
            if dt_seconds <= 0:
                return
            alpha = 1.0 - math.exp(-dt_seconds / max(0.05, _CORRECTION_TAU_S))
            step = self._phase_correction * alpha
            # Cap negative step so the playhead never reverses and never
            # crawls so slowly that it looks like the BPM dropped. The
            # ratio (e.g. 0.5) keeps the playhead moving at ≥ 50% of normal
            # speed during a slow-down correction.
            natural = dt_seconds * self._bpm / 60.0
            if step < -natural * _NEG_CAP_RATIO:
                step = -natural * _NEG_CAP_RATIO
            # Shifting t0 backward by `step` seconds adds `step` beats to
            # now_beat — that's how we "speed up" the clock momentarily.
            self._t0_seconds -= step * 60.0 / self._bpm
            self._phase_correction -= step

    def beats_to_seconds(self, beats: float) -> float:
        return beats * self.seconds_per_beat

    def seconds_to_beats(self, seconds: float) -> float:
        return seconds * self._bpm / 60.0
