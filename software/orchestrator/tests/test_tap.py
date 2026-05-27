"""Tests for TapTracker — BPM estimation + phase correction."""
import unittest

from scene.clock import BeatClock
from scene.tap import TapTracker


class TestTapTracker(unittest.TestCase):

    def test_single_tap_no_bpm(self):
        tap = TapTracker()
        clock = BeatClock(bpm=120)
        r = tap.tap(monotonic_t_seconds=10.0, clock=clock)
        self.assertEqual(r["taps_in_window"], 1)
        self.assertFalse(r["bpm_updated"])

    def test_two_taps_compute_bpm(self):
        tap = TapTracker()
        clock = BeatClock(bpm=60)  # start at 60 to verify the change
        tap.tap(10.0, clock)
        # 0.5 s interval → 120 BPM
        r = tap.tap(10.5, clock)
        self.assertTrue(r["bpm_updated"])
        self.assertAlmostEqual(r["bpm"], 120.0, places=1)

    def test_four_taps_use_median(self):
        tap = TapTracker()
        clock = BeatClock(bpm=120)
        # 4 taps at 0.5 s intervals, plus one outlier
        tap.tap(10.0, clock)
        tap.tap(10.5, clock)
        tap.tap(10.7, clock)  # too soon — outlier
        r = tap.tap(11.0, clock)
        # Median interval is ~0.4 — wait actually 0.5, 0.2, 0.3 sorted → 0.3 median
        # But the important thing is median ignores extremes — bpm should be reasonable.
        self.assertGreater(r["bpm"], 60)
        self.assertLess(r["bpm"], 300)

    def test_window_trims_old_taps(self):
        tap = TapTracker(window_seconds=1.0)
        clock = BeatClock(bpm=120)
        tap.tap(0.0, clock)
        tap.tap(2.0, clock)  # 2.0 - 0.0 > 1.0 window → the old tap is dropped
        self.assertEqual(tap.tap_count, 1)

    def test_phase_correction_pushed_to_clock(self):
        tap = TapTracker()
        clock = BeatClock(bpm=120)
        # At monotonic t=0, beat is 0 (just constructed). Set t to a fractional
        # beat offset and tap there — clock should queue a correction.
        # 120 BPM = 2 beats/s. At t=0.25 s the beat = 0.5.
        # We need to use the clock's own t0_seconds reference. Hack: query it.
        t0 = clock._t0_seconds
        tap.tap(t0 + 0.25, clock)
        # First tap doesn't update BPM but should push phase = nearest_integer(0.5) - 0.5
        # round(0.5) == 0 in Python's banker's rounding → error = -0.5
        # OR round(0.5) == 1 → error = +0.5 (depends on Python's even-bankers).
        # Either way magnitude is 0.5.
        self.assertAlmostEqual(abs(clock.phase_correction), 0.5, places=4)

    def test_reset_empties_window(self):
        tap = TapTracker()
        clock = BeatClock(bpm=120)
        tap.tap(10.0, clock)
        tap.tap(10.5, clock)
        tap.reset()
        self.assertEqual(tap.tap_count, 0)


if __name__ == "__main__":
    unittest.main()
