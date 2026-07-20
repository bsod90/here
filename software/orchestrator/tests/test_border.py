"""Tests for the floor-border LED subsystem (border.py).

All hardware-free: the SPI strips no-op without spidev, and the animations
are pure numpy so render_frame can be exercised directly.
"""
import unittest

import numpy as np

from border import (BorderController, ANIMATIONS, PALETTE_PRESETS,
                    COLOR_ORDERS, _pal_lerp, _pal_array, _LUT, _spd, _SpiStrip)


class FakeConfig:
    def __init__(self, border):
        self._d = {"border": border}

    def get(self, key, default=None):
        return self._d.get(key, default)

    def set(self, key, value):
        cur = self._d.setdefault(key, {})
        cur.update(value)


def base_cfg(**over):
    c = {
        "enabled": True, "fps": 24, "brightness": 0.5, "speed": 0.3,
        "color": [80, 120, 255],
        "palette": [[80, 120, 255], [40, 90, 205], [95, 70, 205]],
        "animation": "pulse",
        "segments": [{"spi": "1.0", "num": 30}],
    }
    c.update(over)
    return c


def make(**over):
    cfg = FakeConfig(base_cfg(**over))
    return BorderController(cfg), cfg


class TestEncoding(unittest.TestCase):
    def test_lut_bit_pattern(self):
        # byte 0x00 → all '0' bits → each 100 → 0x92 0x49 0x24 (100100100…)
        self.assertEqual(_LUT[0x00], bytes((0x92, 0x49, 0x24)))
        # byte 0xFF → all '1' bits → each 110 → 0xDB 0x6D 0xB6
        self.assertEqual(_LUT[0xFF], bytes((0xDB, 0x6D, 0xB6)))

    def test_lut_covers_all_bytes(self):
        self.assertEqual(len(_LUT), 256)
        self.assertTrue(all(len(b) == 3 for b in _LUT))


class TestPalette(unittest.TestCase):
    def test_lerp_endpoints_and_wrap(self):
        pal = _pal_array([[0, 0, 0], [255, 0, 0]])
        out = _pal_lerp(pal, np.array([0.0, 0.5, 0.999]))
        np.testing.assert_allclose(out[0], [0, 0, 0], atol=1e-3)
        np.testing.assert_allclose(out[1], [255, 0, 0], atol=1e-3)  # 2 colours, 0.5→idx1
        # near 1.0 wraps back toward colour 0
        self.assertLess(out[2][0], 255)

    def test_presets_are_rgb_triples(self):
        for name, pal in PALETTE_PRESETS.items():
            self.assertTrue(pal and all(len(c) == 3 for c in pal), name)


class TestAnimations(unittest.TestCase):
    def test_all_animations_render_valid_frames(self):
        ctrl, _ = make()
        n = 30
        for name in ANIMATIONS:
            for t in (0.0, 3.7, 60.0):
                frame = ctrl.render_frame(t, n, base_cfg(animation=name))
                self.assertEqual(frame.shape, (n, 3), name)
                self.assertEqual(frame.dtype, np.uint8, name)
                self.assertTrue((frame >= 0).all() and (frame <= 255).all(), name)

    def test_brightness_scales_output(self):
        ctrl, _ = make()
        hi = ctrl.render_frame(0.0, 30, base_cfg(animation="solid", brightness=1.0))
        lo = ctrl.render_frame(0.0, 30, base_cfg(animation="solid", brightness=0.2))
        self.assertGreater(int(hi.max()), int(lo.max()))

    def test_zero_brightness_is_dark(self):
        ctrl, _ = make()
        f = ctrl.render_frame(0.0, 30, base_cfg(animation="pulse", brightness=0.0))
        self.assertEqual(int(f.max()), 0)

    def test_gradient_orbit_moves_over_time(self):
        ctrl, _ = make()
        cfg = base_cfg(animation="gradient_orbit", brightness=1.0, speed=1.0)
        a = ctrl.render_frame(0.0, 60, cfg)
        b = ctrl.render_frame(30.0, 60, cfg)
        self.assertTrue(np.abs(a.astype(int) - b.astype(int)).sum() > 0)

    def test_twinkle_persists_per_pixel_state(self):
        ctrl, _ = make()
        cfg = base_cfg(animation="twinkle")
        ctrl.render_frame(0.0, 30, cfg)
        self.assertIn("_tw", ctrl._anim_params)
        self.assertEqual(ctrl._anim_params["_tw"]["n"], 30)


