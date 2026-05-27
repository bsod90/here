"""Verify the M4L device's metadata JSONs are in sync with the canonical
source-of-truth in `software/orchestrator/scene/animations/synth.py`
(NOTE_LANES) and the knob specs in `gen_metadata.py`.

This catches the "added a new event/knob but forgot to regenerate the
M4L JSON" footgun. If this test fails, run:
    cd software/ableton && python3 gen_metadata.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABLETON_DIR = HERE.parent
REPO_ROOT = ABLETON_DIR.parent.parent
ORCH_DIR = REPO_ROOT / "software" / "orchestrator"

if str(ABLETON_DIR) not in sys.path:
    sys.path.insert(0, str(ABLETON_DIR))
if str(ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(ORCH_DIR))


class TestEventsJsonSync(unittest.TestCase):
    def test_event_count_matches_note_lanes(self):
        from scene.animations.synth import SynthAnimation
        data = json.loads((ABLETON_DIR / "here_events.json").read_text())
        self.assertEqual(len(data["events"]), len(SynthAnimation.NOTE_LANES),
                         "here_events.json is stale — run gen_metadata.py")

    def test_event_labels_match(self):
        from scene.animations.synth import SynthAnimation
        data = json.loads((ABLETON_DIR / "here_events.json").read_text())
        for i, lane in enumerate(SynthAnimation.NOTE_LANES):
            entry = data["events"][i]
            self.assertEqual(entry["label"], lane["label"],
                             f"label drift at index {i}")
            self.assertEqual(entry["event"], lane["event"],
                             f"event drift at index {i}")
            # Pitches are dense from base_pitch.
            self.assertEqual(entry["pitch"], data["base_pitch"] + i)

    def test_base_pitch_is_c1(self):
        data = json.loads((ABLETON_DIR / "here_events.json").read_text())
        self.assertEqual(data["base_pitch"], 36,
                         "BASE_PITCH should be 36 (Drum Rack C1)")


class TestKnobsJsonSync(unittest.TestCase):
    def test_master_knobs_present(self):
        data = json.loads((ABLETON_DIR / "here_knobs.json").read_text())
        keys = {k["key"] for k in data["master"]}
        # Spot-check the most-used knobs are there.
        for must_have in ("radius_min", "radius_max", "brightness",
                          "shimmer_intensity"):
            self.assertIn(must_have, keys,
                          f"master knob {must_have!r} missing from here_knobs.json")

    def test_physics_knobs_match_params_dataclass(self):
        # Every PhysicsParams field should be representable as a knob.
        from scene.physics import PhysicsParams
        data = json.loads((ABLETON_DIR / "here_knobs.json").read_text())
        physics_keys = {k["key"] for k in data["physics"]}
        param_keys = set(PhysicsParams().to_dict().keys())
        missing = param_keys - physics_keys
        self.assertFalse(missing,
                         f"physics params not exposed as knobs: {missing}")

    def test_oval_knobs_have_three_defaults(self):
        data = json.loads((ABLETON_DIR / "here_knobs.json").read_text())
        for k in data["oval"]:
            self.assertEqual(len(k["defaults"]), 3,
                             f"oval knob {k['key']!r} needs 3 defaults (one per ring)")


class TestRegenerateProducesSameOutput(unittest.TestCase):
    """If gen_metadata.py emits different JSON than what's committed,
    the committed files are stale."""

    def test_events_json_is_up_to_date(self):
        import gen_metadata
        expected = json.dumps(
            {"base_pitch": gen_metadata.BASE_PITCH, "events": gen_metadata.build_events()},
            indent=2,
        ) + "\n"
        on_disk = (ABLETON_DIR / "here_events.json").read_text()
        self.assertEqual(on_disk, expected,
                         "here_events.json is stale — run gen_metadata.py")

    def test_knobs_json_is_up_to_date(self):
        import gen_metadata
        expected = json.dumps(gen_metadata.build_knobs(), indent=2) + "\n"
        on_disk = (ABLETON_DIR / "here_knobs.json").read_text()
        self.assertEqual(on_disk, expected,
                         "here_knobs.json is stale — run gen_metadata.py")


if __name__ == "__main__":
    unittest.main()
