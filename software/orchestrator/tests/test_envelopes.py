"""Tests for Envelope sampling and Modulator lifecycle."""
import unittest

from scene.envelopes import (
    Envelope,
    Modulator,
    combine,
    default_envelopes,
)


class TestEnvelopeSample(unittest.TestCase):

    def test_empty_envelope_returns_zero(self):
        e = Envelope(points=[])
        self.assertEqual(e.sample(0.0), 0.0)
        self.assertEqual(e.sample(0.5), 0.0)
        self.assertEqual(e.sample(1.0), 0.0)

    def test_single_point(self):
        e = Envelope(points=[(0.5, 0.7)])
        self.assertEqual(e.sample(0.0), 0.7)
        self.assertEqual(e.sample(0.5), 0.7)
        self.assertEqual(e.sample(1.0), 0.7)

    def test_two_point_linear(self):
        e = Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp="linear")
        self.assertAlmostEqual(e.sample(0.0), 0.0)
        self.assertAlmostEqual(e.sample(0.25), 0.25)
        self.assertAlmostEqual(e.sample(0.5), 0.5)
        self.assertAlmostEqual(e.sample(1.0), 1.0)

    def test_two_point_cosine(self):
        e = Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp="cosine")
        # cosine: at t=0.5 → 0.5 exactly
        self.assertAlmostEqual(e.sample(0.5), 0.5, places=5)
        # cosine: at t=0.25 → (1-cos(pi/4))/2 = (1-0.7071)/2 ≈ 0.1464
        self.assertAlmostEqual(e.sample(0.25), 0.14644660, places=5)

    def test_multi_point(self):
        # spike: rises to 1 at t=0.1, falls back to 0 at t=1.0
        e = Envelope(points=[(0.0, 0.0), (0.1, 1.0), (1.0, 0.0)], interp="linear")
        self.assertAlmostEqual(e.sample(0.0), 0.0)
        self.assertAlmostEqual(e.sample(0.05), 0.5)
        self.assertAlmostEqual(e.sample(0.1), 1.0)
        self.assertAlmostEqual(e.sample(0.55), 0.5)
        self.assertAlmostEqual(e.sample(1.0), 0.0)

    def test_clamps_out_of_range(self):
        e = Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp="linear")
        self.assertAlmostEqual(e.sample(-0.5), 0.0)
        self.assertAlmostEqual(e.sample(1.5), 1.0)

    def test_to_dict_round_trip(self):
        e = Envelope(points=[(0.0, 0.0), (0.5, 0.8), (1.0, 0.2)], interp="cosine")
        d = e.to_dict()
        e2 = Envelope.from_dict(d)
        self.assertEqual(e2.interp, "cosine")
        self.assertEqual(len(e2.points), 3)
        self.assertAlmostEqual(e2.sample(0.5), 0.8)

    def test_from_dict_sorts_points(self):
        e = Envelope.from_dict({"points": [[1.0, 1.0], [0.0, 0.0], [0.5, 0.5]]})
        self.assertEqual([p[0] for p in e.points], [0.0, 0.5, 1.0])


class TestModulatorOneShot(unittest.TestCase):
    """One-shot modulator: plays envelope once, then done (no release)."""

    def test_before_start_returns_none(self):
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=1.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=2.0, duration_beats=1.0,
        )
        self.assertIsNone(m.value_at(1.0))
        self.assertIsNone(m.value_at(1.999))

    def test_attack_rise(self):
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=1.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=2.0,
        )
        self.assertAlmostEqual(m.value_at(0.0), 0.0)
        self.assertAlmostEqual(m.value_at(1.0), 0.5)
        self.assertAlmostEqual(m.value_at(1.999), 0.9995, places=3)

    def test_one_shot_done_after_duration(self):
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=1.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=1.0,
        )
        # At exactly duration → done (no release env).
        self.assertIsNone(m.value_at(1.0))
        self.assertIsNone(m.value_at(2.0))
        self.assertTrue(m.done(1.0))

    def test_one_shot_pulse_shape(self):
        # Classic pulse: rises, falls, ends.
        envs = default_envelopes()
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=1.0,
            envelope=envs["pulse_default"],
            start_beat=0.0, duration_beats=1.0,
        )
        # Past start → small positive value
        self.assertGreater(m.value_at(0.01), 0.0)
        # Near peak (around t=0.08 in pulse_default)
        v_peak = m.value_at(0.08)
        self.assertGreater(v_peak, 0.5)
        # Near end → near zero
        self.assertLess(m.value_at(0.95), 0.2)
        # After end → None
        self.assertIsNone(m.value_at(1.5))

    def test_absolute_op_maps_to_base_to_peak(self):
        m = Modulator(
            target="radius", op="absolute",
            base_value=10.0, peak_value=20.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=1.0,
        )
        self.assertAlmostEqual(m.value_at(0.0), 10.0)
        self.assertAlmostEqual(m.value_at(0.5), 15.0)


