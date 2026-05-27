"""OSC input — receives MIDI-style events + knob updates from the HERE
Max for Live device (or any OSC source).

The audio-band envelope follower of v1 is gone — the new HERE.amxd is a
MIDI Effect that sends note_on/note_off + knob OSC. The orchestrator's
event router owns pitch → event resolution via its `lanes` table (which
mirrors `SynthAnimation.NOTE_LANES`).

Topic map:
  /here/scene/note_on/<pitch>   <velocity:float>              fire event for lane[pitch - BASE_PITCH]
  /here/scene/note_off/<pitch>                                release sustain for that event
  /here/scene/synth/<key>       <value:float>                 update a synth meta knob
  /here/scene/physics/<key>     <value:float>                 update a physics param
  /here/scene/oval/<i>/<key>    <value:float>                 update per-ring knob (key in skew|phase|blur|radius_scale|segments|gap)
  /here/scene/palette           <int>                         immediate palette swap (no fade)
  /here/scene/bpm               <bpm:float>                   set tempo
  /here/scene/beat                                            tap-sync (treats now as loop-zero)
  /here/scene/event/<name>      <duration_beats> [<palette>]  legacy: trigger by name (used by admin buttons + tests)

`BASE_PITCH = 36` (MIDI C1) matches Drum Rack convention — pitch 36 maps
to NOTE_LANES[0] ("Expand"), pitch 75 to NOTE_LANES[39] ("Shimmer").
"""
from __future__ import annotations

import logging
import math
import threading
from typing import Optional

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server

logger = logging.getLogger(__name__)

# MIDI C1 — Drum Rack's first pad. Each note up the keyboard from here
# walks through NOTE_LANES in order.
BASE_PITCH = 36

# Legacy band names — kept so the OscState class API doesn't break any
# stale callers, but no longer wired to OSC topics. Safe to delete with
# OscState itself once no consumer remains.
BANDS = ("low", "mid", "high")


class OscState:
    """Legacy holder for audio-band envelope levels — no longer driven by
    OSC. Retained as a no-op snapshot source so existing wiring in
    `AnimationEngine` keeps working without conditionals."""

    def __init__(self):
        self._raw: dict[str, float] = {b: 0.0 for b in BANDS}
        self._smoothed: dict[str, float] = {b: 0.0 for b in BANDS}
        self._last_trigger_ms: dict[str, float] = {"kick": -1e9}
        self._trigger_vel: dict[str, float] = {"kick": 0.0}
        self._lock = threading.Lock()
        self._last_read_ms: Optional[float] = None
        self.attack_s: float = 0.02
        self.release_s: float = 0.18

    def set_band(self, name: str, value: float) -> None:
        if name not in self._raw:
            return
        v = 0.0 if value is None else max(0.0, min(1.0, float(value)))
        with self._lock:
            self._raw[name] = v

    def fire_trigger(self, name: str, velocity: float = 1.0, t_ms: float = 0.0) -> None:
        if name not in self._last_trigger_ms:
            return
        vel = max(0.0, min(1.0, float(velocity)))
        with self._lock:
            self._last_trigger_ms[name] = t_ms
            self._trigger_vel[name] = vel

    def snapshot(self, time_ms: float) -> dict:
        with self._lock:
            if self._last_read_ms is None:
                self._last_read_ms = time_ms
            dt = max(0.0, (time_ms - self._last_read_ms) / 1000.0)
            self._last_read_ms = time_ms

            for name in BANDS:
                raw = self._raw[name]
                cur = self._smoothed[name]
                tc = self.attack_s if raw > cur else self.release_s
                alpha = 1.0 - math.exp(-dt / tc) if tc > 0 else 1.0
                self._smoothed[name] = cur + (raw - cur) * alpha

            triggers = {}
            for name, ts in self._last_trigger_ms.items():
                triggers[name] = {
                    "age_ms": time_ms - ts,
                    "vel": self._trigger_vel.get(name, 1.0),
                }
            return {
                "bands": dict(self._smoothed),
                "raw": dict(self._raw),
                "triggers": triggers,
            }


