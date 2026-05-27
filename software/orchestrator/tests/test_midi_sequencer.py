"""Tests for the true-MIDI sequencer — emits note_on / note_off pairs."""
import unittest

from scene.midi_sequencer import MidiSequencer


class FakeDispatcher:
    """Records every event in order."""
    def __init__(self):
        self.events: list[dict] = []
    def dispatch(self, event: dict) -> None:
        self.events.append(event)


class FakeClock:
    """Hand-cranked clock — drift-free for tests."""
    def __init__(self, beat=0.0):
        self._beat = beat
    def now_beat(self):
        return self._beat
    def advance(self, delta):
        self._beat += delta


def _types(disp: FakeDispatcher) -> list[str]:
    return [e["type"] for e in disp.events]


def _pitches(disp: FakeDispatcher) -> list[int]:
    return [e["pitch"] for e in disp.events]


class TestNoteStorage(unittest.TestCase):

    def test_set_notes_replaces(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 0, "length_beats": 1}])
        seq.set_notes([{"pitch": 1, "start_beat": 2, "length_beats": 0.5}])
        self.assertEqual(len(seq.notes), 1)
        self.assertEqual(seq.notes[0]["pitch"], 1)

    def test_set_notes_drops_out_of_range(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([
            {"pitch": 0,  "start_beat": -0.1, "length_beats": 1},   # negative
            {"pitch": 0,  "start_beat":  4.0, "length_beats": 1},   # at loop end
            {"pitch": 0,  "start_beat":  3.99, "length_beats": 1},  # valid
            {"pitch": 0,  "start_beat":  1.0, "length_beats": 0},   # zero len
            {"pitch": -1, "start_beat":  1.0, "length_beats": 1},   # bad pitch
        ])
        self.assertEqual(len(seq.notes), 1)

    def test_set_loop_length_preserves_all_notes(self):
        """Loop length changes are non-destructive — past-loop notes are
        kept (won't fire) so expanding the loop later brings them back."""
        seq = MidiSequencer(loop_length_beats=8)
        seq.set_notes([
            {"pitch": 0, "start_beat": 1.0, "length_beats": 1},
            {"pitch": 0, "start_beat": 6.0, "length_beats": 1},
        ])
        seq.set_loop_length(4)
        self.assertEqual(len(seq.notes), 2,
                         "shrinking loop must preserve notes past the new end")
        seq.set_loop_length(8)
        self.assertEqual(len(seq.notes), 2)


class TestPlayImmediate(unittest.TestCase):

    def test_fires_note_at_playhead(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 0.0, "length_beats": 1.0}])
        clk = FakeClock(beat=0.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        self.assertEqual(_types(disp), ["note_on"])
        self.assertEqual(disp.events[0]["pitch"], 0)

    def test_fires_note_when_clock_drifted(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 0.0, "length_beats": 1.0}])
        clk = FakeClock(beat=0.05)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        self.assertEqual(_types(disp), ["note_on"])

    def test_does_not_fire_distant_notes(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([
            {"pitch": 0, "start_beat": 0.0, "length_beats": 0.5},  # at playhead
            {"pitch": 1, "start_beat": 2.0, "length_beats": 0.5},  # far away
        ])
        clk = FakeClock(beat=0.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        self.assertEqual(_pitches(disp), [0])


class TestCrossing(unittest.TestCase):

    def test_note_on_fires_on_crossing(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1.0, "length_beats": 0.5}])
        clk = FakeClock(beat=0.5)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        disp.events.clear()
        clk.advance(0.7)
        seq.tick(clk, disp)
        # At cur=1.2, last=0.5 → note_on at 1.0 fires.
        self.assertEqual(_types(disp), ["note_on"])
        self.assertAlmostEqual(disp.events[0]["beat"], 1.0)

    def test_note_off_fires_at_note_end(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1.0, "length_beats": 0.5}])
        clk = FakeClock(beat=0.5)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        disp.events.clear()
        # Cross both note_on (1.0) and note_off (1.5) in one big tick.
        clk.advance(1.2)
        seq.tick(clk, disp)
        self.assertEqual(_types(disp), ["note_on", "note_off"])

    def test_note_off_alone_fires(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1.0, "length_beats": 1.0}])
        clk = FakeClock(beat=0.5)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        # Step forward past note_on (1.0), stop before note_off (2.0).
        clk.advance(0.7)   # cur = 1.2 → fires note_on
        seq.tick(clk, disp)
        disp.events.clear()
        clk.advance(1.0)   # cur = 2.2 → fires note_off
        seq.tick(clk, disp)
        self.assertEqual(_types(disp), ["note_off"])

    def test_loop_wrap_fires_both_sides(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([
            {"pitch": 0, "start_beat": 0.0, "length_beats": 0.5},  # on @ 0, off @ 0.5
            {"pitch": 1, "start_beat": 3.5, "length_beats": 0.25}, # on @ 3.5, off @ 3.75
        ])
        clk = FakeClock(beat=3.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        disp.events.clear()
        # Advance past loop end to cur = 0.2; wrap window = [3.0, 4) ∪ [0, 0.2).
        clk.advance(1.2)
        seq.tick(clk, disp)
        # Expected order: 3.5 note_on, 3.75 note_off (pitch 1), 0.0 note_on (pitch 0).
        # Note_off (0.5) didn't cross yet.
        names = [(e["pitch"], e["type"]) for e in disp.events]
        self.assertEqual(names, [(1, "note_on"), (1, "note_off"), (0, "note_on")])

    def test_note_spanning_loop_end_emits_off_in_next_iteration(self):
        seq = MidiSequencer(loop_length_beats=4)
        # Note starts at 3.5, length 1.0 → ends at (3.5+1.0) % 4 = 0.5.
        seq.set_notes([{"pitch": 0, "start_beat": 3.5, "length_beats": 1.0}])
        clk = FakeClock(beat=3.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        disp.events.clear()
        clk.advance(1.0)   # cur = 0.0 (mod 4); window [3.0, 0.0)? actually mod gives cur=0.0
        # Note: cur = 4.0 % 4 = 0.0; that equals last_pos boundary…
        # Move a tiny bit further to be safe.
        clk.advance(0.05)  # cur = 0.05
        seq.tick(clk, disp)
        # Crossed: note_on at 3.5 only (note_off at 0.5 hasn't been crossed yet).
        self.assertEqual(_types(disp), ["note_on"])
        # Continue to cross the off at 0.5.
        clk.advance(0.6)   # cur = 0.65
        seq.tick(clk, disp)
        self.assertIn("note_off", _types(disp))


class TestPlayStop(unittest.TestCase):

    def test_stop_silences_subsequent_ticks(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 2.5, "length_beats": 1}])
        clk = FakeClock(beat=2.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        seq.stop()
        clk.advance(2.0)
        seq.tick(clk, disp)
        self.assertEqual(disp.events, [])

    def test_resync_skips_one_window(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1.0, "length_beats": 1}])
        clk = FakeClock(beat=0.0)
        disp = FakeDispatcher()
        seq.play(clock=clk, dispatcher=disp)
        disp.events.clear()
        # Big jump in playhead (simulates phase snap).
        clk.advance(2.0)
        seq.resync_to_playhead()
        seq.tick(clk, disp)
        # First tick after resync only records position, no fires.
        self.assertEqual(disp.events, [])
        # Subsequent ticks resume crossings.
        clk.advance(1.5)   # cross note_off at 2.0
        seq.tick(clk, disp)
        self.assertIn("note_off", _types(disp))


