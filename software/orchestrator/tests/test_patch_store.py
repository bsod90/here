"""PatchStore — filesystem CRUD for synth patches. Mirrors the existing
test_sequence_store.py shape since both stores share the same sanitize
+ unique-name machinery."""
import json
import tempfile
import unittest
from pathlib import Path

from scene.patch_store import PatchStore, PATCH_SECTIONS


class TestPatchStoreCRUD(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = PatchStore(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_round_trip(self):
        body = {
            "synth":   {"radius_default": 9.0},
            "curves":  {"transition_default": {"points": [[0, 0], [1, 1]]}},
            "physics": {"speed": 30.0},
            "bpm":     104.0,
        }
        name = self.store.save("my-patch", body)
        self.assertEqual(name, "my-patch")
        loaded = self.store.load("my-patch")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["synth"], body["synth"])
        self.assertEqual(loaded["curves"], body["curves"])
        self.assertEqual(loaded["physics"], body["physics"])
        self.assertAlmostEqual(loaded["bpm"], 104.0)
        # Metadata fields added by store.
        self.assertEqual(loaded["name"], "my-patch")
        self.assertIn("modified_at", loaded)

    def test_save_drops_unknown_sections(self):
        """The whitelist (PATCH_SECTIONS) is enforced — unknown keys
        don't end up in the saved file."""
        body = {
            "synth": {"radius_default": 9.0},
            "evil":  {"do_not_save": True},
            "another_unknown": [1, 2, 3],
        }
        self.store.save("safe", body)
        loaded = self.store.load("safe")
        self.assertIn("synth", loaded)
        self.assertNotIn("evil", loaded)
        self.assertNotIn("another_unknown", loaded)

    def test_load_missing_returns_none(self):
        self.assertIsNone(self.store.load("does-not-exist"))

    def test_exists(self):
        self.assertFalse(self.store.exists("foo"))
        self.store.save("foo", {"bpm": 100.0})
        self.assertTrue(self.store.exists("foo"))

    def test_list_returns_summaries_sorted(self):
        self.store.save("beta", {"synth": {}})
        self.store.save("alpha", {"curves": {}})
        self.store.save("gamma", {"physics": {}})
        listing = self.store.list()
        names = [p["name"] for p in listing]
        self.assertEqual(names, ["alpha", "beta", "gamma"])
        # Summary flags match.
        by_name = {p["name"]: p for p in listing}
        self.assertTrue(by_name["alpha"]["has_curves"])
        self.assertFalse(by_name["alpha"]["has_synth"])
        self.assertTrue(by_name["beta"]["has_synth"])
        self.assertTrue(by_name["gamma"]["has_physics"])

    def test_delete(self):
        self.store.save("doomed", {"bpm": 90.0})
        self.assertTrue(self.store.exists("doomed"))
        self.assertTrue(self.store.delete("doomed"))
        self.assertFalse(self.store.exists("doomed"))
        # Deleting missing returns False, doesn't raise.
        self.assertFalse(self.store.delete("doomed"))

    def test_unique_name_padding(self):
        self.store.save("base", {})
        self.assertEqual(self.store.unique_name("base"), "base-2")
        self.store.save("base-2", {})
        self.assertEqual(self.store.unique_name("base"), "base-3")
        # Fresh name returns unchanged.
        self.assertEqual(self.store.unique_name("fresh"), "fresh")

    def test_save_sanitizes_unsafe_name(self):
        """Path-separators and spaces are stripped — the saved file
        lives under the sanitized name."""
        out_name = self.store.save("../with spaces/and slashes", {"bpm": 100.0})
        self.assertNotIn("/", out_name)
        self.assertNotIn("..", out_name)
        self.assertTrue(self.store.exists(out_name))

    def test_corrupt_file_is_skipped_by_list(self):
        """A malformed JSON file in the patches dir doesn't break list()
        — it's silently skipped (already-saved patches keep working)."""
        good = self.store.save("good", {"bpm": 90.0})
        bad_path = Path(self._tmp.name) / "broken.json"
        bad_path.write_text("not json {{")
        listing = self.store.list()
        names = [p["name"] for p in listing]
        self.assertIn("good", names)
        self.assertNotIn("broken", names)


class TestPatchSectionsWhitelist(unittest.TestCase):
    """PATCH_SECTIONS is the source of truth for what gets persisted in
    a patch. This test pins the current set so an accidental deletion
    of a key (e.g. event_defaults, added in iter 1) gets caught."""

    def test_whitelist_contains_expected_sections(self):
        expected = {
            "synth", "curves", "physics", "default_durations",
            "event_defaults", "bpm", "palette_idx", "active_sequence",
        }
        self.assertEqual(set(PATCH_SECTIONS), expected)


class TestSeedDefaultsIdempotent(unittest.TestCase):
    """`seed_defaults` writes the bundled breathing patch + sequence on
    first boot. If files already exist (subsequent boot), it must not
    overwrite — preserving the user's edits."""

    def setUp(self):
        self._patch_dir = tempfile.TemporaryDirectory()
        self._seq_dir = tempfile.TemporaryDirectory()
        from scene.patch_store import PatchStore
        from scene.sequence_store import SequenceStore
        self.patches = PatchStore(self._patch_dir.name)
        self.sequences = SequenceStore(self._seq_dir.name)

    def tearDown(self):
        self._patch_dir.cleanup()
        self._seq_dir.cleanup()

    def test_first_call_seeds(self):
        import logging
        from scene.default_presets import seed_defaults, BREATHING_PATCH
        self.assertFalse(self.patches.exists(BREATHING_PATCH["name"]))
        seed_defaults(self.patches, self.sequences, logging.getLogger("test"))
        self.assertTrue(self.patches.exists(BREATHING_PATCH["name"]))

    def test_second_call_does_not_overwrite_user_edits(self):
        import logging
        from scene.default_presets import seed_defaults, BREATHING_PATCH
        # First call seeds.
        seed_defaults(self.patches, self.sequences, logging.getLogger("test"))
        # User modifies the patch.
        modified = self.patches.load(BREATHING_PATCH["name"])
        modified["bpm"] = 999.0
        self.patches.save(BREATHING_PATCH["name"], modified)
        # Re-seed.
        seed_defaults(self.patches, self.sequences, logging.getLogger("test"))
        # Modified version is preserved.
        loaded = self.patches.load(BREATHING_PATCH["name"])
        self.assertAlmostEqual(loaded["bpm"], 999.0,
                               msg="seed_defaults overwrote user's edited patch")


if __name__ == "__main__":
    unittest.main()