class TestModulatorWithRelease(unittest.TestCase):
    """Held modulator: sustains at peak until release(), then ramps back."""

    def _make(self):
        return Modulator(
            target="radius", op="absolute",
            base_value=10.0, peak_value=20.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp="linear"),
            start_beat=0.0, duration_beats=1.0,
            release_envelope=Envelope(points=[(0.0, 1.0), (1.0, 0.0)], interp="linear"),
            release_duration_beats=1.0,
        )

    def test_sustains_at_peak_after_duration(self):
        m = self._make()
        # Past duration but not released → holds at envelope.sample(1.0) = peak
        self.assertAlmostEqual(m.value_at(2.0), 20.0)
        self.assertAlmostEqual(m.value_at(10.0), 20.0)

    def test_release_ramps_back_to_base(self):
        m = self._make()
        m.release(2.0)
        self.assertAlmostEqual(m.value_at(2.0), 20.0)        # release start = held value
        self.assertAlmostEqual(m.value_at(2.5), 15.0)        # halfway back
        self.assertAlmostEqual(m.value_at(2.999), 10.01, places=2)
        # Past release → done.
        self.assertIsNone(m.value_at(3.0))
        self.assertIsNone(m.value_at(4.0))

    def test_release_mid_attack_freezes_held_value(self):
        m = self._make()
        # Release at t=0.5 → held = 10 + (20-10)*0.5 = 15.0
        m.release(0.5)
        self.assertAlmostEqual(m.value_at(0.5), 15.0)
        self.assertAlmostEqual(m.value_at(1.0), 12.5)        # halfway through release
        self.assertIsNone(m.value_at(1.5))

    def test_release_is_idempotent(self):
        m = self._make()
        m.release(2.0)
        m.release(3.0)  # should not move the release point
        self.assertEqual(m.release_beat, 2.0)


class TestCombine(unittest.TestCase):
    """combine() folds multiple active modulators on the same target."""

    def test_absolute_overrides_base(self):
        m = Modulator(
            target="alpha", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=1.0,
        )
        # No active modulator → returns base.
        self.assertAlmostEqual(combine("alpha", 0.3, [], 0.5), 0.3)
        # Absolute at t=0.5 → mod returns 0.5; base ignored.
        self.assertAlmostEqual(combine("alpha", 0.3, [m], 0.5), 0.5)

    def test_additive_adds_to_base(self):
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=0.5,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=1.0,
        )
        # At t=0.5 mod contributes 0.25 → base 0.3 + 0.25 = 0.55
        self.assertAlmostEqual(combine("alpha", 0.3, [m], 0.5), 0.55)

    def test_multiplicative_scales(self):
        m = Modulator(
            target="alpha", op="multiplicative",
            base_value=1.0, peak_value=2.0,
            envelope=Envelope(points=[(0.0, 0.0), (1.0, 1.0)]),
            start_beat=0.0, duration_beats=1.0,
        )
        # At t=0.5 mod returns 1.5 → 0.3 * 1.5 = 0.45
        self.assertAlmostEqual(combine("alpha", 0.3, [m], 0.5), 0.45)

    def test_multiple_additives_sum(self):
        m1 = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=0.1,
            envelope=Envelope(points=[(0.0, 1.0)]),  # constant 1.0
            start_beat=0.0, duration_beats=10.0,
        )
        m2 = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=0.2,
            envelope=Envelope(points=[(0.0, 1.0)]),
            start_beat=0.0, duration_beats=10.0,
        )
        # base + 0.1 + 0.2 = 0.7
        self.assertAlmostEqual(combine("alpha", 0.4, [m1, m2], 1.0), 0.7)

    def test_skips_other_targets(self):
        m = Modulator(
            target="alpha", op="additive",
            base_value=0.0, peak_value=10.0,
            envelope=Envelope(points=[(0.0, 1.0)]),
            start_beat=0.0, duration_beats=10.0,
        )
        # Combine on "radius" should ignore the alpha modulator.
        self.assertAlmostEqual(combine("radius", 5.0, [m], 1.0), 5.0)


class TestValidation(unittest.TestCase):
    def test_invalid_op_raises(self):
        with self.assertRaises(ValueError):
            Modulator(
                target="x", op="bogus",
                base_value=0, peak_value=1,
                envelope=Envelope(points=[(0, 0), (1, 1)]),
                start_beat=0, duration_beats=1,
            )

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            Modulator(
                target="x", op="absolute",
                base_value=0, peak_value=1,
                envelope=Envelope(points=[(0, 0), (1, 1)]),
                start_beat=0, duration_beats=-1,
            )


if __name__ == "__main__":
    unittest.main()
