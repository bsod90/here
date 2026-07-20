"""Tests for the guided-meditation mode (meditation.py).

The MeditationController is driven off bench occupancy (a getter we control
here) and plays one of the enabled meditations once per occupancy, crossfading
with the ocean. We drive the state machine by stepping `tick()` directly — no
thread, no real mixer — with fakes for config / engine / audio, and a temp
media dir holding empty stand-in files (the fake audio never decodes them).
"""
import random
import tempfile
import unittest
from pathlib import Path

from meditation import (MeditationController, OCEAN, OCCUPIED_MODE,
                        PLAYGROUND_MODE, RIPPLES_MODE, IDLE_MODE, FADE_S,
                        RELEASE_PLAYING_S, _clip)


class FakeConfig:
    def __init__(self, meditation):
        self._d = {"audio": {"meditation": meditation}, "mode": IDLE_MODE,
                   "scale": {"release_seconds": 10.0}}

    def get(self, key, default=None):
        return self._d.get(key, default)

    def set(self, key, value):
        cur = self._d.get(key)
        if isinstance(cur, dict) and isinstance(value, dict):
            for k, v in value.items():
                if isinstance(cur.get(k), dict) and isinstance(v, dict):
                    cur[k].update(v)
                else:
                    cur[k] = v       # lists replace wholesale
        else:
            self._d[key] = value


class FakeEngine:
    def __init__(self, mode=IDLE_MODE):
        self.mode = mode


class FakeAudio:
    def __init__(self):
        self.tracks = {}
        self.clips = {}
        self.calls = []

    def set_track(self, name, enabled=None, volume=None, fade=None):
        self.calls.append(("set_track", name, enabled, volume, fade))
        tr = self.tracks.setdefault(name, {"enabled": False, "volume": 1.0})
        if enabled is not None:
            tr["enabled"] = bool(enabled)
        if volume is not None:
            tr["volume"] = float(volume)

    def register_clip(self, name, path, volume=1.0):
        self.calls.append(("register_clip", name, str(path), volume))
        self.clips[name] = {"file": str(path), "loaded": True, "playing": False,
                            "position_sec": 0.0, "duration_sec": 60.0}

    def play_clip(self, name, start_sec=0.0, fade=None):
        self.calls.append(("play_clip", name, start_sec, fade))
        c = self.clips.setdefault(name, {"loaded": True, "duration_sec": 60.0})
        c["playing"] = True
        c["position_sec"] = start_sec

    def stop_clip(self, name, fade=None):
        self.calls.append(("stop_clip", name, fade))
        c = self.clips.get(name)
        if c:
            c["playing"] = False

    def clip_status(self, name):
        return self.clips.get(name)

    def finish_clip(self, name):
        c = self.clips[name]
        c["playing"] = False
        c["position_sec"] = c["duration_sec"]


class Occ:
    def __init__(self, value=False):
        self.value = value

    def __call__(self):
        return self.value


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def make(items=None, volume=0.8, occupied=False, seed=0):
    """Build a controller over a temp media dir. `items` defaults to one
    enabled meditation (med1)."""
    td = tempfile.mkdtemp(prefix="here-med-test-")
    if items is None:
        items = [{"id": "med1", "label": "Meditation 1 [Nadia]",
                  "file": "meditation1.wav", "enabled": True}]
    # Touch a stand-in file for every item so _present() is true.
    for it in items:
        (Path(td) / it["file"]).write_bytes(b"x")
    cfg = FakeConfig({"volume": volume, "items": [dict(it) for it in items]})
    engine = FakeEngine(mode=IDLE_MODE)
    audio = FakeAudio()
    occ = Occ(occupied)
    clk = Clock()
    rel = []
    ctrl = MeditationController(cfg, engine, audio, media_dir=td,
                               occupancy_getter=occ,
                               release_setter=lambda s: rel.append(s),
                               clock=clk, rng=random.Random(seed))
    ctrl._rel = rel
    ctrl._clk = clk
    ctrl._td = td
    return ctrl, cfg, engine, audio, occ


def kinds(audio):
    return [c[0] for c in audio.calls]


def played_clip(audio):
    """The clip name of the most recent play_clip call."""
    for c in reversed(audio.calls):
        if c[0] == "play_clip":
            return c[1]
    return None


TWO = [
    {"id": "med1", "label": "M1", "file": "meditation1.wav", "enabled": True},
    {"id": "med2", "label": "M2", "file": "meditation2.wav", "enabled": True},
]


