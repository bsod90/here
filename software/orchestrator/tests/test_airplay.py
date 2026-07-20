"""AirPlay receiver tests — FIFO frame path, engine-mode takeover, the
audio mixer's aux input, and the admin routes. uxplay itself is never
launched (its process management is monkeypatched out)."""
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np

from airplay import AirPlayReceiver
from animation_engine import MODE_REGISTRY, _render_airplay
from audio import AudioPlayer
from config import ConfigManager

try:
    from fastapi.testclient import TestClient
    _HAVE_CLIENT = True
except ImportError:                  # pragma: no cover
    _HAVE_CLIENT = False


_FRAME_BYTES = 12          # tiny 2×2 "matrix" keeps the FIFO tests fast


class FakeEngine:
    def __init__(self):
        self.mode = "standby"
        self.airplay = None


class FakeAudio:
    def __init__(self):
        self.fed = b""
        self.volume = None

    def feed_aux(self, pcm, volume=1.0):
        self.fed += pcm
        self.volume = volume


def _wait(cond, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return False


class ReceiverFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        self.config = ConfigManager(path=str(root / "cfg.json"))
        self.config.set("airplay", {
            "enabled": True,
            "data_dir": str(root / "data"),
            "idle_timeout_s": 0.3,
            "volume": 0.8,
        })
        self.engine = FakeEngine()
        self.audio = FakeAudio()
        self.rx = AirPlayReceiver(self.config, engine=self.engine,
                                  audio=self.audio,
                                  frame_bytes=_FRAME_BYTES)
        # Never launch a real uxplay from the test suite.
        self.rx._launch = lambda: None
        self.engine.airplay = self.rx

    def tearDown(self):
        self.rx.stop()
        self._td.cleanup()

    def _write_fifo(self, path, data):
        """Writer runs on a thread — opening a FIFO for write blocks until
        the reader's fd exists, which the receiver creates lazily."""
        def w():
            with open(path, "wb") as f:
                f.write(data)
                f.flush()
        t = threading.Thread(target=w, daemon=True)
        t.start()
        return t


class TestVideoPath(ReceiverFixture):
    def test_frames_flow_and_mode_takeover_and_restore(self):
        self.rx.start()
        self.assertTrue(_wait(lambda: self.rx.video_fifo.is_fifo()))

        f1 = bytes(range(_FRAME_BYTES))
        f2 = bytes(reversed(range(_FRAME_BYTES)))
        self._write_fifo(self.rx.video_fifo, f1 + f2).join(timeout=2.0)

        self.assertTrue(_wait(lambda: self.rx.latest_frame() == f2))
        self.assertEqual(self.engine.mode, "airplay")
        self.assertTrue(self.rx.status()["streaming"])
        self.assertEqual(self.rx.status()["frames"], 2)

        # No more frames → idle timeout hands the mode back.
        time.sleep(0.4)
        self.rx.poke()
        self.assertTrue(_wait(lambda: self.engine.mode == "standby"))
        self.assertFalse(self.rx.status()["streaming"])

    def test_no_restore_if_mode_changed_meanwhile(self):
        self.rx.start()
        self.assertTrue(_wait(lambda: self.rx.video_fifo.is_fifo()))
        self._write_fifo(self.rx.video_fifo,
                         b"\x01" * _FRAME_BYTES).join(timeout=2.0)
        self.assertTrue(_wait(lambda: self.engine.mode == "airplay"))
        # Meditation (or the user) takes the mode while streaming…
        self.engine.mode = "playground"
        time.sleep(0.4)
        self.rx.poke()
        _wait(lambda: not self.rx.status()["streaming"])
        # …the receiver must not stomp it on idle.
        self.assertEqual(self.engine.mode, "playground")

    def test_partial_frame_is_held_until_complete(self):
        self.rx.start()
        self.assertTrue(_wait(lambda: self.rx.video_fifo.is_fifo()))
        half = _FRAME_BYTES // 2
        self._write_fifo(self.rx.video_fifo, b"\x05" * half).join(timeout=2.0)
        time.sleep(0.3)
        self.assertIsNone(self.rx.latest_frame())


class TestAudioPath(ReceiverFixture):
    def test_audio_feeds_mixer_with_configured_volume(self):
        self.rx.start()
        self.assertTrue(_wait(lambda: self.rx.audio_fifo.is_fifo()))
        pcm = b"\x00\x01\x02\x03" * 100          # whole 4-byte frames
        self._write_fifo(self.rx.audio_fifo, pcm).join(timeout=2.0)
        self.assertTrue(_wait(lambda: len(self.audio.fed) == len(pcm)))
        self.assertEqual(self.audio.fed, pcm)
        self.assertAlmostEqual(self.audio.volume, 0.8)

    def test_unaligned_tail_not_fed(self):
        self.rx.start()
        self.assertTrue(_wait(lambda: self.rx.audio_fifo.is_fifo()))
        self._write_fifo(self.rx.audio_fifo, b"\xAA" * 10).join(timeout=2.0)
        _wait(lambda: len(self.audio.fed) >= 8)
        time.sleep(0.2)
        self.assertEqual(len(self.audio.fed), 8)   # 10 → two whole frames


class TestCommand(ReceiverFixture):
    def test_sink_chain_flips_vertically_by_default(self):
        cmd = " ".join(self.rx._cmd())
        self.assertIn("videoflip method=vertical-flip", cmd)
        self.assertIn("aspectratiocrop aspect-ratio=1/1", cmd)

    def test_flip_none_removes_element(self):
        self.config.set("airplay", {"video_flip": "none"})
        self.assertNotIn("videoflip", " ".join(self.rx._cmd()))


class TestDisabled(ReceiverFixture):
    def test_disabled_receiver_reads_nothing(self):
        self.config.set("airplay", {"enabled": False})
        self.rx.start()
        time.sleep(0.3)
        self.assertFalse(self.rx.video_fifo.exists())
        self.assertFalse(self.rx.status()["streaming"])

    def test_test_pattern_requires_enabled(self):
        self.config.set("airplay", {"enabled": False})
        self.assertFalse(self.rx.start_test())


class TestEngineMode(unittest.TestCase):
    def test_registered(self):
        self.assertIn("airplay", MODE_REGISTRY)

    def test_render_blits_latest_frame(self):
        class Svc:
            def latest_frame(self):
                return bytes([10, 20, 30] * 4)
        eng = FakeEngine()
        eng.airplay = Svc()
        frame = bytearray(12)
        _render_airplay(eng, frame, 0.0, None, None, {})
        self.assertEqual(bytes(frame), bytes([10, 20, 30] * 4))

    def test_render_black_without_frames(self):
        eng = FakeEngine()
        eng.airplay = None
        frame = bytearray(b"\xFF" * 12)
        _render_airplay(eng, frame, 0.0, None, None, {})
        self.assertEqual(bytes(frame), b"\x00" * 12)

    def test_render_applies_fades(self):
        class Svc:
            def latest_frame(self):
                return bytes([200] * 12)
        eng = FakeEngine()
        eng.airplay = Svc()
        frame = bytearray(12)
        _render_airplay(eng, frame, 0.0, 0.5, None, {})
        self.assertTrue(all(b == 100 for b in frame))


class TestAuxMix(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.player = AudioPlayer(media_dir=self._td.name)

    def tearDown(self):
        self.player.stop()
        self._td.cleanup()

    def _block(self, frames=1024):
        out = np.zeros((frames, 2), dtype=np.float32)
        self.player._callback(out, frames, None, None)
        return out

    def _feed_sine(self, blocks=1):
        t = np.arange(1024 * blocks)
        wave = (np.sin(2 * np.pi * 440 * t / 44100) * 0.5 * 32767).astype(np.int16)
        stereo = np.repeat(wave, 2).tobytes()
        self.player.feed_aux(stereo, volume=1.0)

    def test_aux_ramps_in_and_mixes(self):
        for _ in range(8):
            self._feed_sine()
        peak = 0.0
        for _ in range(8):
            peak = max(peak, float(np.abs(self._block()).max()))
        self.assertGreater(peak, 0.1)

    def test_aux_silent_when_starved(self):
        for _ in range(4):
            self._feed_sine()
        for _ in range(30):                 # drain ring + ramp out
            self._block()
        time.sleep(0.3)                     # fed-recently window expires
        out = self._block()
        self.assertLess(float(np.abs(out).max()), 1e-4)

    def test_master_gate_silences_aux(self):
        self.player.set_master_enabled(False)
        for _ in range(200):                # master glide is 2 s ≈ 86 blocks
            self._feed_sine()
            out = self._block()
        self.assertLess(float(np.abs(out).max()), 1e-4)

    def test_ring_is_bounded(self):
        for _ in range(60):                 # ~1.4 s of audio at 1024/block
            self._feed_sine()
        self.assertLessEqual(self.player._aux_len, 44100 // 2)

    def test_aux_active_flag(self):
        self.assertFalse(self.player.aux_active())
        self._feed_sine()
        self.assertTrue(self.player.aux_active())


@unittest.skipUnless(_HAVE_CLIENT, "httpx/TestClient not installed")
class TestAirplayRoutes(unittest.TestCase):
    def setUp(self):
        from admin.routes import create_app
        from tests.test_admin_routes import StubEngine, StubTransport
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        self.config = ConfigManager(path=str(root / "cfg.json"))
        self.config.set("airplay", {"enabled": False,
                                    "data_dir": str(root / "data")})
        self.rx = AirPlayReceiver(self.config, engine=None, audio=None,
                                  frame_bytes=_FRAME_BYTES)
        self.rx._launch = lambda: None
        app = create_app(self.config, StubEngine(), StubTransport(),
                         airplay=self.rx)
        self.client = TestClient(app)

    def tearDown(self):
        self.rx.stop()
        self._td.cleanup()

    def test_get_status(self):
        r = self.client.get("/api/airplay")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertFalse(body["enabled"])
        self.assertIn("installed", body)

    def test_put_toggle_and_name(self):
        r = self.client.put("/api/airplay",
                            json={"enabled": True, "name": "HERE floor"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["enabled"])
        self.assertEqual(r.json()["name"], "HERE floor")
        cfg = self.config.get("airplay")
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["name"], "HERE floor")

    def test_put_volume_validation(self):
        r = self.client.put("/api/airplay", json={"volume": "loud"})
        self.assertEqual(r.status_code, 400)
        r = self.client.put("/api/airplay", json={"volume": 0.4})
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.json()["volume"], 0.4)

    def test_put_name_validation(self):
        r = self.client.put("/api/airplay", json={"name": ""})
        self.assertEqual(r.status_code, 400)

    def test_test_pattern_requires_enabled(self):
        r = self.client.post("/api/airplay/test", json={})
        self.assertEqual(r.status_code, 409)


if __name__ == "__main__":
    unittest.main()
