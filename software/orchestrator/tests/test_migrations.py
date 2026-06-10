"""Tests for config schema migrations (migrations.py)."""
import tempfile
import unittest
from pathlib import Path

import migrations
from config import ConfigManager
from scene import SequenceStore


class MigrationFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.config = ConfigManager(path=str(Path(self._td.name) / "cfg.json"))

    def tearDown(self):
        self._td.cleanup()


class TestSceneMigration(MigrationFixture):

    def test_animation_repointed_breathing_to_synth(self):
        self.config.set("scene", {"animation": "breathing"})
        migrations.migrate_scene_breathing_to_synth(self.config)
        self.assertEqual(self.config.get("scene")["animation"], "synth")

    def test_idempotent_and_preserves_synth_settings(self):
        self.config.set("scene", {"animation": "synth",
                                  "synth": {"radius_max": 11.0}})
        migrations.migrate_scene_breathing_to_synth(self.config)
        migrations.migrate_scene_breathing_to_synth(self.config)
        self.assertEqual(self.config.get("scene")["synth"]["radius_max"], 11.0)


class TestAudioMigration(MigrationFixture):

    def test_backdrop_scalars_move_to_ocean_track(self):
        self.config.set("audio", {"backdrop_enabled": True,
                                  "backdrop_volume": 0.8})
        migrations.migrate_audio_backdrop_to_tracks(self.config)
        audio = self.config.get("audio")
        self.assertTrue(audio["tracks"]["ocean"]["enabled"])
        self.assertEqual(audio["tracks"]["ocean"]["volume"], 0.8)
        # Legacy keys neutralized so the next boot skips the migration.
        self.assertIsNone(audio["backdrop_enabled"])
        self.assertIsNone(audio["backdrop_volume"])

    def test_runs_once_then_respects_later_track_edits(self):
        self.config.set("audio", {"backdrop_enabled": True,
                                  "backdrop_volume": 0.8})
        migrations.migrate_audio_backdrop_to_tracks(self.config)
        # User later turns the ocean off; a re-run must NOT resurrect it.
        self.config.set("audio", {"tracks": {"ocean": {"enabled": False}}})
        migrations.migrate_audio_backdrop_to_tracks(self.config)
        self.assertFalse(self.config.get("audio")["tracks"]["ocean"]["enabled"])

    def test_noop_without_legacy_fields(self):
        before = self.config.get("audio")
        migrations.migrate_audio_backdrop_to_tracks(self.config)
        self.assertEqual(self.config.get("audio"), before)

    def test_run_config_migrations_covers_both(self):
        self.config.set("scene", {"animation": "breathing"})
        self.config.set("audio", {"backdrop_enabled": False})
        migrations.run_config_migrations(self.config)
        self.assertEqual(self.config.get("scene")["animation"], "synth")
        self.assertFalse(self.config.get("audio")["tracks"]["ocean"]["enabled"])


class TestSequencerNotesMigration(MigrationFixture):

    def setUp(self):
        super().setUp()
        self.store = SequenceStore(str(Path(self._td.name) / "sequences"))

    def test_legacy_notes_become_a_named_sequence(self):
        notes = [{"lane": 0, "beat": 0.0, "duration": 1.0}]
        self.config.set("scene", {"sequencer": {"notes": notes,
                                                "loop_length_beats": 8.0}})
        name = migrations.migrate_sequencer_notes(self.config, self.store)
        self.assertIsNotNone(name)
        data = self.store.load(name)
        self.assertEqual(data["notes"], notes)
        self.assertEqual(data["loop_length_beats"], 8.0)
        seq_cfg = self.config.get("scene")["sequencer"]
        self.assertEqual(seq_cfg["active_sequence"], name)

    def test_noop_when_active_sequence_already_set(self):
        self.config.set("scene", {"sequencer": {"notes": [{"lane": 0}],
                                                "active_sequence": "x"}})
        self.assertIsNone(
            migrations.migrate_sequencer_notes(self.config, self.store))

    def test_noop_without_notes(self):
        self.assertIsNone(
            migrations.migrate_sequencer_notes(self.config, self.store))


if __name__ == "__main__":
    unittest.main()
