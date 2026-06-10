"""Tests for Nadia's Playground controller (playground.py).

Render-path tests inject marker animations into the registry so we can
assert exactly which animation painted at a given timeline position —
no LED hardware or real animation output needed. Timeline-v2 fades are
pinned to 0 in the cut-behavior tests and exercised explicitly in
TestFadesAndBlending.
"""
import logging
import tempfile
import unittest
from pathlib import Path

import numpy as np

from audio import AudioPlayer, _SR
from config import ConfigManager
from grid import FRAME_BYTES
from playground import Playground, REC_CLIP


def setUpModule():
    logging.getLogger("playground").setLevel(logging.CRITICAL)
    logging.getLogger("audio").setLevel(logging.CRITICAL)


def tearDownModule():
    logging.getLogger("playground").setLevel(logging.NOTSET)
    logging.getLogger("audio").setLevel(logging.NOTSET)


def clip(anim, start, dur, fi=0.0, fo=0.0):
    return {"animation": anim, "start_sec": start, "duration_sec": dur,
            "fade_in_sec": fi, "fade_out_sec": fo}


class PlaygroundFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.config = ConfigManager(path=str(Path(self._td.name) / "cfg.json"))
        self.config.set("audio", {"media_dir": str(Path(self._td.name) / "media")})
        self.pg = Playground(self.config)
        self.frame = bytearray(FRAME_BYTES)
        # Marker animations record (anim_id, time_ms) per render call and
        # paint a solid grey level so blend weights are measurable.
        self.calls = []
        for marker, level in (("red", 100), ("blue", 200)):
            def make(marker=marker, level=level):
                def adapter(f, t, s):
                    self.calls.append((marker, t))
                    f[:] = bytes([level]) * len(f)
                return adapter
            self.pg._anims[marker] = (marker.title(), make())

    def tearDown(self):
        self.pg.stop()
        self._td.cleanup()

    def render(self, t_ms):
        self.pg.render(self.frame, t_ms, {})


class TestTimelineSanitization(PlaygroundFixture):

    def test_malformed_clips_are_dropped(self):
        self.pg.set_timeline([
            {"animation": "red", "start_sec": 0, "duration_sec": 5},
            {"animation": "blue"},                       # missing keys
            {"start_sec": 1, "duration_sec": 1},         # no animation
            "not a dict",
            {"animation": "red", "start_sec": "x", "duration_sec": 1},
        ])
        tl = self.pg.snapshot()["timeline"]
        self.assertEqual(len(tl), 1)
        self.assertEqual(tl[0]["animation"], "red")

    def test_values_are_clamped(self):
        self.pg.set_timeline([
            {"animation": "red", "start_sec": -3, "duration_sec": 0,
             "fade_in_sec": -1},
        ])
        c = self.pg.snapshot()["timeline"][0]
        self.assertEqual(c["start_sec"], 0.0)
        self.assertGreaterEqual(c["duration_sec"], 0.1)
        self.assertEqual(c["fade_in_sec"], 0.0)

    def test_fades_are_optional(self):
        self.pg.set_timeline([
            {"animation": "red", "start_sec": 0, "duration_sec": 5},
        ])
        c = self.pg.snapshot()["timeline"][0]
        self.assertNotIn("fade_in_sec", c)      # falls back to default

    def test_timeline_persists_to_config(self):
        self.pg.set_timeline([clip("red", 1, 2)])
        saved = self.config.get("playground")["timeline"]
        self.assertEqual(len(saved), 1)
        # Survives a fresh Playground built from the same config.
        pg2 = Playground(self.config)
        self.assertEqual(len(pg2.snapshot()["timeline"]), 1)


