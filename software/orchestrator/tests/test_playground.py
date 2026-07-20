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
from playground import Playground, _med_clip


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

    def test_has_track_reflects_timeline_content(self):
        self.assertFalse(self.pg.has_track(self.pg._selected))
        self.assertFalse(self.pg.has_track("nope"))
        self.pg.set_timeline([clip("red", 0, 2)])
        self.assertTrue(self.pg.has_track(self.pg._selected))

    def test_timeline_persists_to_config(self):
        self.pg.set_timeline([clip("red", 1, 2)])
        tracks = self.config.get("playground")["tracks"]
        # Persisted under the bound track (unbound when no meditations).
        saved = next(iter(tracks.values()))
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

    def test_sequence_ends_to_black(self):
        # After the timeline finishes, the floor stays BLACK — the final
        # clip's fade-out is the ending. It must neither snap back to the
        # button pressed before play NOR re-trigger the last clip's
        # animation (the post-meditation "mandala ghost flash" bug).
        self.pg.trigger("blue")
        self.pg.set_timeline([clip("blue", 0, 1), clip("red", 1, 1)])
        self.pg.play()
        self.render(0.0)
        self.assertTrue(self.pg.snapshot()["playing"])
        n_calls = len(self.calls)
        self.render(5_000.0)         # past the end
        self.assertFalse(self.pg.snapshot()["playing"])
        self.render(6_000.0)
        self.assertEqual(len(self.calls), n_calls)    # no animation rendered
        self.assertEqual(max(self.frame), 0)          # floor is dark

    def test_stop_hold_black_leaves_floor_dark(self):
        # The meditation hand-off stops playback WITHOUT falling back to
        # the last-triggered animation.
        self.pg.trigger("red")
        self.pg.set_timeline([clip("blue", 0, 10)])
        self.pg.play()
        self.render(0.0)
        self.pg.stop(hold_black=True)
        self.render(1_000.0)
        self.assertEqual(max(self.frame), 0)

    def test_editor_stop_returns_to_triggered_animation(self):
        self.pg.trigger("red")
        self.pg.set_timeline([clip("blue", 0, 10)])
        self.pg.play()
        self.render(0.0)
        self.pg.stop()                # the tab's ■ Stop keeps old behavior
        self.render(1_000.0)
        self.assertEqual(self.calls[-1][0], "red")

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
        for key in ("animations", "wled", "palettes", "current", "playing",
                    "timeline", "position_sec", "duration_sec",
                    "default_fade_sec", "meditations", "selected",
                    "selected_duration", "recording", "play_with_recording",
                    "recording_playing"):
            self.assertIn(key, snap)
        ids = [a["id"] for a in snap["animations"]]
        # Curated playground set (everything else was removed from the
        # registry; the underlying modules still exist for the engine).
        for builtin in ("breathing", "standby", "noise", "mandala", "waves",
                        "mandala2", "sunflower"):
            self.assertIn(builtin, ids)

    def test_position_none_when_stopped(self):
        self.assertIsNone(self.pg.snapshot()["position_sec"])

    def test_duration_covers_release_tail(self):
        self.pg.set_timeline([clip("red", 0, 4, fo=2.0)])
        self.assertAlmostEqual(self.pg.snapshot()["duration_sec"], 6.0)

    def test_builtin_animations_render_without_error(self):
        for anim in ("breathing", "standby", "flower", "welcome",
                     "talking", "chill", "winddown", "blobs", "ink", "noise", "mandala", "waves", "rain", "mandala2", "spiral", "disco", "sunflower",
                     "meadow", "waterlily", "dandelion", "eyes"):
            self.pg.trigger(anim)
            for t in (0.0, 500.0, 2_000.0):
                self.render(t)

    def test_eyes_renders_and_blinks(self):
        # Baked-frame animation: nonzero (inverted sketch glows), and the
        # blink means different loop positions paint different frames.
        self.pg.trigger("eyes")
        # The engine keeps ONE state dict per mode visit; a fresh dict per
        # render (the fixture default) would re-stamp the clock each frame.
        state = {}
        self.pg.render(self.frame, 100.0, state)   # stamps t0; fade starts
        self.pg.render(self.frame, 2_100.0, state) # fade-in done → glows
        a = bytes(self.frame)
        self.assertGreater(max(a), 0)
        self.pg.render(self.frame, 2_900.0, state) # ~0.8s on — mid-blink
        self.assertNotEqual(bytes(self.frame), a)