class TestSpeedDial(unittest.TestCase):
    def test_half_center_double(self):
        # Geometric dial: 0% → half, 50% → calibrated, 100% → double.
        self.assertAlmostEqual(_spd({"speed": 0.0}), 1.0, places=6)
        self.assertAlmostEqual(_spd({"speed": 0.5}), 2.0, places=6)
        self.assertAlmostEqual(_spd({"speed": 1.0}), 4.0, places=6)

    def test_monotonic(self):
        self.assertLess(_spd({"speed": 0.2}), _spd({"speed": 0.8}))


class TestColorOrder(unittest.TestCase):
    def test_all_six_orders_present(self):
        self.assertEqual(set(COLOR_ORDERS), {
            "RGB", "RBG", "GRB", "GBR", "BRG", "BGR"})

    def test_permutation_reorders_channels(self):
        # A no-spidev strip: show() must not raise and the perm is correct.
        rgb = np.array([[10, 20, 30]], dtype=np.uint8)
        # GRB → bytes (G,R,B) = (20,10,30); verify the perm picks those columns.
        self.assertEqual(tuple(rgb[:, COLOR_ORDERS["GRB"]][0]), (20, 10, 30))
        self.assertEqual(tuple(rgb[:, COLOR_ORDERS["RBG"]][0]), (10, 30, 20))
        s = _SpiStrip(9, 9, 1)        # bus that won't open → no-op show
        s.show(rgb, "RBG")            # must not raise


class TestController(unittest.TestCase):
    def test_total_sums_segments(self):
        ctrl, _ = make(segments=[{"spi": "1.0", "num": 30},
                                 {"spi": "0.0", "num": 20}])
        self.assertEqual(ctrl._total, 50)

    def test_status_reports_strips_and_options(self):
        ctrl, _ = make()
        st = ctrl.status()
        self.assertEqual(st["total"], 30)
        self.assertEqual(len(st["strips"]), 1)
        self.assertIn("pulse", st["animations"])
        self.assertIn("cold", st["palettes"])
        # No spidev in test env → strip not ok, but it must not crash.
        self.assertFalse(st["strips"][0]["ok"])

    def test_reload_rebuilds_strips(self):
        ctrl, cfg = make()
        cfg.set("border", {"segments": [{"spi": "1.0", "num": 99}]})
        ctrl.reload()
        self.assertEqual(ctrl._total, 99)

    def test_push_slices_frame_across_segments(self):
        ctrl, _ = make(segments=[{"spi": "1.0", "num": 10},
                                 {"spi": "0.0", "num": 5}])
        # _push must not raise even though strips are no-op (no spidev).
        frame = np.zeros((15, 3), dtype=np.uint8)
        ctrl._push(frame)


