"""Tests for the in-memory audio mixer (audio.py).

The real-time path is exercised by calling AudioPlayer._callback directly
with numpy buffers — no PortAudio / sound hardware involved. Sample
`data` arrays are injected straight into the track model so ffmpeg is
only needed for the one decode round-trip test (skipped if absent).
"""
import logging
import queue
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import audio as audio_mod
from audio import AudioPlayer, _BLOCKSIZE, _CHANNELS, _MON_PCM_QMAX, _RAMP_S, _SR


def setUpModule():
    logging.getLogger("audio").setLevel(logging.CRITICAL)


def tearDownModule():
    logging.getLogger("audio").setLevel(logging.NOTSET)


def make_player(tracks=None, media_dir=None):
    """AudioPlayer with no real files — loader thread exits immediately."""
    md = media_dir or tempfile.mkdtemp(prefix="here-audio-test-")
    return AudioPlayer(media_dir=md, tracks=tracks or {})


def inject(player, name, data, enabled=False, volume=0.5, gain=0.0):
    """Install a fully-loaded track directly into the mixer model."""
    player._tracks[name] = {
        "file": f"{name}.wav", "label": name.title(),
        "enabled": enabled, "volume": volume, "loop": True,
        "data": data, "gain": gain, "pos": 0,
    }


def run_block(player, frames=_BLOCKSIZE):
    out = np.zeros((frames, _CHANNELS), dtype=np.float32)
    player._callback(out, frames, None, None)
    return out


class TestTrackModel(unittest.TestCase):

    def test_constructor_normalizes_tracks(self):
        p = make_player(tracks={
            "ocean": {"file": "ocean.wav", "label": "Ocean",
                      "enabled": True, "volume": 2.5},
            "bare": {},
        })
        ocean = p._tracks["ocean"]
        self.assertTrue(ocean["enabled"])
        self.assertEqual(ocean["volume"], 1.0)      # clamped
        self.assertIsNone(ocean["data"])            # nothing decoded
        self.assertEqual(ocean["gain"], 0.0)
        bare = p._tracks["bare"]
        self.assertEqual(bare["label"], "Bare")
        self.assertFalse(bare["enabled"])

    def test_set_track_updates_and_clamps(self):
        p = make_player(tracks={"ocean": {"file": "o.wav"}})
        p.set_track("ocean", enabled=True, volume=1.7)
        self.assertTrue(p._tracks["ocean"]["enabled"])
        self.assertEqual(p._tracks["ocean"]["volume"], 1.0)
        p.set_track("ocean", volume=-0.3)
        self.assertEqual(p._tracks["ocean"]["volume"], 0.0)
        # enabled untouched when only volume passed
        self.assertTrue(p._tracks["ocean"]["enabled"])

    def test_set_track_unknown_is_noop(self):
        p = make_player()
        p.set_track("nope", enabled=True)           # must not raise

    def test_set_backdrop_aliases_ocean(self):
        p = make_player(tracks={"ocean": {"file": "o.wav"}})
        p.set_backdrop(enabled=True, volume=0.25)
        self.assertTrue(p._tracks["ocean"]["enabled"])
        self.assertEqual(p._tracks["ocean"]["volume"], 0.25)

    def test_snapshot_mirrors_legacy_backdrop_fields(self):
        p = make_player(tracks={"ocean": {"file": "o.wav", "volume": 0.4},
                                "fire": {"file": "f.wav"}})
        snap = p.snapshot()
        self.assertIn("ocean", snap["tracks"])
        self.assertIn("fire", snap["tracks"])
        self.assertEqual(snap["backdrop_volume"], 0.4)
        self.assertFalse(snap["backdrop_present"])  # no data loaded
        self.assertFalse(snap["running"])

    def test_snapshot_without_ocean_has_no_legacy_fields(self):
        p = make_player(tracks={"fire": {"file": "f.wav"}})
        snap = p.snapshot()
        self.assertNotIn("backdrop_enabled", snap)