class OscServer:
    """Threaded UDP OSC server. Routes incoming messages to the Scene.

    `time_provider` returns the engine's monotonic time in ms so any
    timing-sensitive trigger handlers (currently none) can align with
    the frame clock.
    `scene` (optional) is the Scene instance that receives `/here/scene/*`.
    """

    # Valid per-ring knob keys (matches admin.js OVAL_KNOBS).
    OVAL_KEYS = ("skew", "phase", "blur", "radius_scale", "segments", "gap")

    def __init__(self, state: OscState, time_provider, host: str = "0.0.0.0",
                 port: int = 9000, scene=None):
        self._state = state
        self._now_ms = time_provider
        self._host = host
        self._port = port
        self._scene = scene
        self._server: Optional[osc_server.ThreadingOSCUDPServer] = None
        self._thread: Optional[threading.Thread] = None

    # ── MIDI-style: note_on / note_off by pitch ──────────────────────
    def _on_note_on(self, addr, *args):
        if self._scene is None:
            return
        pitch = _parse_pitch(addr)
        if pitch is None:
            return
        lane_idx = pitch - BASE_PITCH
        if not (0 <= lane_idx < len(self._scene.router.lanes)):
            logger.debug(f"OSC note_on: pitch {pitch} out of lane range")
            return
        velocity = float(args[0]) if args else 1.0
        # Route through router.dispatch so the lane mapping owns the
        # pitch → event resolution (single source of truth with the
        # sequencer + piano roll).
        self._scene.router.dispatch({
            "type": "note_on",
            "pitch": lane_idx,
            "beat": self._scene.current_beat(),
            "velocity": max(0.0, min(1.0, velocity)),
            "params": {},
        })

    def _on_note_off(self, addr, *args):
        if self._scene is None:
            return
        pitch = _parse_pitch(addr)
        if pitch is None:
            return
        lane_idx = pitch - BASE_PITCH
        if not (0 <= lane_idx < len(self._scene.router.lanes)):
            return
        self._scene.router.dispatch({
            "type": "note_off",
            "pitch": lane_idx,
            "beat": self._scene.current_beat(),
            "velocity": 0.0,
            "params": {},
        })

    # ── Knob updates: synth meta / physics / per-oval ────────────────
    def _on_synth_knob(self, addr, *args):
        if self._scene is None or not args:
            return
        key = addr.rsplit("/", 1)[1]
        try:
            value = float(args[0])
        except (TypeError, ValueError):
            return
        self._scene.apply_synth_meta({key: value})

    def _on_physics_knob(self, addr, *args):
        if self._scene is None or not args:
            return
        key = addr.rsplit("/", 1)[1]
        try:
            value = float(args[0])
        except (TypeError, ValueError):
            return
        self._scene.apply_physics_params({key: value})

    def _on_oval_knob(self, addr, *args):
        """`/here/scene/oval/<i>/<key>` → mirrors admin OVAL_KNOBS keys."""
        if self._scene is None or not args:
            return
        # addr is like "/here/scene/oval/0/blur"
        parts = addr.rsplit("/", 2)
        if len(parts) != 3:
            return
        try:
            idx = int(parts[1])
        except (TypeError, ValueError):
            return
        key = parts[2]
        if key not in self.OVAL_KEYS or not (0 <= idx < 3):
            return
        try:
            value = float(args[0])
        except (TypeError, ValueError):
            return
        self._scene.apply_synth_meta({f"oval_{key}_{idx}": value})

    def _on_palette(self, addr, *args):
        if self._scene is None or not args:
            return
        try:
            palette = int(args[0])
        except (TypeError, ValueError):
            return
        # Immediate swap — no crossfade. (Use /here/scene/event/color_palette
        # for the smooth cross-fade.)
        self._scene.set_state("palette_idx", palette)
        self._scene.set_state("palette_target_idx", palette)
        self._scene.set_state("palette_blend", 0.0)

    # ── Tempo + tap-sync ─────────────────────────────────────────────
    def _on_scene_bpm(self, addr, *args):
        if self._scene is None or not args:
            return
        try:
            self._scene.set_bpm(float(args[0]))
        except (TypeError, ValueError):
            pass

    def _on_scene_beat(self, addr, *args):
        """OSC /here/scene/beat as a 'Set 1' tap — drift the clock so
        loop_pos == 0 right now (instead of snapping)."""
        if self._scene is None:
            return
        import time as _time
        self._scene.align_to_loop_zero(_time.monotonic())

    # ── Legacy: trigger event by name ────────────────────────────────
    def _on_scene_event(self, event_name):
        def handler(addr, *args):
            if self._scene is None:
                return
            # None lets the saved event_default (from the admin UI) win.
            # Explicit OSC arg overrides.
            duration_beats = None
            params = {}
            if args:
                try:
                    duration_beats = float(args[0])
                except (TypeError, ValueError):
                    pass
            # Optional second arg: an int param (used by color_palette for
            # which palette index to fade to).
            if len(args) >= 2:
                try:
                    params["palette"] = int(args[1])
                except (TypeError, ValueError):
                    pass
            self._scene.trigger(event_name, duration_beats, params)
        return handler

    def start(self) -> None:
        disp = osc_dispatcher.Dispatcher()

        # Scene topics.
        disp.map("/here/scene/bpm", self._on_scene_bpm)
        disp.map("/here/scene/beat", self._on_scene_beat)
        disp.map("/here/scene/palette", self._on_palette)

        # MIDI-style note routing — wildcard match on pitch suffix.
        disp.map("/here/scene/note_on/*", self._on_note_on)
        disp.map("/here/scene/note_off/*", self._on_note_off)

        # Knob updates — wildcard match on key suffix.
        disp.map("/here/scene/synth/*", self._on_synth_knob)
        disp.map("/here/scene/physics/*", self._on_physics_knob)
        # Per-oval: `/here/scene/oval/<i>/<key>` — two wildcards.
        disp.map("/here/scene/oval/*/*", self._on_oval_knob)

        # Bind every registered router event so admin / tests can trigger
        # by name. Kept for back-compat; the M4L device prefers note_on.
        if self._scene is not None:
            for event_name in self._scene.router.events:
                disp.map(f"/here/scene/event/{event_name}",
                         self._on_scene_event(event_name))

        # Catch-all for visibility while iterating.
        disp.set_default_handler(
            lambda addr, *args: logger.debug(f"OSC unmapped: {addr} {args}")
        )
        self._server = osc_server.ThreadingOSCUDPServer((self._host, self._port), disp)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="osc-server", daemon=True
        )
        self._thread.start()
        logger.info(f"OSC listening on udp/{self._host}:{self._port}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def _parse_pitch(addr: str) -> Optional[int]:
    """Last path segment as an int, or None if not parseable."""
    try:
        return int(addr.rsplit("/", 1)[1])
    except (ValueError, IndexError):
        return None
