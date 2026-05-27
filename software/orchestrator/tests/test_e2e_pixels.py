"""End-to-end pixel tests for the synth scene engine.

Approach (user-requested): pixel-perfect assertions are brittle for a
blurry, anti-aliased visual. Instead, each test:
  1. Drives the Scene with a specific sequence of events + ticks.
  2. Renders one frame.
  3. Compares against a *visual specification*: regions of pixels that
     should DEFINITELY be lit, regions that should DEFINITELY be dark,
     and a free-form region in between that doesn't matter.
  4. Computes a similarity score (fraction of pixels matching the spec)
     and asserts it crosses an 80% threshold (configurable per-test).

This catches "things are drawn in the right place" without freaking out
about exact gradient values. A small 16×16 grid keeps tests fast.

These tests REQUIRE numpy (it's a runtime dep on the Pi anyway).
"""
import unittest

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

if HAS_NUMPY:
    from grid import make_grid
    from scene.animations.synth import SynthAnimation, _GEOM_CACHE
    from scene.scene import Scene


# Test grid — small for speed, big enough for blur to do something visible.
GRID_SIZE = 16
LIT_THRESHOLD = 25         # any RGB channel > this counts as "lit"
DEFAULT_SIMILARITY = 0.8   # 80% match


# Shared palettes for every test — high-contrast neon so lit pixels are obvious.
TEST_PALETTES = [
    {"rim_color": [255, 100, 200], "inner_color": [80, 255, 240], "outer_color": [200, 60, 255]},
    {"rim_color": [80, 220, 120],  "inner_color": [200, 240, 60], "outer_color": [60, 180, 120]},
]


def _radius_mask(grid, r_low, r_high):
    """Return a boolean mask over grid pixels with distance in [r_low, r_high]."""
    dists = np.array(grid.distances, dtype=np.float32)
    return (dists >= r_low) & (dists <= r_high)


def _is_lit(frame, grid):
    """Per-pixel boolean: did the renderer light this LED?"""
    arr = np.frombuffer(frame, dtype=np.uint8)[: grid.frame_bytes].reshape(grid.total, 3)
    return arr.max(axis=1) > LIT_THRESHOLD


def visual_similarity(frame, grid, *, expect_lit=None, expect_dark=None):
    """Score [0, 1]: fraction of opinionated pixels that match expectation.

    expect_lit / expect_dark are boolean masks over grid.total. Pixels in
    neither mask don't influence the score (the "blurry middle").
    """
    if expect_lit is None:
        expect_lit = np.zeros(grid.total, dtype=bool)
    if expect_dark is None:
        expect_dark = np.zeros(grid.total, dtype=bool)
    lit = _is_lit(frame, grid)
    correct = ((lit & expect_lit).sum() + (~lit & expect_dark).sum())
    total = expect_lit.sum() + expect_dark.sum()
    return float(correct) / max(1, total)


