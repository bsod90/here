"""Tests for BeatClock — phase-preserving BPM change, reset, conversion helpers."""
import time
import unittest

from scene.clock import BeatClock


class TestBeatClock(unittest.TestCase):

    def test_initial_beat_is_zero(self):
        c = BeatClock(bpm=120)
        # Allow a tiny amount of drift since BeatClock anchors t0 in its
        # constructor; reading now_beat immediately should be ~0.
        self.assertLess(c.now_beat(), 0.01)

    def test_beat_advances_with_wall_clock(self):
        c = BeatClock(bpm=240)  # 4 beats/sec
        time.sleep(0.5)
        # ~2 beats elapsed; allow slop for scheduling.
        self.assertGreater(c.now_beat(), 1.7)
        self.assertLess(c.now_beat(), 2.3)

    def test_set_bpm_preserves_phase(self):
        c = BeatClock(bpm=120)
        time.sleep(0.2)
        b0 = c.now_beat()
        c.set_bpm(60)
        b1 = c.now_beat()
        # No jump at the moment of change.
        self.assertAlmostEqual(b0, b1, delta=0.02)
        # But the rate has changed.
        time.sleep(0.2)
        b2 = c.now_beat()
        delta = b2 - b1  # at 60 BPM, 0.2s → 0.2 beats
        self.assertGreater(delta, 0.1)
        self.assertLess(delta, 0.3)

    def test_reset_phase_anchors_to_now(self):
        c = BeatClock(bpm=120)
        time.sleep(0.3)
        self.assertGreater(c.now_beat(), 0.4)
        c.reset_phase()
        self.assertLess(c.now_beat(), 0.01)

    def test_conversion_helpers(self):
        c = BeatClock(bpm=120)
        self.assertAlmostEqual(c.seconds_per_beat, 0.5)
        self.assertAlmostEqual(c.beats_to_seconds(4), 2.0)
        self.assertAlmostEqual(c.seconds_to_beats(1.0), 2.0)

    def test_bpm_clamped(self):
        c = BeatClock(bpm=120)
        c.set_bpm(0.1)
        self.assertGreaterEqual(c.bpm, 1.0)
        c.set_bpm(10000)
        self.assertLessEqual(c.bpm, 400.0)


class TestBeatClockPhaseCorrection(unittest.TestCase):

    def test_no_correction_pending_by_default(self):
        c = BeatClock(bpm=120)
        self.assertEqual(c.phase_correction, 0.0)

    def test_request_accumulates_under_threshold(self):
        c = BeatClock(bpm=120)
        c.request_phase_correction(0.3)
        c.request_phase_correction(-0.1)
        # Both below the snap threshold → both queued for smooth drift.
        self.assertAlmostEqual(c.phase_correction, 0.2)

    def test_request_large_correction_snaps_bulk(self):
        """A 5-beat correction should snap the bulk and only queue the
        residual (≤ 0.5 beats), so we don't stall the playhead."""
        c = BeatClock(bpm=120)
        c.request_phase_correction(5.0)
        # Residual capped at 0.5 beats.
        self.assertLessEqual(abs(c.phase_correction), 0.5 + 1e-6)

    def test_tick_consumes_correction_exponentially(self):
        c = BeatClock(bpm=120)
        c.request_phase_correction(0.4)
        # 1 tick of 1.0 s (= one τ) should consume ~63%.
        c.tick(1.0)
        remaining = c.phase_correction
        self.assertGreater(remaining, 0.1)
        self.assertLess(remaining, 0.25)

    def test_positive_correction_advances_beat(self):
        c = BeatClock(bpm=120)
        before = c.now_beat()
        c.request_phase_correction(2.0)
        # Wait real time too so natural advancement happens.
        time.sleep(0.5)
        c.tick(0.5)
        after = c.now_beat()
        # Natural advancement ~1 beat at 120 BPM in 0.5 s; correction adds
        # extra speed-up. After-before should clearly exceed 1.
        self.assertGreater(after - before, 1.1)

    def test_negative_correction_does_not_reverse(self):
        c = BeatClock(bpm=120)
        c.request_phase_correction(-5.0)
        before = c.now_beat()
        time.sleep(0.1)
        c.tick(0.1)
        after = c.now_beat()
        # Capped so playhead still moves forward despite huge negative request.
        self.assertGreaterEqual(after, before)

    def test_correction_consumed_to_zero_eventually(self):
        c = BeatClock(bpm=120)
        c.request_phase_correction(0.2)
        for _ in range(60):
            c.tick(0.1)
        # After ~6 s (= 4τ), residual ~e⁻⁴ · 0.2 ≈ 0.004 — small enough.
        self.assertLess(abs(c.phase_correction), 0.01)

    def test_reset_phase_clears_correction(self):
        c = BeatClock(bpm=120)
        c.request_phase_correction(0.5)
        c.reset_phase()
        self.assertEqual(c.phase_correction, 0.0)

    def test_beat_at_uses_current_t0(self):
        c = BeatClock(bpm=120)
        time.sleep(0.1)
        t = time.monotonic()
        beat_now = c.beat_at(t)
        # Equivalent to now_beat() to within microseconds.
        self.assertAlmostEqual(beat_now, c.now_beat(), delta=0.01)


if __name__ == "__main__":
    unittest.main()
