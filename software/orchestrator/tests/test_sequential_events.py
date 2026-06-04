"""Sequential correctness tests for dissolve / respawn / regrow / pull_center.

Each cycle of these events must return the scene to a known clean state
regardless of how many times it's repeated, regardless of overlap with
other events, and regardless of how rapidly they're triggered. Without
these guarantees, a sequence note placed on Dissolve at the end of every
loop drifts into a stuck state after a few iterations.
"""
import time
import unittest

from scene.animations.synth import SynthAnimation
from scene.scene import Scene


def _build():
    anim = SynthAnimation({
        "radius_default": 8.0,
        "radius_min": 3.0, "radius_max": 16.0,
    })
    scn = Scene(anim, bpm=120.0)
    scn.reset_phase()
    return scn


def _set_beat(scn, beat: float) -> None:
    clk = scn._clock
    clk._t0_seconds = time.monotonic() - beat * 60.0 / clk.bpm


def _advance_to(scn, beat: float, step: float = 0.1, time_ms_base: float = 0.0) -> float:
    """Step scn forward in time to absolute `beat`, ticking every `step`
    beats. Returns the engine time_ms after the last tick."""
    cur = scn._clock.now_beat()
    t_ms = time_ms_base
    seconds_per_beat = 60.0 / scn._clock.bpm
    while cur < beat:
        nxt = min(cur + step, beat)
        _set_beat(scn, nxt)
        t_ms += (nxt - cur) * seconds_per_beat * 1000.0
        scn.tick(t_ms)
        cur = nxt
    return t_ms


class TestDissolveCycle(unittest.TestCase):
    """Dissolve always ends with alpha = 0 (scene empty)."""

    def test_single_dissolve_ends_in_floating_cloud(self):
        scn = _build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 6.0)   # well past total duration
        # Dissolve now settles into a floating cloud: visible (alpha up),
        # particles active (dissolve_amount=1), free-drifting (orbit_lock 0).
        self.assertGreater(scn.state["alpha"], 0.5,
                           msg="dissolve should end in a visible floating cloud")
        self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)
        self.assertAlmostEqual(scn.state["dot_orbit_lock"], 0.0, places=2)

    def test_repeated_dissolves_all_end_floating(self):
        """Triggering Dissolve five times in a row at varied beats must
        always settle into the floating cloud — no stuck state."""
        scn = _build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 5.0)
        for k in range(5):
            scn.trigger("dissolve", duration_beats=4.0)
            _advance_to(scn, scn._clock.now_beat() + 4.5)
            self.assertGreater(
                scn.state["alpha"], 0.5,
                msg=f"dissolve iteration {k}: alpha was {scn.state['alpha']:.3f}",
            )
            self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)


class TestRespawnCycle(unittest.TestCase):
    """Respawn always ends in the "fresh" state: alpha=1, dissolve_amount=0,
    no oval rotation/velocity, ball centered."""

    def _assert_fresh(self, scn, msg=""):
        self.assertAlmostEqual(scn.state["alpha"], 1.0, places=2, msg=f"alpha {msg}")
        self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2,
                               msg=f"dissolve_amount {msg}")
        for i in range(3):
            self.assertAlmostEqual(scn.state[f"oval_velocity_{i}"], 0.0,
                                   places=2, msg=f"oval_velocity_{i} {msg}")
        self.assertAlmostEqual(scn.physics.cx, 0.0, places=1, msg=f"cx {msg}")
        self.assertAlmostEqual(scn.physics.cy, 0.0, places=1, msg=f"cy {msg}")

    def test_respawn_from_empty(self):
        scn = _build()
        scn.tick(0.0)
        # Make it empty first.
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 5.0)
        scn.trigger("respawn", duration_beats=4.0)
        _advance_to(scn, scn._clock.now_beat() + 5.0)
        self._assert_fresh(scn, "after respawn-from-empty")

    def test_repeated_dissolve_respawn(self):
        """Dissolve → Respawn cycle repeated multiple times must always
        end with the same fresh state. No state drift between cycles."""
        scn = _build()
        scn.tick(0.0)
        for k in range(4):
            scn.trigger("dissolve", duration_beats=4.0)
            _advance_to(scn, scn._clock.now_beat() + 5.0)
            scn.trigger("respawn", duration_beats=4.0)
            _advance_to(scn, scn._clock.now_beat() + 5.0)
            self._assert_fresh(scn, f"cycle {k}")

    def test_rapid_retrigger(self):
        """Triggering dissolve mid-respawn and vice-versa must still
        converge to the right final state for whichever fires last."""
        scn = _build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 1.0)    # mid-disperse
        scn.trigger("dissolve", duration_beats=4.0)   # retrigger
        _advance_to(scn, 2.0)
        scn.trigger("respawn", duration_beats=4.0)
        _advance_to(scn, 3.0)
        scn.trigger("respawn", duration_beats=4.0)   # retrigger respawn
        _advance_to(scn, scn._clock.now_beat() + 5.0)
        self._assert_fresh(scn, "after rapid retrigger ending on respawn")


