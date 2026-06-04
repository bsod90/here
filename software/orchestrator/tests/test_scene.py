"""Tests for Scene v2 — orchestrates clock + modulators + physics + sequencer + router."""
import time
import unittest

from scene.envelopes import Envelope, Modulator
from scene.events import ImpulseAction, ModulatorAction
from scene.scene import Scene


class MockAnimation:
    """Minimal animation — no numpy, no rendering, just provides state schema."""
    name = "mock"

    NOTE_LANES = [
        {"label": "Lane A", "event": "test_alpha", "params": {}},
        {"label": "Lane B", "event": "test_impulse", "params": {}},
    ]

    def initial_state(self):
        return {
            "alpha": 0.0,
            "radius": 8.0,
            "oval_rotation_0": 0.0,
            "oval_velocity_0": 0.0,
            "palette_idx": 0,
            "palette_target_idx": 0,
            "palette_blend": 0.0,
        }

    def tick(self, state, beat, dt_seconds):
        # Integrate rotation like SynthAnimation does.
        state["oval_rotation_0"] = state.get("oval_rotation_0", 0.0) + \
            state.get("oval_velocity_0", 0.0) * dt_seconds

    def render(self, *args, **kwargs):
        pass


def _build():
    """Construct a Scene with a couple of test events registered on top
    of the default catalog."""
    scn = Scene(MockAnimation(), bpm=120.0)
    # Register a deterministic alpha-additive event for tests.
    scn.router.register("test_alpha", ModulatorAction(
        target="alpha", op="additive",
        peak_value=0.5, duration_beats=1.0,
        ease="instant",        # constant 1.0 → always contributes peak
        tag="alpha",
    ))
    # And an impulse event.
    scn.router.register("test_impulse", ImpulseAction(dx=1.0, dy=0.0))
    return scn


class TestSceneBasics(unittest.TestCase):

    def test_initial_state_from_animation(self):
        scn = _build()
        self.assertEqual(scn.state["alpha"], 0.0)
        self.assertEqual(scn.state["radius"], 8.0)

    def test_lanes_inherited_from_animation(self):
        scn = _build()
        self.assertEqual(len(scn.router.lanes), 2)
        self.assertEqual(scn.router.lanes[0]["label"], "Lane A")

    def test_set_animation_rebinds_router_lanes(self):
        scn = _build()
        class Anim2(MockAnimation):
            NOTE_LANES = [{"label": "Only", "event": "expand"}]
        scn.set_animation(Anim2())
        self.assertEqual(len(scn.router.lanes), 1)
        self.assertEqual(scn.router.lanes[0]["label"], "Only")

    def test_trigger_unknown_returns_false(self):
        scn = _build()
        self.assertFalse(scn.trigger("bogus"))

    def test_trigger_known_runs_action(self):
        scn = _build()
        self.assertTrue(scn.trigger("test_alpha"))
        self.assertEqual(len(scn._modulators), 1)
        self.assertEqual(scn._modulators[0].target, "alpha")


class TestModulatorLifecycle(unittest.TestCase):

    def test_set_state_drops_existing_modulators_on_target(self):
        scn = _build()
        scn.trigger("test_alpha")
        scn.set_state("alpha", 0.7)
        self.assertEqual(scn.state["alpha"], 0.7)
        self.assertFalse(any(m.target == "alpha" for m in scn._modulators))

    def test_modulator_writes_to_state_on_tick(self):
        scn = _build()
        scn.reset_phase()              # set t0 to now (now_beat() ≈ 0)
        scn.trigger("test_alpha")      # additive 0.5 over 1 beat (start ≈ 0)
        scn.tick(0.0)                  # first tick — establish baseline
        scn.tick(100.0)                # 0.1 s → 0.2 beats
        # additive of 0.5 → state alpha should be 0 (base) + 0.5 = 0.5
        self.assertAlmostEqual(scn.state["alpha"], 0.5, places=2)
        # Doesn't accumulate across ticks.
        scn.tick(200.0)
        self.assertAlmostEqual(scn.state["alpha"], 0.5, places=2)

    def test_choked_retrigger_replaces_existing(self):
        scn = _build()
        scn.trigger("test_alpha")
        # Simulate a sequencer event for the same pitch — should choke prior.
        from scene.envelopes import Modulator, Envelope
        env = Envelope(points=[(0.0, 1.0), (1.0, 0.0)])
        m1 = Modulator(target="alpha", op="absolute",
                       base_value=0, peak_value=1, envelope=env,
                       start_beat=0, duration_beats=10, pitch=42, tag="t")
        scn.add_modulator(m1)
        self.assertEqual(sum(1 for m in scn._modulators if m.pitch == 42 and not m.released), 1)
        # Now a second on the same pitch+tag should choke the first.
        m2 = Modulator(target="alpha", op="absolute",
                       base_value=0, peak_value=1, envelope=env,
                       start_beat=1, duration_beats=10, pitch=42, tag="t")
        scn.add_modulator(m2)
        active = [m for m in scn._modulators if m.pitch == 42 and not m.released]
        self.assertEqual(len(active), 1)
        self.assertIs(active[0], m2)

    def test_release_pitch_marks_released(self):
        scn = _build()
        from scene.envelopes import Modulator, Envelope
        env = Envelope(points=[(0.0, 1.0)])
        m = Modulator(target="radius", op="absolute",
                      base_value=0, peak_value=10, envelope=env,
                      start_beat=0, duration_beats=10,
                      release_envelope=Envelope(points=[(0.0, 1.0), (1.0, 0.0)]),
                      release_duration_beats=2.0,
                      pitch=5, tag="r")
        scn.add_modulator(m)
        scn.release_pitch(5, "r", beat=1.0)
        self.assertTrue(m.released)
        self.assertEqual(m.release_beat, 1.0)


