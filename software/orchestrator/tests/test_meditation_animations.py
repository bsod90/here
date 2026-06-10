"""Render-sanity tests for the guided-meditation playground animations
(welcome, talking, chill, winddown) — they must paint, move, respect the
master brightness, and never crash with empty params."""
import unittest

import numpy as np

from grid import FRAME_BYTES
from animations import welcome, talking, chill, winddown

MODULES = {
    "welcome": welcome,
    "talking": talking,
    "chill": chill,
    "winddown": winddown,
}


def paint(module, t_ms, params=None, state=None):
    frame = bytearray(FRAME_BYTES)
    module.render(frame, t_ms, params or {}, state if state is not None else {})
    return np.frombuffer(bytes(frame), dtype=np.uint8)


class TestMeditationAnimations(unittest.TestCase):

    def test_all_render_nonzero(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                state = {}
                paint(mod, 0.0, state=state)      # stamp intro timers
                px = paint(mod, 10_000.0, state=state)
                self.assertGreater(int(px.sum()), 0,
                                   f"{name} painted nothing")

    def test_all_animate_over_time(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                state = {}
                a = paint(mod, 1_000.0, state=state)
                b = paint(mod, 9_000.0, state=state)
                self.assertFalse(np.array_equal(a, b),
                                 f"{name} is static")

    def test_zero_brightness_is_dark(self):
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                px = paint(mod, 5_000.0, params={"brightness": 0.0})
                self.assertEqual(int(px.max()), 0)

    def test_render_without_state_dict(self):
        # Adapters always pass a state dict, but the modules must also
        # survive state=None (e.g. ad-hoc preview calls).
        for name, mod in MODULES.items():
            with self.subTest(animation=name):
                frame = bytearray(FRAME_BYTES)
                mod.render(frame, 0.0, {}, None)

    def test_welcome_blooms_in_from_dark(self):
        state = {}
        early = paint(welcome, 0.0, state=state)
        late = paint(welcome, 20_000.0, state=state)
        self.assertLess(int(early.sum()), int(late.sum()),
                        "welcome should start dim and bloom up")

    def test_talking_stays_low_key(self):
        # Talking must not exceed its configured level ceiling — it sits
        # underneath a voice, so a full-blast frame is a bug.
        px = paint(talking, 3_000.0)
        self.assertLess(int(px.max()), 255)

    def test_chill_covers_the_floor(self):
        # The aurora is field-filling: a healthy share of LEDs lit, not
        # one centered blob.
        px = paint(chill, 5_000.0).reshape(-1, 3)
        lit = int((px.sum(axis=1) > 0).sum())
        self.assertGreater(lit, px.shape[0] // 2)

    def test_winddown_dimmer_than_welcome(self):
        # Wind-down ends the session — overall energy should sit below
        # the welcome bloom at steady state.
        w_state, d_state = {}, {}
        paint(welcome, 0.0, state=w_state)
        paint(winddown, 0.0, state=d_state)
        w = paint(welcome, 30_000.0, state=w_state)
        d = paint(winddown, 30_000.0, state=d_state)
        self.assertLess(int(d.sum()), int(w.sum()))


if __name__ == "__main__":
    unittest.main()