class TestEnabled(unittest.TestCase):

    def test_enabled_when_item_on_and_file_present(self):
        ctrl, *_ = make()
        self.assertTrue(ctrl.enabled())

    def test_disabled_when_no_item_on(self):
        items = [{"id": "med1", "label": "M1", "file": "meditation1.wav",
                  "enabled": False}]
        ctrl, *_ = make(items=items)
        self.assertFalse(ctrl.enabled())

    def test_disabled_ignores_occupancy(self):
        items = [{"id": "med1", "label": "M1", "file": "meditation1.wav",
                  "enabled": False}]
        ctrl, cfg, engine, audio, occ = make(items=items)
        occ.value = True
        ctrl.tick()
        self.assertNotIn("play_clip", kinds(audio))


class TestSingle(unittest.TestCase):

    def test_sit_plays_the_meditation_and_silences_ocean(self):
        ctrl, cfg, engine, audio, occ = make()
        occ.value = True
        ctrl.tick()
        self.assertFalse(audio.tracks[OCEAN]["enabled"])
        self.assertEqual(engine.mode, OCCUPIED_MODE)
        self.assertEqual(played_clip(audio), _clip("med1"))

    def test_finish_pauses_then_ripples(self):
        ctrl, cfg, engine, audio, occ = make()
        occ.value = True
        ctrl.tick()
        audio.finish_clip(_clip("med1"))
        ctrl.tick()
        self.assertEqual(engine.mode, OCCUPIED_MODE)   # still in the pause
        ctrl._clk.advance(5.1)
        ctrl.tick()
        self.assertEqual(engine.mode, RIPPLES_MODE)
        self.assertTrue(audio.tracks[OCEAN]["enabled"])

    def test_leave_rearms_and_restores_ocean(self):
        ctrl, cfg, engine, audio, occ = make()
        occ.value = True
        ctrl.tick()
        occ.value = False
        ctrl.tick()
        self.assertIn(("stop_clip", _clip("med1"), FADE_S), audio.calls)
        self.assertTrue(audio.tracks[OCEAN]["enabled"])
        self.assertEqual(engine.mode, IDLE_MODE)

    def test_release_dwell_long_while_playing_then_cleared(self):
        ctrl, cfg, engine, audio, occ = make()
        occ.value = True
        ctrl.tick()
        self.assertEqual(ctrl._rel[-1], RELEASE_PLAYING_S)
        occ.value = False
        ctrl.tick()
        self.assertIsNone(ctrl._rel[-1])


class FakePlayground:
    """Stub of the Playground controller — records visual-track calls."""

    def __init__(self, tracks=None):
        self.tracks = tracks or {}
        self.calls = []

    def has_track(self, mid):
        return bool(self.tracks.get(mid))

    def select(self, mid):
        self.calls.append(("select", mid))
        return True

    def play(self, with_recording=False, start_sec=0.0):
        self.calls.append(("play", with_recording))

    def stop(self, hold_black=False):
        self.calls.append(("stop", hold_black))


