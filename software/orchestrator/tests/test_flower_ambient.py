"""The 4-petal flower's ambient-life filter (flower.py).

The flower's intro has a long 'hold' stage where it sits fully open and,
without the ambient filter, perfectly still. These tests confirm the ambient
filter introduces gentle frame-to-frame motion during that hold (and during
the static, no-sequence mode), and that disabling it freezes the hold again.
"""
import unittest

import numpy as np

from grid import FRAME_BYTES
from animations import flower


def paint(t_ms, params, state):
    frame = bytearray(FRAME_BYTES)
    flower.render(frame, t_ms, params, state)
    return np.frombuffer(bytes(frame), dtype=np.uint8).astype(int)


# Default timing: center 2s + grow 1.5s + hold 2s → hold spans 3.5s..5.5s.
HOLD_A, HOLD_B = 4_000.0, 5_000.0


class TestAmbient(unittest.TestCase):

    def test_hold_is_static_without_ambient(self):
        p = {"ambient": False, "motion_blur": False}
        st = {}
        paint(0.0, p, st)                       # stamp t0
        a = paint(HOLD_A, p, st)
        b = paint(HOLD_B, p, st)
        # Same open flower, no motion → identical frames during the hold.
        self.assertEqual(int(np.abs(a - b).sum()), 0)

    def test_hold_moves_with_ambient(self):
        p = {"ambient": True, "motion_blur": False}
        st = {}
        paint(0.0, p, st)
        a = paint(HOLD_A, p, st)
        b = paint(HOLD_B, p, st)
        # Ambient sway/warp/breath/shimmer → the held frame is no longer frozen.
        self.assertGreater(int(np.abs(a - b).sum()), 0)

    def test_shimmer_alone_modulates_brightness(self):
        # Only the shimmer on (no geometry motion) still livens the hold.
        p = {"ambient": True, "motion_blur": False,
             "ambient_sway_deg": 0.0, "ambient_warp": 0.0, "ambient_breath": 0.0,
             "ambient_shimmer": 0.2}
        st = {}
        paint(0.0, p, st)
        a = paint(HOLD_A, p, st)
        b = paint(HOLD_B, p, st)
        self.assertGreater(int(np.abs(a - b).sum()), 0)

    def test_shimmer_keeps_black_gaps_black(self):
        # Multiplicative shimmer must never light the black space between
        # petals (it only scales already-lit pixels). Disable the geometry
        # motion so the petals sit in the same place as the no-shimmer render.
        nomove = {"ambient_sway_deg": 0.0, "ambient_warp": 0.0,
                  "ambient_breath": 0.0, "motion_blur": False}
        off = {**nomove, "ambient": False}
        on = {**nomove, "ambient": True, "ambient_shimmer": 0.3}
        st_off, st_on = {}, {}
        paint(0.0, off, st_off); paint(0.0, on, st_on)
        lit = paint(HOLD_A, off, st_off)
        shim = paint(HOLD_A, on, st_on)
        black = lit.reshape(-1, 3).sum(axis=1) == 0
        shim_rgb = shim.reshape(-1, 3).sum(axis=1)
        self.assertEqual(int(shim_rgb[black].sum()), 0)

    def test_static_mode_also_lives(self):
        # sequence=False (just sit open) should still shimmer/sway.
        p = {"sequence": False, "ambient": True, "motion_blur": False}
        a = paint(4_000.0, p, {})
        b = paint(6_500.0, p, {})
        self.assertGreater(int(np.abs(a - b).sum()), 0)

    def test_ambient_stays_in_range(self):
        # Output must remain valid 0..255 bytes with ambient pushed hard.
        p = {"ambient": True, "ambient_shimmer": 0.3, "brightness": 1.0}
        px = paint(13_000.0, p, {"_seed": 1})
        self.assertTrue((px >= 0).all() and (px <= 255).all())


if __name__ == "__main__":
    unittest.main()
