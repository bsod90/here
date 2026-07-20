"""Nadia's Playground — an isolated experimentation mode.

See docs/nadia_playground.md for the full "what & why". In short: a safe
enclave for a non-technical collaborator (Nadia) to build a guided
meditation by sequencing animations on a REAL seconds timeline over her
own recorded audio — without touching breathing/standby/scene.

Kept deliberately isolated:
  * its own mode ("playground" in animation_engine.MODE_REGISTRY)
  * its own config section ("playground")
  * its own routes (admin/routes/playground.py) + admin tab

Timeline model (v3 — "score an existing meditation"):
  * Instead of uploading a recording, the editor BINDS to one of the
    existing meditations (audio.meditation.items). Each meditation keeps
    its OWN animation event-track (config.playground.tracks[<id>]); the
    editor scrolls along that meditation's length with its audio waveform
    drawn behind the clips.
  * clips: {animation, start_sec, duration_sec[, fade_in_sec, fade_out_sec]}
  * every clip eases in over fade_in_sec at its head, and eases out over
    fade_out_sec PAST its end (a release tail, like a DAW clip). Butted
    clips therefore crossfade naturally: the outgoing clip is still
    fading down while the incoming one ramps up. Gaps fade to dark.
  * overlapping clips all render and blend by weight (no more
    "topmost wins" hard cut).
  * the playhead position + total duration are exposed in snapshot();
    play(start_sec=…) seeks — both the animations and the meditation
    audio start from that offset, sample-aligned through the audio mixer.

The selected meditation's audio plays through the shared AudioPlayer as a
one-shot clip named `pg:<id>` (audio.register_clip/play_clip): it starts
within ~23 ms of the animations and mixes cleanly with the ambience
tracks. Only the selected meditation is decoded (lazy), so the playground
doesn't duplicate the MeditationController's whole library at boot.

Lanes available on a track = the garden animations PLUS the WLED-ported
effects (animations/wled_*.py). The latter also get their own tunable
"WLED animations" section (per-effect preview button + a few live knobs
+ palette picker); see WLED_FX below.

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

import palettes as _palettes
from animations import breathing as _breathing
from animations import standby as _standby
from animations import noise as _noise
from animations import mandala as _mandala
from animations import waves as _waves
from animations import mandala2 as _mandala2
from animations import mandala3 as _mandala3
from animations import sunflower as _sunflower
from animations import rain as _rain
from animations import eyes as _eyes

# WLED-ported effects (animations/wled_*.py). Grouped + tunable in the
# playground's "WLED animations" section. Ported line-by-line from WLED
# v0.15 with bit-exact FastLED math (see animations/_wled.py).
from animations import wled_distort as _w_distort
from animations import wled_noise2d as _w_noise2d
from animations import wled_sunrad as _w_sunrad
# Not WLED ports — the MIDI engine's shimmering border (synth.py's
# border-glow layer) and its flower variant, but they live in the same
# tunable-knobs section.
from animations import borderglow as _borderglow
from animations import darkflower as _darkflower

logger = logging.getLogger(__name__)


# ── WLED effect catalog ─────────────────────────────────────────────
# Each entry: id, friendly label, render module, the few knobs worth
# exposing (key, label, min, max), and whether it samples our palettes.
# `knobs` keys map straight onto config.playground.<id>.<key> overrides
# (PUT /api/config deep-merges them; the render reads them live). The
# module's DEFAULTS supply starting values + everything not exposed.
WLED_FX = [
    {"id": "border", "label": "Border (shimmer)", "mod": _borderglow, "palette": True,
     "knobs": [("speed", "Vibrato", 0, 255), ("intensity", "Shimmer", 0, 255),
               ("custom1", "Width", 16, 255), ("custom2", "Spin", 0, 255)]},
    {"id": "darkflower", "label": "Dark flower", "mod": _darkflower, "palette": True,
     "knobs": [("speed", "Vibrato", 0, 255), ("intensity", "Shimmer", 0, 255),
               ("custom1", "Width", 16, 255), ("custom2", "Spin", 0, 255),
               ("custom3", "Breath", 0, 255)]},
    {"id": "wled_distort", "label": "Distortion Waves", "mod": _w_distort, "palette": True,
     "knobs": [("speed", "Speed", 0, 255), ("intensity", "Scale", 0, 255)],
     "toggles": [("blue_off", "Blue off")]},
    {"id": "wled_noise2d", "label": "Noise 2D", "mod": _w_noise2d, "palette": True,
     "knobs": [("speed", "Drift", 0, 255), ("intensity", "Scale", 0, 255)]},
    {"id": "wled_sunrad", "label": "Sun Radiation", "mod": _w_sunrad, "palette": False,
     "knobs": [("speed", "Variance", 0, 255), ("intensity", "Brightness", 0, 255)]},
]
WLED_BY_ID = {fx["id"]: fx for fx in WLED_FX}

# Gentle crossfade when entering/leaving the playground mode.
FADE_IN_S = 2.0
FADE_OUT_S = 2.0
# Fade applied when the meditation recording is stopped mid-play
# (editor ■ Stop, sequence end) — never cut the voice abruptly.
REC_FADE_S = 3.0

# The playground plays the SELECTED meditation's audio through the shared
# mixer as a one-shot clip named `pg:<meditation-id>`. Each meditation has
# its own animation event-track (a seconds-timeline) keyed by that id.
REC_CLIP = "recording"          # legacy name (kept for back-compat imports)
_PG_PREFIX = "pg:"
# Track key used when no meditation is bound (e.g. tests, empty fleet).
_UNBOUND = "_unbound"


def _med_clip(mid: str) -> str:
    return f"{_PG_PREFIX}{mid}"

# Default clip ease used when a timeline clip doesn't override it.
DEFAULT_FADE_SEC = 1.5


def _apply_master_brightness(frame: bytearray, b: float) -> None:
    """Scale the finished frame by the global master brightness dial."""
    if b >= 0.999:
        return
    arr = np.frombuffer(bytes(frame), dtype=np.uint8).astype(np.float32)
    frame[:] = (arr * b).astype(np.uint8).tobytes()


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
        # True while the engine's crossfade INTO playground mode is still
        # in flight — lets animations hold their intro until it's done.
        self._in_mode_fade = False
        # Per-frame snapshot of config.playground (one deepcopy per frame,
        # refreshed at the top of render()) + the global master dials'
        # virtual clock (see render()).
        self._frame_cfg: dict = self._config.get("playground") or {}
        self._vt_ms = 0.0
        self._vt_last_ms: float | None = None
        # Per-meditation event tracks, cached in memory (synced to config on
        # edits) so render doesn't deepcopy config every frame. Each track is
        # a seconds-timeline of animation clips bound to a meditation id.
        cfg = self._config.get("playground") or {}
        self._tracks: dict[str, list[dict]] = {
            k: list(v or []) for k, v in (cfg.get("tracks") or {}).items()}
        # Migrate a legacy single `timeline` into the first meditation's track.
        legacy = cfg.get("timeline")
        self._default_fade = float(cfg.get("default_fade_sec", DEFAULT_FADE_SEC))
        self._anims = self._build_registry()
        # Bind to a meditation: the saved selection if still valid, else the
        # first available one (or unbound when no meditations exist).
        meds = self._meditation_items()
        ids = [m["id"] for m in meds]
        sel = cfg.get("selected")
        self._selected = sel if sel in ids else (ids[0] if ids else _UNBOUND)
        if legacy and self._selected not in self._tracks:
            self._tracks[self._selected] = list(legacy)
        self._timeline: list[dict] = list(self._tracks.get(self._selected) or [])
        # Register every present meditation's audio as a one-shot clip so the
        # selected one is instantly playable (decode runs in the background).
        self._register_med_clips()

    # ── Animation registry ─────────────────────────────────────────
    def _build_registry(self) -> dict:
        """name → (label, adapter(frame, time_ms, state)). Adapters reuse
        the existing animation renders with their live config params, so
        "Breathing" and "Standby" here look like the real modes."""
        def breathing_adapter(frame, time_ms, state):
            # Anchor the breath cycle to the moment this animation starts
            # (state is reset on each trigger/play), so it always begins
            # at the start of an inhale — small center circle expanding —
            # instead of joining the cycle mid-breath. While the engine's
            # mode crossfade is still in flight, keep re-stamping the
            # anchor: the circle holds at the small center until the
            # transition finishes, THEN the first inhale begins.
            if self._in_mode_fade or "t0" not in state:
                state["t0"] = time_ms
            _breathing.render(frame, time_ms - state["t0"],
                              self._config.get("breathing") or {})

        def standby_adapter(frame, time_ms, state):
            _standby.render(frame, time_ms, self._config.get("standby") or {}, state)

        def pg_adapter(module, section):
            def adapter(frame, time_ms, state):
                # `_frame_cfg` is the playground config snapshotted ONCE
                # per rendered frame (render() refreshes it) — live knob
                # edits still apply next frame, without a config deepcopy
                # per animation per frame.
                cfg = self._frame_cfg
                module.render(frame, time_ms, cfg.get(section) or {}, state)
            return adapter

        reg = {
            "breathing":  ("Breathing", breathing_adapter),
            "standby":    ("Standby (stars)", standby_adapter),
            "noise":      ("White noise (shimmer)", pg_adapter(_noise, "noise")),
            "mandala":    ("Mandala", pg_adapter(_mandala, "mandala")),
            "waves":      ("Underwater", pg_adapter(_waves, "waves")),
            "mandala2":   ("Mandala II (pearls)", pg_adapter(_mandala2, "mandala2")),
            "mandala3":   ("Mandala III (lattice)", pg_adapter(_mandala3, "mandala3")),
            "sunflower":  ("Sunflower (spiral)", pg_adapter(_sunflower, "sunflower")),
            # Same module as the post-meditation "ripples" rest screen,
            # but with its own livelier garden defaults + overrides
            # under config.playground.rain.
            "rain":       ("Water droplets", pg_adapter(_rain, "rain")),
            # Hand-drawn blinking eyes baked from Dream_1.mp4 (see
            # animations/eyes.py for the conversion recipe).
            "eyes":       ("Eyes", pg_adapter(_eyes, "eyes")),
        }
        # WLED-ported effects share the same live-config adapter (their
        # tuned knobs live under config.playground.<id>).
        for fx in WLED_FX:
            reg[fx["id"]] = (fx["label"], pg_adapter(fx["mod"], fx["id"]))
        return reg

    def animation_list(self) -> list[dict]:
        # Garden animations only (the WLED-ported effects live in their own
        # section + list, so they don't crowd the trigger buttons).
        return [{"id": k, "label": v[0]} for k, v in self._anims.items()
                if k not in WLED_BY_ID]

    # ── WLED effects: knob metadata + current values ────────────────
    def wled_list(self) -> list[dict]:
        """Per-effect descriptor for the WLED section: friendly label,
        the knobs to render, whether it takes a palette, and the current
        effective values (module DEFAULTS overlaid with config overrides)."""
        cfg = self._config.get("playground") or {}
        out = []
        for fx in WLED_FX:
            defaults = dict(getattr(fx["mod"], "DEFAULTS", {}))
            values = {**defaults, **(cfg.get(fx["id"]) or {})}
            out.append({
                "id": fx["id"],
                "label": fx["label"],
                "palette": fx["palette"],
                "knobs": [{"key": k, "label": lbl, "min": lo, "max": hi}
                          for (k, lbl, lo, hi) in fx["knobs"]],
                "toggles": [{"key": k, "label": lbl}
                            for (k, lbl) in fx.get("toggles", [])],
                "values": {k: values.get(k) for k in
                           ([kk for (kk, *_2) in fx["knobs"]]
                            + [kk for (kk, *_3) in fx.get("toggles", [])]
                            + (["palette"] if fx["palette"] else [])
                            + ["brightness"])},
            })
        return out

    # ── Meditations (the audio each event-track is built over) ──────
    def _meditation_items(self) -> list[dict]:
        """Normalized meditation list from config.audio.meditation.items."""
        med = ((self._config.get("audio") or {}).get("meditation") or {})
        out = []
        for it in (med.get("items") or []):
            mid = it.get("id")
            if not mid:
                continue
            out.append({"id": mid, "label": it.get("label", mid),
                        "file": it.get("file")})
        return out

    def _med_path(self, file: str | None) -> Path | None:
        if not file:
            return None
        return self._media_dir() / file

    def _register_med_clips(self) -> None:
        """Register the SELECTED meditation's audio as a `pg:<id>` clip (lazy:
        only the one being edited is decoded, so we don't duplicate the
        MeditationController's decodes for the whole library at boot)."""
        if self._audio is None or self._selected == _UNBOUND:
            return
        for m in self._meditation_items():
            if m["id"] != self._selected:
                continue
            path = self._med_path(m["file"])
            if path is not None and path.is_file():
                self._audio.register_clip(_med_clip(m["id"]), path)

    def meditations(self) -> list[dict]:
        """Selectable meditations + presence/duration for the UI."""
        out = []
        for m in self._meditation_items():
            path = self._med_path(m["file"])
            present = bool(path and path.is_file())
            dur = 0.0
            if self._audio is not None:
                st = self._audio.clip_status(_med_clip(m["id"]))
                if st and st.get("loaded"):
                    dur = float(st.get("duration_sec") or 0.0)
            out.append({"id": m["id"], "label": m["label"], "file": m["file"],
                        "present": present, "duration_sec": dur})
        return out

    def has_track(self, mid: str) -> bool:
        """True when this meditation has a non-empty sequenced event-track —
        the MeditationController uses it to decide whether a sit plays the
        sequenced visuals or falls back to the breathing circle."""
        with self._lock:
            if mid == self._selected:
                return bool(self._timeline)
            return bool(self._tracks.get(mid))

    def select(self, mid: str) -> bool:
        """Bind the editor to a meditation: stash the current track, load the
        chosen meditation's track, persist the selection. Returns False for
        an unknown id."""
        if mid not in {m["id"] for m in self._meditation_items()}:
            return False
        with self._lock:
            self.stop()
            self._tracks[self._selected] = list(self._timeline)
            self._selected = mid
            self._timeline = list(self._tracks.get(mid) or [])
        self._persist()
        if self._audio is not None and self._audio.clip_status(_med_clip(mid)) is None:
            self._register_med_clips()
        return True

    def _selected_duration(self) -> float:
        if self._audio is None or self._selected == _UNBOUND:
            return 0.0
        st = self._audio.clip_status(_med_clip(self._selected))
        return float(st["duration_sec"]) if st and st.get("loaded") else 0.0

    def _persist(self) -> None:
        cfg = self._config.get("playground") or {}
        cfg["tracks"] = {k: list(v) for k, v in self._tracks.items()}
        cfg["selected"] = self._selected
        cfg["default_fade_sec"] = self._default_fade
        cfg.pop("timeline", None)          # legacy single timeline retired
        cfg.pop("recording_file", None)
        self._config.set("playground", cfg)

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
            st = self._audio.clip_status(_med_clip(self._selected))
            if st and st["loaded"]:
                end = max(end, st["duration_sec"])
        return end

    # ── Render (engine thread) ──────────────────────────────────────
    def render(self, frame: bytearray, time_ms: float, state: dict,
               fade_in: float | None = None) -> None:
        with self._lock:
            # `fade_in` is the engine's mode-crossfade progress (0..1, or
            # None outside a transition). Sequenced intros wait for it.
            self._in_mode_fade = fade_in is not None and fade_in < 1.0
            # One config snapshot per frame (adapters read it live).
            self._frame_cfg = self._config.get("playground") or {}
            master = self._frame_cfg.get("master") or {}
            # Global MASTER SPEED: every animation clock runs on a shared
            # virtual clock advanced by dt×speed, so the dial stretches
            # all animations live without jumping their phase. Timeline
            # POSITION stays on real time — sequenced sits must remain in
            # sync with the meditation voice.
            try:
                speed = max(0.05, min(4.0, float(master.get("speed", 1.0))))
            except (TypeError, ValueError):
                speed = 1.0
            if self._vt_last_ms is None:
                self._vt_ms = time_ms
            else:
                self._vt_ms += (time_ms - self._vt_last_ms) * speed
            self._vt_last_ms = time_ms
            vt = self._vt_ms
            try:
                master_b = max(0.0, min(1.0, float(master.get("brightness", 1.0))))
            except (TypeError, ValueError):
                master_b = 1.0
            # The engine hands us a FRESH `state` dict every time the
            # playground mode is (re)entered — use that to reset the
            # per-animation clocks, so intros (breathing's first inhale,
            # the flower's center, …) replay from the top on each visit
            # instead of resuming wherever they left off last time.
            if "entered" not in state:
                state["entered"] = True
                self._anim_states = {}
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
                    # The floor stays BLACK after the final clip's fade-out
                    # — the sequence's own ending is authoritative. (We used
                    # to hold the last clip's ANIMATION here, but that
                    # re-triggered it from scratch: a ghost flash of e.g.
                    # the mandala fading back in right after the track had
                    # deliberately faded it out.)
                    self._current = None
                else:
                    self._render_timeline_locked(frame, vt, pos)
                    _apply_master_brightness(frame, master_b)
                    return
            # Not playing a sequence → show the current (button-triggered) anim.
            self._render_anim_locked(self._current, frame, vt)
            _apply_master_brightness(frame, master_b)

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
        rec = (self._audio.clip_status(_med_clip(self._selected))
               if self._audio is not None and self._selected != _UNBOUND else None)
        with self._lock:
            return {
                "animations": self.animation_list(),
                "wled": self.wled_list(),
                "palettes": _palettes.NAMES,
                "current": self._current,
                "playing": self._playing,
                "position_sec": self._position_sec if self._playing else None,
                "duration_sec": self._sequence_end_locked(),
                "default_fade_sec": self._default_fade,
                "master": {"brightness": 1.0, "speed": 1.0,
                           **((self._config.get("playground") or {}).get("master") or {})},
                "timeline": list(self._timeline),
                # Per-meditation event-track model.
                "meditations": self.meditations(),
                "selected": None if self._selected == _UNBOUND else self._selected,
                "selected_duration": self._selected_duration(),
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
            self._tracks[self._selected] = clean
        self._persist()

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

    def stop(self, hold_black: bool = False) -> None:
        """Stop timeline playback. The editor's ■ Stop falls back to the
        last-triggered animation (Nadia expects her button back); the
        meditation hand-off passes `hold_black=True` so the floor stays
        dark instead of flashing that animation between the sequence's
        ending and the rest screen."""
        with self._lock:
            self._playing = False
            self._play_pending = False
            self._position_sec = None
            if hold_black:
                self._current = None
            self._stop_recording_locked()

    # ── Meditation audio (the selected meditation's clip) ───────────
    def _media_dir(self) -> Path:
        audio_cfg = self._config.get("audio") or {}
        return Path(audio_cfg.get("media_dir", "/opt/here/media"))

    def reload_recording(self) -> None:
        """(Re)register every meditation's audio with the mixer (decode runs
        in the background). Kept named for back-compat with bootstrap."""
        self._register_med_clips()

    def play_recording(self, start_sec: float = 0.0) -> None:
        with self._lock:
            self._start_recording_locked(start_sec)

    def stop_recording(self) -> None:
        with self._lock:
            self._stop_recording_locked()

    def _start_recording_locked(self, start_sec: float = 0.0) -> None:
        if self._audio is None or self._selected == _UNBOUND:
            logger.warning("playground: no meditation selected — audio unavailable")
            return
        clip = _med_clip(self._selected)
        if self._audio.clip_status(clip) is None:
            self._register_med_clips()
        if self._audio.clip_status(clip) is None:
            logger.warning("playground: no audio for meditation %r", self._selected)
            return
        self._audio.play_clip(clip, start_sec)

    def _stop_recording_locked(self) -> None:
        # Fade the voice out gracefully — this fires on the editor's
        # ■ Stop AND when a timeline ends while playing with audio, and
        # the default ~80 ms ramp cut the meditation off mid-word.
        if self._audio is not None and self._selected != _UNBOUND:
            self._audio.stop_clip(_med_clip(self._selected), fade=REC_FADE_S)

    def stop_all(self) -> None:
        self.stop()
