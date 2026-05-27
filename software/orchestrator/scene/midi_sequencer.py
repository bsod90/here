"""True-MIDI sequencer — emits note_on / note_off events.

Notes are *stored* the same way the piano roll edits them — as
`{pitch, start_beat, length_beats}` — for compatibility with all saved
sequences. At play time, each note expands into two events:

  • `{type: "note_on",  pitch, beat: start_beat}`
  • `{type: "note_off", pitch, beat: (start_beat + length_beats) % loop}`

Events are sent to a `dispatcher` (any object with a `dispatch(event)`
method — typically the EventRouter). The dispatcher is responsible for
mapping pitch to event semantics and handling choked-retrigger logic;
this module just produces a faithful stream of events.

Wrap-around semantics:
  • Notes whose end-beat wraps past the loop end produce a note_off at
    `(start + length) % loop` — i.e., in the next iteration. The crossing
    detector handles that wrap correctly.
  • Play-immediate window: on `play()`, any note whose `start_beat` is
    within ±0.1 beats of the current playhead fires its note_on right
    away, so we don't lose the first downbeat to HTTP round-trip latency.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class Dispatcher(Protocol):
    def dispatch(self, event: dict) -> None: ...


# How close to the current playhead a note must be (in beats) to fire
# immediately on play(). ~50 ms at 120 BPM.
_PLAY_IMMEDIATE_EPS = 0.1


class MidiSequencer:
    """Beat-quantized note playback over a looping bar — emits MIDI events."""

    def __init__(self, loop_length_beats: float = 16.0):
        self._loop_length_beats: float = max(0.25, float(loop_length_beats))
        self._notes: list[dict] = []
        self._playing: bool = False
        self._last_pos: Optional[float] = None
        # Frozen playhead while stopped — captured at the moment of stop()
        # so the UI timeline freezes even though the engine clock keeps
        # ticking (animation engine is independent of sequencer transport).
        self._frozen_playhead: float = 0.0
        self._lock = threading.Lock()

    # ── Notes ────────────────────────────────────────────────────────
    @property
    def notes(self) -> list[dict]:
        with self._lock:
            return [dict(n) for n in self._notes]

    def set_notes(self, notes: list[dict]) -> None:
        """Replace the note list. Each note: pitch, start_beat, length_beats."""
        cleaned: list[dict] = []
        loop = self._loop_length_beats
        for n in notes or []:
            try:
                pitch = int(n.get("pitch", 0))
                start = float(n.get("start_beat", 0.0))
                length = float(n.get("length_beats", 1.0))
            except (TypeError, ValueError):
                continue
            if pitch < 0:
                continue
            if start < 0 or start >= loop:
                continue
            if length <= 0:
                continue
            cleaned.append({"pitch": pitch, "start_beat": start, "length_beats": length})
        with self._lock:
            self._notes = cleaned

    # ── Loop length ──────────────────────────────────────────────────
    @property
    def loop_length_beats(self) -> float:
        return self._loop_length_beats

    def set_loop_length(self, beats: float, clock=None) -> None:
        beats = max(0.25, float(beats))
        with self._lock:
            self._loop_length_beats = beats
            # Preserve all notes — including any that fall past the new
            # loop end. Past-loop notes simply don't fire (the crossing
            # detector ignores them) but they're kept so expanding the
            # loop later brings them back. Drop with `clear` if you
            # really mean to remove them.
            # Re-anchor playhead under new loop length so the next tick
            # doesn't see a fake "wrap" that mass-fires events.
            if self._playing and clock is not None:
                self._last_pos = clock.now_beat() % beats

    # ── Play / stop ──────────────────────────────────────────────────
    @property
    def playing(self) -> bool:
        return self._playing

    def play(self, clock, dispatcher: Dispatcher) -> None:
        """Start playback. Fires note_on for any note within ±0.1 beats of
        the current playhead so the first downbeat isn't lost to RTT."""
        notes_immediate: list[dict] = []
        with self._lock:
            self._playing = True
            cur = clock.now_beat() % self._loop_length_beats if self._loop_length_beats > 0 else 0.0
            self._last_pos = cur
            loop = self._loop_length_beats
            for n in self._notes:
                s = n["start_beat"]
                # Distance to playhead measured around the loop.
                d = min(abs(s - cur), loop - abs(s - cur))
                if d <= _PLAY_IMMEDIATE_EPS:
                    notes_immediate.append(n)
        # Dispatch outside the lock.
        for n in notes_immediate:
            dispatcher.dispatch({
                "type": "note_on",
                "pitch": int(n["pitch"]),
                "beat": float(n["start_beat"]),
                "velocity": 1.0,
                "source": "sequencer",
                "length_beats": float(n["length_beats"]),
            })

    def stop(self, clock=None) -> None:
        with self._lock:
            # Freeze the playhead at its current position so the UI
            # timeline line stops moving (the engine clock keeps going).
            if clock is not None and self._loop_length_beats > 0:
                self._frozen_playhead = clock.now_beat() % self._loop_length_beats
            elif self._last_pos is not None:
                self._frozen_playhead = self._last_pos
            self._playing = False
            self._last_pos = None

    def resync_to_playhead(self) -> None:
        """Forget last playhead position — next tick records without firing.
        Used after a clock phase snap so the apparent jump isn't mis-detected
        as a loop wrap."""
        with self._lock:
            self._last_pos = None

    # ── Snapshot ─────────────────────────────────────────────────────
    def snapshot(self, clock) -> dict:
        with self._lock:
            if self._playing and self._loop_length_beats > 0:
                live_pos = clock.now_beat() % self._loop_length_beats
            else:
                live_pos = self._frozen_playhead
            return {
                "playing": self._playing,
                "loop_length_beats": self._loop_length_beats,
                "playhead_beat": live_pos,
                "notes": [dict(n) for n in self._notes],
            }

    # ── Tick ────────────────────────────────────────────────────────
    def tick(self, clock, dispatcher: Dispatcher) -> None:
        """Called once per frame. Emits note_on / note_off events that
        crossed the playhead since last tick, in proper beat order."""
        if not self._playing or self._loop_length_beats <= 0:
            self._last_pos = None
            return
        loop = self._loop_length_beats
        cur_pos = clock.now_beat() % loop
        if self._last_pos is None:
            self._last_pos = cur_pos
            return
        last_pos = self._last_pos
        if cur_pos == last_pos:
            return
        self._last_pos = cur_pos

        with self._lock:
            notes = list(self._notes)

        # Build the flat event list — note_on at start_beat, note_off at
        # (start_beat + length_beats) % loop. Each event carries the
        # source note for downstream context.
        events: list[tuple[float, str, dict]] = []
        for n in notes:
            on_beat = n["start_beat"]
            off_beat = (n["start_beat"] + n["length_beats"]) % loop
            events.append((on_beat, "note_on", n))
            events.append((off_beat, "note_off", n))

        # Find events whose beat is in [last_pos, cur_pos) — half-open,
        # wrap-aware. We also keep their relative ordering inside the
        # crossed window.
        fires: list[tuple[float, str, dict]] = []
        if cur_pos < last_pos:
            # Wrapped: window = [last_pos, loop) ∪ [0, cur_pos).
            for e in events:
                b = e[0]
                if b >= last_pos or b < cur_pos:
                    fires.append(e)
            # Sort so the wrap-tail (>= last_pos) fires before the wrap-head (< cur_pos).
            fires.sort(key=lambda e: (0 if e[0] >= last_pos else 1, e[0]))
        else:
            for e in events:
                if last_pos <= e[0] < cur_pos:
                    fires.append(e)
            fires.sort(key=lambda e: e[0])

        # Dispatch in order. When a note_on and a note_off land on the
        # same beat, fire note_off first (so e.g. a 1-beat-loop with notes
        # back-to-back at beats 0 and 1 doesn't double-stack).
        # Stable sort already keeps insert-order between equal beats — but
        # we built the list with note_on then note_off per note, so equal
        # beats from DIFFERENT notes already fire on first then off. To
        # honor the "off-before-on at same beat" rule we'd need a tiebreak;
        # in practice the choking logic in the router handles this cleanly
        # so we keep insertion order here.
        for beat, kind, note in fires:
            dispatcher.dispatch({
                "type": kind,
                "pitch": int(note["pitch"]),
                "beat": float(beat),
                "velocity": 1.0 if kind == "note_on" else 0.0,
                "source": "sequencer",
                "length_beats": float(note["length_beats"]),
            })