class TestMixCallback(unittest.TestCase):

    def test_silent_when_no_tracks(self):
        p = make_player()
        out = run_block(p)
        self.assertEqual(float(np.abs(out).max()), 0.0)

    def test_gain_ramps_up_not_jumps(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=True, volume=1.0)
        out = run_block(p)
        step = _BLOCKSIZE / (_RAMP_S * _SR)
        # First block: gain glides 0 → step, so output starts silent and
        # ends near `step`, never at full volume.
        self.assertAlmostEqual(float(out[0, 0]), 0.0, places=5)
        self.assertLess(float(out[-1, 0]), step + 0.01)
        self.assertAlmostEqual(p._tracks["t"]["gain"], step, places=5)

    def test_gain_reaches_target_after_ramp_time(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=True, volume=0.8)
        blocks_needed = int(np.ceil(_RAMP_S * _SR / _BLOCKSIZE)) + 1
        for _ in range(blocks_needed):
            run_block(p)
        self.assertAlmostEqual(p._tracks["t"]["gain"], 0.8, places=5)
        out = run_block(p)
        self.assertAlmostEqual(float(out[0, 0]), 0.8, places=4)

    def test_disable_ramps_down_then_freezes(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=False, volume=1.0, gain=1.0)
        run_block(p)
        g_after_one = p._tracks["t"]["gain"]
        self.assertLess(g_after_one, 1.0)
        self.assertGreater(g_after_one, 0.0)        # ramping, not cut
        for _ in range(20):
            run_block(p)
        self.assertEqual(p._tracks["t"]["gain"], 0.0)
        pos_frozen = p._tracks["t"]["pos"]
        run_block(p)
        # Fully-silent track is skipped — playhead frozen.
        self.assertEqual(p._tracks["t"]["pos"], pos_frozen)

    def test_volume_change_is_a_ramp_without_restart(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=True, volume=1.0, gain=1.0)
        pos_before = p._tracks["t"]["pos"]
        p.set_track("t", volume=0.2)
        run_block(p)
        g = p._tracks["t"]["gain"]
        self.assertLess(g, 1.0)
        self.assertGreater(g, 0.2)                  # mid-glide
        # Playhead advanced — no restart from 0.
        self.assertEqual(p._tracks["t"]["pos"],
                         (pos_before + _BLOCKSIZE) % len(data))

    def test_loop_wraps_seamlessly(self):
        p = make_player()
        n = 700                                      # shorter than one block
        data = np.arange(n * _CHANNELS, dtype=np.float32).reshape(n, _CHANNELS)
        inject(p, "t", data, enabled=True, volume=1.0, gain=1.0)
        run_block(p)
        self.assertEqual(p._tracks["t"]["pos"], _BLOCKSIZE % n)

    def test_tracks_mix_independently(self):
        p = make_player()
        a = np.full((_SR, _CHANNELS), 0.25, dtype=np.float32)
        b = np.full((_SR, _CHANNELS), 0.5, dtype=np.float32)
        inject(p, "a", a, enabled=True, volume=1.0, gain=1.0)
        inject(p, "b", b, enabled=True, volume=1.0, gain=1.0)
        out = run_block(p)
        self.assertAlmostEqual(float(out[0, 0]), 0.75, places=4)
        # Touching b's volume leaves a's playhead/gain alone.
        p.set_track("b", volume=0.0)
        run_block(p)
        self.assertEqual(p._tracks["a"]["gain"], 1.0)

    def test_mix_clips_to_unit_range(self):
        p = make_player()
        loud = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "a", loud, enabled=True, volume=1.0, gain=1.0)
        inject(p, "b", loud, enabled=True, volume=1.0, gain=1.0)
        out = run_block(p)
        self.assertLessEqual(float(out.max()), 1.0)

    def test_unloaded_track_is_skipped(self):
        p = make_player(tracks={"ghost": {"file": "missing.wav",
                                          "enabled": True, "volume": 1.0}})
        out = run_block(p)                           # data is None
        self.assertEqual(float(np.abs(out).max()), 0.0)

    def test_callback_tees_mix_to_monitor_queue(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=True, volume=1.0, gain=1.0)
        run_block(p)
        chunk = p._mon_pcm_q.get_nowait()
        self.assertEqual(len(chunk), _BLOCKSIZE * _CHANNELS * 4)  # f32

    def test_monitor_queue_drops_oldest_when_full(self):
        p = make_player()
        data = np.ones((_SR, _CHANNELS), dtype=np.float32)
        inject(p, "t", data, enabled=True, volume=1.0, gain=1.0)
        for _ in range(_MON_PCM_QMAX + 5):
            run_block(p)                             # never raises
        self.assertEqual(p._mon_pcm_q.qsize(), _MON_PCM_QMAX)


