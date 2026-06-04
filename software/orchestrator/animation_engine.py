"""Animation engine — runs the frame loop in a dedicated thread.

Modes are described by a single declarative `MODE_REGISTRY` (one entry
per mode) instead of being open-coded in three places (validation, fade
durations, render dispatch). Adding a mode = adding one entry.
"""
from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass
from typing import Callable

from grid import FRAME_BYTES, TOTAL
from animations import breathing, standby, debug, weight_shadows, fireplace
from engine_state import TransitionCoordinator, PowerEstimator


# ── Mode registry ───────────────────────────────────────────────
# A mode is a labelled render strategy. Each entry packages everything
# the engine needs to know about it:
#   * how long its fade-in / fade-out crossfade should be
#   * whether it needs the engine to maintain a per-mode mutable state
#     dict (sparkles, flares, …) that's reset on (re)entry
#   * a render callable with a uniform signature
#
# Animation modules (breathing.py, standby.py, …) own their FADE_IN_S /
# FADE_OUT_S constants — the registry just exposes them in one place.

@dataclass(frozen=True)
class ModeSpec:
    name: str
    render: Callable                         # (engine, frame, t_ms, fade_in, fade_out, state) → None
    fade_in_s: float = 0.0
    fade_out_s: float = 0.0
    needs_state: bool = False                # engine keeps a per-mode state dict


def _render_breathing(engine, frame, t_ms, fade_in, fade_out, state):
    params = engine.config.get("breathing") or {}
    sess = params.get("session") or {}
    phase = sess.get("preview_phase") or "auto"
    # `auto` is the natural behaviour (the breath loop); other values
    # force a specific session-phase render via the Tune UI.
    phase_arg = None if phase == "auto" else phase
    breathing.render(frame, t_ms, params,
                     fade_in=fade_in, fade_out=fade_out, phase=phase_arg)


def _render_standby(engine, frame, t_ms, fade_in, fade_out, state):
    params = engine.config.get("standby")
    standby.render(frame, t_ms, params, state,
                   fade_in=fade_in, fade_out=fade_out)


def _render_fireplace(engine, frame, t_ms, fade_in, fade_out, state):
    params = engine.config.get("fireplace") or {}
    fireplace.render(frame, t_ms, params, state,
                     fade_in=fade_in, fade_out=fade_out)


def _render_debug(engine, frame, t_ms, fade_in, fade_out, state):
    debug.render(frame, t_ms, {})


def _render_midi(engine, frame, t_ms, fade_in, fade_out, state):
    # User-facing mode name is "midi"; the underlying framework keeps
    # the original "scene" name in code + config + API (to avoid
    # rewriting saved sequences / patches / config files).
    if engine.scene is None:
        return
    scene_cfg = engine.config.get("scene") or {}
    anim_name = scene_cfg.get("animation") or "synth"
    anim_cfg = scene_cfg.get(anim_name) or {}
    # Re-apply persisted config to the animation meta ONLY when it changed.
    # Live knob edits arrive over OSC via apply_synth_meta (which updates
    # meta directly, NOT config); re-applying config every frame would
    # revert those edits each frame — the "knob does nothing" bug.
    if (hasattr(engine.scene._animation, "update_meta")
            and anim_cfg != engine._last_synth_cfg):
        engine.scene._animation.update_meta(anim_cfg)
        engine._last_synth_cfg = dict(anim_cfg)
    breath_cfg = engine.config.get("breathing") or {}
    render_params = {"palettes": breath_cfg.get("palettes", [])}
    engine.scene.tick(t_ms)
    engine.scene.render(frame, t_ms, render_params)


def _render_off(engine, frame, t_ms, fade_in, fade_out, state):
    for i in range(len(frame)):
        frame[i] = 0


MODE_REGISTRY: dict[str, ModeSpec] = {
    "breathing": ModeSpec("breathing", _render_breathing,
                          breathing.FADE_IN_S, breathing.FADE_OUT_S),
    "standby":   ModeSpec("standby",   _render_standby,
                          standby.FADE_IN_S,   standby.FADE_OUT_S,
                          needs_state=True),
    "fireplace": ModeSpec("fireplace", _render_fireplace,
                          fireplace.FADE_IN_S, fireplace.FADE_OUT_S,
                          needs_state=True),
    "midi":      ModeSpec("midi",      _render_midi),
    "debug":     ModeSpec("debug",     _render_debug),
    "off":       ModeSpec("off",       _render_off),
}

# Legacy mode name migrations (old saved configs).
LEGACY_MODE_ALIASES: dict[str, str] = {
    "weight": "standby",   # briefly a top-level mode, now a scale overlay
    "music":  "midi",      # pre-Scene framework name
    "scene":  "midi",      # renamed once the tab was relabeled MIDI
}

# Power constants (from docs/inventory.md)
WATTS_PER_LED_FULL_WHITE = 0.1  # WS2811 at full RGB white
SYSTEM_IDLE_WATTS = 10.5        # RPi(5W) + WLED(1W) + Fan(1.5W) + Amp idle(2W) + misc(1W)

logger = logging.getLogger(__name__)


