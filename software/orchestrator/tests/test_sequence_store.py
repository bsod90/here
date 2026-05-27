"""Tests for SequenceStore — list, save, load, duplicate, delete, sanitization."""
import json
import tempfile
import unittest
from pathlib import Path

from scene.sequence_store import SequenceStore, sanitize_name


class TestSanitize(unittest.TestCase):
    def test_safe_chars_preserved(self):
        self.assertEqual(sanitize_name("my-loop_2.v1"), "my-loop_2.v1")

    def test_spaces_become_dashes(self):
        self.assertEqual(sanitize_name("my first jam"), "my-first-jam")

    def test_slashes_stripped(self):
        self.assertEqual(sanitize_name("../etc/passwd"), "etc-passwd")

    def test_empty_or_only_separators(self):
        self.assertEqual(sanitize_name(""), "untitled")
        self.assertEqual(sanitize_name("---"), "untitled")
        self.assertEqual(sanitize_name("..."), "untitled")


class TestSequenceStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = SequenceStore(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load_round_trip(self):
        notes = [
            {"pitch": 0, "start_beat": 0.0, "length_beats": 1.0},
            {"pitch": 4, "start_beat": 2.5, "length_beats": 0.25},
        ]
        self.store.save("test", notes=notes, loop_length_beats=8.0)
        data = self.store.load("test")
        self.assertIsNotNone(data)
        self.assertEqual(data["name"], "test")
        self.assertEqual(data["loop_length_beats"], 8.0)
        self.assertEqual(data["notes"], notes)
        self.assertIn("modified_at", data)

    def test_save_returns_sanitized_name(self):
        n = self.store.save("My Cool Loop!!", notes=[], loop_length_beats=4)
        self.assertEqual(n, "My-Cool-Loop")
        self.assertTrue(self.store.exists("My-Cool-Loop"))

    def test_load_nonexistent_returns_none(self):
        self.assertIsNone(self.store.load("nope"))

    def test_list_returns_summaries_sorted(self):
        self.store.save("b", notes=[{"pitch": 0, "start_beat": 0, "length_beats": 1}], loop_length_beats=4)
        self.store.save("a", notes=[], loop_length_beats=8)
        items = self.store.list()
        self.assertEqual([x["name"] for x in items], ["a", "b"])
        self.assertEqual(items[0]["note_count"], 0)
        self.assertEqual(items[1]["note_count"], 1)
        self.assertEqual(items[1]["loop_length_beats"], 4.0)

    def test_duplicate(self):
        notes = [{"pitch": 1, "start_beat": 1.0, "length_beats": 0.5}]
        self.store.save("src", notes=notes, loop_length_beats=8)
        new_name = self.store.duplicate("src", "copy")
        self.assertEqual(new_name, "copy")
        data = self.store.load("copy")
        self.assertEqual(data["notes"], notes)
        self.assertEqual(data["loop_length_beats"], 8.0)

    def test_duplicate_missing_source(self):
        self.assertIsNone(self.store.duplicate("nope", "copy"))

    def test_delete(self):
        self.store.save("victim", notes=[], loop_length_beats=4)
        self.assertTrue(self.store.exists("victim"))
        self.assertTrue(self.store.delete("victim"))
        self.assertFalse(self.store.exists("victim"))

    def test_delete_missing(self):
        self.assertFalse(self.store.delete("nope"))

    def test_unique_name_pads_suffix(self):
        self.store.save("loop", notes=[], loop_length_beats=4)
        self.store.save("loop-2", notes=[], loop_length_beats=4)
        self.assertEqual(self.store.unique_name("loop"), "loop-3")
        self.assertEqual(self.store.unique_name("new"), "new")

    def test_save_overwrites(self):
        self.store.save("x", notes=[{"pitch": 0, "start_beat": 0, "length_beats": 1}], loop_length_beats=4)
        self.store.save("x", notes=[], loop_length_beats=8)
        d = self.store.load("x")
        self.assertEqual(d["notes"], [])
        self.assertEqual(d["loop_length_beats"], 8.0)


if __name__ == "__main__":
    unittest.main()