class TestRegrowCycle(unittest.TestCase):
    """Regrow scrubs aux state + animates dissolve_amount; doesn't touch
    radius/alpha. After duration, dissolve_amount = 0 and all aux state
    is at defaults."""

    def test_regrow_clears_aux(self):
        scn = _build()
        # Mess things up: spin, dispersed, ball off-center.
        scn.set_state("oval_velocity_1", 5.0)
        scn.set_state("oval_rotation_2", 3.14)
        scn.set_state("dissolve_amount", 0.7)
        scn.physics.cx = 4.0
        scn.physics.cy = -3.0
        scn.physics.vx = 2.0
        scn.tick(0.0)
        scn.trigger("regrow", duration_beats=3.0)
        _advance_to(scn, scn._clock.now_beat() + 4.0)
        # All aux back to clean defaults.
        self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2)
        for i in range(3):
            self.assertAlmostEqual(scn.state[f"oval_velocity_{i}"], 0.0, places=2)
        self.assertAlmostEqual(scn.physics.cx, 0.0, places=1)
        self.assertAlmostEqual(scn.physics.cy, 0.0, places=1)
        self.assertAlmostEqual(scn.physics.vx, 0.0, places=1)

    def test_repeated_regrow_idempotent(self):
        scn = _build()
        scn.tick(0.0)
        for _ in range(5):
            scn.trigger("regrow", duration_beats=2.0)
            _advance_to(scn, scn._clock.now_beat() + 2.5)
            self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2)


class TestPullCenter(unittest.TestCase):
    """Pull Center always lands the ball at exact (0, 0, 0, 0) after its
    configured duration, regardless of starting position."""

    def test_lands_exactly_at_center(self):
        scn = _build()
        scn.physics.cx = 5.0
        scn.physics.cy = -3.5
        scn.physics.vx = 10.0
        scn.physics.vy = -2.0
        scn.tick(0.0)
        scn.trigger("pull_center", duration_beats=2.0)
        _advance_to(scn, scn._clock.now_beat() + 2.5)
        self.assertEqual(scn.physics.cx, 0.0)
        self.assertEqual(scn.physics.cy, 0.0)
        self.assertEqual(scn.physics.vx, 0.0)
        self.assertEqual(scn.physics.vy, 0.0)

    def test_multiple_pulls_back_to_back(self):
        scn = _build()
        for k in range(4):
            scn.physics.cx = (k + 1) * 1.5
            scn.physics.cy = -(k + 1) * 1.0
            scn.tick(0.0)
            scn.trigger("pull_center", duration_beats=1.5)
            _advance_to(scn, scn._clock.now_beat() + 2.0)
            self.assertEqual(scn.physics.cx, 0.0, msg=f"iteration {k}")
            self.assertEqual(scn.physics.cy, 0.0, msg=f"iteration {k}")


