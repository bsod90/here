"""HTTP-level tests for the admin panel: inline core endpoints
(mode/status/targets/transport/config/logs), audio routes, playground
routes, and the WLED reverse proxy (with a faked upstream).

Uses FastAPI's TestClient (httpx). Skipped entirely if httpx isn't
installed (it's a dev-only dependency, not in requirements.txt).
"""
import gzip
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    _HAVE_CLIENT = True
except ImportError:                  # pragma: no cover
    _HAVE_CLIENT = False

from audio import AudioPlayer
from config import ConfigManager
from playground import Playground
from meditation import MeditationController
from admin.routes import create_app
from admin.routes import wled as wled_routes


class StubEngine:
    def __init__(self):
        self.mode = "standby"
        self.actual_fps = 30.0
        self.uptime_seconds = 42
        self.power_estimate = {"avg_watts": 12.0}
        self.playground = None
        self.on_mode_change = None

    def time_ms(self):
        return 0.0


class StubTransport:
    def __init__(self, targets=None):
        self._targets = list(targets or [])

    def update_targets(self, targets):
        self._targets = list(targets)

    def get_targets(self):
        return [dict(t) for t in self._targets]


@unittest.skipUnless(_HAVE_CLIENT, "httpx/TestClient not installed")
class AdminAppFixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        self.config = ConfigManager(path=str(root / "cfg.json"))
        self.media_dir = root / "media"
        self.media_dir.mkdir()
        self.config.set("audio", {"media_dir": str(self.media_dir)})
        # Stand-in files so the default meditation items read as present.
        for it in (self.config.get("audio") or {}).get("meditation", {}).get("items", []):
            (self.media_dir / it["file"]).write_bytes(b"x")
        self.engine = StubEngine()
        self.transport = StubTransport(self.config.get("targets"))
        self.audio = AudioPlayer(media_dir=self.media_dir,
                                 tracks=(self.config.get("audio") or {}).get("tracks"))
        self.playground = Playground(self.config, audio=self.audio)
        self.meditation = MeditationController(
            self.config, self.engine, self.audio, media_dir=self.media_dir)
        app = create_app(self.config, self.engine, self.transport,
                         audio=self.audio, playground=self.playground,
                         meditation=self.meditation)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self._td.cleanup()


class TestCoreEndpoints(AdminAppFixture):

    def test_index_is_no_store(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertIn("<html", r.text.lower())

    def test_status_shape(self):
        r = self.client.get("/api/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("mode", "fps", "uptime_s", "power"):
            self.assertIn(key, body)

    def test_set_mode_valid(self):
        r = self.client.post("/api/mode/fireplace")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.engine.mode, "fireplace")
        self.assertEqual(self.config.get("mode"), "fireplace")

    def test_set_mode_invalid(self):
        r = self.client.post("/api/mode/disco")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.engine.mode, "standby")

    def test_sensor_simulation(self):
        # The fixture's meditation controller is ENABLED, so "occupied"
        # defers the visuals to it (no direct breathing switch — that
        # flashed the circle at the start of sequenced sits); "empty"
        # still snaps to standby.
        r = self.client.post("/api/sensor/occupied")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["sensor"], "occupied")
        self.assertNotEqual(r.json()["mode"], "breathing")
        r = self.client.post("/api/sensor/empty")
        self.assertEqual(r.json()["mode"], "standby")
        r = self.client.post("/api/sensor/weird")
        self.assertEqual(r.status_code, 400)

    def test_config_roundtrip(self):
        r = self.client.put("/api/config",
                            json={"standby": {"spawn_rate": 9}})
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/config")
        self.assertEqual(r.json()["standby"]["spawn_rate"], 9)
        # Deep-merged — sibling keys survive.
        self.assertIn("sparkle_density", r.json()["standby"])

    def test_restore_defaults_section(self):
        self.config.set("standby", {"spawn_rate": 99})
        r = self.client.post("/api/defaults/restore/standby")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.config.get("standby")["spawn_rate"], 2)

    def test_restore_defaults_unknown_section(self):
        r = self.client.post("/api/defaults/restore/nonsense")
        self.assertEqual(r.status_code, 400)

    def test_targets_crud(self):
        n0 = len(self.client.get("/api/targets").json())
        r = self.client.post("/api/targets",
                             json={"name": "Second", "ip": "10.0.0.2"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["targets"]), n0 + 1)
        r = self.client.put(f"/api/targets/{n0}", json={"enabled": False})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.config.get("targets")[n0]["enabled"])
        r = self.client.put("/api/targets/99", json={})
        self.assertEqual(r.status_code, 404)
        r = self.client.delete(f"/api/targets/{n0}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.config.get("targets")), n0)
        r = self.client.delete("/api/targets/99")
        self.assertEqual(r.status_code, 404)

    def test_transport_settings(self):
        r = self.client.put("/api/transport", json={"fps": 25})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/transport").json()["fps"], 25)

    def test_logs_endpoint(self):
        r = self.client.get("/api/logs")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json()["logs"], list)

    def test_osc_state_disabled(self):
        r = self.client.get("/api/osc/state")
        self.assertEqual(r.json(), {})


