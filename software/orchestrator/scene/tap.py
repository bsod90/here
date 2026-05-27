"""TapTracker — turns tap events into BPM + phase corrections.

Each tap is a monotonic timestamp (already compensated for client-side
latency by the route handler). We keep a 3-second rolling window of taps.

On each tap:
  * If we have ≥ 2 taps in the window, recompute BPM from the median of
    pairwise intervals. Median is robust to one off-tempo tap.
  * Compute the beat value the clock would have reported at the tap
    moment. The beat should be an integer; phase error is the gap from
    nearest integer.
  * Push that error into the clock as a gradual phase correction.
"""
from __future__ import annotations

import threading


class TapTracker:
    def __init__(self, window_seconds: float = 3.0, max_taps: int = 8):
        self._window = float(window_seconds)
        self._max = int(max_taps)
        self._taps: list[float] = []   # monotonic timestamps
        self._lock = threading.Lock()

    @property
    def tap_count(self) -> int:
        with self._lock:
            return len(self._taps)

    def reset(self) -> None:
        with self._lock:
            self._taps = []

    def tap(self, monotonic_t_seconds: float, clock) -> dict:
        """Record a tap and update the clock. Returns a small summary."""
        with self._lock:
            # Trim taps older than the window.
            cutoff = monotonic_t_seconds - self._window
            self._taps = [t for t in self._taps if t > cutoff]
            self._taps.append(monotonic_t_seconds)
            if len(self._taps) > self._max:
                self._taps = self._taps[-self._max:]
            taps = list(self._taps)

        bpm_updated = False
        if len(taps) >= 2:
            intervals = sorted(taps[i] - taps[i - 1] for i in range(1, len(taps)))
            median = intervals[len(intervals) // 2]
            if median > 0:
                candidate = 60.0 / median
                # Clamp to a sensible musical range.
                candidate = max(20.0, min(300.0, candidate))
                clock.set_bpm(candidate)
                bpm_updated = True

        # Phase: at the tap moment, beat should be on an integer. Push the
        # nearest-integer error into the clock as gradual drift.
        beat_at_tap = clock.beat_at(monotonic_t_seconds)
        nearest = round(beat_at_tap)
        error = nearest - beat_at_tap
        clock.request_phase_correction(error)

        return {
            "bpm": clock.bpm,
            "bpm_updated": bpm_updated,
            "phase_correction_beats": clock.phase_correction,
            "taps_in_window": len(taps),
            "phase_error_at_tap": error,
        }