class AnimationEngine:
    def __init__(self, config, transport, sim_bus=None, osc_state=None,
                 scene=None, scale=None, time_provider=time.monotonic):
        self.config = config
        self.transport = transport
        self.sim_bus = sim_bus
        self.osc_state = osc_state
        self.scene = scene
        self.scale = scale
        # Injected monotonic clock — defaults to time.monotonic, but
        # tests can pass a fake clock to drive the frame loop or the
        # transition coordinator without real-time sleeps.
        self._clock = time_provider
        # Last scene.<anim> config applied to the animation meta. We only
        # re-apply on change so live knob edits over OSC aren't clobbered
        # every frame (see _render_midi).
        self._last_synth_cfg = None
        self.frame = bytearray(FRAME_BYTES)
        # Migrate stale modes (e.g. "music" before the scene refactor) so a
        # saved config from a previous version doesn't leave the engine in a
        # no-op dispatch branch.
        saved_mode = config.get("mode") or "breathing"
        if saved_mode in LEGACY_MODE_ALIASES:
            saved_mode = LEGACY_MODE_ALIASES[saved_mode]
            config.set("mode", saved_mode)
        if saved_mode not in MODE_REGISTRY:
            saved_mode = "breathing"
            config.set("mode", saved_mode)
        self._mode = saved_mode
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        # Per-mode mutable state, one dict per mode that declares
        # needs_state=True. Reset on (re)entry to that mode.
        self._mode_states: dict[str, dict] = {
            name: {} for name, spec in MODE_REGISTRY.items() if spec.needs_state
        }
        # Crossfade coordinator (owns from/to/t0 + scratch layer buffer).
        self._transition = TransitionCoordinator(self._fade_durations)
        # Power averaging (LED watts + system idle + battery runtime).
        self._power = PowerEstimator(
            system_idle_watts=SYSTEM_IDLE_WATTS,
            battery_wh=4096,
            watts_per_led_full_white=WATTS_PER_LED_FULL_WHITE,
            total_leds=TOTAL,
        )
        self._start_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._fps_time = 0.0

    @property
    def mode(self):
        with self._lock:
            return self._mode

    @mode.setter
    def mode(self, value):
        with self._lock:
            prev = self._mode
            self._mode = value
            # Reset per-mode state on (re)entry so e.g. standby starts
            # with an empty sparkle population.
            spec = MODE_REGISTRY.get(value)
            if spec is not None and spec.needs_state:
                self._mode_states[value] = {}
            # A pair where BOTH modes declare a fade gets crossfaded;
            # everything else (debug/midi/off) is an instant cut.
            if prev != value and self._has_fade(prev) and self._has_fade(value):
                self._transition.start(prev, value, self.time_ms())
            else:
                self._transition.clear()

    @property
    def actual_fps(self):
        return round(self._fps, 1)

    @property
    def uptime_seconds(self):
        if self._start_time == 0:
            return 0
        return round(self._clock() - self._start_time)

    def time_ms(self) -> float:
        """Engine-relative monotonic clock in ms (matches `time_ms` passed to renderers)."""
        if self._start_time == 0:
            return 0.0
        return (self._clock() - self._start_time) * 1000.0

    @property
    def power_estimate(self) -> dict:
        """Current rolling-average draw + battery runtime, computed by
        the PowerEstimator co-object."""
        return self._power.estimate()

    def start(self):
        self._running = True
        self._start_time = self._clock()
        self._fps_time = self._start_time
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Animation engine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Animation engine stopped")

    def _loop(self):
        while self._running:
            fps = self.config.get("transport").get("fps", 22)
            target_interval = 1.0 / max(fps, 1)
            frame_start = self._clock()
            time_ms = (frame_start - self._start_time) * 1000

            mode = self.mode

            # Mode transition first — if it's in flight, the transition
            # render claims the frame for this tick.
            if not self._transition.render(time_ms, self.frame, self._render_mode):
                self._render_mode(mode, self.frame, time_ms)

            # Weight shadows overlay — additive, on top of whatever just
            # painted (mode render or transition). Only when the scale's
            # overlay toggle is on.
            if self.scale is not None and self.scale.cfg.weight_overlay:
                scale_cfg = self.config.get("scale") or {}
                weight_params = scale_cfg.get("shadows") or {}
                snap = self.scale.snapshot()
                weight_shadows.render(self.frame, time_ms, weight_params,
                                      snap, clear=False)

            self.transport.send_frame(self.frame)

            # Mirror the same frame to any simulator UI clients so what
            # they render matches what WLED is rendering.
            if self.sim_bus is not None:
                self.sim_bus.push_frame(self.frame)

            # Power: PowerEstimator owns the rolling-window average.
            self._power.push_frame_rgb_sum(sum(self.frame), self._clock())

            # FPS tracking
            self._frame_count += 1
            now = self._clock()
            elapsed_fps = now - self._fps_time
            if elapsed_fps >= 1.0:
                self._fps = self._frame_count / elapsed_fps
                self._frame_count = 0
                self._fps_time = now

            # Sleep to maintain framerate
            elapsed = now - frame_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _fade_durations(self, mode: str) -> tuple[float, float]:
        """(fade_in_s, fade_out_s) — declared in the registry. Modes
        without a crossfade get (0, 0) and are cut to instantly."""
        spec = MODE_REGISTRY.get(mode)
        if spec is None:
            return (0.0, 0.0)
        return (spec.fade_in_s, spec.fade_out_s)

    def _has_fade(self, mode: str | None) -> bool:
        if mode is None:
            return False
        fin, fout = self._fade_durations(mode)
        return (fin > 0.0) or (fout > 0.0)

    def _render_mode(self, mode: str, frame: bytearray, time_ms: float,
                     fade_in: float | None = None,
                     fade_out: float | None = None) -> None:
        """Dispatch a render for `mode` into `frame` via the registry.
        Unknown mode names silently no-op (engine policy: never crash a
        frame on a bad mode value — config migration in __init__ is the
        place to catch that)."""
        spec = MODE_REGISTRY.get(mode)
        if spec is None:
            return
        state = self._mode_states.get(mode) if spec.needs_state else None
        spec.render(self, frame, time_ms, fade_in, fade_out, state)