class TestTriggerAndPlayback(PlaygroundFixture):

    def test_trigger_shows_animation_immediately(self):
        self.pg.trigger("red")
        self.render(1000.0)
        self.assertEqual(self.calls[-1][0], "red")

    def test_trigger_unknown_keeps_previous(self):
        self.pg.trigger("red")
        self.pg.trigger("nope")
        self.render(0.0)
        self.assertEqual(self.calls[-1][0], "red")

    def test_play_renders_clips_at_their_times(self):
        self.pg.set_timeline([clip("red", 0, 2), clip("blue", 2, 2)])
        self.pg.play()
        self.render(10_000.0)        # stamps start at t=10s
        self.assertEqual(self.calls[-1][0], "red")
        self.render(11_000.0)        # 1s in → still red
        self.assertEqual(self.calls[-1][0], "red")
        self.render(13_000.0)        # 3s in → blue
        self.assertEqual(self.calls[-1][0], "blue")

    def test_sequence_ends_and_falls_back_to_current(self):
        self.pg.trigger("blue")
        self.pg.set_timeline([clip("red", 0, 1)])
        self.pg.play()
        self.render(0.0)
        self.assertTrue(self.pg.snapshot()["playing"])
        self.render(5_000.0)         # past the end
        self.assertFalse(self.pg.snapshot()["playing"])
        self.render(6_000.0)
        self.assertEqual(self.calls[-1][0], "blue")   # back to triggered anim

    def test_gap_between_clips_is_dark(self):
        self.pg.set_timeline([clip("red", 0, 1), clip("blue", 5, 1)])
        self.pg.play()
        self.render(0.0)
        self.render(3_000.0)         # in the gap
        self.assertEqual(max(self.frame), 0)

    def test_stop_halts_playback(self):
        self.pg.set_timeline([clip("red", 0, 10)])
        self.pg.play()
        self.render(0.0)
        self.pg.stop()
        self.assertFalse(self.pg.snapshot()["playing"])

    def test_trigger_cancels_playback(self):
        self.pg.set_timeline([clip("red", 0, 10)])
        self.pg.play()
        self.render(0.0)
        self.pg.trigger("blue")
        self.assertFalse(self.pg.snapshot()["playing"])
        self.render(1_000.0)
        self.assertEqual(self.calls[-1][0], "blue")

    def test_seek_starts_mid_sequence(self):
        self.pg.set_timeline([clip("red", 0, 2), clip("blue", 2, 8)])
        self.pg.play(start_sec=5.0)
        self.render(100_000.0)       # stamp; position should be ~5s
        self.assertEqual(self.calls[-1][0], "blue")
        snap = self.pg.snapshot()
        self.assertAlmostEqual(snap["position_sec"], 5.0, places=3)

    def test_broken_animation_never_raises(self):
        def boom(f, t, s):
            raise RuntimeError("render bug")
        self.pg._anims["boom"] = ("Boom", boom)
        self.pg.trigger("boom")
        self.render(0.0)             # must not propagate


class TestFadesAndBlending(PlaygroundFixture):

    def test_clip_weight_envelope(self):
        w = Playground._clip_weight
        # attack inside the head
        self.assertEqual(w(0.0, 0.0, 10.0, 2.0, 2.0), 0.0)
        self.assertAlmostEqual(w(1.0, 0.0, 10.0, 2.0, 2.0), 0.5)
        # plateau
        self.assertEqual(w(5.0, 0.0, 10.0, 2.0, 2.0), 1.0)
        # release extends PAST the end
        self.assertAlmostEqual(w(11.0, 0.0, 10.0, 2.0, 2.0), 0.5)
        self.assertEqual(w(12.0, 0.0, 10.0, 2.0, 2.0), 0.0)
        # zero fades = hard cut
        self.assertEqual(w(0.0, 0.0, 10.0, 0.0, 0.0), 1.0)
        self.assertEqual(w(10.0, 0.0, 10.0, 0.0, 0.0), 0.0)

    def test_fade_in_dims_the_frame(self):
        self.pg.set_timeline([clip("red", 0, 10, fi=2.0)])
        self.pg.play()
        self.render(0.0)             # stamp; pos=0 → weight 0 → dark
        self.assertEqual(max(self.frame), 0)
        self.render(1_000.0)         # 1s in → weight 0.5 → grey 50
        self.assertAlmostEqual(max(self.frame), 50, delta=2)
        self.render(5_000.0)         # plateau → full 100
        self.assertAlmostEqual(max(self.frame), 100, delta=1)

    def test_release_tail_keeps_sequence_alive(self):
        self.pg.set_timeline([clip("red", 0, 1, fo=2.0)])
        self.pg.play()
        self.render(0.0)
        self.render(2_000.0)         # 1s past end, inside the tail
        self.assertTrue(self.pg.snapshot()["playing"])
        self.assertAlmostEqual(max(self.frame), 50, delta=2)
        self.render(3_500.0)         # tail over → sequence done
        self.assertFalse(self.pg.snapshot()["playing"])

    def test_butted_clips_crossfade_without_black_dip(self):
        # red 0-2 releases over 1s past its end while blue attacks over
        # its first 1s → at the boundary the weights sum to ~1.
        self.pg.set_timeline([clip("red", 0, 2, fi=0, fo=1.0),
                              clip("blue", 2, 2, fi=1.0, fo=0)])
        self.pg.play()
        self.render(0.0)
        self.render(2_500.0)         # mid-crossfade: red w=0.5, blue w=0.5
        level = max(self.frame)
        # 0.5*100 + 0.5*200 = 150 — and definitely not a dip to black.
        self.assertAlmostEqual(level, 150, delta=4)

    def test_overlapping_clips_blend_normalized(self):
        self.pg.set_timeline([clip("red", 0, 4), clip("blue", 0, 4)])
        self.pg.play()
        self.render(0.0)
        self.render(2_000.0)         # both at weight 1 → normalized 0.5/0.5
        self.assertAlmostEqual(max(self.frame), 150, delta=4)
        # Both animations actually rendered.
        recent = {c[0] for c in self.calls[-2:]}
        self.assertEqual(recent, {"red", "blue"})