class TestClips(unittest.TestCase):
    """One-shot clip playback (the meditation recording path)."""

    def make_clip_player(self, seconds=2.0):
        p = make_player()
        data = np.ones((int(seconds * _SR), _CHANNELS), dtype=np.float32)
        p._tracks["rec"] = {
            "file": "rec.wav", "label": "Rec", "enabled": False,
            "volume": 1.0, "loop": False, "clip": True,
            "path": "/x/rec.wav", "data": data, "gain": 0.0, "pos": 0,
        }
        return p

    def test_play_clip_seeks_and_enables(self):
        p = self.make_clip_player()
        p.play_clip("rec", start_sec=1.5)
        tr = p._tracks["rec"]
        self.assertTrue(tr["enabled"])
        self.assertEqual(tr["pos"], int(1.5 * _SR))
        self.assertEqual(tr["gain"], 0.0)        # re-ramps from silence

    def test_clip_advances_and_stops_at_end(self):
        p = self.make_clip_player(seconds=0.05)   # 2205 samples ≈ 3 blocks
        p.play_clip("rec")
        n = len(p._tracks["rec"]["data"])
        blocks = 0
        while p._tracks["rec"]["enabled"] and blocks < 10:
            run_block(p)
            blocks += 1
        tr = p._tracks["rec"]
        self.assertFalse(tr["enabled"])           # auto-stopped
        self.assertEqual(tr["pos"], n)
        self.assertEqual(tr["gain"], 0.0)
        st = p.clip_status("rec")
        self.assertFalse(st["playing"])

    def test_clip_does_not_loop(self):
        p = self.make_clip_player(seconds=0.05)
        p.play_clip("rec")
        for _ in range(10):
            run_block(p)
        pos_end = p._tracks["rec"]["pos"]
        run_block(p)                              # ended clip is inert
        self.assertEqual(p._tracks["rec"]["pos"], pos_end)

    def test_stop_clip_keeps_position_for_rampout(self):
        p = self.make_clip_player()
        p.play_clip("rec", start_sec=1.0)
        run_block(p)
        p.stop_clip("rec")
        # Position untouched — the ramp-out plays from where it was.
        self.assertGreaterEqual(p._tracks["rec"]["pos"], int(1.0 * _SR))
        self.assertFalse(p._tracks["rec"]["enabled"])

    def test_clip_status_reports_position_and_duration(self):
        p = self.make_clip_player(seconds=2.0)
        st = p.clip_status("rec")
        self.assertTrue(st["loaded"])
        self.assertFalse(st["playing"])
        self.assertAlmostEqual(st["duration_sec"], 2.0, places=3)
        p.play_clip("rec")
        run_block(p)
        st = p.clip_status("rec")
        self.assertTrue(st["playing"])
        self.assertAlmostEqual(st["position_sec"], _BLOCKSIZE / _SR, places=4)

    def test_clip_status_none_for_tracks_and_unknown(self):
        p = make_player(tracks={"ocean": {"file": "o.wav"}})
        self.assertIsNone(p.clip_status("ocean"))
        self.assertIsNone(p.clip_status("nope"))

    def test_clips_separated_from_tracks_in_snapshot(self):
        p = self.make_clip_player()
        snap = p.snapshot()
        self.assertNotIn("rec", snap["tracks"])
        self.assertIn("rec", snap["clips"])
        self.assertTrue(snap["clips"]["rec"]["loaded"])

    def test_register_clip_same_path_is_noop_after_load(self):
        p = self.make_clip_player()
        data_before = p._tracks["rec"]["data"]
        p.register_clip("rec", "/x/rec.wav")      # same path, already loaded
        self.assertIs(p._tracks["rec"]["data"], data_before)

    def test_register_clip_new_path_replaces(self):
        p = self.make_clip_player()
        p.register_clip("rec", "/y/other.wav")
        self.assertIsNone(p._tracks["rec"]["data"])  # awaiting decode
        self.assertEqual(p._tracks["rec"]["path"], "/y/other.wav")

    def test_clip_mixes_with_looping_track(self):
        p = self.make_clip_player()
        loop_data = np.full((_SR, _CHANNELS), 0.25, dtype=np.float32)
        inject(p, "ocean", loop_data, enabled=True, volume=1.0, gain=1.0)
        p._tracks["rec"]["gain"] = 1.0
        p._tracks["rec"]["enabled"] = True
        out = run_block(p)
        self.assertAlmostEqual(float(out[-1, 0]), 1.0, places=2)  # clipped sum
        # Stopping the clip leaves the ocean untouched.
        p.stop_clip("rec")
        for _ in range(20):
            out = run_block(p)
        self.assertAlmostEqual(float(out[0, 0]), 0.25, places=3)


