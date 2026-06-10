"""Nadia's Playground — an isolated experimentation mode.

See docs/nadia_playground.md for the full "what & why". In short: a safe
enclave for a non-technical collaborator (Nadia) to build a guided
meditation by sequencing animations on a REAL seconds timeline over her
own recorded audio — without touching breathing/standby/scene.

Kept deliberately isolated:
  * its own mode ("playground" in animation_engine.MODE_REGISTRY)
  * its own config section ("playground")
  * its own routes (admin/routes/playground.py) + admin tab

Timeline model (v2 — "record audio first, then cover it with clips"):
  * clips: {animation, start_sec, duration_sec[, fade_in_sec, fade_out_sec]}
  * every clip eases in over fade_in_sec at its head, and eases out over
    fade_out_sec PAST its end (a release tail, like a DAW clip). Butted
    clips therefore crossfade naturally: the outgoing clip is still
    fading down while the incoming one ramps up. Gaps fade to dark.
  * overlapping clips all render and blend by weight (no more
    "topmost wins" hard cut).
  * the playhead position + total duration are exposed in snapshot();
    play(start_sec=…) seeks — both the animations and the recording
    start from that offset, sample-aligned through the audio mixer.

Her meditation recording plays through the shared AudioPlayer as a
one-shot clip (audio.register_clip/play_clip): it starts within ~23 ms
of the animations and mixes cleanly with the ambience tracks (the old
implementation forked an ffplay subprocess — ~0.5 s of unpredictable
start latency, useless for syncing animation cues to the voice).

ADDING A NEW ANIMATION (Claude does this when Nadia describes an idea):
  1. Write a render module under animations/ with
     `render(frame, time_ms, params, state)` that paints the 44×44 frame
     (see animations/welcome.py for the pattern; numpy, self-contained,
     heavily-commented DEFAULTS dict).
  2. Register it in `Playground._build_registry()` with a friendly label
     and its config.playground.<name> params section.
  It then auto-appears as a trigger button AND a timeline lane in her tab.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from animations import breathing as _breathing
from animations import standby as _standby
from animations import flower as _flower
from animations import welcome as _welcome
from animations import chill as _chill
from animations import winddown as _winddown
from animations import talking as _talking
from animations import lotus as _lotus
from animations import dandelion as _dandelion
from animations import sunflower as _sunflower
from animations import meadow as _meadow
from animations import waterlily as _waterlily
from animations import moodflower as _moodflower

logger = logging.getLogger(__name__)

# Gentle crossfade when entering/leaving the playground mode.
FADE_IN_S = 2.0
FADE_OUT_S = 2.0

# Name of the meditation-recording clip inside the AudioPlayer.
REC_CLIP = "recording"

# Default clip ease used when a timeline clip doesn't override it.
DEFAULT_FADE_SEC = 1.5


def _clear(frame: bytearray) -> None:
    frame[:] = bytes(len(frame))


class Playground:
    """Holds Nadia's animation registry, the seconds-timeline, playback
    state, and her recording playback. The engine's playground mode calls
    `render()`; the /api/playground routes call the control methods."""

    def __init__(self, config, audio=None):
        self._config = config
        self._audio = audio
        self._lock = threading.RLock()
        # Per-animation mutable state (e.g. standby sparkles), reset on
        # (re)trigger / play so each run starts clean.
        self._anim_states: dict[str, dict] = {}
        self._current = "breathing"      # shown when not playing a sequence
        self._playing = False
        self._play_pending = False       # set by play(); render stamps start
        self._play_start_ms = 0.0
        self._play_offset_sec = 0.0      # seek offset for the pending play
        self._play_with_recording = False
        self._position_sec: float | None = None   # playhead (render thread)
        # Timeline cached in memory (synced to config on edits) so render
        # doesn't deepcopy config every frame.
        cfg = self._config.get("playground") or {}
        self._timeline: list[dict] = list(cfg.get("timeline") or [])
        self._default_fade = float(cfg.get("default_fade_sec", DEFAULT_FADE_SEC))
        self._anims = self._build_registry()
        # Make the recording instantly triggerable (decode runs in the
        # background inside the AudioPlayer).
        self.reload_recording()

    # ── Animation registry ─────────────────────────────────────────
    def _build_registry(self) -> dict:
        """name → (label, adapter(frame, time_ms, state)). Adapters reuse
        the existing animation renders with their live config params, so
        "Breathing" and "Standby" here look like the real modes."""
        def breathing_adapter(frame, time_ms, state):
            _breathing.render(frame, time_ms, self._config.get("breathing") or {})

        def standby_adapter(frame, time_ms, state):
            _standby.render(frame, time_ms, self._config.get("standby") or {}, state)

        def pg_adapter(module, section):
            def adapter(frame, time_ms, state):
                cfg = self._config.get("playground") or {}
                module.render(frame, time_ms, cfg.get(section) or {}, state)
            return adapter

        return {
            "breathing":  ("Breathing", breathing_adapter),
            "standby":    ("Standby (stars)", standby_adapter),
            "flower":     ("Flower (4 petals)", pg_adapter(_flower, "flower")),
            "welcome":    ("Welcome (bloom)", pg_adapter(_welcome, "welcome")),
            "talking":    ("Talking (sound waves)", pg_adapter(_talking, "talking")),
            "chill":      ("Chill (aurora)", pg_adapter(_chill, "chill")),
            "winddown":   ("Wind-down (settle)", pg_adapter(_winddown, "winddown")),
            # The flower garden 🌸 — see each module's DEFAULTS for knobs.
            "lotus":      ("Lotus (unfolding)", pg_adapter(_lotus, "lotus")),
            "sunflower":  ("Sunflower (spiral)", pg_adapter(_sunflower, "sunflower")),
            "meadow":     ("Night meadow", pg_adapter(_meadow, "meadow")),
            "waterlily":  ("Water lily (pond)", pg_adapter(_waterlily, "waterlily")),
            "dandelion":  ("Dandelion (let go)", pg_adapter(_dandelion, "dandelion")),
            "moodflower": ("Mood flower (shimmer)", pg_adapter(_moodflower, "moodflower")),
        }

    def animation_list(self) -> list[dict]:
        return [{"id": k, "label": v[0]} for k, v in self._anims.items()]

    # ── Timeline geometry helpers ───────────────────────────────────
    def _clip_window(self, c: dict) -> tuple[float, float, float, float]:
        """(start, end, fade_in, fade_out) — fades default to the
        playground-wide default when the clip doesn't set its own."""
        start = float(c.get("start_sec", 0.0))
        end = start + float(c.get("duration_sec", 0.0))
        fi = max(0.0, float(c.get("fade_in_sec", self._default_fade)))
        fo = max(0.0, float(c.get("fade_out_sec", self._default_fade)))
        return start, end, fi, fo

    @staticmethod
    def _clip_weight(pos: float, start: float, end: float,
                     fi: float, fo: float) -> float:
        """Blend weight of a clip at timeline position `pos`. Attack is
        inside the clip head; release extends PAST the end so butted
        clips crossfade instead of dipping to black."""
        if pos < start or pos >= end + fo:
            return 0.0
        w = 1.0
        if fi > 0.0 and pos < start + fi:
            w = (pos - start) / fi
        if pos >= end:                       # in the release tail
            w = min(w, 1.0 - (pos - end) / fo) if fo > 0.0 else 0.0
        return max(0.0, min(1.0, w))

    def _sequence_end_locked(self) -> float:
        """Timeline runs until the last release tail ends — or until the
        recording does, when playing with it (so her voice is never cut
        off by animations that end early)."""
        end = 0.0
        for c in self._timeline:
            _, e, _, fo = self._clip_window(c)
            end = max(end, e + fo)
        if self._play_with_recording and self._audio is not None:
            st = self._audio.clip_status(REC_CLIP)
            if st and st["loaded"]:
                end = max(end, st["duration_sec"])
        return end

    # ── Render (engine thread) ──────────────────────────────────────
    def render(self, frame: bytearray, time_ms: float, state: dict) -> None:
        with self._lock:
            if self._play_pending:
                self._play_pending = False
                self._playing = True
                # Seek: pretend the sequence started `offset` seconds ago.
                self._play_start_ms = time_ms - self._play_offset_sec * 1000.0
                self._anim_states = {}
                if self._play_with_recording:
                    self._start_recording_locked(self._play_offset_sec)

            if self._playing:
                pos = (time_ms - self._play_start_ms) / 1000.0
                self._position_sec = pos
                if pos >= self._sequence_end_locked():   # sequence finished
                    self._playing = False
                    self._position_sec = None
                    self._stop_recording_locked()
                else:
                    self._render_timeline_locked(frame, time_ms, pos)
                    return
            # Not playing a sequence → show the current (button-triggered) anim.
            self._render_anim_locked(self._current, frame, time_ms)

    def _render_timeline_locked(self, frame: bytearray, time_ms: float,
                                pos: float) -> None:
        active = []
        for c in self._timeline:
            start, end, fi, fo = self._clip_window(c)
            w = self._clip_weight(pos, start, end, fi, fo)
            if w > 0.001:
                active.append((c.get("animation"), w))
        if not active:
            _clear(frame)                    # real gap → dark
            return
        if len(active) == 1 and active[0][1] > 0.999:
            # Fast path: one fully-on clip renders straight into the frame.
            self._render_anim_locked(active[0][0], frame, time_ms)
            return
        # Blend: render each active clip into a scratch buffer and sum
        # by weight. Weights above a total of 1 are normalized so an
        # overlap never over-brightens; below 1 they dim toward black
        # (that's the fade).
        total = sum(w for _, w in active)
        scale = 1.0 / total if total > 1.0 else 1.0
        acc = np.zeros(len(frame), dtype=np.float32)
        for anim_id, w in active:
            scratch = bytearray(len(frame))
            self._render_anim_locked(anim_id, scratch, time_ms)
            acc += np.frombuffer(scratch, dtype=np.uint8).astype(np.float32) * (w * scale)
        frame[:] = np.clip(acc, 0.0, 255.0).astype(np.uint8).tobytes()

    def _render_anim_locked(self, anim_id, frame, time_ms) -> None:
        entry = self._anims.get(anim_id)
        if entry is None:
            _clear(frame)
            return
        st = self._anim_states.setdefault(anim_id, {})
        try:
            entry[1](frame, time_ms, st)
        except Exception:
            logger.exception("playground: animation %r render failed", anim_id)
            _clear(frame)

    # ── Controls (route thread) ─────────────────────────────────────
    def snapshot(self) -> dict:
        cfg = self._config.get("playground") or {}
        rec = self._audio.clip_status(REC_CLIP) if self._audio is not None else None
        with self._lock:
            return {
                "animations": self.animation_list(),
                "current": self._current,
                "playing": self._playing,
                "position_sec": self._position_sec if self._playing else None,
                "duration_sec": self._sequence_end_locked(),
                "default_fade_sec": self._default_fade,
                "timeline": list(self._timeline),
                "recording_file": cfg.get("recording_file"),
                "recording": rec,
                "play_with_recording": self._play_with_recording,
                "recording_playing": bool(rec and rec["playing"]),
            }

    def set_timeline(self, items: list) -> None:
        clean = []
        for c in items or []:
            try:
                clip = {
                    "animation": str(c["animation"]),
                    "start_sec": max(0.0, float(c["start_sec"])),
                    "duration_sec": max(0.1, float(c["duration_sec"])),
                }
                # Optional per-clip ease overrides (absent = default).
                for k in ("fade_in_sec", "fade_out_sec"):
                    if c.get(k) is not None:
                        clip[k] = max(0.0, float(c[k]))
                clean.append(clip)
            except (KeyError, TypeError, ValueError):
                continue
        with self._lock:
            self._timeline = clean
        cfg = self._config.get("playground") or {}
        cfg["timeline"] = clean
        self._config.set("playground", cfg)

    def trigger(self, anim_id: str) -> None:
        """Instantly show one animation (button press); stops any sequence."""
        with self._lock:
            self._playing = False
            self._play_pending = False
            self._position_sec = None
            self._stop_recording_locked()
            if anim_id in self._anims:
                self._current = anim_id
                self._anim_states[anim_id] = {}

    def play(self, with_recording: bool = False, start_sec: float = 0.0) -> None:
        """Start the timeline — optionally from `start_sec` (seek). The
        render thread stamps the actual start on its next frame."""
        with self._lock:
            self._play_with_recording = bool(with_recording)
            self._play_offset_sec = max(0.0, float(start_sec))
            self._play_pending = True

    def stop(self) -> None:
        with self._lock:
            self._playing = False
            self._play_pending = False
            self._position_sec = None
            self._stop_recording_locked()

    # ── Recording (one-shot clip in the shared AudioPlayer) ─────────
    def _recording_path(self) -> Path | None:
        cfg = self._config.get("playground") or {}
        name = cfg.get("recording_file")
        if not name:
            return None
        return self._media_dir() / "playground" / name

    def _media_dir(self) -> Path:
        audio_cfg = self._config.get("audio") or {}
        return Path(audio_cfg.get("media_dir", "/opt/here/media"))

    def reload_recording(self) -> None:
        """(Re)register the configured recording with the mixer. Called at
        boot and after an upload; decode happens in the background."""
        path = self._recording_path()
        if path is None or self._audio is None:
            return
        if not path.is_file():
            logger.warning("playground: recording file missing: %s", path)
            return
        self._audio.register_clip(REC_CLIP, path)

    def play_recording(self, start_sec: float = 0.0) -> None:
        with self._lock:
            self._start_recording_locked(start_sec)

    def stop_recording(self) -> None:
        with self._lock:
            self._stop_recording_locked()

    def _start_recording_locked(self, start_sec: float = 0.0) -> None:
        if self._audio is None:
            logger.warning("playground: no audio player — recording unavailable")
            return
        if self._audio.clip_status(REC_CLIP) is None:
            self.reload_recording()
        if self._audio.clip_status(REC_CLIP) is None:
            logger.warning("playground: no recording to play (%s)",
                           self._recording_path())
            return
        self._audio.play_clip(REC_CLIP, start_sec)

    def _stop_recording_locked(self) -> None:
        if self._audio is not None:
            self._audio.stop_clip(REC_CLIP)

    def stop_all(self) -> None:
        self.stop()