class TestSpatialDithering(unittest.TestCase):
    """At the border's dim running brightness only ~a dozen hardware
    levels exist. Fixed per-pixel dither offsets spread quantization
    jumps across the strip (slow fades ripple instead of stepping) while
    a static colour renders IDENTICAL frames — no temporal flicker."""

    def test_strip_average_hits_fractional_level(self):
        ctrl, _ = make()
        cfg = base_cfg(animation="solid", color=[255, 255, 255],
                       brightness=0.25)
        target = 0.25 ** 2.2 * 255.0            # ideal float level ≈ 12.08
        f = ctrl.render_frame(0.0, 300, cfg)    # long strip → tight average
        self.assertAlmostEqual(float(f.mean()), target, delta=0.15)

    def test_dither_spans_adjacent_levels_across_pixels(self):
        ctrl, _ = make()
        cfg = base_cfg(animation="solid", color=[210, 210, 210],
                       brightness=0.25)
        vals = {int(v) for v in ctrl.render_frame(0.0, 60, cfg)[:, 0]}
        self.assertGreaterEqual(len(vals), 2, "no dithering happening")
        self.assertLessEqual(max(vals) - min(vals), 1,
                             "dither must only span adjacent levels")

    def test_static_input_is_temporally_stable(self):
        # THE flicker regression: a constant colour must produce
        # byte-identical frames — the offsets never move over time.
        ctrl, _ = make()
        cfg = base_cfg(animation="solid", color=[10, 60, 255],
                       brightness=0.25)
        first = ctrl.render_frame(0.0, 60, cfg)
        for i in range(1, 40):
            np.testing.assert_array_equal(
                ctrl.render_frame(i * 0.02, 60, cfg), first)

    def test_zero_stays_exactly_zero(self):
        ctrl, _ = make()
        cfg = base_cfg(animation="solid", color=[0, 0, 0], brightness=1.0)
        for i in range(20):
            self.assertEqual(int(ctrl.render_frame(i * 0.02, 30, cfg).max()), 0)


class TestColorSync(unittest.TestCase):
    """color_sync follows the floor's dominant colour, eased — never a snap."""

    def test_render_uses_the_floor_color(self):
        buf = bytes([0, 200, 0]) * 100          # floor showing green
        ctrl = BorderController(FakeConfig(base_cfg()),
                                frame_source=lambda: buf)
        ctrl._update_sync_color(0.05)           # first sample snaps
        f = ctrl.render_frame(0.0, 10, base_cfg(animation="solid",
                                                brightness=1.0))
        px = f[0].astype(int)
        self.assertGreater(px[1], px[0])
        self.assertGreater(px[1], px[2])

    def test_transition_is_gradual_then_settles(self):
        src = {"buf": bytes([0, 200, 0]) * 100}
        ctrl = BorderController(FakeConfig(base_cfg()),
                                frame_source=lambda: src["buf"])
        ctrl._update_sync_color(0.05)
        src["buf"] = bytes([200, 0, 0]) * 100   # floor switches to red
        ctrl._update_sync_color(1.0 / 60.0)     # one 60fps tick later…
        self.assertGreater(ctrl._sync_rgb[1], ctrl._sync_rgb[0],
                           "one tick must not snap to the new colour")
        for _ in range(60 * 15):                # ≫ the 3 s time constant
            ctrl._update_sync_color(1.0 / 60.0)
        self.assertGreater(ctrl._sync_rgb[0], ctrl._sync_rgb[1])

    def test_sync_off_keeps_configured_color(self):
        buf = bytes([0, 200, 0]) * 100
        ctrl = BorderController(FakeConfig(base_cfg(color_sync=False)),
                                frame_source=lambda: buf)
        ctrl._update_sync_color(0.05)
        f = ctrl.render_frame(0.0, 10, base_cfg(animation="solid",
                                                brightness=1.0,
                                                color_sync=False,
                                                color=[255, 0, 0]))
        px = f[0].astype(int)
        self.assertGreater(px[0], px[1])

    def test_dark_floor_holds_last_color(self):
        src = {"buf": bytes([0, 200, 0]) * 100}
        ctrl = BorderController(FakeConfig(base_cfg()),
                                frame_source=lambda: src["buf"])
        ctrl._update_sync_color(0.05)
        before = ctrl._sync_rgb.copy()
        src["buf"] = bytes(300)                  # floor goes fully dark
        for _ in range(30):
            ctrl._update_sync_color(1.0 / 60.0)
        np.testing.assert_allclose(ctrl._sync_rgb, before)

    def test_no_frame_source_is_a_noop(self):
        ctrl, _ = make()
        ctrl._update_sync_color(0.05)
        self.assertIsNone(ctrl._sync_rgb)


if __name__ == "__main__":
    unittest.main()