class TestPlaygroundVisuals(unittest.TestCase):
    """A sit plays the meditation's sequenced playground track (visuals
    only — the audio stays the controller's own clip); no track → the
    classic breathing circle; pause + ripples rest stay untouched."""

    def _make(self, tracks):
        ctrl, cfg, engine, audio, occ = make()
        engine.playground = FakePlayground(tracks)
        return ctrl, engine, audio, occ

    TRACK = {"med1": [{"animation": "x", "start_sec": 0, "duration_sec": 5}]}

    def test_sit_plays_the_sequenced_track(self):
        ctrl, engine, audio, occ = self._make(self.TRACK)
        occ.value = True
        ctrl.tick()
        self.assertEqual(engine.mode, PLAYGROUND_MODE)
        self.assertIn(("select", "med1"), engine.playground.calls)
        self.assertIn(("play", False), engine.playground.calls)
        # The audio is still OUR meditation clip, not the playground's.
        self.assertEqual(played_clip(audio), _clip("med1"))
        self.assertFalse(audio.tracks[OCEAN]["enabled"])

    def test_sit_without_track_falls_back_to_breathing(self):
        ctrl, engine, audio, occ = self._make({})
        occ.value = True
        ctrl.tick()
        self.assertEqual(engine.mode, OCCUPIED_MODE)
        self.assertNotIn(("play", False), engine.playground.calls)

    def test_finish_pauses_then_ripples_then_deferred_stop(self):
        ctrl, engine, audio, occ = self._make(self.TRACK)
        occ.value = True
        ctrl.tick()
        audio.finish_clip(_clip("med1"))
        ctrl.tick()
        self.assertEqual(engine.mode, PLAYGROUND_MODE)   # still in the pause
        self.assertNotIn(("stop", True), engine.playground.calls)
        ctrl._clk.advance(5.1)
        ctrl.tick()
        self.assertEqual(engine.mode, RIPPLES_MODE)      # rest screen
        # The stop is DEFERRED past the crossfade so the outgoing timeline
        # keeps rendering while it fades — not an instant snap to black.
        self.assertNotIn(("stop", True), engine.playground.calls)
        ctrl._clk.advance(3.6)
        ctrl.tick()
        self.assertIn(("stop", True), engine.playground.calls)
        self.assertTrue(audio.tracks[OCEAN]["enabled"])  # slow ocean return

    def test_vacate_stops_the_track_after_the_fade(self):
        ctrl, engine, audio, occ = self._make(self.TRACK)
        occ.value = True
        ctrl.tick()
        occ.value = False
        ctrl.tick()
        self.assertEqual(engine.mode, IDLE_MODE)
        self.assertNotIn(("stop", True), engine.playground.calls)
        ctrl._clk.advance(3.6)
        ctrl.tick()
        self.assertIn(("stop", True), engine.playground.calls)

    def test_resit_cancels_pending_stop(self):
        # Leave and sit again within the fade window: the deferred stop
        # from the old sit must NOT kill the new sit's playback.
        ctrl, engine, audio, occ = self._make(self.TRACK)
        occ.value = True
        ctrl.tick()
        occ.value = False
        ctrl.tick()                    # vacate → stop deferred
        occ.value = True
        ctrl.tick()                    # new sit before the deadline
        ctrl._clk.advance(4.0)
        ctrl.tick()
        self.assertNotIn(("stop", True), engine.playground.calls)
        self.assertEqual(engine.mode, PLAYGROUND_MODE)


class TestRandomNoRepeat(unittest.TestCase):

    def _play_once(self, ctrl, occ):
        occ.value = True
        ctrl.tick()                  # sit → play
        pid = ctrl._last_id
        occ.value = False
        ctrl.tick()                  # leave → re-arm
        return pid

    def test_two_enabled_never_repeat_consecutively(self):
        ctrl, cfg, engine, audio, occ = make(items=TWO, seed=3)
        picks = [self._play_once(ctrl, occ) for _ in range(12)]
        self.assertEqual(set(picks), {"med1", "med2"})        # both get used
        for a, b in zip(picks, picks[1:]):
            self.assertNotEqual(a, b, f"repeat in {picks}")

    def test_single_enabled_always_same(self):
        ctrl, cfg, engine, audio, occ = make(items=TWO, seed=1)
        # disable med2 → only med1 available
        ctrl.set_enabled("med2", False)
        picks = [self._play_once(ctrl, occ) for _ in range(5)]
        self.assertEqual(picks, ["med1"] * 5)


class TestToggleAndVolume(unittest.TestCase):

    def test_set_enabled_persists_and_changes_availability(self):
        ctrl, cfg, engine, audio, occ = make(items=TWO)
        ctrl.set_enabled("med1", False)
        ids = [it["id"] for it in ctrl._available()]
        self.assertEqual(ids, ["med2"])
        # persisted in config
        saved = {it["id"]: it["enabled"]
                 for it in cfg.get("audio")["meditation"]["items"]}
        self.assertFalse(saved["med1"])

    def test_set_enabled_unknown_id_returns_false(self):
        ctrl, *_ = make(items=TWO)
        self.assertFalse(ctrl.set_enabled("nope", True))

    def test_set_volume_applies_to_all_clips(self):
        ctrl, cfg, engine, audio, occ = make(items=TWO)
        ctrl.set_volume(0.3)
        self.assertEqual(audio.tracks[_clip("med1")]["volume"], 0.3)
        self.assertEqual(audio.tracks[_clip("med2")]["volume"], 0.3)
        self.assertAlmostEqual(cfg.get("audio")["meditation"]["volume"], 0.3)

    def test_state_lists_items(self):
        ctrl, *_ = make(items=TWO)
        st = ctrl.state()
        self.assertEqual([i["id"] for i in st["items"]], ["med1", "med2"])
        self.assertTrue(all(i["present"] for i in st["items"]))
        self.assertTrue(st["mode_enabled"])


if __name__ == "__main__":
    unittest.main()
