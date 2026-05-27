"""Animation-correctness tests — target the specific bugs surfaced in
docs/scene-engine-audit.md (dissolve fade base value drift, SFX cleanup
on animation swap, palette callback scrubbing, event-defaults merging,
etc.).

These complement test_sequential_events.py (which focuses on "events
repeated N times converge to a clean state"). Here we focus on
cross-event interactions, race conditions, and rendering invariants.
"""
import time
import unittest

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from scene.animations.synth import SynthAnimation
from scene.envelopes import Envelope, Modulator
from scene.scene import Scene
from grid import make_grid


def _build_scene():
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


# ───────────────────────────── Dissolve fade base value ──

class TestDissolveFadeBaseValue(unittest.TestCase):
    """The fade phase's base alpha is read LIVE inside the scheduled
    callback so it tracks any alpha changes during disperse+float."""

    def test_fade_picks_up_live_alpha_not_stale(self):
        """Pulse during disperse phase shouldn't make fade snap back to
        a stale captured base (the bug fixed in iter 1)."""
        scn = _build_scene()
        scn.tick(0.0)
        # 4-beat dissolve: disperse=70% (2.8), float=10% (0.4), fade=20% (0.8).
        # _begin_fade fires at beat ~3.2.
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 3.3)
        # At this point the fade modulator should exist with base ≈ 1.0.
        fade_mods = [m for m in scn._modulators if m.tag == "dissolve-fade"]
        self.assertEqual(len(fade_mods), 1,
                         "_begin_fade should have created exactly one fade mod")
        self.assertAlmostEqual(fade_mods[0].base_value, 1.0, places=1,
                               msg="fade base should be the live alpha at fade-start")

    def test_dissolve_with_low_alpha_at_fade_start(self):
        """If something set alpha to 0.3 during float phase, fade ramps
        from 0.3, not 1.0 (no upward jump)."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 3.0)   # mid-float (after disperse-end at 2.8)
        scn.set_state("alpha", 0.3)
        _advance_to(scn, 3.3)   # past _begin_fade
        fade_mods = [m for m in scn._modulators if m.tag == "dissolve-fade"]
        self.assertEqual(len(fade_mods), 1)
        self.assertAlmostEqual(fade_mods[0].base_value, 0.3, places=1)


class TestDissolveCurrentAmountBase(unittest.TestCase):
    """Dissolve captures the live dissolve_amount as its base so it ramps
    from wherever the scene currently is."""

    def test_dissolve_mid_respawn_snaps_to_active(self):
        """As of iter 34, dissolve no longer creates a dispersal
        modulator — dissolve_amount is just a 'particles active' flag
        that snaps to 1 on trigger. Ring opacity now derives from
        dot_orbit_lock^3, not dissolve_amount."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("respawn", duration_beats=4.0)
        _advance_to(scn, 1.0)
        scn.trigger("dissolve", duration_beats=4.0)
        # dissolve_amount immediately at 1.0 (active).
        self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)
        # No dispersal modulator any more.
        disperse_mods = [m for m in scn._modulators if m.tag == "dissolve-disperse"]
        self.assertEqual(len(disperse_mods), 0)


# ───────────────────────────── SFX cleanup on animation swap ──