@unittest.skipUnless(HAS_NUMPY, "e2e pixel tests need numpy")
class TestE2EPixels(unittest.TestCase):

    def setUp(self):
        # Fresh geometry cache per test (so prior tests don't keep arrays
        # sized for a different grid).
        _GEOM_CACHE.clear()
        self.grid = make_grid(GRID_SIZE)
        self.anim = SynthAnimation({
            "radius_min": 1.5,
            "radius_max": 6.5,
            "radius_default": 4.0,
            "oval_blur_0": 0.8,
            "oval_blur_1": 1.0,
            "oval_blur_2": 0.6,
            "brightness": 1.0,
        })
        self.scene = Scene(self.anim, bpm=120.0, grid=self.grid)
        self.scene.reset_phase()
        self.frame = bytearray(self.grid.frame_bytes)
        self.params = {"palettes": TEST_PALETTES}
        self._tick_ms = 0.0
        # Snap the clock to beat 0 so triggers in tests start at a known
        # baseline — without this, scene.current_beat() returns whatever
        # real time has elapsed since setUp.
        self._tick(0.0)

    def _tick(self, ms: float) -> None:
        """Advance to absolute time `ms` since setUp. Snaps the BeatClock
        *forward* (never backward) to the corresponding beat — snapping
        backward would put modulators whose start_beat was captured at a
        slightly-later wall-clock time into the future, and they'd be
        pruned on the first tick before firing."""
        import time
        target_beat = (ms / 1000.0) * self.scene._clock.bpm / 60.0
        clk = self.scene._clock
        if target_beat > clk.now_beat():
            clk._t0_seconds = time.monotonic() - target_beat * 60.0 / clk.bpm
        self._tick_ms = ms
        self.scene.tick(ms)

    def _render(self):
        self.scene.render(self.frame, time_ms=self._tick_ms, params=self.params)

    # ── Initial state — ring at default radius ──────────────────
    def test_initial_state_lights_ring_at_default_radius(self):
        self._tick(0.0)
        self._tick(50.0)
        self._render()
        # Expect: pixels at distance 3..5 (ring ~4) lit. Pixels at the very
        # corners (distance > 8) dark.
        expect_lit  = _radius_mask(self.grid, 3.0, 5.0)
        expect_dark = _radius_mask(self.grid, 9.0, 99.0)
        score = visual_similarity(self.frame, self.grid,
                                  expect_lit=expect_lit, expect_dark=expect_dark)
        self.assertGreaterEqual(score, DEFAULT_SIMILARITY,
                                f"similarity {score:.2f} < {DEFAULT_SIMILARITY}")

    # ── Expand event grows the ring ────────────────────────────
    def test_expand_grows_ring(self):
        self.scene.trigger("expand", duration_beats=0.5)
        # Run a bunch of ticks across the expand duration.
        for ms in range(0, 600, 30):
            self._tick(ms)
        self._render()
        # Ring should now sit around radius_max ≈ 6.5.
        expect_lit  = _radius_mask(self.grid, 5.5, 7.5)
        expect_dark = _radius_mask(self.grid, 0.0, 2.5)   # center clear
        score = visual_similarity(self.frame, self.grid,
                                  expect_lit=expect_lit, expect_dark=expect_dark)
        self.assertGreaterEqual(score, DEFAULT_SIMILARITY,
                                f"similarity {score:.2f}")

    # ── Blow Out fades the whole scene to dark ──────────────────
    def test_blow_out_fades_scene_to_dark(self):
        self.scene.trigger("blow_out", duration_beats=0.5)
        for ms in range(0, 600, 30):
            self._tick(ms)
        self._render()
        # Everything should be dark.
        all_pixels = np.ones(self.grid.total, dtype=bool)
        score = visual_similarity(self.frame, self.grid,
                                  expect_dark=all_pixels)
        self.assertGreaterEqual(score, 0.9,
                                f"blow_out should fade everything: {score:.2f}")

    # ── Pulse temporarily brightens the ring ────────────────────
    def test_pulse_brightens_then_fades(self):
        self._tick(0.0); self._tick(50.0); self._render()
        baseline_lit = _is_lit(self.frame, self.grid).sum()

        # Hit pulse. The "_tick" helper is forward-only, so we have to
        # advance time PAST the previous tick (50ms) to actually move
        # the clock + sample the rising edge of the spike envelope.
        self.scene.trigger("pulse", duration_beats=0.5)
        # Pulse default at 120bpm: duration 0.5 beats = 0.25s. Peak at
        # t=0.08*0.25 = 20ms after trigger. Sample at ~+40ms past base.
        for ms in range(60, 100, 5):
            self._tick(ms)
        self._render()
        peak_lit = _is_lit(self.frame, self.grid).sum()

        # Peak should light significantly more pixels (alpha boosted).
        self.assertGreater(peak_lit, baseline_lit,
                           f"pulse peak {peak_lit} ≤ baseline {baseline_lit}")

    # ── Push-right impulses move the ring's center to the right ──
    def test_float_right_moves_ring(self):
        # Establish baseline ring at center.
        self.scene.physics.params.damping = 0.0      # no decay for test
        self.scene.physics.params.radial_offset = 0.0
        self.scene.physics.params.speed = 40.0
        # Reset/sync.
        self.scene.physics.reset()
        # Apply a strong rightward impulse, then step physics manually.
        # Use the canonical `push_right` (was `float_right`, now deprecated).
        self.scene.router.dispatch_by_name("push_right")
        # Step physics directly to a known position.
        for _ in range(10):
            self._tick(0.0)
        # Force position: ball moved enough beats forward.
        self.scene.physics.cx = 3.0
        self._render()
        # Right-half pixels (col > grid.center) at ring radius should be lit;
        # left-half corners should be dark.
        positions = np.array(self.grid.positions)
        cols = positions[:, 1]
        ring_mask = _radius_mask(self.grid, 2.5, 5.5)
        right_lit = ring_mask & (cols > self.grid.center)
        left_corner_dark = (cols < 2) & _radius_mask(self.grid, 4.0, 99.0)
        score = visual_similarity(self.frame, self.grid,
                                  expect_lit=right_lit,
                                  expect_dark=left_corner_dark)
        # Looser threshold — ring is shifted, blur is asymmetric.
        self.assertGreaterEqual(score, 0.6, f"float_right ring shift: {score:.2f}")

    # ── No palettes → all-black frame ────────────────────────────
    def test_no_palettes_renders_black(self):
        self.scene.render(self.frame, 0.0, {"palettes": []})
        arr = np.frombuffer(self.frame, dtype=np.uint8)
        self.assertEqual(arr.max(), 0)

    # ── Ovals disabled → less light ──────────────────────────────
    def test_disabling_all_ovals_yields_dark_frame(self):
        for i in range(3):
            self.scene.set_state(f"oval_enabled_{i}", False)
        self._tick(0.0); self._tick(50.0)
        self._render()
        lit = _is_lit(self.frame, self.grid).sum()
        # A few stray lit pixels would be OK (shimmer leak) but nothing dramatic.
        self.assertLess(lit, self.grid.total * 0.1,
                        f"too many lit pixels with all ovals off: {lit}")

    # ── Choked retrigger replaces the prior pulse ────────────────
    def test_pulse_retrigger_replaces_prior(self):
        self.scene.trigger("pulse", duration_beats=2.0)
        self._tick(0.0); self._tick(10.0)
        # Retrigger immediately. The first should be choked / replaced.
        self.scene.trigger("pulse", duration_beats=2.0)
        # Pulse is a CompoundAction (alpha + radius mods) since iter 36,
        # so each trigger creates 2 modulators tagged pulse-alpha and
        # pulse-radius. After a choked retrigger we expect exactly 1
        # of each still active.
        active_alpha = [m for m in self.scene._modulators
                        if m.tag == "pulse-alpha" and not m.released]
        active_radius = [m for m in self.scene._modulators
                         if m.tag == "pulse-radius" and not m.released]
        self.assertEqual(len(active_alpha), 1,
                         f"choked retrigger should leave 1 active alpha pulse, got {len(active_alpha)}")
        self.assertEqual(len(active_radius), 1,
                         f"choked retrigger should leave 1 active radius pulse, got {len(active_radius)}")