class TestAudioRoutes(AdminAppFixture):

    def test_snapshot(self):
        r = self.client.get("/api/audio")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ocean", r.json()["tracks"])

    def test_put_track_updates_and_persists(self):
        r = self.client.put("/api/audio", json={"track": "fireplace",
                                                "enabled": True,
                                                "volume": 0.7})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["tracks"]["fireplace"]["enabled"])
        self.assertAlmostEqual(r.json()["tracks"]["fireplace"]["volume"], 0.7)
        saved = self.config.get("audio")["tracks"]["fireplace"]
        self.assertTrue(saved["enabled"])
        # The untouched track is untouched.
        self.assertFalse(r.json()["tracks"]["ocean"]["enabled"])

    def test_put_legacy_backdrop_fields(self):
        r = self.client.put("/api/audio", json={"backdrop_enabled": True,
                                                "backdrop_volume": 0.3})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["tracks"]["ocean"]["enabled"])
        self.assertAlmostEqual(r.json()["tracks"]["ocean"]["volume"], 0.3)

    def test_put_bad_volume(self):
        r = self.client.put("/api/audio", json={"volume": "loud"})
        self.assertEqual(r.status_code, 400)

    def test_put_volume_clamped(self):
        r = self.client.put("/api/audio", json={"track": "ocean",
                                                "volume": 7})
        self.assertEqual(r.json()["tracks"]["ocean"]["volume"], 1.0)

    def test_snapshot_includes_meditation(self):
        r = self.client.get("/api/audio")
        self.assertIn("meditation", r.json())
        self.assertIn("items", r.json()["meditation"])

    def test_meditation_get_lists_items(self):
        r = self.client.get("/api/meditation")
        self.assertEqual(r.status_code, 200)
        ids = [i["id"] for i in r.json()["items"]]
        self.assertEqual(ids, ["med1", "med2", "med4"])

    def test_put_meditation_volume_persists(self):
        r = self.client.put("/api/meditation", json={"volume": 0.4})
        self.assertEqual(r.status_code, 200)
        self.assertAlmostEqual(r.json()["volume"], 0.4)
        self.assertAlmostEqual(
            self.config.get("audio")["meditation"]["volume"], 0.4)

    def test_put_meditation_toggle_item(self):
        r = self.client.put("/api/meditation",
                            json={"id": "med2", "enabled": True})
        self.assertEqual(r.status_code, 200)
        items = {i["id"]: i["enabled"] for i in r.json()["items"]}
        self.assertTrue(items["med2"])
        saved = {i["id"]: i["enabled"]
                 for i in self.config.get("audio")["meditation"]["items"]}
        self.assertTrue(saved["med2"])

    def test_put_meditation_unknown_id(self):
        r = self.client.put("/api/meditation",
                            json={"id": "nope", "enabled": True})
        self.assertEqual(r.status_code, 404)

    def test_put_meditation_bad_volume(self):
        r = self.client.put("/api/meditation", json={"volume": "loud"})
        self.assertEqual(r.status_code, 400)


