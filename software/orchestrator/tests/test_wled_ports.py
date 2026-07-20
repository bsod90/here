"""Regression tests for the WLED-port primitives in animations/_wled.py.

Both cases here are real bugs we shipped once:
  * abs8 must truncate to int8 BEFORE the abs — a plain abs() turned the
    bump byte-wrap at Perlin zero-crossings into a black contour line
    across Sun Radiation.
  * inoise8_raw must be the bit-exact FastLED raw (−64..+64) — a stray
    duplicate definition (inoise8()−128, ≈ ±127) once shadowed it.
"""
import unittest

import numpy as np

from grid import FRAME_BYTES, GRID
from animations import _wled as w
from animations import borderglow, darkflower, wled_sunrad


class TestAbs8(unittest.TestCase):

    def test_matches_int8_truncation_semantics(self):
        # C: abs8((int8_t)v) for every int the effects can produce.
        v = np.arange(-600, 600)
        expect = np.abs(((v + 128) % 256) - 128)
        got = w.abs8(v)
        np.testing.assert_array_equal(got, expect.astype(np.float32))

    def test_byte_wrap_jump_reads_small(self):
        # The Sun Radiation case: a bump wrap of ±224 must reflect to 32,
        # not stay at 224 (which crushed the heat to black).
        self.assertEqual(float(w.abs8(-224)), 32.0)
        self.assertEqual(float(w.abs8(224)), 32.0)


class TestInoise8Raw(unittest.TestCase):

    def test_range_is_fastled_raw(self):
        xs = np.arange(0, 1 << 16, 97)
        vals = w.inoise8_raw(xs, xs * 3, 12345)
        self.assertGreaterEqual(float(vals.min()), -64.0)
        self.assertLessEqual(float(vals.max()), 64.0)


class TestBorderGlow(unittest.TestCase):
    """The MIDI engine's shimmering border, ported to the playground."""

    def _px(self, t_ms, state):
        frame = bytearray(FRAME_BYTES)
        borderglow.render(frame, t_ms, {"fade_in_s": 0.0}, state)
        return np.frombuffer(bytes(frame), dtype=np.uint8).reshape(GRID, GRID, 3)

    def test_lights_the_rim_not_the_center(self):
        px = self._px(1_000.0, {"t0": 0.0})
        self.assertGreater(int(px[0].sum()), 0)      # top edge lit
        self.assertGreater(int(px[-1].sum()), 0)     # bottom edge lit
        self.assertGreater(int(px[:, 0].sum()), 0)   # left edge lit
        self.assertEqual(int(px[GRID // 2, GRID // 2].sum()), 0)  # center dark

    def test_shimmer_animates_the_edge(self):
        st = {"t0": 0.0}
        a = self._px(1_000.0, st)
        b = self._px(3_000.0, st)
        self.assertFalse(np.array_equal(a, b), "border shimmer is static")


class TestDarkFlower(unittest.TestCase):
    """Shimmering border + a breathing, shimmer-rimmed bloom inside."""

    def _px(self, t_ms, state):
        frame = bytearray(FRAME_BYTES)
        darkflower.render(frame, t_ms, {"fade_in_s": 0.0}, state)
        return np.frombuffer(bytes(frame), np.uint8).reshape(GRID, GRID, 3)

    def test_frame_and_bloom_both_lit(self):
        st = {"t0": 0.0}
        px = self._px(5_000.0, st)               # mid-breath → bloom open
        self.assertGreater(int(px[0].sum()), 0)  # border top edge lit
        c = GRID // 2
        self.assertGreater(int(px[c, c].sum()), 0)  # bloom centre lit
        # The gap between bloom and border stays dark (it's a flower in
        # a frame, not a filled floor).
        self.assertEqual(int(px[6, c].sum() + px[c, 6].sum()), 0)

    def test_bloom_breathes(self):
        st = {"t0": 0.0}
        lit = []
        for t in (500.0, 2_000.0, 3_500.0, 5_000.0, 6_500.0, 8_000.0, 9_500.0):
            px = self._px(t, st).reshape(-1, 3)
            lit.append(int((px.sum(axis=1) > 12).sum()))
        self.assertGreater(max(lit), min(lit) * 1.5,
                           f"bloom radius never moved: {lit}")

    def test_shimmer_animates_the_rims(self):
        st = {"t0": 0.0}
        a = self._px(4_000.0, st)
        b = self._px(4_400.0, st)
        self.assertFalse(np.array_equal(a, b), "shimmer is static")


class TestSunRadiation(unittest.TestCase):

    def test_renders_a_visible_sun(self):
        frame = bytearray(FRAME_BYTES)
        wled_sunrad.render(frame, 45_000.0,
                           {"fade_in_s": 0.0}, {"t0": 0.0})
        px = np.frombuffer(bytes(frame), dtype=np.uint8)
        self.assertGreater(int(px.sum()), 0)


if __name__ == "__main__":
    unittest.main()
