"""OSC server handler tests.

Verifies that the handlers in `OscServer` route correctly to the Scene
without needing a live UDP socket — we call the handlers directly with
the same `(addr, *args)` shape the python-osc dispatcher would use.

Covers the M4L device's wire protocol:
  - /here/scene/note_on/<pitch>     <vel>
  - /here/scene/note_off/<pitch>
  - /here/scene/synth/<key>         <value>
  - /here/scene/physics/<key>       <value>
  - /here/scene/oval/<i>/<key>      <value>
  - /here/scene/palette             <int>
"""
from __future__ import annotations

import os
import sys
import unittest

# Make the orchestrator importable when tests run from repo root.
THIS_DIR = os.path.dirname(__file__)
ORCH_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if ORCH_DIR not in sys.path:
    sys.path.insert(0, ORCH_DIR)

try:
    from pythonosc import dispatcher as _osc_disp  # noqa: F401
    HAS_PYTHONOSC = True
except ImportError:
    HAS_PYTHONOSC = False


def _build_scene():
    """Minimal Scene with the default SynthAnimation, no I/O wiring."""
    from scene.scene import Scene
    from scene.animations.synth import SynthAnimation
    scene = Scene(animation=SynthAnimation({"radius_default": 8.0}))
    # tick(0) seeds initial state so router lanes are populated.
    scene.tick(0.0)
    return scene


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscNoteOnOff(unittest.TestCase):
    """`/here/scene/note_on/<pitch>` should fire the lane's event via the
    router's lane mapping (same path the sequencer uses). pitch 36 (C1)
    maps to NOTE_LANES[0] = Expand."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_note_on_pitch_36_triggers_expand(self):
        self.server._on_note_on("/here/scene/note_on/36", 1.0)
        # Expand creates a modulator on 'radius'.
        radius_mods = [m for m in self.scene._modulators if m.target == "radius"]
        self.assertEqual(len(radius_mods), 1)

    def test_note_on_pitch_38_triggers_rotate_cw(self):
        # pitch 38 → NOTE_LANES[2] = Rotate CW (CompoundAction; first
        # action is a TorqueAction that lands an active torque).
        self.server._on_note_on("/here/scene/note_on/38", 1.0)
        # TorqueAction registers an active torque on the Scene.
        self.assertTrue(len(self.scene._active_torques) > 0)

    def test_note_off_releases_sustain(self):
        # rotate_cw is a sustain event — note_on registers a torque,
        # note_off should clear it.
        self.server._on_note_on("/here/scene/note_on/38", 1.0)
        self.assertTrue(len(self.scene._active_torques) > 0)
        self.server._on_note_off("/here/scene/note_off/38")
        # rotate_cw is decay-on-release (angular friction takes over).
        # The active torque should be gone.
        self.assertEqual(len(self.scene._active_torques), 0)

    def test_out_of_range_pitch_silently_dropped(self):
        # pitch 200 is way past NOTE_LANES — should be a no-op, not raise.
        self.server._on_note_on("/here/scene/note_on/200", 1.0)
        # Below BASE_PITCH should also be a no-op.
        self.server._on_note_on("/here/scene/note_on/10", 1.0)
        # No modulators fired.
        self.assertEqual(self.scene._modulators, [])

    def test_no_velocity_defaults_to_one(self):
        # M4L might omit velocity for an immediate-fire pattern.
        self.server._on_note_on("/here/scene/note_on/36")
        radius_mods = [m for m in self.scene._modulators if m.target == "radius"]
        self.assertEqual(len(radius_mods), 1)

    def test_unparseable_pitch_dropped(self):
        # If somehow the address didn't end in an int, drop the message.
        self.server._on_note_on("/here/scene/note_on/foo", 1.0)
        self.assertEqual(self.scene._modulators, [])


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscSynthKnobs(unittest.TestCase):
    """`/here/scene/synth/<key> <float>` mirrors the admin PUT /api/scene/synth
    contract via the Scene.apply_synth_meta helper."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_radius_min_lands_in_animation_meta(self):
        self.server._on_synth_knob("/here/scene/synth/radius_min", 3.7)
        self.assertAlmostEqual(self.scene._animation.meta["radius_min"], 3.7,
                               places=3)

    def test_brightness_change_persists_in_meta(self):
        self.server._on_synth_knob("/here/scene/synth/brightness", 1.5)
        self.assertAlmostEqual(self.scene._animation.meta["brightness"], 1.5,
                               places=3)

    def test_unparseable_value_dropped(self):
        # Bad value — meta should be unchanged.
        before = dict(self.scene._animation.meta)
        self.server._on_synth_knob("/here/scene/synth/radius_min", "not_a_number")
        self.assertEqual(self.scene._animation.meta, before)

    def test_no_args_dropped(self):
        before = dict(self.scene._animation.meta)
        self.server._on_synth_knob("/here/scene/synth/radius_min")
        self.assertEqual(self.scene._animation.meta, before)


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscPhysicsKnobs(unittest.TestCase):
    """`/here/scene/physics/<key> <float>` mirrors the admin PUT
    /api/scene/physics contract."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_damping_applied(self):
        self.server._on_physics_knob("/here/scene/physics/damping", 1.2)
        self.assertAlmostEqual(self.scene.physics.params.damping, 1.2,
                               places=3)

    def test_bounce_applied(self):
        self.server._on_physics_knob("/here/scene/physics/bounce", 0.5)
        self.assertAlmostEqual(self.scene.physics.params.bounce, 0.5, places=3)

    def test_unknown_key_dropped(self):
        # Key not in PhysicsParams — silently ignored.
        before = self.scene.physics.params.to_dict()
        self.server._on_physics_knob("/here/scene/physics/no_such_key", 1.0)
        self.assertEqual(self.scene.physics.params.to_dict(), before)


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscOvalKnobs(unittest.TestCase):
    """`/here/scene/oval/<i>/<key> <float>` writes oval_<key>_<i> into
    animation meta + live state."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_outer_blur_updates_meta(self):
        self.server._on_oval_knob("/here/scene/oval/0/blur", 4.2)
        self.assertAlmostEqual(self.scene._animation.meta["oval_blur_0"], 4.2,
                               places=3)

    def test_inner_skew_updates_state(self):
        # skew lives in state too (apply_synth_meta mirrors via set_state).
        self.server._on_oval_knob("/here/scene/oval/2/skew", 0.4)
        self.assertAlmostEqual(self.scene.state["oval_skew_2"], 0.4, places=3)

    def test_invalid_oval_index_dropped(self):
        before = dict(self.scene._animation.meta)
        # i=3 is out of range (only 0..2 valid).
        self.server._on_oval_knob("/here/scene/oval/3/blur", 1.0)
        self.assertEqual(self.scene._animation.meta, before)

    def test_unknown_key_dropped(self):
        before = dict(self.scene._animation.meta)
        self.server._on_oval_knob("/here/scene/oval/0/bogus", 1.0)
        self.assertEqual(self.scene._animation.meta, before)


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscPalette(unittest.TestCase):
    """`/here/scene/palette <int>` is an immediate swap (no crossfade)."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_palette_swap(self):
        self.server._on_palette("/here/scene/palette", 2)
        self.assertEqual(int(self.scene.state["palette_idx"]), 2)
        self.assertEqual(int(self.scene.state["palette_target_idx"]), 2)
        self.assertEqual(float(self.scene.state["palette_blend"]), 0.0)


if __name__ == "__main__":
    unittest.main()
