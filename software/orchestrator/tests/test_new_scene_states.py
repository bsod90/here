"""New scene-state events: reset_scene, fade_out, border_glow,
floating_particles, and the dissolve→float / respawn-from-float reworks.
These complement the headless render checks in render_states.py."""
import time
import unittest

from scene.animations.synth import SynthAnimation
from scene.scene import Scene


def _build():
    scn = Scene(SynthAnimation({"radius_default": 8.0,
                                "radius_min": 3.0, "radius_max": 16.0}),
                bpm=120.0)
    scn.reset_phase()
    scn.tick(0.0)
    return scn


def _advance(scn, beats):
    clk = scn._clock
    target = clk.now_beat() + beats
    spb = 60.0 / clk.bpm
    t_ms = 0.0
    while clk.now_beat() < target:
        nxt = min(clk.now_beat() + 0.1, target)
        clk._t0_seconds = time.monotonic() - nxt * spb
        t_ms += 0.1 * spb * 1000.0
        scn.tick(t_ms)
    return t_ms


class TestResetScene(unittest.TestCase):
    def test_reset_blanks_everything(self):
        scn = _build()
        scn.trigger("expand", duration_beats=0.5)
        scn.trigger("border_glow", duration_beats=0.5)
        _advance(scn, 1.0)
        scn.trigger("reset_scene")
        self.assertAlmostEqual(scn.state["alpha"], 0.0, places=2)
        self.assertAlmostEqual(scn.state["radius"], 0.0, places=2)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2)
        self.assertAlmostEqual(scn.state["border_glow_amount"], 0.0, places=2)
        self.assertIsNone(scn._animation._dots_xy)


class TestBorderGlow(unittest.TestCase):
    def test_border_fades_in_and_pins(self):
        scn = _build()
        scn.trigger("border_glow", duration_beats=1.0)
        _advance(scn, 1.5)
        self.assertAlmostEqual(scn.state["border_glow_amount"], 1.0, places=2,
                               msg="border should fade in to 1 and pin")


class TestFloatingParticles(unittest.TestCase):
    def test_from_empty_spawns_and_fades_in(self):
        scn = _build()
        scn.trigger("reset_scene")
        scn.trigger("floating_particles", duration_beats=2.0)
        # Particles seeded from beyond the borders.
        self.assertIsNotNone(scn._animation._dots_xy)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)
        self.assertAlmostEqual(scn.state["dot_orbit_lock"], 0.0, places=2)
        self.assertGreater(scn.state["dot_bound"], 0.0)   # contained on-grid
        _advance(scn, 2.5)
        self.assertAlmostEqual(scn.state["dot_visibility"], 1.0, places=1)


class TestDissolveRespawnRework(unittest.TestCase):
    def test_dissolve_settles_into_float(self):
        scn = _build()
        scn.trigger("expand", duration_beats=0.5)
        scn.trigger("dissolve", duration_beats=4.0)
        _advance(scn, 5.0)
        self.assertGreater(scn.state["alpha"], 0.5)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 1.0, places=2)
        self.assertAlmostEqual(scn.state["dot_orbit_lock"], 0.0, places=2)

    def test_respawn_gathers_existing_float_without_respawn(self):
        scn = _build()
        scn.trigger("dissolve", duration_beats=3.0)
        _advance(scn, 3.5)                 # now floating
        dots_before = scn._animation._dots_xy
        self.assertIsNotNone(dots_before)
        scn.trigger("respawn", duration_beats=3.0)
        # No re-spawn: the SAME particle buffer is gathered (not replaced
        # with a fresh edge-spawn) → identity preserved right after trigger.
        self.assertIs(scn._animation._dots_xy, dots_before)
        _advance(scn, 3.5)
        self.assertAlmostEqual(scn.state["dissolve_amount"], 0.0, places=2)
        self.assertGreater(scn.state["alpha"], 0.5)


if __name__ == "__main__":
    unittest.main()