class TestSnapshot(unittest.TestCase):
    def test_snapshot_reports_state_while_playing(self):
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1, "length_beats": 1}])
        clk = FakeClock(beat=2.5)
        seq.play(clock=clk, dispatcher=FakeDispatcher())
        snap = seq.snapshot(clk)
        self.assertTrue(snap["playing"])
        self.assertEqual(snap["loop_length_beats"], 4)
        self.assertAlmostEqual(snap["playhead_beat"], 2.5)
        self.assertEqual(len(snap["notes"]), 1)

    def test_snapshot_freezes_playhead_when_stopped(self):
        """Engine clock keeps going, but the sequencer's reported
        playhead freezes at the stop moment so the UI timeline stops."""
        seq = MidiSequencer(loop_length_beats=4)
        seq.set_notes([{"pitch": 0, "start_beat": 1, "length_beats": 1}])
        clk = FakeClock(beat=0.0)
        seq.play(clock=clk, dispatcher=FakeDispatcher())
        clk.advance(2.5)   # clock advances to beat 2.5
        seq.stop(clock=clk)
        clk.advance(10.0)  # engine clock keeps going; playhead should not
        snap = seq.snapshot(clk)
        self.assertFalse(snap["playing"])
        self.assertAlmostEqual(snap["playhead_beat"], 2.5,
                               msg="playhead should freeze at stop")


if __name__ == "__main__":
    unittest.main()