class TestPlaygroundRoutes(AdminAppFixture):

    def test_snapshot(self):
        r = self.client.get("/api/playground")
        self.assertEqual(r.status_code, 200)
        self.assertIn("animations", r.json())

    def test_trigger_switches_engine_to_playground(self):
        r = self.client.post("/api/playground/trigger/standby")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.engine.mode, "playground")
        self.assertEqual(r.json()["current"], "standby")

    def test_set_timeline(self):
        r = self.client.put("/api/playground", json={"timeline": [
            {"animation": "breathing", "start_sec": 0, "duration_sec": 5},
        ]})
        self.assertEqual(len(r.json()["timeline"]), 1)

    def test_snapshot_lists_meditations_and_wled(self):
        snap = self.client.get("/api/playground").json()
        self.assertIn("meditations", snap)
        self.assertIn("wled", snap)
        self.assertIn("palettes", snap)
        self.assertTrue(any(e["id"] == "wled_noise2d" for e in snap["wled"]))

    def test_select_binds_meditation(self):
        meds = self.client.get("/api/playground").json()["meditations"]
        if not meds:
            self.skipTest("no meditations configured in fixture")
        mid = meds[0]["id"]
        r = self.client.post(f"/api/playground/select/{mid}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["selected"], mid)

    def test_select_unknown_meditation(self):
        r = self.client.post("/api/playground/select/nope")
        self.assertEqual(r.status_code, 404)

    def test_waveform_unknown_meditation(self):
        r = self.client.get("/api/playground/waveform/nope")
        self.assertEqual(r.status_code, 404)

    def test_transcript_unknown_meditation(self):
        r = self.client.get("/api/playground/transcript/nope")
        self.assertEqual(r.status_code, 404)

    def test_transcript_missing_sidecar(self):
        meds = self.client.get("/api/playground").json()["meditations"]
        if not meds:
            self.skipTest("no meditations configured in fixture")
        r = self.client.get(f"/api/playground/transcript/{meds[0]['id']}")
        self.assertEqual(r.status_code, 404)

    def test_transcript_served_from_sidecar(self):
        meds = self.client.get("/api/playground").json()["meditations"]
        if not meds:
            self.skipTest("no meditations configured in fixture")
        med = meds[0]
        sidecar = self.media_dir / (med["file"] + ".transcript.json")
        sidecar.write_text(json.dumps({
            "language": "en",
            "segments": [{"start": 1.5, "end": 3.0, "text": "breathe in"}],
        }))
        r = self.client.get(f"/api/playground/transcript/{med['id']}")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["language"], "en")
        self.assertEqual(body["segments"][0]["text"], "breathe in")


class FakeUpstream:
    """Stand-in for urllib's response object in the WLED proxy."""

    def __init__(self, status=200, headers=None, body=b""):
        self.status = status
        self._headers = headers or {}
        self._body = body

    def getheaders(self):
        return list(self._headers.items())

    def read(self):
        return self._body


class TestWledProxy(AdminAppFixture):

    def test_wled_host_picks_first_enabled_and_strips_cidr(self):
        cfg = ConfigManager(path=str(Path(self._td.name) / "w.json"))
        cfg.set("targets", [
            {"name": "off", "ip": "10.0.0.1", "enabled": False},
            {"name": "on", "ip": "192.168.10.20/24", "enabled": True},
        ])
        self.assertEqual(wled_routes._wled_host(cfg), "192.168.10.20")

    def test_wled_host_none_without_targets(self):
        cfg = ConfigManager(path=str(Path(self._td.name) / "w2.json"))
        cfg.set("targets", [])
        self.assertIsNone(wled_routes._wled_host(cfg))

    def test_proxy_503_when_no_target(self):
        self.config.set("targets", [])
        r = self.client.get("/wled/json/state")
        self.assertEqual(r.status_code, 503)

    def test_bare_wled_redirects_to_slash(self):
        r = self.client.get("/wled", follow_redirects=False)
        self.assertEqual(r.status_code, 307)
        self.assertEqual(r.headers["location"], "/wled/")

    def test_html_geturl_rewritten_and_uncached(self):
        html = ('<html><script>function getURL(e){return '
                + wled_routes._GETURL_FROM + '+e}</script></html>')
        fake = FakeUpstream(headers={
            "Content-Type": "text/html",
            "Content-Encoding": "gzip",
            "ETag": '"abc"',
            "X-Frame-Options": "DENY",
        }, body=gzip.compress(html.encode()))
        with patch("urllib.request.urlopen", return_value=fake):
            r = self.client.get("/wled/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(wled_routes._GETURL_TO, r.text)
        self.assertNotIn(wled_routes._GETURL_FROM, r.text)
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertNotIn("x-frame-options", r.headers)
        self.assertNotIn("etag", r.headers)

    def test_binary_passthrough_untouched(self):
        body = bytes(range(256))
        fake = FakeUpstream(headers={"Content-Type": "application/octet-stream"},
                            body=body)
        with patch("urllib.request.urlopen", return_value=fake):
            r = self.client.get("/wled/presets.json")
        self.assertEqual(r.content, body)

    def test_conditional_headers_stripped_from_upstream_request(self):
        seen = {}

        def fake_urlopen(req, timeout=10):
            seen.update({k.lower(): v for k, v in req.header_items()})
            return FakeUpstream(headers={"Content-Type": "text/plain"},
                                body=b"ok")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            r = self.client.get("/wled/common.js",
                                headers={"If-None-Match": '"abc"',
                                         "If-Modified-Since": "yesterday"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("if-none-match", seen)
        self.assertNotIn("if-modified-since", seen)

    def test_upstream_error_is_502(self):
        with patch("urllib.request.urlopen",
                   side_effect=OSError("no route to host")):
            r = self.client.get("/wled/json/state")
        self.assertEqual(r.status_code, 502)


if __name__ == "__main__":
    unittest.main()