class TestRecordingThroughMixer(PlaygroundFixture):
    """The recording is a one-shot clip inside the AudioPlayer. We inject
    decoded data directly (no ffmpeg needed) and check the playground
    drives it correctly."""

    def setUp(self):
        super().setUp()
        # Bind a meditation (its audio is the playground's "recording").
        self.config.set("audio", {"meditation": {"items": [
            {"id": "med1", "label": "M1", "file": "rec.wav", "enabled": True}]}})
        self.pg._selected = "med1"
        self.clip = _med_clip("med1")
        self.audio = AudioPlayer(media_dir=self._td.name, tracks={})
        # 3 s of silence, "already decoded".
        self.audio._tracks[self.clip] = {
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
        tr = self.audio._tracks[self.clip]
        self.assertTrue(tr["enabled"])
        self.assertEqual(tr["pos"], 0)

    def test_seek_aligns_recording_position(self):
        self.pg.set_timeline([clip("red", 0, 10)])
        self.pg.play(with_recording=True, start_sec=2.0)
        self.render(0.0)
        self.assertEqual(self.audio._tracks[self.clip]["pos"], int(2.0 * _SR))

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
        self.assertFalse(self.audio._tracks[self.clip]["enabled"])

    def test_without_recording_clip_stays_silent(self):
        self.pg.set_timeline([clip("red", 0, 5)])
        self.pg.play(with_recording=False)
        self.render(0.0)
        self.assertFalse(self.audio._tracks[self.clip]["enabled"])

    def test_play_recording_without_file_is_safe(self):
        pg2 = Playground(self.config)            # no audio at all
        pg2.play_recording()                     # must not raise


if __name__ == "__main__":
    unittest.main()


class TestEngineFadeOut(unittest.TestCase):
    def test_render_playground_honors_fade_out(self):
        # THE "meditation ended abruptly" bug: the engine's playground
        # dispatcher dropped fade_out, so leaving playground mode rendered
        # the timeline at full brightness through the whole crossfade and
        # then snapped to black.
        from types import SimpleNamespace
        from animation_engine import _render_playground

        class PG:
            def render(self, frame, t_ms, state, fade_in=None):
                frame[:] = bytes([200]) * len(frame)

        engine = SimpleNamespace(playground=PG())
        full = bytearray(FRAME_BYTES)
        _render_playground(engine, full, 0.0, None, None, {})
        mid = bytearray(FRAME_BYTES)
        _render_playground(engine, mid, 0.0, None, 0.5, {})
        out = bytearray(FRAME_BYTES)
        _render_playground(engine, out, 0.0, None, 1.0, {})
        self.assertEqual(full[0], 200)
        self.assertAlmostEqual(mid[0], 100, delta=1)
        self.assertEqual(out[0], 0)


class TestMasterControls(PlaygroundFixture):
    """Global dials over every playground animation."""

    def test_master_brightness_scales_frame(self):
        self.config.set("playground", {"master": {"brightness": 0.5}})
        self.pg.trigger("blue")               # marker paints solid 200
        self.render(1_000.0)
        self.assertAlmostEqual(max(self.frame), 100, delta=2)

    def test_master_speed_stretches_animation_clock(self):
        self.config.set("playground", {"master": {"speed": 2.0}})
        self.pg.trigger("red")
        self.render(1_000.0)
        t1 = self.calls[-1][1]
        self.render(2_000.0)                  # +1 s real time
        t2 = self.calls[-1][1]
        self.assertAlmostEqual(t2 - t1, 2_000.0, delta=1.0)

    def test_master_speed_leaves_timeline_position_alone(self):
        # Sequenced sits must stay in sync with the voice: the SEQUENCE
        # advances in real time even when animations run 2x.
        self.config.set("playground", {"master": {"speed": 2.0}})
        self.pg.set_timeline([clip("red", 0, 2), clip("blue", 2, 60)])
        self.pg.play()
        self.render(0.0)
        self.render(1_000.0)                  # 1s real → still clip 1
        self.assertEqual(self.calls[-1][0], "red")
        self.render(3_000.0)                  # 3s real → clip 2
        self.assertEqual(self.calls[-1][0], "blue")