class TestMonitorLifecycle(unittest.TestCase):

    def test_first_listener_starts_encoder_last_stops_it(self):
        p = make_player()
        with patch.object(p, "_start_encoder") as start, \
             patch.object(p, "_stop_encoder") as stop:
            q1, q2 = queue.Queue(), queue.Queue()
            sid1 = p.add_listener(None, q1)
            sid2 = p.add_listener(None, q2)
            self.assertEqual(start.call_count, 1)    # only the first
            p.remove_listener(sid1)
            stop.assert_not_called()                 # one listener left
            p.remove_listener(sid2)
            self.assertEqual(stop.call_count, 1)

    def test_stop_encoder_signals_end_of_stream(self):
        p = make_player()
        received = []

        class FakeLoop:
            def call_soon_threadsafe(self, fn, *a):
                fn(*a)

        q = queue.Queue()
        with patch.object(p, "_start_encoder"):
            p.add_listener(FakeLoop(), q)
        p._stop_encoder()                            # no proc — still EOFs
        self.assertIsNone(q.get_nowait())

    def test_enqueue_drops_oldest_on_full_listener_queue(self):
        q = queue.Queue(maxsize=2)
        AudioPlayer._enqueue(q, b"1")
        AudioPlayer._enqueue(q, b"2")
        AudioPlayer._enqueue(q, b"3")
        self.assertEqual(q.get_nowait(), b"2")
        self.assertEqual(q.get_nowait(), b"3")


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class TestDecode(unittest.TestCase):

    def test_decode_resamples_to_stereo_float32(self):
        # Mono 8 kHz, 0.25 s — _decode must upmix + resample to 44.1 k.
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tone.wav"
            sr, dur = 8000, 0.25
            n = int(sr * dur)
            with wave.open(str(path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                t = np.arange(n) / sr
                pcm = (np.sin(2 * np.pi * 440 * t) * 12000).astype(np.int16)
                w.writeframes(pcm.tobytes())
            data = AudioPlayer._decode(path)
        self.assertIsNotNone(data)
        self.assertEqual(data.shape[1], _CHANNELS)
        self.assertAlmostEqual(len(data) / _SR, dur, delta=0.05)
        self.assertEqual(data.dtype, np.float32)

    def test_decode_garbage_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "junk.wav"
            path.write_bytes(b"not audio at all")
            self.assertIsNone(AudioPlayer._decode(path))


class TestLoader(unittest.TestCase):

    def test_missing_file_leaves_track_unloaded(self):
        p = make_player(tracks={"ocean": {"file": "absent.wav"}})
        p._loader.join(timeout=5)
        self.assertIsNone(p._tracks["ocean"]["data"])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_loader_decodes_present_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "blip.wav"
            with wave.open(str(path), "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(_SR)
                w.writeframes(struct.pack("<4h", 1000, 1000, -1000, -1000))
            p = make_player(tracks={"blip": {"file": "blip.wav"}},
                            media_dir=td)
            p._loader.join(timeout=10)
            self.assertIsNotNone(p._tracks["blip"]["data"])
            snap = p.snapshot()
            self.assertTrue(snap["tracks"]["blip"]["present"])


if __name__ == "__main__":
    unittest.main()
