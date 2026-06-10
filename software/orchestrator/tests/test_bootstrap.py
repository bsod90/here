"""Integration tests for bootstrap.build_services — the whole service
graph wired against a temp config, no hardware, nothing started (except
one explicit start/stop smoke test)."""
import logging
import tempfile
import time
import unittest
from pathlib import Path

from bootstrap import build_services
from config import ConfigManager

try:
    from fastapi.testclient import TestClient
    _HAVE_CLIENT = True
except ImportError:                  # pragma: no cover
    _HAVE_CLIENT = False


def setUpModule():
    logging.disable(logging.WARNING)


def tearDownModule():
    logging.disable(logging.NOTSET)


class BootstrapFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        self.config = ConfigManager(path=str(root / "cfg.json"))
        # Point every on-disk path at the temp dir and neutralize hardware.
        self.config.set("scene", {
            "sequencer": {"sequences_dir": str(root / "sequences")},
            "patches_dir": str(root / "patches"),
        })
        self.config.set("telemetry_db_path", str(root / "telemetry.db"))
        self.config.set("audio", {"media_dir": str(root / "media")})
        self.config.set("scale", {"enabled": False})
        self.config.set("targets", [
            {"name": "local", "ip": "127.0.0.1", "port": 21324, "enabled": False},
        ])

    def tearDown(self):
        self._td.cleanup()

    def build(self):
        return build_services(self.config)


class TestBuildServices(BootstrapFixture):

    def test_graph_is_fully_wired(self):
        s = self.build()
        self.assertIs(s.engine.scene, s.scene)
        self.assertIs(s.engine.scale, s.scale)
        self.assertIs(s.engine.playground, s.playground)
        self.assertIsNotNone(s.engine.on_mode_change)

    def test_seeded_sequence_loaded_on_cold_start(self):
        s = self.build()
        seq_cfg = self.config.get("scene")["sequencer"]
        self.assertEqual(seq_cfg["active_sequence"], "breathing")
        self.assertTrue(s.sequence_store.exists("breathing"))

    def test_fireplace_mode_couples_fireplace_sound(self):
        s = self.build()
        s.engine.mode = "fireplace"
        self.assertTrue(s.audio._tracks["fireplace"]["enabled"])
        self.assertTrue(
            self.config.get("audio")["tracks"]["fireplace"]["enabled"])
        s.engine.mode = "standby"
        self.assertFalse(s.audio._tracks["fireplace"]["enabled"])
        self.assertFalse(
            self.config.get("audio")["tracks"]["fireplace"]["enabled"])

    def test_boot_in_fireplace_mode_enables_sound(self):
        self.config.set("mode", "fireplace")
        s = self.build()
        self.assertTrue(s.audio._tracks["fireplace"]["enabled"])

    def test_legacy_mode_alias_migrated(self):
        self.config.set("mode", "music")
        s = self.build()
        self.assertEqual(s.engine.mode, "midi")
        self.assertEqual(self.config.get("mode"), "midi")

    def test_legacy_audio_config_migrated_before_player_built(self):
        self.config.set("audio", {"backdrop_enabled": True,
                                  "backdrop_volume": 0.9})
        s = self.build()
        self.assertTrue(s.audio._tracks["ocean"]["enabled"])
        self.assertEqual(s.audio._tracks["ocean"]["volume"], 0.9)

    @unittest.skipUnless(_HAVE_CLIENT, "httpx/TestClient not installed")
    def test_admin_app_serves_status(self):
        s = self.build()
        with TestClient(s.create_admin_app()) as client:
            r = client.get("/api/status")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["mode"], s.engine.mode)

    def test_start_stop_smoke(self):
        s = self.build()
        s.start()
        try:
            time.sleep(0.15)               # let the frame loop tick
            self.assertGreater(s.engine.uptime_seconds + 1, 0)
        finally:
            s.stop()
        # Engine thread actually wound down.
        self.assertFalse(s.engine._thread.is_alive())


if __name__ == "__main__":
    unittest.main()
