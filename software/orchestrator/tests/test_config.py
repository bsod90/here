"""Tests for ConfigManager — persistence, deep merge, corruption
recovery, and atomic writes."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from config import ConfigManager, DEFAULT_CONFIG, get_defaults


class ConfigFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.path = Path(self._td.name) / "config.json"

    def tearDown(self):
        self._td.cleanup()

    def manager(self):
        return ConfigManager(path=str(self.path))


class TestDefaultsAndLoad(ConfigFixture):

    def test_missing_file_yields_defaults(self):
        cfg = self.manager()
        self.assertEqual(cfg.get("mode"), DEFAULT_CONFIG["mode"])
        self.assertFalse(self.path.exists())     # nothing saved on read

    def test_corrupt_file_yields_defaults(self):
        self.path.write_text('{"mode": "standb')  # truncated mid-write
        cfg = self.manager()
        self.assertEqual(cfg.get("mode"), DEFAULT_CONFIG["mode"])

    def test_saved_values_override_defaults(self):
        self.path.write_text(json.dumps({"mode": "fireplace"}))
        cfg = self.manager()
        self.assertEqual(cfg.get("mode"), "fireplace")
        # Untouched sections still come from defaults.
        self.assertIn("breathing", cfg.get_all())

    def test_saved_partial_section_deep_merges_with_defaults(self):
        self.path.write_text(json.dumps({"standby": {"spawn_rate": 7}}))
        cfg = self.manager()
        standby = cfg.get("standby")
        self.assertEqual(standby["spawn_rate"], 7)
        self.assertIn("sparkle_density", standby)  # default kept

    def test_get_defaults_returns_fresh_copy(self):
        d1 = get_defaults()
        d1["mode"] = "mutated"
        d1["standby"]["spawn_rate"] = 999
        d2 = get_defaults()
        self.assertEqual(d2["mode"], DEFAULT_CONFIG["mode"])
        self.assertNotEqual(d2["standby"]["spawn_rate"], 999)


class TestSetAndPersist(ConfigFixture):

    def test_set_persists_to_disk(self):
        cfg = self.manager()
        cfg.set("mode", "fireplace")
        on_disk = json.loads(self.path.read_text())
        self.assertEqual(on_disk["mode"], "fireplace")

    def test_set_dict_deep_merges(self):
        cfg = self.manager()
        cfg.set("standby", {"spawn_rate": 5})
        standby = cfg.get("standby")
        self.assertEqual(standby["spawn_rate"], 5)
        self.assertIn("sparkle_density", standby)

    def test_set_non_dict_replaces(self):
        cfg = self.manager()
        cfg.set("targets", [])
        self.assertEqual(cfg.get("targets"), [])

    def test_roundtrip_through_new_manager(self):
        cfg = self.manager()
        cfg.set("playground", {"recording_file": "n.mp3"})
        cfg2 = self.manager()
        self.assertEqual(cfg2.get("playground")["recording_file"], "n.mp3")

    def test_get_returns_copies(self):
        cfg = self.manager()
        section = cfg.get("standby")
        section["spawn_rate"] = 12345
        self.assertNotEqual(cfg.get("standby")["spawn_rate"], 12345)


class TestAtomicWrites(ConfigFixture):

    def test_no_temp_files_left_behind(self):
        cfg = self.manager()
        for i in range(5):
            cfg.set("mode", f"m{i}")
        leftovers = [p for p in Path(self._td.name).iterdir()
                     if p.name != "config.json"]
        self.assertEqual(leftovers, [])

    def test_file_is_always_complete_json(self):
        """Hammer saves from several threads; the on-disk file must parse
        as complete JSON at every observation (no torn writes)."""
        cfg = self.manager()
        stop = threading.Event()
        errors = []

        def writer(n):
            i = 0
            while not stop.is_set():
                cfg.set(f"w{n}", {"i": i})
                i += 1

        def reader():
            while not stop.is_set():
                try:
                    if self.path.exists():
                        json.loads(self.path.read_text())
                except json.JSONDecodeError as e:   # pragma: no cover
                    errors.append(e)
                    stop.set()

        threads = ([threading.Thread(target=writer, args=(n,)) for n in range(3)]
                   + [threading.Thread(target=reader)])
        for t in threads:
            t.start()
        stop.wait(timeout=1.0)
        stop.set()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(errors, [])

    def test_replace_preserves_old_content_until_swap(self):
        cfg = self.manager()
        cfg.set("mode", "standby")
        # Simulate the dangerous moment: a temp file exists alongside a
        # valid config. A fresh manager must read the real file, not tmp.
        (Path(self._td.name) / "config.json.garbage.tmp").write_text("{junk")
        cfg2 = self.manager()
        self.assertEqual(cfg2.get("mode"), "standby")

    def test_save_failure_leaves_original_intact(self):
        cfg = self.manager()
        cfg.set("mode", "standby")
        original = self.path.read_text()
        with patch("config.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                cfg.set("mode", "fireplace")
        self.assertEqual(self.path.read_text(), original)
        # No temp litter after the failure either.
        leftovers = [p for p in Path(self._td.name).iterdir()
                     if p.name != "config.json"]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()


class TestDiffPersistence(ConfigFixture):
    """Only the diff from DEFAULT_CONFIG is written to disk — untouched
    settings must keep tracking shipped defaults across upgrades (the
    old full-bake behaviour silently shadowed every future default)."""

    def test_untouched_defaults_are_not_baked(self):
        cfg = self.manager()
        cfg.set("mode", "fireplace")
        on_disk = json.loads(self.path.read_text())
        self.assertEqual(on_disk, {"mode": "fireplace"})

    def test_value_reset_to_default_drops_from_disk(self):
        cfg = self.manager()
        cfg.set("standby", {"spawn_rate": 5})
        self.assertIn("standby", json.loads(self.path.read_text()))
        cfg.set("standby", {"spawn_rate": DEFAULT_CONFIG["standby"]["spawn_rate"]})
        self.assertNotIn("standby", json.loads(self.path.read_text()))

    def test_unknown_keys_survive(self):
        cfg = self.manager()
        cfg.set("my_custom_section", {"x": 1})
        cfg.set("mode", "fireplace")
        cfg2 = self.manager()
        self.assertEqual(cfg2.get("my_custom_section"), {"x": 1})