class TestPhysicsIntegration(unittest.TestCase):

    def test_impulse_event_moves_ball(self):
        """Push events use a duration-integrated force model. Even with a
        default trigger duration, one tick is enough to register the
        force on the ball's velocity."""
        scn = _build()
        self.assertEqual(scn.physics.vx, 0.0)
        scn.trigger("test_impulse")
        # First tick integrates the force. Use a non-zero dt.
        scn.tick(0.0)
        scn.tick(50.0)
        self.assertGreater(scn.physics.vx, 0.0)

    def test_pull_center_lifecycle_lands_at_zero(self):
        """pull_center sets a duration-bounded lifecycle. After ticking
        past the duration the ball is GUARANTEED at exact (0, 0)."""
        import time
        scn = _build()
        scn.physics.cx = 3.0
        scn.physics.cy = -2.0
        scn.physics.vx = 5.0
        scn.physics.vy = 0.0
        scn.tick(0.0)
        scn.router.dispatch_by_name(
            "pull_center", event_type="note_on",
            params={"duration_beats": 1.0},
        )
        # Advance the clock 1.5 beats past the pull's start.
        clk = scn._clock
        clk._t0_seconds = time.monotonic() - 1.5 * 60.0 / clk.bpm
        scn.tick(1500.0)
        self.assertEqual(scn.physics.cx, 0.0)
        self.assertEqual(scn.physics.cy, 0.0)
        self.assertEqual(scn.physics.vx, 0.0)
        self.assertEqual(scn.physics.vy, 0.0)

    def test_ball_integrated_each_tick(self):
        scn = _build()
        scn.physics.vx = 10.0
        scn.physics.params.damping = 0.0
        scn.reset_phase()
        scn.tick(0.0)
        scn.tick(100.0)   # 0.1s
        # Position moved by vx*dt = 10 * 0.1 = 1.0
        self.assertAlmostEqual(scn.physics.cx, 1.0, places=2)


class TestSnapshot(unittest.TestCase):

    def test_snapshot_has_required_fields(self):
        scn = _build()
        snap = scn.snapshot()
        for k in ("bpm", "beat", "animation", "modulators", "ball",
                  "curves", "physics", "events", "state", "sequencer"):
            self.assertIn(k, snap)

    def test_snapshot_lanes_on_sequencer_for_ui_compat(self):
        scn = _build()
        snap = scn.snapshot()
        self.assertIn("lanes", snap["sequencer"])
        self.assertEqual(len(snap["sequencer"]["lanes"]), 2)


class TestAlignToLoopZero(unittest.TestCase):

    def test_align_returns_correction(self):
        scn = _build()
        scn.sequencer.set_loop_length(4.0)
        clk = scn._clock
        clk.reset_phase()
        clk._t0_seconds -= 0.15   # ~0.3 beats forward at 120bpm
        info = scn.align_to_loop_zero(time.monotonic())
        # Backwards correction toward 0.
        self.assertLess(info["correction_beats"], 0)
        self.assertAlmostEqual(info["correction_beats"], -0.3, delta=0.1)

    def test_align_forward_past_half(self):
        scn = _build()
        scn.sequencer.set_loop_length(4.0)
        clk = scn._clock
        clk.reset_phase()
        clk._t0_seconds -= 1.5    # ~3 beats forward
        info = scn.align_to_loop_zero(time.monotonic())
        self.assertGreater(info["correction_beats"], 0)
        self.assertAlmostEqual(info["correction_beats"], 1.0, delta=0.1)


class TestSequencerIntegration(unittest.TestCase):

    def test_sequencer_drives_router(self):
        """End-to-end: a note in the sequencer fires its lane event,
        which creates a Modulator on the scene."""
        scn = _build()
        scn.sequencer.set_loop_length(4.0)
        scn.sequencer.set_notes([
            {"pitch": 0, "start_beat": 0.0, "length_beats": 1.0},   # test_alpha
        ])
        scn.reset_phase()
        scn.sequencer.play(clock=scn._clock, dispatcher=scn.router)
        # play() fires the immediate note → Modulator created.
        self.assertEqual(len(scn._modulators), 1)
        self.assertEqual(scn._modulators[0].target, "alpha")


class TestEventCatalogPresent(unittest.TestCase):
    """The default catalog should register all the canonical events
    (+ keep the deprecated float_* / push_center aliases for back-
    compat with old saved sequences)."""
    def test_all_events_registered(self):
        scn = _build()
        events = scn.router.events
        for name in (
            # Canonical names
            "expand", "contract", "pulse", "blow_out", "regrow",
            "rotate_cw", "rotate_ccw",
            "pull_center", "push_random",
            "color_palette", "dissolve", "respawn",
            "reset_scene", "fade_out", "border_glow", "floating_particles",
            "meteors", "dust", "flash", "wipe",
            # Deprecated but kept for back-compat (warn on first use).
            "float_center", "push_center",
        ):
            self.assertIn(name, events)


if __name__ == "__main__":
    unittest.main()
