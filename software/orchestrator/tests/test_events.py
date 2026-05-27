"""Tests for the EventRouter — lane mapping, action types, name dispatch."""
import unittest

from scene.envelopes import Envelope, Modulator, default_envelopes
from scene.events import (
    AnchorAction,
    CompoundAction,
    EventRouter,
    ImpulseAction,
    ModulatorAction,
)


class _FakePhysics:
    """Minimal stand-in for BallPhysics — just enough to satisfy RecenterAction."""
    cx: float = 0.0
    cy: float = 0.0
    vx: float = 0.0
    vy: float = 0.0


class FakeSceneAPI:
    """Captures every call the router makes — for assertions."""
    def __init__(self):
        self.modulators: list[Modulator] = []
        self.released: list[tuple] = []   # (pitch, tag, beat)
        self.impulses: list[tuple[float, float]] = []
        self.center_locks: list[bool] = []
        self.state: dict[str, float] = {}
        self.scheduled: list[tuple] = []
        self.beat: float = 0.0
        self.curves: dict[str, Envelope] = default_envelopes()
        self.physics = _FakePhysics()

    def add_modulator(self, mod):
        self.modulators.append(mod)

    def release_pitch(self, pitch, tag, beat):
        self.released.append((pitch, tag, beat))

    def apply_impulse(self, dx, dy):
        self.impulses.append((dx, dy))

    def set_center_lock(self, lock):
        self.center_locks.append(lock)

    def get_state(self, key, default=0.0):
        return self.state.get(key, default)

    def set_state(self, key, value):
        self.state[key] = value

    def apply_torque(self, key, target, torque):
        self.torques = getattr(self, "torques", {})
        self.torques[key] = (target, torque)

    def remove_torque(self, key):
        self.torques = getattr(self, "torques", {})
        self.torques.pop(key, None)

    def clear_torques(self, predicate=None):
        self.torques = getattr(self, "torques", {})
        if predicate is None:
            self.torques.clear()
        else:
            self.torques = {k: v for k, v in self.torques.items()
                            if predicate(k, v[0], v[1])}

    def schedule(self, beats_from_now, fn):
        self.scheduled.append((beats_from_now, fn))

    def current_beat(self):
        return self.beat


def _on(pitch=None, beat=0.0, params=None):
    return {"type": "note_on", "pitch": pitch, "beat": beat,
            "velocity": 1.0, "source": "test", "params": params or {}}


def _off(pitch=None, beat=1.0, params=None):
    return {"type": "note_off", "pitch": pitch, "beat": beat,
            "velocity": 0.0, "source": "test", "params": params or {}}


class TestModulatorAction(unittest.TestCase):

    def test_note_on_creates_modulator(self):
        scn = FakeSceneAPI()
        scn.beat = 2.0    # scene's absolute beat; action reads via current_beat()
        action = ModulatorAction(
            target="alpha", op="additive", peak_value=1.0, duration_beats=1.0,
            curve_id="pulse_default",
        )
        action.on(_on(pitch=3, beat=999.0), scn)   # event.beat is loop-pos, ignored
        self.assertEqual(len(scn.modulators), 1)
        m = scn.modulators[0]
        self.assertEqual(m.target, "alpha")
        self.assertEqual(m.op, "additive")
        self.assertEqual(m.start_beat, 2.0)         # comes from scn.current_beat()
        self.assertEqual(m.pitch, 3)

    def test_absolute_mod_captures_current_state_as_base(self):
        scn = FakeSceneAPI()
        scn.state["radius"] = 11.5
        action = ModulatorAction(
            target="radius", op="absolute", peak_value=20.0, duration_beats=1.0,
        )
        action.on(_on(beat=0.0), scn)
        self.assertEqual(scn.modulators[0].base_value, 11.5)

    def test_explicit_base_value_takes_precedence(self):
        scn = FakeSceneAPI()
        action = ModulatorAction(
            target="radius", op="absolute", peak_value=20.0, duration_beats=1.0,
            base_value=5.0,
        )
        action.on(_on(), scn)
        self.assertEqual(scn.modulators[0].base_value, 5.0)

    def test_lane_params_override_duration_and_peak(self):
        scn = FakeSceneAPI()
        action = ModulatorAction(
            target="alpha", op="additive", peak_value=1.0, duration_beats=1.0,
        )
        action.on(_on(params={"duration_beats": 4.0, "peak": 0.5}), scn)
        m = scn.modulators[0]
        self.assertEqual(m.duration_beats, 4.0)
        self.assertEqual(m.peak_value, 0.5)

    def test_note_off_releases(self):
        scn = FakeSceneAPI()
        action = ModulatorAction(
            target="alpha", op="absolute", peak_value=1.0,
            duration_beats=1.0, release_beats=0.5,
            tag="alpha-tag",
        )
        action.on(_on(pitch=5), scn)
        scn.beat = 1.0
        action.off(_off(pitch=5), scn)
        self.assertEqual(scn.released, [(5, "alpha-tag", 1.0)])

    def test_release_envelope_attached_when_release_beats_positive(self):
        scn = FakeSceneAPI()
        action = ModulatorAction(
            target="alpha", op="absolute", peak_value=1.0,
            duration_beats=1.0, release_beats=0.5,
        )
        action.on(_on(), scn)
        self.assertIsNotNone(scn.modulators[0].release_envelope)

    def test_no_release_envelope_for_oneshot(self):
        scn = FakeSceneAPI()
        # release_curve_id=None → no release tail even if release_beats=0
        # (the action explicitly opts out of release semantics).
        action = ModulatorAction(
            target="alpha", op="additive", peak_value=1.0,
            duration_beats=1.0, release_beats=0.0,
            release_curve_id=None,
        )
        action.on(_on(), scn)
        self.assertIsNone(scn.modulators[0].release_envelope)