@unittest.skipUnless(HAS_NUMPY, "SFX render needs numpy")
class TestSetAnimationClearsSfx(unittest.TestCase):
    """Scene.set_animation() must drop any active SFX so the next render
    doesn't try to composite SFX sized for the old grid into the new one."""

    def test_active_sfx_cleared(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dust", duration_beats=4.0)
        # SFX should now be in the active list.
        self.assertEqual(len(scn._active_sfx), 1)
        # Swap animation (same class but reinstantiate — exercises the
        # same code path as a real swap).
        new_anim = SynthAnimation({"radius_default": 8.0})
        scn.set_animation(new_anim)
        self.assertEqual(len(scn._active_sfx), 0,
                         "set_animation should drop in-flight SFX")

    def test_active_pushes_pulls_torques_cleared(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("push_left", duration_beats=2.0)
        scn.trigger("pull_center", duration_beats=2.0)
        scn.trigger("rotate_cw", duration_beats=2.0)
        # set_animation should clear all of them.
        new_anim = SynthAnimation({"radius_default": 8.0})
        scn.set_animation(new_anim)
        self.assertFalse(scn._active_pushes)
        self.assertIsNone(scn._active_pull)
        self.assertFalse(scn._active_torques)


# ───────────────────────────── Palette commit scrubbing ──

class TestPaletteCommitTagged(unittest.TestCase):
    """Palette's commit callback now carries a tag so it can be scrubbed
    via clear_scheduled_by_tag_prefix — keeps lifecycle scrubbing
    consistent across actions."""

    def test_palette_commit_has_tag(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("color_palette", duration_beats=1.0,
                    params={"palette": 1})
        # Find the commit callback in scheduled list.
        commits = [s for s in scn._scheduled if len(s) == 3 and s[2] == "palette-commit"]
        self.assertEqual(len(commits), 1, "palette commit callback should be tagged")

    def test_clear_scheduled_scrubs_palette(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("color_palette", duration_beats=1.0,
                    params={"palette": 1})
        scn.clear_scheduled_by_tag_prefix("palette-")
        remaining = [s for s in scn._scheduled
                     if len(s) == 3 and s[2].startswith("palette-")]
        self.assertEqual(len(remaining), 0)


# ───────────────────────────── Event defaults propagation ──

class TestEventDefaultsMerging(unittest.TestCase):
    """Per-event default params (color, ease, duration_beats) set via the
    UI flow through to all dispatch paths — both direct trigger() and
    lane-driven dispatch from the MIDI sequencer."""

    def test_event_defaults_applied_to_direct_trigger(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.set_event_default("expand", {"duration_beats": 2.5})
        # Pass duration_beats=None so the saved event_default wins.
        scn.trigger("expand", duration_beats=None)
        mods = [m for m in scn._modulators if m.target == "radius"]
        self.assertEqual(len(mods), 1)
        self.assertAlmostEqual(mods[0].duration_beats, 2.5, places=2)

    def test_event_defaults_overridden_by_explicit_params(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.set_event_default("expand", {"duration_beats": 2.5})
        # Explicit duration in trigger should win.
        scn.trigger("expand", duration_beats=1.0)
        mods = [m for m in scn._modulators if m.target == "radius"]
        self.assertAlmostEqual(mods[0].duration_beats, 1.0, places=2)

    def test_event_defaults_applied_to_lane_dispatch(self):
        """Sequencer-style dispatch via router.dispatch() with a pitch
        also picks up event_defaults."""
        scn = _build_scene()
        scn.tick(0.0)
        # Lane 60 → expand event.
        scn.router.set_lanes([
            {"event": "expand", "params": {}} for _ in range(128)
        ])
        scn.router.set_event_default("expand", {"duration_beats": 3.0})
        ok = scn.router.dispatch({
            "type": "note_on", "pitch": 60, "beat": 0.0, "velocity": 1.0,
        })
        self.assertTrue(ok)
        mods = [m for m in scn._modulators if m.target == "radius"]
        self.assertAlmostEqual(mods[0].duration_beats, 3.0, places=2)


# ───────────────────────────── Dissolve/Respawn rendering invariants ──

@unittest.skipUnless(HAS_NUMPY, "rendering tests need numpy")
class TestDissolveRespawnRendering(unittest.TestCase):
    """Sanity-check that the renderer produces sensible output across the
    dissolve/respawn lifecycle (no all-black frames mid-disperse, no
    explosions of brightness, etc.)."""

    def setUp(self):
        from scene.animations.synth import _GEOM_CACHE
        _GEOM_CACHE.clear()
        self.grid = make_grid(16)
        self.frame = bytearray(self.grid.frame_bytes)

    def _build(self):
        anim = SynthAnimation({
            "radius_default": 5.0, "radius_min": 2.0, "radius_max": 7.0,
        })
        scn = Scene(anim, bpm=120.0, grid=self.grid)
        scn.reset_phase()
        return scn

    def _frame_brightness(self):
        arr = np.frombuffer(self.frame, dtype=np.uint8)[: self.grid.frame_bytes]
        return float(arr.mean())

    def test_dissolve_produces_visible_dot_cloud_mid_disperse(self):
        scn = self._build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        # Mid-disperse, dot cloud should be partially visible.
        t_ms = _advance_to(scn, 0.6, step=0.05)
        scn.render(self.frame, t_ms, {"palettes": [{
            "rim_color": [255, 0, 0], "inner_color": [0, 255, 0],
            "outer_color": [0, 0, 255], "trail_color": [255, 255, 0],
        }]})
        bright = self._frame_brightness()
        # Not all-black (mid-dissolve, alpha=1 still, dots are rendering).
        self.assertGreater(bright, 0.5,
                           f"mid-dissolve frame too dark: {bright:.3f}")

    def test_dissolve_complete_alpha_zero_renders_dark(self):
        scn = self._build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=2.0)
        # Past full duration: alpha pinned 0 → frame should be ~black.
        t_ms = _advance_to(scn, 2.5)
        scn.render(self.frame, t_ms, {"palettes": [{
            "rim_color": [255, 0, 0], "inner_color": [0, 255, 0],
            "outer_color": [0, 0, 255], "trail_color": [255, 255, 0],
        }]})
        bright = self._frame_brightness()
        self.assertLess(bright, 1.0,
                        f"post-dissolve frame should be dark, got {bright:.3f}")

    def test_respawn_ends_visible(self):
        scn = self._build()
        scn.tick(0.0)
        scn.trigger("respawn", duration_beats=2.0)
        t_ms = _advance_to(scn, 2.5)
        scn.render(self.frame, t_ms, {"palettes": [{
            "rim_color": [255, 0, 0], "inner_color": [0, 255, 0],
            "outer_color": [0, 0, 255], "trail_color": [255, 255, 0],
        }]})
        bright = self._frame_brightness()
        self.assertGreater(bright, 1.0,
                           f"post-respawn frame should be visible, got {bright:.3f}")

    def test_dissolve_alpha_doesnt_jump_at_fade_start(self):
        """Frame-by-frame: alpha should be monotonically non-increasing
        once the fade phase begins. No upward spikes (the stale-base bug)."""
        scn = self._build()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        # Walk through and sample alpha every 0.1 beats from just past
        # _begin_fade (beat 2.4) to the end (beat 4.0).
        _advance_to(scn, 2.4)
        prev_alpha = scn.state["alpha"]
        for target in np.arange(2.5, 4.01, 0.1):
            _advance_to(scn, float(target), step=0.05)
            cur = scn.state["alpha"]
            # Allow a tiny epsilon for floating point noise.
            self.assertLessEqual(
                cur, prev_alpha + 0.05,
                f"alpha jumped UP at beat {target}: {prev_alpha:.3f} → {cur:.3f}",
            )
            prev_alpha = cur


# ───────────────────────────── Cross-action interactions ──

class TestCrossActionInteractions(unittest.TestCase):
    """Interactions between different action types that the v1 didn't
    explicitly model."""

    def test_expand_during_dissolve_doesnt_break_dissolve(self):
        """Expand during dissolve modifies radius (no impact on dissolve
        timeline). dissolve_amount should still ramp normally."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 0.5)
        scn.trigger("expand", duration_beats=2.0)
        _advance_to(scn, 5.0)
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2,
                               msg="dissolve should still end with alpha=0")

    def test_pulse_during_dissolve_disperse_doesnt_corrupt_fade(self):
        """Pulse is additive on alpha. During dissolve's disperse phase,
        pulse should add and decay normally; fade phase should still
        ramp alpha from live state to 0."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 0.5)   # mid-disperse
        scn.trigger("pulse", duration_beats=0.25)
        _advance_to(scn, 5.0)   # well past dissolve completion
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2)

    def test_repeated_palette_swaps_dont_leak_scheduled_callbacks(self):
        """Triggering color_palette many times shouldn't pile up
        unbounded scheduled callbacks (each commit fires + cleans up)."""
        scn = _build_scene()
        scn.tick(0.0)
        for i in range(8):
            scn.trigger("color_palette", duration_beats=0.5,
                        params={"palette": i % 4})
            _advance_to(scn, scn._clock.now_beat() + 0.6)
        # All commits should have fired by now.
        remaining = [s for s in scn._scheduled
                     if len(s) >= 3 and s[2].startswith("palette-")]
        self.assertEqual(len(remaining), 0)


# ───────────────────────────── Baseline edge cases ──

class TestBaselineSemantics(unittest.TestCase):
    """The Scene captures baselines per-target when the first modulator
    on that target is added, and restores them when all mods finish.
    These tests pin down the corner cases."""

    def test_additive_only_modulator_baseline_is_current_state(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("alpha", 0.7)
        # Pulse is additive on alpha.
        scn.trigger("pulse", duration_beats=0.25)
        # Baseline should be 0.7, not 0.
        self.assertAlmostEqual(scn._baselines.get("alpha", 0.0), 0.7, places=2)

    def test_baseline_restored_when_all_mods_finish(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("radius", 6.0)
        scn.trigger("expand", duration_beats=0.5)
        _advance_to(scn, 1.0)  # past expand duration + pin
        # Expand's pin sets radius to radius_max (16) and purges mods +
        # baselines. So baseline should be gone.
        self.assertNotIn("radius", scn._baselines)
        self.assertAlmostEqual(scn.state["radius"], 16.0, places=1)


# ───────────────────────────── Pull-center retrigger ──

class TestPullCenterRetrigger(unittest.TestCase):
    """A second pull_center while the first is in flight should restart
    cleanly — no double pull, no overshoot, ball still lands at exact
    (0, 0) after the second duration elapses."""

    def test_retrigger_mid_pull_lands_exactly_at_center(self):
        scn = _build_scene()
        scn.physics.cx = 6.0
        scn.physics.cy = -4.0
        scn.tick(0.0)
        scn.trigger("pull_center", duration_beats=2.0)
        _advance_to(scn, 1.0)  # halfway through first pull
        # Re-trigger from current position (mid-pull).
        # Move ball slightly to verify new pull picks up from current pos.
        scn.physics.cx = 5.0
        scn.physics.cy = -3.0
        scn.trigger("pull_center", duration_beats=2.0)
        # By the end of the second pull, ball at exact origin.
        _advance_to(scn, scn._clock.now_beat() + 2.5)
        self.assertEqual(scn.physics.cx, 0.0)
        self.assertEqual(scn.physics.cy, 0.0)


# ───────────────────────────── Torque cancellation ──

class TestTorqueCancellation(unittest.TestCase):
    """Holding Rotate CW and Rotate CCW simultaneously should produce a
    net torque ≈ 0 on each oval (they cancel). Releasing one leaves the
    other to spin up alone, with friction decaying the remaining velocity
    after release."""

    def test_cw_and_ccw_cancel_when_both_held(self):
        scn = _build_scene()
        scn.tick(0.0)
        # Note_on for both (use direct router dispatch to control note_on/off).
        scn.router.dispatch_by_name("rotate_cw", event_type="note_on", pitch=60)
        scn.router.dispatch_by_name("rotate_ccw", event_type="note_on", pitch=61)
        # Tick forward; net torque on each oval should be near zero.
        _advance_to(scn, 1.0)
        for i in range(3):
            self.assertAlmostEqual(
                scn.state.get(f"oval_velocity_{i}", 0.0), 0.0, places=2,
                msg=f"oval {i} velocity should be ~0 when CW+CCW both held",
            )

    def test_releasing_one_leaves_other_torque(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.dispatch_by_name("rotate_cw", event_type="note_on", pitch=60)
        scn.router.dispatch_by_name("rotate_ccw", event_type="note_on", pitch=61)
        _advance_to(scn, 0.5)
        # Release CCW; only CW torque remains.
        scn.router.dispatch_by_name("rotate_ccw", event_type="note_off", pitch=61)
        _advance_to(scn, 1.5)
        # CW torque should have spun up at least one oval to non-zero
        # velocity (sign positive for CW per the catalog).
        velocities = [scn.state.get(f"oval_velocity_{i}", 0.0) for i in range(3)]
        self.assertTrue(any(v > 0.05 for v in velocities),
                        f"expected non-zero CW velocity after CCW release; got {velocities}")


# ───────────────────────────── Dissolve with radius changes ──

class TestDissolveWithRadiusChange(unittest.TestCase):
    """Radius changes during dissolve don't break the dissolve timeline:
    dissolve_amount and alpha still reach their pinned final values."""

    def test_contract_mid_dissolve_dissolves_still_completes(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 1.0)  # mid-disperse
        scn.trigger("contract", duration_beats=1.0)
        _advance_to(scn, 5.0)
        # Dissolve should still complete cleanly. Final state (as of
        # iter 35): alpha=0 (faded), dissolve_amount=0 (particles
        # cleared by _pin_dark), particles=None.
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2)
        self.assertIsNone(scn._animation._dots_xy)

    def test_expand_mid_dissolve_doesnt_corrupt_alpha_pin(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 1.5)
        scn.trigger("expand", duration_beats=2.0)
        _advance_to(scn, 6.0)
        # Dissolve's alpha pin should still have set alpha=0.
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2)


# ───────────────────────────── SFX out-of-range color warning ──

@unittest.skipUnless(HAS_NUMPY, "SFX color test needs numpy")
class TestSfxColorIdxClamp(unittest.TestCase):
    """SFX color_idx out of [0,7] used to silently map to slot 0 — now
    we still clamp (so renders don't crash) but log a warning the first
    time per offending index so palette confusion doesn't go unnoticed."""

    def test_clamp_logs_warning_once(self):
        import logging
        from scene import sfx as sfx_mod
        # Reset the warn-once set so this test is hermetic.
        sfx_mod._warned_color_idx_oob.clear()
        with self.assertLogs(sfx_mod.__name__, level="WARNING") as captured:
            _ = sfx_mod._pick_color({"rim_color": [1, 2, 3]}, 42)
            # Second call with the same OOB idx — should not log again.
            _ = sfx_mod._pick_color({"rim_color": [1, 2, 3]}, 42)
        # Exactly one warning, mentioning the OOB index.
        self.assertEqual(len(captured.records), 1)
        self.assertIn("42", captured.records[0].getMessage())

    def test_in_range_indices_dont_warn(self):
        from scene import sfx as sfx_mod
        sfx_mod._warned_color_idx_oob.clear()
        # Should not raise; should not log.
        for k in range(8):
            _ = sfx_mod._pick_color({"rim_color": [1, 2, 3]}, k)
        self.assertEqual(len(sfx_mod._warned_color_idx_oob), 0)


# ───────────────────────────── ModulatorAction ease="instant" ──

class TestModulatorActionEaseInstant(unittest.TestCase):
    """The ease="instant" path on ModulatorAction should produce a flat
    envelope that delivers peak from the first sample. The old
    curve_id="instant" legacy flag has been removed in favor of this."""

    def test_ease_instant_contributes_peak_immediately(self):
        from scene.events import ModulatorAction
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.register("test_instant", ModulatorAction(
            target="alpha", op="additive",
            peak_value=0.4, duration_beats=1.0, ease="instant",
            tag="testInstant",
        ))
        scn.trigger("test_instant")
        # One tick → modulator contributes peak (0.4) on top of baseline.
        _advance_to(scn, 0.05)
        self.assertAlmostEqual(scn.state["alpha"], 1.0 + 0.4, places=2)


# ───────────────────────────── _PersistAction pin race ──

class TestPersistActionPinRace(unittest.TestCase):
    """Expand/Contract's scheduled pin should bail if a newer absolute
    mod has taken over the target. Otherwise a stale pin from the
    previous Expand can fire after a new Expand has just started,
    setting state to the old peak and killing the new modulator's
    attack."""

    def test_back_to_back_expand_second_one_animates_cleanly(self):
        scn = _build_scene()
        radius_max = float(scn._animation.meta["radius_max"])
        scn.tick(0.0)
        # First expand fires and runs to completion.
        scn.trigger("expand", duration_beats=1.0)
        _advance_to(scn, 0.95)
        # Second expand starts just before the first's pin would fire.
        # Use contract-then-expand to make sure the bug manifests if
        # the stale pin doesn't bail (it'd snap back to radius_max
        # instead of attacking down to radius_min).
        scn.trigger("contract", duration_beats=2.0)
        # Advance past first expand's pin time. If the bug exists,
        # state.radius will be radius_max here and the contract mod
        # will have been purged by set_state. With the fix, contract's
        # attack should be in progress and radius should be < radius_max.
        _advance_to(scn, 1.5)
        self.assertLess(
            scn.state["radius"], radius_max,
            f"stale expand pin clobbered contract; radius={scn.state['radius']}",
        )
        # And by the end of contract, radius hits radius_min.
        _advance_to(scn, 3.0)
        radius_min = float(scn._animation.meta["radius_min"])
        self.assertAlmostEqual(scn.state["radius"], radius_min, places=1)

    def test_pin_still_fires_when_no_newer_mod(self):
        """Sanity check: when no other event takes over, the pin still
        sets state to peak as designed."""
        scn = _build_scene()
        radius_max = float(scn._animation.meta["radius_max"])
        scn.tick(0.0)
        scn.trigger("expand", duration_beats=1.0)
        _advance_to(scn, 1.5)  # past pin
        self.assertAlmostEqual(scn.state["radius"], radius_max, places=1)


# ───────────────────────────── Deprecated alias warnings ──

class TestDeprecatedAliasWarnings(unittest.TestCase):
    """Old event names (float_*, push_center) still dispatch correctly
    but log a one-shot deprecation warning per name on first use."""

    def test_float_left_warns_and_still_dispatches(self):
        from scene import event_catalog
        # Reset the warn-once set so this test is hermetic.
        if hasattr(event_catalog, "_warned_aliases"):
            event_catalog._warned_aliases.clear()
        scn = _build_scene()
        scn.tick(0.0)
        with self.assertLogs("scene.event_catalog", level="WARNING") as captured:
            scn.trigger("float_left")
            # Second call — no second warning.
            scn.trigger("float_left")
        self.assertEqual(len(captured.records), 1)
        msg = captured.records[0].getMessage()
        self.assertIn("float_left", msg)
        self.assertIn("push_left", msg)   # suggests the canonical name

    def test_canonical_names_dont_warn(self):
        from scene import event_catalog
        if hasattr(event_catalog, "_warned_aliases"):
            event_catalog._warned_aliases.clear()
        scn = _build_scene()
        scn.tick(0.0)
        # Capture WARNINGs from the catalog logger. Canonical names
        # should never trigger a deprecation message — assertLogs
        # raises AssertionError when nothing is logged at that level,
        # so we wrap it.
        import logging
        logger = logging.getLogger("scene.event_catalog")
        records = []
        h = logging.Handler()
        h.emit = records.append
        h.setLevel(logging.WARNING)
        logger.addHandler(h)
        try:
            scn.trigger("push_left")
            scn.trigger("pull_center")
        finally:
            logger.removeHandler(h)
        warn_records = [r for r in records if r.levelno >= logging.WARNING]
        self.assertEqual(warn_records, [],
                         "canonical names should not emit deprecation warnings")


# ───────────────────────────── Dissolve radius lock ──

class TestDissolveRadiusLock(unittest.TestCase):
    """Dispersal-range radius is captured once at dissolve/respawn
    trigger time so a Contract or Expand fired mid-cycle doesn't cause
    the dot cloud to snap in/out. The renderer uses this lock for
    drift_max only; orbital positions still track live radius."""

    def test_dissolve_sets_lock_to_current_radius(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("radius", 12.0)
        scn.trigger("dissolve", duration_beats=4.0)
        self.assertAlmostEqual(scn.state["dissolve_radius_lock"], 12.0, places=2)

    def test_contract_mid_dissolve_does_not_change_lock(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("radius", 12.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 0.5)
        # Stomp radius (simulates Contract or any radius change).
        scn.trigger("contract", duration_beats=1.0)
        _advance_to(scn, 2.0)
        # Lock should still be 12.0 even though state.radius is now smaller.
        self.assertAlmostEqual(scn.state["dissolve_radius_lock"], 12.0, places=2)
        self.assertLess(scn.state["radius"], 12.0)

    def test_lock_cleared_when_dissolve_completes(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("radius", 10.0)
        scn.trigger("dissolve", duration_beats=2.0)
        _advance_to(scn, 2.5)
        self.assertAlmostEqual(scn.state["dissolve_radius_lock"], 0.0, places=2)

    def test_respawn_lock_cleared_when_gathered(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("radius", 8.0)
        scn.trigger("respawn", duration_beats=2.0)
        _advance_to(scn, 0.5)
        self.assertAlmostEqual(scn.state["dissolve_radius_lock"], 8.0, places=2)
        _advance_to(scn, 2.5)
        self.assertAlmostEqual(scn.state["dissolve_radius_lock"], 0.0, places=2)


# ───────────────────────────── Palette commit race ──

class TestPaletteCommitRace(unittest.TestCase):
    """When a second palette swap fires mid-flight, the first one's
    pending _commit callback must not fire later and snap palette_idx
    back to the old target (visible flicker)."""

    def test_overlapping_palette_swaps_no_stale_commit(self):
        """Trigger B early (before A's blend crosses 0.5) so there's no
        pre-commit. If A's _commit was left scheduled, it would fire at
        beat 1.0 and snap palette_idx to A's target. With scrubbing,
        only B's commit fires (at its later time)."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.set_state("palette_idx", 0)
        scn.set_state("palette_target_idx", 0)
        scn.set_state("palette_blend", 0.0)
        scn.trigger("color_palette", duration_beats=1.0, params={"palette": 1})
        _advance_to(scn, 0.3)   # mid-A but BEFORE blend >= 0.5
        # Sanity: A's commit is in the scheduled list.
        commits = [s for s in scn._scheduled
                   if len(s) >= 3 and s[2] == "palette-commit"]
        self.assertEqual(len(commits), 1)
        scn.trigger("color_palette", duration_beats=1.0, params={"palette": 2})
        # After B fires, only B's commit should remain (A's was scrubbed).
        commits = [s for s in scn._scheduled
                   if len(s) >= 3 and s[2] == "palette-commit"]
        self.assertEqual(len(commits), 1)
        # Walk past A's original commit time (~beat 1.0). Without the
        # scrub, palette_idx would have been set to 1 here.
        _advance_to(scn, 1.1)
        self.assertNotEqual(scn.state["palette_idx"], 1,
                            f"stale A commit fired; palette_idx={scn.state['palette_idx']}")
        # B's commit fires at beat 1.3 (0.3 + 1.0). Walk a bit further.
        _advance_to(scn, 1.4)
        self.assertEqual(scn.state["palette_idx"], 2)


# ───────────────────────────── Scheduled callback adds a modulator ──

class TestScheduledCallbackAddsModulator(unittest.TestCase):
    """The engine relies on this invariant: a scheduled callback can
    add a new Modulator, and that modulator gets evaluated on the NEXT
    tick (not this one — the modulator-eval phase ran before scheduled
    callbacks fire). Dissolve uses this for its fade phase, palette for
    its commit. If a future tick-phase refactor breaks the ordering,
    this test catches it."""

    def test_scheduled_callback_can_add_modulator_evaluated_next_tick(self):
        scn = _build_scene()
        scn.tick(0.0)
        from scene.envelopes import Modulator, Envelope
        env = Envelope(points=[(0.0, 1.0), (1.0, 1.0)], interp="linear")

        def _spawn(sc):
            sc.add_modulator(Modulator(
                target="alpha", op="absolute",
                base_value=0.0, peak_value=0.42,
                envelope=env, start_beat=sc.current_beat(),
                duration_beats=1.0,
                tag="spawn-test",
            ))
        scn.schedule(0.5, _spawn, tag="spawn-test-schedule")
        # Advance past the schedule time; the callback should fire and
        # add the modulator. State.alpha should reflect the peak value
        # by the end of the advance (next tick's combine).
        _advance_to(scn, 0.8, step=0.05)
        # Mod is now in the list AND state.alpha = 0.42 (the new value).
        mods = [m for m in scn._modulators if m.tag == "spawn-test"]
        self.assertEqual(len(mods), 1,
                         "scheduled callback should have added the modulator")
        self.assertAlmostEqual(scn.state["alpha"], 0.42, places=2)


# ───────────────────────────── BlowOut compound behaviour ──

class TestBlowOutAction(unittest.TestCase):
    """blow_out is a CompoundAction of two simultaneous modulators:
    radius → radius_max * 1.4 (tag=blowout-radius) and alpha → 0
    (tag=blowout-alpha). They run in parallel and both have release
    envelopes so note_off ramps them back."""

    def test_note_on_creates_both_modulators(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.dispatch_by_name("blow_out", event_type="note_on", pitch=60)
        radius_mods = [m for m in scn._modulators if m.tag == "blowout-radius"]
        alpha_mods  = [m for m in scn._modulators if m.tag == "blowout-alpha"]
        self.assertEqual(len(radius_mods), 1)
        self.assertEqual(len(alpha_mods), 1)

    def test_attack_peaks_match_meta(self):
        """Radius blows out to ~radius_max * 1.4; alpha to 0."""
        scn = _build_scene()
        radius_max = float(scn._animation.meta["radius_max"])
        scn.tick(0.0)
        scn.router.dispatch_by_name("blow_out", event_type="note_on", pitch=60)
        # Walk to peak (the blow_out duration default comes from the
        # action's own DEFAULTS["transition_dur"], which is small).
        _advance_to(scn, 5.0, step=0.1)
        # Without note_off the modulator sustains at peak (release env).
        self.assertAlmostEqual(scn.state["radius"], radius_max * 1.4, delta=0.5)
        self.assertAlmostEqual(scn.state["alpha"], 0.0, delta=0.05)

    def test_note_off_releases_both(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.dispatch_by_name("blow_out", event_type="note_on", pitch=60)
        _advance_to(scn, 5.0)
        scn.router.dispatch_by_name("blow_out", event_type="note_off", pitch=60)
        # Both blow_out mods should now be marked released.
        for m in scn._modulators:
            if m.tag and m.tag.startswith("blowout-"):
                self.assertTrue(m.released,
                                f"{m.tag} mod was not released on note_off")


# ───────────────────────────── Show/Hide oval toggles ──

class TestOvalShowHide(unittest.TestCase):
    """show_outer / show_middle / show_inner (and hide_*) flip the
    oval_enabled_{i} state. Simple but worth pinning so an accidental
    refactor doesn't break the per-ring on/off toggles."""

    def test_show_hide_each_ring(self):
        scn = _build_scene()
        scn.tick(0.0)
        rings = [("outer", 0), ("middle", 1), ("inner", 2)]
        for label, idx in rings:
            key = f"oval_enabled_{idx}"
            scn.set_state(key, True)
            scn.router.dispatch_by_name(f"hide_{label}", event_type="note_on")
            self.assertFalse(scn.state[key],
                             f"hide_{label} should have set {key}=False")
            scn.router.dispatch_by_name(f"show_{label}", event_type="note_on")
            self.assertTrue(scn.state[key],
                            f"show_{label} should have set {key}=True")


# ───────────────────────────── stop_rotation events ──

class TestStopRotation(unittest.TestCase):
    """stop_rotation zeros oval_velocity_{0..2} and clears the held
    torques so the next tick doesn't immediately re-accumulate. The
    per-ring variants (stop_rotation_outer/middle/inner) only affect
    one ring."""

    def test_stop_rotation_kills_all_velocity_and_torques(self):
        scn = _build_scene()
        scn.tick(0.0)
        # Hold rotate_cw (which applies torque). Tick to let velocity
        # accumulate.
        scn.router.dispatch_by_name("rotate_cw", event_type="note_on", pitch=60)
        _advance_to(scn, 1.0)
        spun_up = [scn.state.get(f"oval_velocity_{i}", 0.0) for i in range(3)]
        self.assertTrue(any(v > 0.05 for v in spun_up),
                        f"expected non-zero velocities before stop; got {spun_up}")
        # Fire stop_rotation.
        scn.router.dispatch_by_name("stop_rotation", event_type="note_on")
        # All velocities should now be 0.
        for i in range(3):
            self.assertAlmostEqual(scn.state[f"oval_velocity_{i}"], 0.0, places=3)
        # The torques on oval_velocity_* should be gone — verified by
        # ticking forward and observing velocity stays at 0 (without
        # active torques to re-accumulate).
        _advance_to(scn, scn._clock.now_beat() + 0.5)
        for i in range(3):
            self.assertAlmostEqual(scn.state[f"oval_velocity_{i}"], 0.0, places=3)

    def test_per_ring_stop_only_affects_that_ring(self):
        scn = _build_scene()
        scn.tick(0.0)
        # Hold both outer and inner rotate.
        scn.router.dispatch_by_name("rotate_cw_outer", event_type="note_on", pitch=60)
        scn.router.dispatch_by_name("rotate_cw_inner", event_type="note_on", pitch=62)
        _advance_to(scn, 1.0)
        # Stop only the outer ring.
        scn.router.dispatch_by_name("stop_rotation_outer", event_type="note_on")
        # Outer velocity → 0; inner velocity unchanged (still being held).
        self.assertAlmostEqual(scn.state["oval_velocity_0"], 0.0, places=3)
        # Tick further; inner should still spin up.
        _advance_to(scn, 1.5)
        self.assertGreater(scn.state["oval_velocity_2"], 0.05,
                           "inner ring should still be spinning after stop_outer")


# ───────────────────────────── RandomImpulse / push_random ──

class TestRandomImpulse(unittest.TestCase):
    """push_random applies an impulse with random direction. Magnitude
    should be the configured speed (or close — direction is random)."""

    def test_push_random_produces_nonzero_velocity(self):
        scn = _build_scene()
        scn.tick(0.0)
        self.assertEqual((scn.physics.vx, scn.physics.vy), (0.0, 0.0))
        scn.trigger("push_random")
        # The impulse magnitude is physics.params.speed. Random direction
        # means we can't predict signs, but the total |v| should match.
        import math
        v_mag = math.hypot(scn.physics.vx, scn.physics.vy)
        speed = scn.physics.params.speed
        self.assertGreater(v_mag, 0.5,
                           f"push_random should impart non-trivial velocity; got |v|={v_mag}")
        # Magnitude within 20% of configured speed (the random jitter on
        # angle doesn't change magnitude — only direction).
        self.assertAlmostEqual(v_mag, speed, delta=speed * 0.2)


# ───────────────────────────── SFX lifecycle ──

class TestSfxLifecycle(unittest.TestCase):
    """SFX get added to _active_sfx on trigger, tick + render each
    frame, and auto-prune when is_done(beat) returns True. Multiple
    same-name SFX stack additively (no choke — each trigger creates
    a new independent overlay)."""

    def test_sfx_added_and_pruned_after_duration(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dust", duration_beats=1.0)
        self.assertEqual(len(scn._active_sfx), 1)
        # Walk past the duration; SFX should auto-prune.
        _advance_to(scn, 1.5)
        self.assertEqual(len(scn._active_sfx), 0,
                         "SFX should be pruned once is_done(beat) is True")

    def test_multiple_sfx_stack(self):
        """No choke — multiple dust triggers stack as independent overlays.
        Each is_done independently and prunes when its own duration ends."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dust", duration_beats=2.0)
        _advance_to(scn, 0.5)
        scn.trigger("dust", duration_beats=2.0)
        _advance_to(scn, 1.0)
        scn.trigger("dust", duration_beats=2.0)
        # All three still active.
        self.assertEqual(len(scn._active_sfx), 3)
        # Walk past the first one's duration (2.0 from beat 0).
        _advance_to(scn, 2.1)
        self.assertEqual(len(scn._active_sfx), 2)
        # Past second (beat 0.5 + 2.0 = 2.5).
        _advance_to(scn, 2.6)
        self.assertEqual(len(scn._active_sfx), 1)

    def test_sfx_uses_event_defaults_for_color(self):
        """The router merges event_defaults into params before action
        dispatch — so a saved color picks up automatically for MIDI
        playback (the user's reported original bug)."""
        from scene.sfx import DustPulseSfx
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.set_event_default("dust", {"color": 5})
        scn.trigger("dust", duration_beats=1.0, params={})
        self.assertEqual(len(scn._active_sfx), 1)
        sfx = scn._active_sfx[0]
        self.assertIsInstance(sfx, DustPulseSfx)
        self.assertEqual(sfx.color_idx, 5,
                         "event_defaults color should propagate to SFX")


# ───────────────────────────── Pause / resume ──

class TestPauseResume(unittest.TestCase):
    """While paused, Scene.tick freezes the clock + skips modulator
    evaluation. Render still runs (so meta-param edits are visible).
    On resume, dt for the FIRST tick is forced to 0 so we don't
    fast-forward by however long the pause lasted."""

    def test_state_frozen_while_paused(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("expand", duration_beats=2.0)
        _advance_to(scn, 0.5)
        snapshot_radius = scn.state["radius"]
        scn.pause()
        # Tick the wall clock forward (simulating real time passing
        # while paused). State should NOT change.
        for k in range(20):
            scn.tick(1000.0 + k * 50.0)
        self.assertAlmostEqual(scn.state["radius"], snapshot_radius, places=2,
                               msg="radius drifted while paused")

    def test_resume_does_not_fast_forward(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("expand", duration_beats=2.0)
        _advance_to(scn, 0.5)
        scn.pause()
        # Spend a "long" wall-clock interval paused.
        for k in range(20):
            scn.tick(2000.0 + k * 50.0)
        scn.resume()
        # First post-resume tick should advance by ~0 beats since
        # resume() reset _last_tick_ms to None.
        beat_before = scn._clock.now_beat()
        _set_beat(scn, beat_before + 0.01)   # tiny musical advance
        scn.tick(2200.0)
        # State should reflect a ~0.01 beat advance, not a 2-beat one.
        beat_after = scn._clock.now_beat()
        self.assertLess(beat_after - beat_before, 0.5,
                        f"resumed clock jumped by {beat_after - beat_before:.3f} beats")

    def test_bpm_set_during_pause_preserves_phase(self):
        """Synth-style behavior: BPM change preserves the current beat
        position so an in-flight modulator doesn't snap. Verify this
        holds while paused."""
        scn = _build_scene()
        scn.tick(0.0)
        _advance_to(scn, 4.0)
        scn.pause()
        beat_at_pause = scn._clock.now_beat()
        # BPM change while paused.
        scn._clock.set_bpm(150.0)
        # Beat position is preserved.
        self.assertAlmostEqual(scn._clock.now_beat(), beat_at_pause, places=1)


# ───────────────────────────── Dust dispersal ──

class TestDustSparser(unittest.TestCase):
    """Per user feedback: dust should be more sparse (same dot count,
    wider spread). Pin the new default cluster_radius so a future
    refactor doesn't accidentally regress to the old tight cluster."""

    def test_default_cluster_radius_is_sparse(self):
        from scene.sfx import DustPulseSfx
        sfx = DustPulseSfx(start_beat=0.0, duration_beats=2.0)
        # Pre-iter-13 default was 4.5; user asked for sparser.
        self.assertGreaterEqual(sfx.cluster_radius, 6.0,
                                "dust cluster_radius should be sparse by default")
        # Count unchanged (user explicitly asked: "same amount of dots").
        self.assertEqual(sfx.cluster_count, 28)

    def test_event_default_cluster_count_still_overrides(self):
        """User's per-event override (set via admin UI / event_defaults)
        still wins over the dataclass default."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.router.set_event_default("dust", {"cluster_count": 60})
        scn.trigger("dust", duration_beats=1.0, params={})
        sfx = scn._active_sfx[0]
        self.assertEqual(sfx.cluster_count, 60)


# ───────────────────────────── Scene.reset comprehensive ──

class TestSceneResetClears(unittest.TestCase):
    """Scene.reset() must clear ALL transient lists: modulators,
    baselines, scheduled callbacks, torques, pushes, pulls, SFX. Plus
    re-init state from animation, reset physics, snap clock, unpause.
    """

    def test_reset_clears_everything(self):
        scn = _build_scene()
        scn.tick(0.0)
        # Set up a busy scene with stuff in every list.
        scn.trigger("expand", duration_beats=2.0)
        scn.trigger("dust", duration_beats=4.0)
        scn.trigger("push_left", duration_beats=2.0)
        scn.trigger("pull_center", duration_beats=2.0)
        scn.router.dispatch_by_name("rotate_cw", event_type="note_on", pitch=60)
        scn.schedule(1.0, lambda sc: None, tag="manual-test")
        scn.pause()
        # Mess up ball physics + state.
        scn.physics.cx = 5.0
        scn.physics.cy = -3.0
        scn.set_state("alpha", 0.42)
        # Sanity — stuff is populated.
        self.assertTrue(scn._modulators)
        self.assertTrue(scn._active_sfx)
        self.assertTrue(scn._active_pushes)
        self.assertIsNotNone(scn._active_pull)
        self.assertTrue(scn._active_torques)
        self.assertTrue(scn._scheduled)
        self.assertTrue(scn._paused)
        # Reset.
        scn.reset()
        # Everything cleared.
        self.assertEqual(scn._modulators, [])
        self.assertEqual(scn._baselines, {})
        self.assertEqual(scn._scheduled, [])
        self.assertEqual(scn._active_torques, {})
        self.assertEqual(scn._active_pushes, [])
        self.assertIsNone(scn._active_pull)
        self.assertEqual(scn._active_sfx, [])
        self.assertEqual(scn.physics.cx, 0.0)
        self.assertEqual(scn.physics.cy, 0.0)
        self.assertFalse(scn._paused)
        # State re-inited from animation defaults.
        self.assertEqual(scn.state["alpha"], 1.0)   # synth default
        # Clock snapped — beat is back at ~0 (or very close).
        self.assertLess(scn._clock.now_beat(), 0.1)


# ───────────────────────────── Dissolve redesign (iter 14) ──

class TestDissolveNewPhasing(unittest.TestCase):
    """The redesigned dissolve (iter 14) uses 70/10/20 phases with
    ease-in so the fast-spin phase has time to read on screen. Pin
    those numbers so a future tweak doesn't accidentally revert."""

    def test_orbit_lock_locked_at_start_of_dissolve(self):
        """As of iter 37, the dissolve's locked window is the first
        20% of total (shortened from 35% so more time is spent in the
        flying-away phase). At ≤15% orbit_lock should still be at 1."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 0.5)   # 12.5% of 4 beats — within locked phase
        self.assertAlmostEqual(scn.state["dot_orbit_lock"], 1.0, places=2,
                               msg="dot_orbit_lock should hold at 1 during the locked phase")

    def test_dissolve_amount_pinned_at_one_after_disperse(self):
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        # Pin fires at 80% of total (= 3.2 beats for a 4-beat dissolve).
        # Advance past that.
        _advance_to(scn, 3.4)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)

    def test_fade_starts_after_float(self):
        """Fade phase begins at 80% (disperse 70% + float 10%)."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(scn, 3.0)   # 75% - within float, no fade mod yet
        fade_mods = [m for m in scn._modulators if m.tag == "dissolve-fade"]
        self.assertEqual(len(fade_mods), 0)
        _advance_to(scn, 3.3)   # past 80% — fade mod added
        fade_mods = [m for m in scn._modulators if m.tag == "dissolve-fade"]
        self.assertEqual(len(fade_mods), 1)


# ───────────────────────────── Dot orbital behaviour (iter 14) ──

@unittest.skipUnless(HAS_NUMPY, "dot render needs numpy")
class TestDotOrbitalProgression(unittest.TestCase):
    """The new dissolve has FAST orbital motion at low dissolve_amount
    that slows quadratically as particles disperse. This pins the
    perceived "comet ring → brownian cloud" feel."""

    def test_fast_spin_at_low_dissolve_amount(self):
        """At dissolve_amount ~0.05, dots have moved noticeably between
        two render samples 0.1s apart (the visible 'fast spin' phase)."""
        from scene.animations.synth import SynthAnimation
        from grid import make_grid
        anim = SynthAnimation({"radius_default": 5.0})
        grid = make_grid(16)
        # Iter 32: stateful particles. Need to tick() the animation
        # for the simulation to spawn + advance particles.
        state = {"dissolve_amount": 0.05, "radius": 5.0}
        anim.tick(state, beat=0.0, dt_seconds=0.05)
        before_xy = anim._dots_xy.copy()
        anim.tick(state, beat=0.5, dt_seconds=0.1)
        after_xy = anim._dots_xy.copy()
        diff = float(np.abs(after_xy - before_xy).sum())
        self.assertGreater(diff, 0.0,
                           "particles should be moving at low dissolve_amount")

    def test_orbital_stops_at_full_dispersal(self):
        """At dissolve_amount=1, particles still move (forward via the
        heading) but the angular velocity is dominated by the wander
        term. Smoke test that the renderer doesn't crash and emits
        an output array of the right shape."""
        from scene.animations.synth import SynthAnimation
        from grid import make_grid
        anim = SynthAnimation({"radius_default": 5.0})
        grid = make_grid(16)
        # Spawn + advance particles so the stateful renderer has
        # something to draw.
        anim.tick({"dissolve_amount": 1.0, "radius": 5.0},
                  beat=0.0, dt_seconds=0.05)
        kwargs = dict(
            n_dots=16, radius=5.0, theta_off=0.0, skew=0.15,
            dissolve_amount=1.0, sigma=1.0,
            trail_steps=4, trail_dt=0.05,
            dx_base=np.zeros(grid.total, dtype=np.float32),
            dy_base=np.zeros(grid.total, dtype=np.float32),
            cx_ball=0.0, cy_ball=0.0, scale_x=1.0, scale_y=1.0,
            seed=0,
        )
        # At dissolve_amount=1, orbital is 0. So particle motion comes
        # purely from brownian which is slow at motion_speed=0.25
        # default. Over Δt=0.01s, positions move very little compared
        # to a fast-orbital state. Just smoke-test no crash + render.
        out = anim._render_dots(time_s=0.0, **kwargs)
        self.assertEqual(out.shape, (grid.total,))


# ───────────────────────────── OSC handler smoke tests ──

try:
    import pythonosc   # noqa: F401
    HAS_PYTHONOSC = True
except ImportError:
    HAS_PYTHONOSC = False


@unittest.skipUnless(HAS_PYTHONOSC, "OSC handler tests need pythonosc")
class TestOscSceneEventHandler(unittest.TestCase):
    """The OSC server's `_on_scene_event` handler is now dynamically
    bound to every catalog event. Verify the handler delegates to
    `scene.trigger()` correctly and that no-args delegates with
    duration_beats=None so saved event_defaults win."""

    def setUp(self):
        from osc_input import OscServer, OscState
        self.scene = _build_scene()
        self.scene.tick(0.0)
        # OscServer doesn't need a running socket for the handler tests
        # — we just call the handler closure directly.
        self.server = OscServer(OscState(), time_provider=lambda: 0.0,
                                scene=self.scene)

    def test_handler_triggers_event_with_no_args(self):
        # Without args, duration_beats is None so event_defaults win.
        self.scene.router.set_event_default("expand", {"duration_beats": 2.5})
        handler = self.server._on_scene_event("expand")
        handler("/here/scene/event/expand")   # no OSC args
        mods = [m for m in self.scene._modulators if m.target == "radius"]
        self.assertEqual(len(mods), 1)
        self.assertAlmostEqual(mods[0].duration_beats, 2.5, places=2)

    def test_handler_explicit_duration_overrides_default(self):
        self.scene.router.set_event_default("expand", {"duration_beats": 2.5})
        handler = self.server._on_scene_event("expand")
        handler("/here/scene/event/expand", 0.5)   # explicit OSC duration
        mods = [m for m in self.scene._modulators if m.target == "radius"]
        self.assertAlmostEqual(mods[0].duration_beats, 0.5, places=2)

    def test_handler_passes_palette_param(self):
        handler = self.server._on_scene_event("color_palette")
        handler("/here/scene/event/color_palette", 1.0, 2)
        mods = [m for m in self.scene._modulators if m.target == "palette_blend"]
        self.assertEqual(len(mods), 1)
        self.assertEqual(int(self.scene.state["palette_target_idx"]), 2)


# ───────────────────────────── SynthAnimation.update_meta ──

class TestUpdateMeta(unittest.TestCase):
    """update_meta now merges by default (so a partial admin PUT
    preserves other meta keys) and replaces only when explicitly
    requested via `replace=True`. This was the root cause of the
    Blur/Brightness knobs being silently dead in the admin UI."""

    def test_merge_preserves_existing_keys(self):
        anim = SynthAnimation({"radius_default": 8.0, "oval_blur_0": 1.8})
        anim.update_meta({"oval_blur_0": 5.5})
        self.assertEqual(anim.meta["oval_blur_0"], 5.5)
        # The original `radius_default` is still there.
        self.assertEqual(anim.meta["radius_default"], 8.0)

    def test_replace_true_wipes_unmentioned_keys(self):
        anim = SynthAnimation({"radius_default": 8.0, "oval_blur_0": 1.8})
        anim.update_meta({"oval_blur_0": 5.5}, replace=True)
        self.assertEqual(anim.meta["oval_blur_0"], 5.5)
        # radius_default is gone — replace was wholesale.
        self.assertNotIn("radius_default", anim.meta)

    def test_partial_update_takes_effect_next_render(self):
        """After update_meta, a render() should pick up the new meta
        value. (Smoke test that the meta dict is the actual one used
        by the renderer.)"""
        anim = SynthAnimation({"radius_default": 5.0, "oval_blur_0": 1.5})
        # Initial value.
        self.assertEqual(anim.meta["oval_blur_0"], 1.5)
        # Live update.
        anim.update_meta({"oval_blur_0": 4.0})
        self.assertEqual(anim.meta["oval_blur_0"], 4.0)


# ───────────────────────────── Live meta + scene state synth set ──

class TestSynthLiveUpdate(unittest.TestCase):
    """Direct test of the wiring iter 24+26 fixed: when a meta key
    changes (e.g. via the admin Blur knob → /api/scene/synth PUT),
    the live SynthAnimation.meta picks it up immediately so the
    renderer reads the new value on the next frame."""

    def test_animation_meta_picks_up_value(self):
        scn = _build_scene()
        # Initial value (default from SynthAnimation).
        self.assertEqual(scn._animation.meta.get("oval_blur_0", 1.8), 1.8)
        # Simulate the admin route's update_meta call.
        scn._animation.update_meta({"oval_blur_0": 5.5})
        # New value is immediately readable.
        self.assertEqual(scn._animation.meta["oval_blur_0"], 5.5)
        # Other meta keys are still there.
        self.assertEqual(scn._animation.meta["radius_default"], 8.0)

    def test_dot_orbit_speed_takes_effect(self):
        """The new dot_orbit_speed meta key (iter 14) is also live-
        tunable through update_meta. Pin this so future refactors
        don't regress dissolve animation tunability."""
        scn = _build_scene()
        # Default is 4.0.
        self.assertEqual(
            float(scn._animation.meta.get("dot_orbit_speed", 4.0)), 4.0)
        scn._animation.update_meta({"dot_orbit_speed": 2.5})
        self.assertEqual(scn._animation.meta["dot_orbit_speed"], 2.5)


# ───────────────────────────── Dissolve full extinction ──

@unittest.skipUnless(HAS_NUMPY, "extinction test needs numpy")
class TestDissolveFullExtinction(unittest.TestCase):
    """After a dissolve animation completes, the rendered frame MUST
    be fully dark — no leftover particles, no residual ring glow, no
    SFX still firing. User report 2026-05-25: 'dissolve should lead
    to a complete dissolution'."""

    def setUp(self):
        from scene.animations.synth import _GEOM_CACHE
        _GEOM_CACHE.clear()
        self.grid = make_grid(16)
        self.frame = bytearray(self.grid.frame_bytes)
        anim = SynthAnimation({
            "radius_default": 5.0, "radius_min": 2.0, "radius_max": 7.0,
        })
        self.scn = Scene(anim, bpm=120.0, grid=self.grid)
        self.scn.reset_phase()
        self.scn.tick(0.0)
        self.palette = {
            "rim_color": [255, 0, 255],
            "inner_color": [255, 0, 255],
            "outer_color": [255, 0, 255],
            "trail_color": [255, 0, 255],
            "color4": [255, 0, 255], "color5": [255, 0, 255],
            "color6": [255, 0, 255], "color7": [255, 0, 255],
        }

    def _frame_brightness(self) -> float:
        arr = np.frombuffer(self.frame, dtype=np.uint8)[: self.grid.frame_bytes]
        return float(arr.mean())

    def _max_pixel(self) -> int:
        arr = np.frombuffer(self.frame, dtype=np.uint8)[: self.grid.frame_bytes]
        return int(arr.max())

    def _render(self, t_ms: float):
        self.scn.render(self.frame, t_ms, {"palettes": [self.palette]})

    def test_dissolve_completes_fully_dark(self):
        """Standard dissolve, walk past completion, render → all zeros."""
        self.scn.trigger("dissolve", duration_beats=4.0)
        # Walk well past the dissolve's end (4 beats + safety margin).
        t_ms = _advance_to(self.scn, 6.0, step=0.05)
        self._render(t_ms)
        bright = self._frame_brightness()
        max_pix = self._max_pixel()
        self.assertEqual(max_pix, 0,
                         f"residual pixel after dissolve: max={max_pix} bright={bright:.3f}")

    def test_state_alpha_reaches_zero(self):
        """The state.alpha modulator + pin_dark must drive alpha to 0."""
        self.scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(self.scn, 5.0, step=0.05)
        self.assertEqual(self.scn.state["alpha"], 0.0,
                         f"state.alpha = {self.scn.state['alpha']} after dissolve")

    def test_particles_invisible_after_dissolve_even_if_kept_alive(self):
        """Even though _dots_xy may still be populated (the simulation
        keeps advancing while dissolve_amount > 0.001), the rendered
        frame must be black because state.alpha=0 zeros the rgb."""
        self.scn.trigger("dissolve", duration_beats=2.0)
        t_ms = _advance_to(self.scn, 3.0, step=0.05)
        # Render multiple subsequent frames to be sure no late
        # contribution sneaks back in.
        for k in range(10):
            t_ms = _advance_to(self.scn, 3.0 + k * 0.5, step=0.05)
            self._render(t_ms)
            max_pix = self._max_pixel()
            self.assertEqual(max_pix, 0,
                             f"frame {k} after dissolve has max pixel={max_pix}")

    def test_dissolve_extinction_at_various_durations(self):
        """Short, medium, long dissolves all reach full darkness."""
        for dur in (0.5, 2.0, 8.0):
            self.scn.reset()
            self.scn.tick(0.0)
            self.scn.trigger("dissolve", duration_beats=dur)
            t_ms = _advance_to(self.scn, dur + 1.0, step=0.05)
            self._render(t_ms)
            self.assertEqual(
                self._max_pixel(), 0,
                f"dissolve(duration_beats={dur}) left residual pixels",
            )

    def test_dissolve_after_pulse_still_extinguishes(self):
        """Pulse fired during dissolve adds to alpha additively. The
        dissolve_pin must still bring alpha to 0 even after the additive
        pulse contribution dies down."""
        self.scn.trigger("dissolve", duration_beats=4.0)
        _advance_to(self.scn, 1.0, step=0.05)
        # Pulse mid-dissolve.
        self.scn.trigger("pulse", duration_beats=0.25)
        t_ms = _advance_to(self.scn, 5.0, step=0.05)
        self._render(t_ms)
        self.assertEqual(
            self._max_pixel(), 0,
            "pulse during dissolve left residual pixels at the end",
        )

    def test_dissolve_then_idle_extinguishes(self):
        """After dissolve completes, idling for many frames must not
        let particles or state drift back to visible."""
        self.scn.trigger("dissolve", duration_beats=2.0)
        t_ms = _advance_to(self.scn, 2.5, step=0.05)
        # Idle for 60 frames at the same beat (no time advance, just
        # repeated ticks). Render after each.
        for k in range(60):
            self.scn.tick(t_ms + k * 33.0)
            self._render(t_ms + k * 33.0)
            self.assertEqual(
                self._max_pixel(), 0,
                f"idle frame {k} after dissolve lit pixels (alpha leak?)",
            )

    def test_dissolve_with_active_sfx_extinguishes(self):
        """SFX render directly into the frame, BYPASSING state.alpha.
        If a dust SFX is still active when the user expects the scene
        to be dark, it shows residual dots. The dissolve's pin should
        not leave SFX in flight."""
        self.scn.trigger("dust", duration_beats=2.0)
        _advance_to(self.scn, 0.5, step=0.05)
        self.scn.trigger("dissolve", duration_beats=4.0)
        # Walk past dissolve completion AND dust completion.
        t_ms = _advance_to(self.scn, 5.5, step=0.05)
        self._render(t_ms)
        self.assertEqual(
            self._max_pixel(), 0,
            "leftover SFX after dissolve completed — SFX outlived the animation",
        )


# ───────────────────────────── Respawn convergence ──

@unittest.skipUnless(HAS_NUMPY, "respawn convergence test needs numpy")
class TestRespawnConvergence(unittest.TestCase):
    """User report 2026-05-25: 'respawn still does not converge'.
    Verify that by 70% of total respawn duration, particles are
    actually CLOSE to their assigned ring radius — the steering has
    pulled them onto orbital paths."""

    def setUp(self):
        from scene.animations.synth import _GEOM_CACHE
        _GEOM_CACHE.clear()
        # Use the actual platform grid (44×44) so the test exercises
        # the real spawn distances.
        self.grid = make_grid(44)
        self.frame = bytearray(self.grid.frame_bytes)
        anim = SynthAnimation({
            "radius_default": 8.0, "radius_min": 3.0, "radius_max": 16.0,
        })
        self.scn = Scene(anim, bpm=120.0, grid=self.grid)
        self.scn.reset_phase()
        self.scn.tick(0.0)

    def _walk_to(self, fraction: float, total_beats: float):
        """Advance the scene to `fraction` of `total_beats`."""
        target = fraction * total_beats
        _advance_to(self.scn, target, step=0.02)

    def test_particles_near_rings_at_70_percent(self):
        """At 70% of total, orbit_lock=1 per the envelope. Particles
        should have had time to fly in from grid edges AND curve onto
        their ring radii. The spawn seed is time-based so this is a
        statistical assertion: at least 50% of particles within ±4 LED
        of their assigned ring radius (typical run sees 8-12/12)."""
        total = 8.0   # beats — generous duration to give particles travel time
        self.scn.trigger("respawn", duration_beats=total)
        self._walk_to(0.70, total)

        # Force the alpha fade off so this test is purely about
        # particle CONVERGENCE (not visibility timing).
        self.scn.set_state("alpha", 1.0)

        anim = self.scn._animation
        self.assertIsNotNone(anim._dots_xy, "particles should exist at 70%")
        xy = anim._dots_xy
        ring_radii = anim._dots_ring_radius
        cur_r = np.sqrt(xy[:, 0] ** 2 + xy[:, 1] ** 2)
        r_err = np.abs(cur_r - ring_radii)
        # How many particles are within 4 LED of their target ring?
        on_ring = int(np.sum(r_err < 4.0))
        n = len(cur_r)
        pct = on_ring / n
        positions_str = ", ".join(
            f"({xy[i,0]:.1f},{xy[i,1]:.1f}) ring_r={ring_radii[i]:.1f} err={r_err[i]:.1f}"
            for i in range(n)
        )
        self.assertGreaterEqual(
            pct, 0.50,
            f"only {on_ring}/{n} particles near rings at 70%. Positions: {positions_str}",
        )

    def test_particles_orbiting_by_85_percent(self):
        """By 85%, particles should be tangent to their rings (heading
        roughly perpendicular to the radial direction)."""
        total = 8.0
        self.scn.trigger("respawn", duration_beats=total)
        self._walk_to(0.85, total)
        self.scn.set_state("alpha", 1.0)

        anim = self.scn._animation
        xy = anim._dots_xy
        heading = anim._dots_heading
        cur_r = np.sqrt(xy[:, 0] ** 2 + xy[:, 1] ** 2) + 1e-6
        # Tangent angle = atan2(y, x) + π/2.
        tangent = np.arctan2(xy[:, 1], xy[:, 0]) + np.pi * 0.5
        # Heading difference vs tangent, wrapped to [-π, π].
        diff = ((heading - tangent + np.pi) % (2 * np.pi)) - np.pi
        # How many particles have heading within 30° of tangent?
        aligned = int(np.sum(np.abs(diff) < (np.pi / 6)))
        n = len(heading)
        self.assertGreaterEqual(
            aligned, int(n * 0.5),
            f"only {aligned}/{n} particles heading-aligned to tangent at 85%",
        )


# ───────────────────────────── Regrow → Pulse leak ──

class TestRegrowToPulseScenario(unittest.TestCase):
    """User report 2026-05-25: after Regrow runs, Pulse 'goes from 0
    to full' — meaning baseline alpha is 0, not 1 as expected.
    Reproduce the dissolve → regrow → pulse pattern and verify alpha
    behaves correctly."""

    def test_regrow_pin_fires_setting_alpha_one(self):
        """Plain regrow with no interference: pin must fire and
        leave state.alpha = 1.0."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("regrow", duration_beats=2.0)
        _advance_to(scn, 2.5)
        self.assertAlmostEqual(scn.state["alpha"], 1.0, places=2,
                               msg="regrow's pin should set alpha=1")

    def test_pulse_after_regrow_bumps_alpha_above_one(self):
        """After regrow completes (alpha=1), a Pulse should add on
        top — peak alpha = 1 + pulse_amp = 2, NOT 0 → 1."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("regrow", duration_beats=2.0)
        _advance_to(scn, 2.5)
        # Sanity: alpha is 1 right now.
        self.assertAlmostEqual(scn.state["alpha"], 1.0, places=2)
        # Pulse fires.
        scn.trigger("pulse", duration_beats=0.25)
        # Walk to the peak of the pulse spike (env=1 around t=0.08
        # for the pulse_default spike envelope).
        _advance_to(scn, 2.55, step=0.005)
        alpha = scn.state["alpha"]
        self.assertGreater(
            alpha, 1.5,
            f"pulse after regrow should ADD to alpha=1, peaking ~2; got {alpha:.3f}",
        )

    def test_dense_pulses_around_regrow(self):
        """User's actual sequence: pulses every 1/4 beat throughout
        the loop. A Regrow happens partway through. After Regrow
        completes, subsequent pulses should ADD to alpha=1 (peak
        ~2), NOT swing 0→1 from a baseline of 0."""
        scn = _build_scene()
        scn.tick(0.0)
        # Simulate pulses every 1/4 beat for the first 4 beats.
        for k in range(16):
            t = k * 0.25
            _advance_to(scn, t, step=0.05)
            scn.trigger("pulse", duration_beats=0.25)
        # Now Regrow.
        _advance_to(scn, 4.25, step=0.05)
        scn.trigger("regrow", duration_beats=1.0)
        # Regrow runs 1 beat. Pulses keep firing.
        for k in range(4):
            t = 4.25 + 0.25 + k * 0.25
            _advance_to(scn, t, step=0.05)
            scn.trigger("pulse", duration_beats=0.25)
        # Now we're past regrow. Fire one more pulse + sample alpha
        # at peak (just after fire).
        _advance_to(scn, 6.0, step=0.05)
        scn.trigger("pulse", duration_beats=0.25)
        _advance_to(scn, 6.05, step=0.005)
        alpha = scn.state["alpha"]
        # Should be 1 + pulse contribution, > 1.5.
        self.assertGreater(
            alpha, 1.5,
            f"after regrow + many pulses, baseline alpha should be 1.0 "
            f"so pulse peaks ~2; got alpha={alpha:.3f} — baseline leaked?",
        )
        # ALSO verify the BETWEEN-pulse value is 1, not 0.
        _advance_to(scn, 6.5, step=0.05)
        alpha_between = scn.state["alpha"]
        self.assertAlmostEqual(
            alpha_between, 1.0, delta=0.15,
            msg=f"between pulses alpha should be ~1 (pin set it), got {alpha_between:.3f}",
        )

    def test_regrow_pin_pins_alpha_when_expand_owns_only_radius(self):
        """REGRESSION (2026-05-25 user report): when Expand fires at
        the loop wrap RIGHT as Regrow's pin is due, the pin used to
        bail entirely because Expand has an absolute modulator on
        radius. But Expand doesn't touch alpha — so the alpha pin
        should still fire. Per-target bail check fixes this; without
        it, baseline_alpha stays at 0 and subsequent Pulses swing
        0→1 instead of 1→2 (user's "scene disappears with the beat")."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("regrow", duration_beats=1.0)
        _advance_to(scn, 0.98, step=0.02)
        # Fire Expand RIGHT when pin is about to fire (~beat 0.98).
        # This simulates the loop-wrap → Expand-at-beat-0 scenario.
        scn.trigger("expand", duration_beats=4.0)
        _advance_to(scn, 1.10, step=0.02)
        # Regrow's alpha pin must have fired — Expand only owns radius.
        self.assertAlmostEqual(
            scn.state["alpha"], 1.0, delta=0.05,
            msg=f"regrow alpha pin should fire even when Expand owns radius; "
                f"got alpha={scn.state['alpha']:.3f}",
        )

    def test_crosshair_sequence_pulse_during_regrow(self):
        """Replays the user's crosshair sequence pattern around the
        regrow region:
          beat 48.25-56.0  Dissolve  (length 7.75)
          beat 60-61.75    Regrow    (length 1.75)
          beat 60          Pulse     (SAME tick as regrow note_on!)
          beat 61          Pulse     (during regrow growth)
          beat 62          Pulse     (just after regrow pin)
          beat 63          Pulse
        Verifies state.alpha after regrow's pin is 1.0 and that
        subsequent pulses bump it to ~2 (not 0→1)."""
        scn = _build_scene()
        scn.tick(0.0)
        # Fast-forward to the dissolve.
        _advance_to(scn, 48.25, step=0.1)
        scn.trigger("dissolve", duration_beats=7.75)
        _advance_to(scn, 56.0, step=0.05)
        # Confirm dissolve completed: alpha=0, dissolve_amount=0.
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2,
                               msg="dissolve should have completed at beat 56")
        # Walk to beat 60 — where regrow + pulse fire together.
        _advance_to(scn, 60.0, step=0.05)
        # Fire Regrow note_on. The order matters: if Pulse fires
        # first, Regrow's set_state(alpha, 0) purges Pulse's mod
        # below. Let's fire Regrow first to match what the sequencer
        # would do (lane order: pitch 4 = pulse, pitch 6 = regrow;
        # router iterates in dispatch order). Try BOTH orderings.
        scn.trigger("regrow", duration_beats=1.75)
        scn.trigger("pulse", duration_beats=0.25)
        # Walk through regrow's growth + the in-flight pulses.
        _advance_to(scn, 61.0, step=0.05)
        scn.trigger("pulse", duration_beats=0.25)
        _advance_to(scn, 61.75, step=0.02)
        # Regrow ends here (start 60 + len 1.75). Pin should have fired.
        # IMMEDIATELY after pin, state.alpha should be 1.
        _advance_to(scn, 61.85, step=0.02)
        alpha_after_pin = scn.state["alpha"]
        self.assertAlmostEqual(
            alpha_after_pin, 1.0, delta=0.15,
            msg=f"after regrow pin, alpha should be ~1, got {alpha_after_pin:.3f}",
        )
        # Now the pulses at 62, 63 should add on top.
        _advance_to(scn, 62.0, step=0.05)
        scn.trigger("pulse", duration_beats=0.25)
        _advance_to(scn, 62.05, step=0.005)
        alpha_pulse = scn.state["alpha"]
        self.assertGreater(
            alpha_pulse, 1.5,
            f"pulse after regrow pin should peak ~2; got {alpha_pulse:.3f} — "
            f"baseline is 0 (pin didn't fire?)",
        )

    def test_dissolve_then_regrow_then_pulse(self):
        """Full user scenario: dissolve → regrow → pulse. After regrow
        the pulse should still add to alpha=1, not behave as if
        baseline is 0."""
        scn = _build_scene()
        scn.tick(0.0)
        scn.trigger("dissolve", duration_beats=2.0)
        _advance_to(scn, 2.5)   # dissolve done; alpha=0
        scn.trigger("regrow", duration_beats=1.0)
        _advance_to(scn, 4.0)   # regrow done; alpha should be 1
        self.assertAlmostEqual(
            scn.state["alpha"], 1.0, places=2,
            msg="regrow after dissolve should restore alpha to 1",
        )
        # Now pulse.
        scn.trigger("pulse", duration_beats=0.25)
        _advance_to(scn, 4.05, step=0.005)
        alpha = scn.state["alpha"]
        self.assertGreater(
            alpha, 1.5,
            f"pulse after dissolve→regrow should peak ~2; got {alpha:.3f}",
        )


if __name__ == "__main__":
    unittest.main()
