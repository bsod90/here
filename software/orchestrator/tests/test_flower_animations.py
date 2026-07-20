"""Render-sanity tests for the flower-garden playground animations
(lotus, dandelion, sunflower, meadow, waterlily, moodflower) plus the
talking sound-wave shimmer."""
import unittest

import numpy as np

from grid import FRAME_BYTES
from animations import (lotus, dandelion, sunflower, meadow, waterlily,
                        moodflower, talking)

MODULES = {
    "lotus": lotus,
    "dandelion": dandelion,
    "sunflower": sunflower,
    "meadow": meadow,
    "waterlily": waterlily,
    "moodflower": moodflower,
}


def paint(module, t_ms, params=None, state=None):
    frame = bytearray(FRAME_BYTES)
    module.render(frame, t_ms, params or {},
                  state if state is not None else {})
    return np.frombuffer(bytes(frame), dtype=np.uint8)


class TestFlowerAnimations(unittest.TestCase):

    def test_all_render_nonzero(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                state = {}
                paint(mod, 0.0, state=state)       # stamp intro timers
                paint(mod, 5_000.0, state=state)   # let spawners run
                px = paint(mod, 20_000.0, state=state)
                self.assertGreater(int(px.sum()), 0,
                                   f"{name} painted nothing")

    def test_all_animate_over_time(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                state = {}
                paint(mod, 0.0, state=state)
                a = paint(mod, 8_000.0, state=state)
                b = paint(mod, 21_000.0, state=state)
                self.assertFalse(np.array_equal(a, b), f"{name} is static")

    def test_zero_brightness_is_dark(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                state = {}
                paint(mod, 0.0, params={"brightness": 0.0}, state=state)
                px = paint(mod, 20_000.0, params={"brightness": 0.0},
                           state=state)
                self.assertEqual(int(px.max()), 0)

    def test_render_without_state_dict(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                frame = bytearray(FRAME_BYTES)
                mod.render(frame, 0.0, {}, None)
                mod.render(frame, 12_000.0, {}, None)

    def test_lotus_unfolds_layer_by_layer(self):
        state = {}
        paint(lotus, 0.0, state=state)
        early = paint(lotus, 3_000.0, state=state)    # core + first ring
        late = paint(lotus, 25_000.0, state=state)    # everything open
        self.assertLess(int(early.sum()), int(late.sum()),
                        "lotus should keep opening over time")

    def test_dandelion_head_thins_out(self):
        # Compare the head density early vs late (deplete_s elapsed) —
        # fewer lit LEDs near the center once the head has shed.
        state = {}
        paint(dandelion, 0.0, state=state)
        early = paint(dandelion, 1_000.0,
                      params={"spawn_period_s": 9999}, state=state)
        state2 = {}
        paint(dandelion, 0.0, state=state2)
        late_t = 1_000.0 + 90.0 * 1000.0              # past deplete_s
        late = paint(dandelion, late_t,
                     params={"spawn_period_s": 9999}, state=state2)
        self.assertLess(int(late.sum()), int(early.sum()),
                        "dandelion head should thin out")

    def test_meadow_spawns_immediately(self):
        # The first flower must appear right away (never an empty meadow
        # when Nadia hits the trigger button).
        state = {}
        paint(meadow, 0.0, state=state)
        self.assertEqual(len(state["flowers"]), 1)

    def test_sunflower_seeds_stay_on_grid(self):
        px = paint(sunflower, 7_000.0)
        self.assertGreater(int(px.sum()), 0)          # never throws OOB

    def test_waterlily_ripples_move(self):
        # With the lily held fixed, frame differences must come from the
        # traveling rings.
        a = paint(waterlily, 1_000.0)
        b = paint(waterlily, 3_000.0)
        self.assertFalse(np.array_equal(a, b))

    def test_moodflower_changes_hue_over_minutes(self):
        state = {}
        paint(moodflower, 0.0, state=state)
        a = paint(moodflower, 30_000.0, state=state,
                  params={"shimmer_amount": 0.0, "cycle_period_s": 120.0})
        b = paint(moodflower, 90_000.0, state=state,
                  params={"shimmer_amount": 0.0, "cycle_period_s": 120.0})
        # Same shape, different palette → frames differ substantially.
        self.assertGreater(int(np.abs(a.astype(int) - b.astype(int)).sum()), 1000)

    def test_talking_shimmer_radiates_waves(self):
        # With shimmer on, there's light well outside the core glow;
        # with it off, that band is essentially dark.
        on = paint(talking, 4_000.0,
                   params={"shimmer_amount": 0.4, "halo": False})
        off = paint(talking, 4_000.0,
                    params={"shimmer_amount": 0.0, "halo": False})
        self.assertGreater(int(on.sum()), int(off.sum()))


if __name__ == "__main__":
    unittest.main()


class TestNoRedDominantPixels(unittest.TestCase):
    """Sunflower and White noise must never render a red-dominant pixel —
    red-leaning values at the dim end read as scattered red LEDs on the
    floor (the gold sunflower heart and the old candle tint both did)."""

    def _worst_red_count(self, mod):
        st = {}
        worst = 0
        for i in range(90):                      # ~36 s of animation
            f = bytearray(FRAME_BYTES)
            mod.render(f, i * 400.0, {}, st)
            px = np.frombuffer(bytes(f), np.uint8).reshape(-1, 3).astype(int)
            red = (px[:, 0] > px[:, 1]) & (px[:, 0] > px[:, 2]) & (px[:, 0] >= 2)
            worst = max(worst, int(red.sum()))
        return worst

    def test_sunflower_never_red(self):
        self.assertEqual(self._worst_red_count(sunflower), 0)

    def test_white_noise_never_red(self):
        from animations import noise
        self.assertEqual(self._worst_red_count(noise), 0)