class TestImpulseAction(unittest.TestCase):

    def test_note_on_applies_impulse(self):
        scn = FakeSceneAPI()
        action = ImpulseAction(dx=1.0, dy=0.0)
        action.on(_on(), scn)
        self.assertEqual(scn.impulses, [(1.0, 0.0)])

    def test_note_off_is_noop(self):
        scn = FakeSceneAPI()
        action = ImpulseAction(dx=1.0, dy=0.0)
        action.off(_off(), scn)
        self.assertEqual(scn.impulses, [])

    def test_lane_scale_param_multiplies_direction(self):
        scn = FakeSceneAPI()
        action = ImpulseAction(dx=1.0, dy=0.0)
        action.on(_on(params={"scale": 2.0}), scn)
        self.assertEqual(scn.impulses, [(2.0, 0.0)])


class TestAnchorAction(unittest.TestCase):
    def test_on_off_toggles_center_lock(self):
        scn = FakeSceneAPI()
        action = AnchorAction()
        action.on(_on(), scn)
        action.off(_off(), scn)
        self.assertEqual(scn.center_locks, [True, False])


class TestCompoundAction(unittest.TestCase):
    def test_fans_out_to_sub_actions(self):
        scn = FakeSceneAPI()
        a1 = ModulatorAction(
            target="radius", op="absolute", peak_value=30.0, duration_beats=1.0,
        )
        a2 = ModulatorAction(
            target="alpha", op="absolute", peak_value=0.0, duration_beats=1.0,
        )
        compound = CompoundAction(actions=[a1, a2])
        compound.on(_on(), scn)
        self.assertEqual(len(scn.modulators), 2)
        compound.off(_off(), scn)
        self.assertEqual(len(scn.released), 2)


class TestRouter(unittest.TestCase):

    def _build(self):
        scn = FakeSceneAPI()
        router = EventRouter(scn, lanes=[
            {"event": "test_a", "params": {}},
            {"event": "test_b", "params": {"scale": 3.0}},
        ])
        router.register("test_a", ImpulseAction(dx=1.0, dy=0.0))
        router.register("test_b", ImpulseAction(dx=0.0, dy=1.0))
        return scn, router

    def test_pitch_routes_to_event(self):
        scn, router = self._build()
        ok = router.dispatch(_on(pitch=0))
        self.assertTrue(ok)
        self.assertEqual(scn.impulses, [(1.0, 0.0)])

    def test_lane_params_pass_through(self):
        scn, router = self._build()
        router.dispatch(_on(pitch=1))
        # test_b lane has scale=3 → impulse direction (0,1) scaled.
        self.assertEqual(scn.impulses, [(0.0, 3.0)])

    def test_event_params_override_lane_params(self):
        scn, router = self._build()
        # Pitch-1 lane has scale=3.0 by default; event overrides to 5.0.
        router.dispatch(_on(pitch=1, params={"scale": 5.0}))
        self.assertEqual(scn.impulses, [(0.0, 5.0)])

    def test_unknown_pitch_does_not_crash(self):
        scn, router = self._build()
        self.assertFalse(router.dispatch(_on(pitch=99)))

    def test_unknown_event_does_not_crash(self):
        scn, router = self._build()
        router.set_lanes([{"event": "missing", "params": {}}])
        self.assertFalse(router.dispatch(_on(pitch=0)))

    def test_dispatch_by_name(self):
        scn, router = self._build()
        ok = router.dispatch_by_name("test_a")
        self.assertTrue(ok)
        self.assertEqual(scn.impulses, [(1.0, 0.0)])

    def test_dispatch_by_name_with_params(self):
        scn, router = self._build()
        router.dispatch_by_name("test_b", params={"scale": 10.0})
        self.assertEqual(scn.impulses, [(0.0, 10.0)])

    def test_dispatch_by_name_unknown_returns_false(self):
        _, router = self._build()
        self.assertFalse(router.dispatch_by_name("nonexistent"))


if __name__ == "__main__":
    unittest.main()