class TestRegrowFollowedByExpand(unittest.TestCase):
    """Regression tests for the loop-boundary bug:
    when a sequence ends with Regrow near the end of the loop and the
    next loop starts with Expand at beat 0, Expand must animate cleanly
    to radius_max — Regrow's stale "pin to default" callback must NOT
    stomp the in-flight Expand.

    The user's report (2026-05-24): "first expand on second loop
    expands briefly then shrinks right away without animation".
    """

    def test_regrow_pin_does_not_clobber_active_expand(self):
        """Regrow fires, then before its pin callback runs Expand starts.
        The pin must skip — Expand owns radius now."""
        scn = _build()
        radius_max = float(scn._animation.meta["radius_max"])
        scn.tick(0.0)
        # Fire regrow with duration 2 beats → schedules pin at beat ~1.98.
        scn.trigger("regrow", duration_beats=2.0)
        # Walk forward 1.5 beats so regrow's grow mod is mid-flight.
        _advance_to(scn, 1.5)
        # Now Expand fires (mimics the next loop's first note).
        scn.trigger("expand", duration_beats=4.0)
        # Walk forward past regrow's pin time (beat 1.98) into Expand's
        # midflight. Regrow's pin should detect Expand's mod and bail.
        _advance_to(scn, 3.0)
        # State.radius must be monotonically growing toward radius_max.
        # If the pin clobbered, radius would have snapped back to
        # radius_default (~8) → much smaller than radius_max (~16).
        self.assertGreater(
            scn.state["radius"], 9.0,
            f"expand should be mid-grow, got radius={scn.state['radius']:.2f}",
        )
        # And by the time Expand pins, radius hits the peak.
        _advance_to(scn, 6.0)
        self.assertAlmostEqual(scn.state["radius"], radius_max, places=1)

    def test_regrow_pin_does_fire_when_no_competitor(self):
        """Sanity check: with no other event in flight, Regrow's pin
        still works as designed — final state is radius_default + alpha=1."""
        scn = _build()
        scn.tick(0.0)
        scn.trigger("regrow", duration_beats=2.0)
        _advance_to(scn, 3.0)
        radius_default = float(scn._animation.meta["radius_default"])
        self.assertAlmostEqual(scn.state["radius"], radius_default, places=1)
        self.assertAlmostEqual(scn.state["alpha"], 1.0, places=2)

    def test_loop_boundary_regrow_then_expand(self):
        """Full loop-boundary reproduction: Regrow at beat 14, then loop
        wraps to beat 0 where Expand fires. The Expand at the new loop
        must NOT be clobbered by the stale pin from the previous loop's
        Regrow."""
        scn = _build()
        radius_max = float(scn._animation.meta["radius_max"])
        scn.tick(0.0)
        # Simulate playhead at beat 14, fire regrow with 2-beat duration.
        _advance_to(scn, 14.0)
        scn.trigger("regrow", duration_beats=2.0)
        # Walk through end of loop (beat 16) into next loop's beat 0.5.
        # During [14, 16): regrow growing.
        # At ~15.98: pin scheduled to fire.
        # At ~16 = beat 0 of new loop: Expand fires.
        # The pin's actual fire time depends on tick granularity, but
        # we advance enough that both Expand-on and pin-fire are due.
        _advance_to(scn, 15.5)
        # Now Expand fires (next loop's first note).
        scn.trigger("expand", duration_beats=4.0)
        # Walk past the regrow pin time + into expand mid-flight.
        _advance_to(scn, 18.0)
        # Radius should reflect Expand growing — NOT snapped to default.
        self.assertGreater(
            scn.state["radius"], 10.0,
            f"expand should be mid-grow past regrow pin; "
            f"radius={scn.state['radius']:.2f} (regrow stomped it?)",
        )
        # And by sustain, hits radius_max.
        _advance_to(scn, 21.0)
        self.assertAlmostEqual(scn.state["radius"], radius_max, places=1)


if __name__ == "__main__":
    unittest.main()