class TestSnapshot(PlaygroundFixture):

    def test_snapshot_shape(self):
        snap = self.pg.snapshot()
        for key in ("animations", "current", "playing", "timeline",
                    "position_sec", "duration_sec", "default_fade_sec",
                    "recording_file", "recording", "play_with_recording",
                    "recording_playing"):
            self.assertIn(key, snap)
        ids = [a["id"] for a in snap["animations"]]
        for builtin in ("breathing", "standby", "flower", "welcome",
                        "talking", "chill", "winddown"):
            self.assertIn(builtin, ids)

    def test_position_none_when_stopped(self):
        self.assertIsNone(self.pg.snapshot()["position_sec"])

    def test_duration_covers_release_tail(self):
        self.pg.set_timeline([clip("red", 0, 4, fo=2.0)])
        self.assertAlmostEqual(self.pg.snapshot()["duration_sec"], 6.0)

    def test_builtin_animations_render_without_error(self):
        for anim in ("breathing", "standby", "flower", "welcome",
                     "talking", "chill", "winddown"):
            self.pg.trigger(anim)
            for t in (0.0, 500.0, 2_000.0):
                self.render(t)


class TestRecordingThroughMixer(PlaygroundFixture):
    """The recording is a one-shot clip inside the AudioPlayer. We inject
    decoded data directly (no ffmpeg needed) and check the playground
    drives it correctly."""

    def setUp(self):
        super().setUp()
        self.audio = AudioPlayer(media_dir=self._td.name, tracks={})
        # 3 s of silence, "already decoded".
        self.audio._tracks[REC_CLIP] = {
            "file": "rec.wav", "label": "Recording", "enabled": False,
            "volume": 1.0, "loop": False, "clip": True,
            "path": "/x/rec.wav",
            "data": np.zeros((int(3 * _SR), 2), dtype=np.float32),
            "gain": 0.0, "pos": 0,
        }
        self.pg._audio = self.audio

    def test_play_with_recording_starts_clip(self):
        self.pg.set_timeline([clip("red", 0, 1)])
        self.pg.play(with_recording=True)
        self.render(0.0)
        tr = self.audio._tracks[REC_CLIP]
        self.assertTrue(tr["enabled"])
        self.assertEqual(tr["pos"], 0)

    def test_seek_aligns_recording_position(self):
        self.pg.set_timeline([clip("red", 0, 10)])
        self.pg.play(with_recording=True, start_sec=2.0)
        self.render(0.0)
        self.assertEqual(self.audio._tracks[REC_CLIP]["pos"], int(2.0 * _SR))

    def test_sequence_runs_until_recording_ends(self):
        # Timeline covers 1 s but the recording is 3 s — her voice must
        # not be cut off.
        self.pg.set_timeline([clip("red", 0, 1)])
        self.pg.play(with_recording=True)
        self.render(0.0)
        self.render(2_000.0)
        self.assertTrue(self.pg.snapshot()["playing"])
        self.render(3_100.0)
        self.assertFalse(self.pg.snapshot()["playing"])

    def test_stop_stops_recording(self):
        self.pg.set_timeline([clip("red", 0, 5)])
        self.pg.play(with_recording=True)
        self.render(0.0)
        self.pg.stop()
        self.assertFalse(self.audio._tracks[REC_CLIP]["enabled"])

    def test_without_recording_clip_stays_silent(self):
        self.pg.set_timeline([clip("red", 0, 5)])
        self.pg.play(with_recording=False)
        self.render(0.0)
        self.assertFalse(self.audio._tracks[REC_CLIP]["enabled"])

    def test_play_recording_without_file_is_safe(self):
        pg2 = Playground(self.config)            # no audio at all
        pg2.play_recording()                     # must not raise


if __name__ == "__main__":
    unittest.main()
