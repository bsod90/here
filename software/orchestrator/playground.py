"""Nadia's Playground — an isolated experimentation mode.

See docs/nadia_playground.md for the full "what & why". In short: a safe
enclave for a non-technical collaborator (Nadia) to build a breathing
meditation by triggering / sequencing animations on a REAL seconds
timeline, toggling the ocean, and playing her own recording — without
touching breathing/standby/scene.

Kept deliberately isolated:
  * its own mode ("playground" in animation_engine.MODE_REGISTRY)
  * its own config section ("playground")
  * its own routes (admin/routes/playground.py) + admin tab
  * its own recording subprocess (does not touch AudioPlayer's backdrop)

ADDING A NEW ANIMATION (Claude does this when Nadia describes an idea):
  1. Write a render adapter `fn(frame, time_ms, state)` that paints the
     44×44 frame (reuse helpers / numpy like the other animations).
  2. Register it in `Playground._build_registry()` with a friendly label.
  It then auto-appears as a trigger button AND a timeline lane in her tab.
"""
from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

from animations import breathing as _breathing
from animations import standby as _standby
from animations import flower as _flower

logger = logging.getLogger(__name__)

# Gentle crossfade when entering/leaving the playground mode.
FADE_IN_S = 2.0
FADE_OUT_S = 2.0


def _clear(frame: bytearray) -> None:
    for i in range(len(frame)):
        frame[i] = 0


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
        self._play_with_recording = False
        self._rec_proc: subprocess.Popen | None = None
        # Timeline cached in memory (synced to config on edits) so render
        # doesn't deepcopy config every frame.
        cfg = self._config.get("playground") or {}
        self._timeline: list[dict] = list(cfg.get("timeline") or [])
        self._anims = self._build_registry()

    # ── Animation registry ─────────────────────────────────────────
    def _build_registry(self) -> dict:
        """name → (label, adapter(frame, time_ms, state)). Adapters reuse
        the existing animation renders with their live config params, so
        "Breathing" and "Standby" here look like the real modes."""
        def breathing_adapter(frame, time_ms, state):
            _breathing.render(frame, time_ms, self._config.get("breathing") or {})

        def standby_adapter(frame, time_ms, state):
            _standby.render(frame, time_ms, self._config.get("standby") or {}, state)

        def flower_adapter(frame, time_ms, state):
            cfg = self._config.get("playground") or {}
            _flower.render(frame, time_ms, cfg.get("flower") or {}, state)

        return {
            "breathing": ("Breathing", breathing_adapter),
            "standby":   ("Standby (stars)", standby_adapter),
            "flower":    ("Flower (4 petals)", flower_adapter),
        }

    def animation_list(self) -> list[dict]:
        return [{"id": k, "label": v[0]} for k, v in self._anims.items()]

    # ── Render (engine thread) ──────────────────────────────────────
    def render(self, frame: bytearray, time_ms: float, state: dict) -> None:
        with self._lock:
            if self._play_pending:
                self._play_pending = False
                self._playing = True
                self._play_start_ms = time_ms
                self._anim_states = {}
                if self._play_with_recording:
                    self._start_recording_locked()

            if self._playing:
                pos = (time_ms - self._play_start_ms) / 1000.0
                end = max((float(c.get("start_sec", 0)) + float(c.get("duration_sec", 0))
                           for c in self._timeline), default=0.0)
                if pos >= end:                      # sequence finished
                    self._playing = False
                    self._stop_recording_locked()
                else:
                    active = [c for c in self._timeline
                              if float(c.get("start_sec", 0)) <= pos
                              < float(c.get("start_sec", 0)) + float(c.get("duration_sec", 0))]
                    if active:
                        # Topmost (last-drawn) clip wins.
                        self._render_anim_locked(active[-1].get("animation"),
                                                 frame, time_ms)
                    else:
                        _clear(frame)            # gap between clips → dark
                    return
            # Not playing a sequence → show the current (button-triggered) anim.
            self._render_anim_locked(self._current, frame, time_ms)

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
        with self._lock:
            return {
                "animations": self.animation_list(),
                "current": self._current,
                "playing": self._playing,
                "timeline": list(self._timeline),
                "recording_file": cfg.get("recording_file"),
                "play_with_recording": self._play_with_recording,
                "recording_playing": (self._rec_proc is not None
                                      and self._rec_proc.poll() is None),
            }

    def set_timeline(self, items: list) -> None:
        clean = []
        for c in items or []:
            try:
                clean.append({
                    "animation": str(c["animation"]),
                    "start_sec": max(0.0, float(c["start_sec"])),
                    "duration_sec": max(0.1, float(c["duration_sec"])),
                })
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
            self._stop_recording_locked()
            if anim_id in self._anims:
                self._current = anim_id
                self._anim_states[anim_id] = {}

    def play(self, with_recording: bool = False) -> None:
        with self._lock:
            self._play_with_recording = bool(with_recording)
            self._play_pending = True       # render() stamps the start time

    def stop(self) -> None:
        with self._lock:
            self._playing = False
            self._play_pending = False
            self._stop_recording_locked()

    # ── Recording playback (own subprocess; coexists with the ocean) ─
    def _recording_path(self) -> Path | None:
        cfg = self._config.get("playground") or {}
        name = cfg.get("recording_file")
        if not name:
            return None
        return self._media_dir() / "playground" / name

    def _media_dir(self) -> Path:
        audio_cfg = self._config.get("audio") or {}
        return Path(audio_cfg.get("media_dir", "/opt/here/media"))

    def play_recording(self) -> None:
        with self._lock:
            self._start_recording_locked()

    def stop_recording(self) -> None:
        with self._lock:
            self._stop_recording_locked()

    def _start_recording_locked(self) -> None:
        self._stop_recording_locked()
        path = self._recording_path()
        if path is None or not path.exists():
            logger.warning("playground: no recording to play (%s)", path)
            return
        try:
            self._rec_proc = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-hide_banner",
                 "-loglevel", "error", str(path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
            logger.info("playground: playing recording %s", path.name)
        except Exception:
            logger.exception("playground: failed to start recording")
            self._rec_proc = None

    def _stop_recording_locked(self) -> None:
        proc = self._rec_proc
        self._rec_proc = None
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:
            logger.exception("playground: error stopping recording")

    def stop_all(self) -> None:
        self.stop()