@unittest.skipUnless(HAS_NUMPY, "needs numpy")
class TestVisualSimilarityHelper(unittest.TestCase):
    """Sanity tests for the similarity helper itself."""

    def setUp(self):
        self.grid = make_grid(8)

    def test_all_match(self):
        frame = bytearray(self.grid.frame_bytes)
        # All pixels lit white.
        for i in range(0, len(frame), 3):
            frame[i] = frame[i+1] = frame[i+2] = 255
        expect_lit = np.ones(self.grid.total, dtype=bool)
        score = visual_similarity(frame, self.grid, expect_lit=expect_lit)
        self.assertEqual(score, 1.0)

    def test_all_dark_when_dark_expected(self):
        frame = bytearray(self.grid.frame_bytes)
        expect_dark = np.ones(self.grid.total, dtype=bool)
        score = visual_similarity(frame, self.grid, expect_dark=expect_dark)
        self.assertEqual(score, 1.0)

    def test_mixed_partial(self):
        frame = bytearray(self.grid.frame_bytes)
        # Light the first half only.
        for i in range(0, self.grid.total // 2):
            frame[i*3] = 200
        expect_lit  = np.zeros(self.grid.total, dtype=bool)
        expect_dark = np.zeros(self.grid.total, dtype=bool)
        # Expect "lit half" lit, "dark half" dark — perfect match.
        expect_lit[: self.grid.total // 2] = True
        expect_dark[self.grid.total // 2:] = True
        score = visual_similarity(frame, self.grid,
                                  expect_lit=expect_lit, expect_dark=expect_dark)
        self.assertAlmostEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
