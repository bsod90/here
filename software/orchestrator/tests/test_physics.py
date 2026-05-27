"""Tests for the squishy-ball physics — impulses, walls, squash, center spring."""
import math
import unittest

from scene.physics import BallPhysics, PhysicsParams


def _params(**overrides) -> PhysicsParams:
    base = PhysicsParams(
        speed=25.0,
        radial_offset=0.0,        # no jitter — deterministic for tests
        squishiness=0.5,
        damping=0.8,
        bounce=0.75,
        center_pull=3.0,
        tau_squash=0.25,
        max_velocity=1000.0,       # high default; tests opt in to clamping
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


class TestImpulse(unittest.TestCase):

    def test_impulse_sets_velocity_in_direction(self):
        b = BallPhysics(params=_params())
        b.impulse(1.0, 0.0)
        self.assertAlmostEqual(b.vx, 25.0, places=4)
        self.assertAlmostEqual(b.vy, 0.0, places=4)

    def test_impulse_normalizes_direction(self):
        b = BallPhysics(params=_params())
        b.impulse(3.0, 4.0)        # magnitude 5 → unit (0.6, 0.8)
        self.assertAlmostEqual(b.vx, 25.0 * 0.6, places=4)
        self.assertAlmostEqual(b.vy, 25.0 * 0.8, places=4)

    def test_zero_impulse_is_noop(self):
        b = BallPhysics(params=_params())
        b.impulse(0.0, 0.0)
        self.assertEqual(b.vx, 0.0)
        self.assertEqual(b.vy, 0.0)

    def test_combined_impulses_sum(self):
        b = BallPhysics(params=_params())
        b.impulse(1.0, 0.0)        # right
        b.impulse(0.0, -1.0)       # up (y-axis flipped: up = -y)
        # Two impulses sum: diagonal toward upper-right.
        self.assertAlmostEqual(b.vx, 25.0, places=4)
        self.assertAlmostEqual(b.vy, -25.0, places=4)

    def test_jitter_keeps_direction_close(self):
        b = BallPhysics(params=_params(radial_offset=0.2))
        b.impulse(1.0, 0.0)
        # Should be roughly +x, never strongly off-axis.
        self.assertGreater(b.vx, 0.0)
        self.assertLess(abs(b.vy), 25.0 * math.sin(0.2) + 0.001)


class TestIntegration(unittest.TestCase):

    def test_position_advances_with_velocity(self):
        b = BallPhysics(params=_params(damping=0.0))
        b.vx = 10.0  # 10 LED/s
        b.tick(0.1, bound_x=100, bound_y=100)
        self.assertAlmostEqual(b.cx, 1.0, places=4)

    def test_damping_decays_velocity(self):
        b = BallPhysics(params=_params(damping=5.0))
        b.vx = 10.0
        for _ in range(20):
            b.tick(0.05, bound_x=100, bound_y=100)
        # After 1 s with damping=5, |v| ≈ 10 * exp(-5) ≈ 0.067
        self.assertLess(abs(b.vx), 0.2)

    def test_velocity_clamped_to_max(self):
        b = BallPhysics(params=_params(damping=0.0, max_velocity=10.0))
        b.vx = 100.0
        b.tick(0.01, bound_x=1000, bound_y=1000)
        self.assertLessEqual(abs(b.vx), 10.0 + 1e-6)


class TestWallCollision(unittest.TestCase):

    def test_wall_bounce_inverts_velocity(self):
        b = BallPhysics(params=_params(damping=0.0, bounce=0.5))
        b.vx = 50.0
        b.cx = 9.5
        # Tick takes us to 9.5 + 50*0.1 = 14.5, clamped to 10. v becomes -0.5*50 = -25.
        b.tick(0.1, bound_x=10.0, bound_y=10.0)
        self.assertAlmostEqual(b.cx, 10.0, places=4)
        self.assertAlmostEqual(b.vx, -25.0, places=4)

    def test_wall_collision_injects_squash(self):
        b = BallPhysics(params=_params(damping=0.0, squishiness=0.5, max_velocity=40))
        b.vx = 40.0    # at max
        b.cx = 9.5
        b.tick(0.1, bound_x=10.0, bound_y=10.0)
        # Wall collision now applies squash directly (immediate, visible
        # deformation): x compresses (sx < 0), perpendicular y bulges (sy > 0).
        self.assertLess(b.sx, 0.0)
        self.assertGreater(b.sy, 0.0)

    def test_squash_relaxes_to_zero(self):
        # Force critically-damped (ζ=1) for a deterministic decay check.
        b = BallPhysics(params=_params(damping=0.0, tau_squash=0.1,
                                        squash_damping=1.0))
        b.sx = -0.4
        b.sx_dot = 0.0
        for _ in range(200):
            b.tick(0.005, bound_x=100, bound_y=100)
        self.assertLess(abs(b.sx), 0.005)
        self.assertGreater(b.sx, -0.05)

    def test_squash_wobbles_when_under_damped(self):
        """Under-damped (ζ < 1) → spring overshoots zero before settling."""
        b = BallPhysics(params=_params(damping=0.0, tau_squash=0.1,
                                        squash_damping=0.3))
        b.sx = -0.4
        b.sx_dot = 0.0
        positive_samples = 0
        for _ in range(200):
            b.tick(0.005, bound_x=100, bound_y=100)
            if b.sx > 0:
                positive_samples += 1
        self.assertGreater(
            positive_samples, 5,
            "under-damped squash should overshoot 0 (give some positive samples)",
        )

    def test_y_wall_collision(self):
        b = BallPhysics(params=_params(damping=0.0, bounce=0.5))
        b.vy = -50.0
        b.cy = -9.5
        b.tick(0.1, bound_x=10, bound_y=10)
        self.assertAlmostEqual(b.cy, -10.0, places=4)
        self.assertAlmostEqual(b.vy, 25.0, places=4)


class TestCenterLock(unittest.TestCase):

    def test_center_lock_pulls_back_to_origin(self):
        b = BallPhysics(params=_params(damping=2.0))
        b.cx = 5.0
        b.set_center_lock(True)
        for _ in range(200):
            b.tick(0.01, bound_x=100, bound_y=100)
        # Critically/over-damped spring → returns to ~0.
        self.assertLess(abs(b.cx), 0.6)

    def test_anchor_snaps_when_settled(self):
        b = BallPhysics(params=_params(damping=10.0, center_pull=10.0))
        b.cx = 0.1
        b.cy = 0.1
        b.vx = 0.1
        b.vy = 0.1
        b.set_center_lock(True)
        # First tick should make us "close + slow" enough → starts counting.
        for _ in range(10):
            b.tick(0.01, bound_x=100, bound_y=100)
        # After enough settled frames, ball anchors at exact origin.
        self.assertEqual(b.cx, 0.0)
        self.assertEqual(b.cy, 0.0)
        self.assertEqual(b.vx, 0.0)
        self.assertEqual(b.vy, 0.0)

    def test_anchor_resets_after_impulse(self):
        b = BallPhysics(params=_params(damping=10.0, center_pull=10.0))
        b.set_center_lock(True)
        # Force into settled state.
        for _ in range(10):
            b.tick(0.01, bound_x=100, bound_y=100)
        # Now hit it.
        b.impulse(1.0, 0.0)
        self.assertGreater(b.vx, 0.0)
        # One tick — should NOT immediately re-anchor.
        b.tick(0.01, bound_x=100, bound_y=100)
        self.assertGreater(abs(b.cx) + abs(b.vx), 0.5)


class TestReset(unittest.TestCase):
    def test_reset_zeros_all_state(self):
        b = BallPhysics(params=_params())
        b.cx = 5.0; b.cy = -3.0
        b.vx = 10.0; b.vy = -20.0
        b.sx = 0.3; b.sy = -0.4
        b.sx_dot = 0.5; b.sy_dot = -0.6
        b.reset()
        for v in (b.cx, b.cy, b.vx, b.vy, b.sx, b.sy, b.sx_dot, b.sy_dot):
            self.assertEqual(v, 0.0)


class TestSnapshot(unittest.TestCase):
    def test_snapshot_includes_state(self):
        b = BallPhysics(params=_params())
        b.cx = 1.5
        b.set_center_lock(True)
        snap = b.snapshot()
        self.assertEqual(snap["cx"], 1.5)
        self.assertTrue(snap["center_lock"])
        for k in ("cx", "cy", "vx", "vy", "sx", "sy", "center_lock"):
            self.assertIn(k, snap)


if __name__ == "__main__":
    unittest.main()
