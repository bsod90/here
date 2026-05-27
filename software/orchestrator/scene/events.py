"""Event router — bridge from MIDI events to Scene/Physics actions.

The MidiSequencer (or a live MIDI source, or an admin button) emits raw
events:
  ``{type: "note_on" | "note_off", pitch: int, beat: float, ...}``

The router maps `pitch` to an event *name* via the lane configuration,
looks up the registered `Action` for that name, and calls `action.on(...)`
or `action.off(...)` with a `SceneAPI` handle.

There are four built-in action types:

  • `ModulatorAction`    — creates a `Modulator` on note_on; releases it
                            (envelope ramp back) on note_off.
  • `ImpulseAction`      — applies a velocity impulse to the ball on
                            note_on; no-op on note_off.
  • `AnchorAction`       — toggles a sustained state on note_on/off
                            (e.g. ball center-pull spring).
  • `CompoundAction`     — fans out to multiple sub-actions (used for
                            events that drive several modulators at once,
                            like `blow_out` = radius + alpha).

The full event catalog (expand/contract/pulse/blow_out/regrow/rotate_*/
float_*/color_palette) is registered in Phase 3 once the Scene wiring
exists. This module is the pure routing/action infrastructure.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from .envelopes import Envelope, Modulator

logger = logging.getLogger(__name__)


# ── SceneAPI: what an Action can ask the Scene to do ─────────────────

class SceneAPI(Protocol):
    """Minimal surface Actions need. Implemented by Scene; faked in tests."""

    def add_modulator(self, mod: Modulator) -> None: ...
    def release_pitch(self, pitch: Optional[int], tag: Optional[str], beat: float) -> None: ...
    def apply_impulse(self, dx: float, dy: float) -> None: ...
    def add_push(self, dx: float, dy: float, magnitude: float,
                 duration_beats: float, interp: str) -> None: ...
    def start_pull_center(self, duration_beats: float, interp: str) -> None: ...
    def apply_torque(self, key, target: str, torque: float) -> None: ...
    def remove_torque(self, key) -> None: ...
    def clear_torques(self) -> None: ...
    def add_sfx(self, sfx) -> None: ...
    def set_center_lock(self, lock: bool) -> None: ...
    def get_state(self, key: str, default: float = 0.0) -> float: ...
    def set_state(self, key: str, value) -> None: ...
    def schedule(self, beats_from_now: float, fn: Callable,
                 tag: Optional[str] = None) -> None: ...
    def clear_modulators_by_tag_prefix(self, prefix: str) -> None: ...
    def clear_scheduled_by_tag_prefix(self, prefix: str) -> None: ...
    def current_beat(self) -> float: ...
    @property
    def curves(self) -> dict[str, Envelope]: ...
    @property
    def physics(self): ...   # BallPhysics — typed Any here to avoid circular import


# ── Actions ──────────────────────────────────────────────────────────

class Action(Protocol):
    def on(self, event: dict, scene: SceneAPI) -> None: ...
    def off(self, event: dict, scene: SceneAPI) -> None: ...


@dataclass
class ModulatorAction:
    """Create a Modulator on note_on; release it on note_off.

    base_value: if None, captured from current scene state at note_on
                (so absolute mods start "from where we are now").
    """
    target: str
    op: str
    peak_value: float
    duration_beats: float
    release_beats: float = 0.0
    # Deprecated; kept so legacy registrations still construct without
    # error. The real envelope shape comes from `ease` (or per-event
    # `params.ease`). Setting this has no effect.
    curve_id: str = "transition_default"
    release_curve_id: Optional[str] = "release_default"   # None → no release tail
    base_value: Optional[float] = None
    tag: Optional[str] = None
    ease: Optional[str] = None   # default curve shape; per-event override via params.ease

    def on(self, event: dict, scene: SceneAPI) -> None:
        params = event.get("params") or {}
        # Ease picker — per-event override of the action's default curve
        # shape. Mapped to one of the interp values supported by Envelope.
        ease = str(params.get("ease",
                              getattr(self, "ease", None) or "ease_in_out"))
        if ease == "instant":
            env = Envelope(points=[(0.0, 1.0), (1.0, 1.0)], interp="linear")
        elif ease in ("pulse", "spike"):
            # Quick rise, slow decay — the classic accent envelope.
            env = Envelope(
                points=[(0.0, 0.0), (0.08, 1.0), (1.0, 0.0)],
                interp="ease_out_quad",
            )
        else:
            interp = _EASE_INTERP.get(ease, "cosine")
            env = Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp=interp)
        rel_ease = str(params.get("release_ease",
                                   getattr(self, "release_ease", None) or "ease_out"))
        rel_interp = _EASE_INTERP.get(rel_ease, "ease_out_quad")
        rel_env = (Envelope(points=[(0.0, 1.0), (1.0, 0.0)], interp=rel_interp)
                   if self.release_curve_id else None)
        base = (
            self.base_value
            if self.base_value is not None
            else (scene.get_state(self.target, 0.0) if self.op == "absolute" else 0.0)
        )
        # Use the scene's absolute beat as the modulator's start_beat. The
        # event["beat"] from the sequencer is the loop-position (0..loop),
        # which would put the mod's start in the past every loop wrap —
        # the modulator would then read as "sustaining at peak forever".
        beat = scene.current_beat()
        # Duration priority: per-event override > action default > curve default.
        # The curve itself carries a "natural" length in beats so the user
        # can dial in transition durations by editing the curve once.
        params = event.get("params") or {}
        if "duration_beats" in params:
            duration = float(params["duration_beats"])
        elif self.duration_beats > 0:
            duration = self.duration_beats
        else:
            duration = float(env.duration_beats)
        if "release_beats" in params:
            release_beats = float(params["release_beats"])
        elif self.release_beats > 0:
            release_beats = self.release_beats
        elif rel_env is not None:
            release_beats = float(rel_env.duration_beats)
        else:
            release_beats = 0.0
        peak = float(params.get("peak", self.peak_value))
        mod = Modulator(
            target=self.target,
            op=self.op,
            base_value=base,
            peak_value=peak,
            envelope=env,
            start_beat=beat,
            duration_beats=duration,
            release_envelope=rel_env,
            release_duration_beats=release_beats,
            pitch=event.get("pitch"),
            tag=self.tag,
        )
        scene.add_modulator(mod)

    def off(self, event: dict, scene: SceneAPI) -> None:
        # If the action has no release curve, it's a one-shot — the
        # envelope already returns to 0 / its end value by itself, so
        # note_off should be a no-op (otherwise a quick click+release
        # on Pulse would cut the decay short).
        if not self.release_curve_id:
            return
        # Use scene's absolute beat — event["beat"] from the sequencer
        # is a loop-position, not absolute time.
        scene.release_pitch(event.get("pitch"), self.tag, scene.current_beat())


# Single source of truth lives in envelopes.EASE_TO_INTERP.
from .envelopes import EASE_TO_INTERP as _EASE_INTERP   # noqa: E402


@dataclass
class ImpulseAction:
    """Push the ball with an impulse — instant when duration=0, or
    integrated over `duration_beats` via the chosen ease curve.

    Per-event params:
      scale (float):     multiplier on physics.speed for this push.
      duration_beats:    > 0 → spreads the push over time with `ease`.
                         (default 0 = instant impulse like the old behavior)
      ease (str):        linear | ease_in | ease_out | ease_in_out
    """
    dx: float
    dy: float

    def on(self, event: dict, scene: SceneAPI) -> None:
        params = event.get("params") or {}
        scale = float(params.get("scale", 1.0))
        duration = float(params.get("duration_beats", 0.0))
        ease = str(params.get("ease", "linear"))
        if duration <= 0:
            # Classic instant impulse — applies directly.
            scene.apply_impulse(self.dx * scale, self.dy * scale)
            return
        # Time-integrated push. Magnitude carried into Scene's push
        # lifecycle; tick integrates curve(t) × magnitude over duration.
        magnitude = float(scene.physics.params.speed) * scale   # type: ignore[attr-defined]
        interp = _EASE_INTERP.get(ease, "linear")
        try:
            scene.add_push(                                    # type: ignore[attr-defined]
                dx=self.dx, dy=self.dy,
                magnitude=magnitude,
                duration_beats=duration,
                interp=interp,
            )
        except AttributeError:
            scene.apply_impulse(self.dx * scale, self.dy * scale)

    def off(self, event: dict, scene: SceneAPI) -> None:
        pass


class RandomImpulseAction:
    """Apply an impulse in a uniformly random direction on note_on.

    Magnitude comes from physics.params.speed by default; can be scaled
    per-event via `params.scale`. Each trigger picks a fresh angle, so
    rapid retriggers throw the ball around chaotically.
    """
    def on(self, event: dict, scene: SceneAPI) -> None:
        import math, random
        params = event.get("params") or {}
        scale = float(params.get("scale", 1.0))
        angle = random.uniform(0.0, 2.0 * math.pi)
        dx = math.cos(angle) * scale
        dy = math.sin(angle) * scale
        scene.apply_impulse(dx, dy)

    def off(self, event: dict, scene: SceneAPI) -> None:
        pass


@dataclass
class TorqueAction:
    """Apply a continuous angular torque to a state target while the note
    is held. note_on starts pushing on the target's velocity at `torque`
    rad/s²; note_off removes the push. The Scene's tick loop integrates
    each active torque into the velocity each frame, then applies global
    angular friction. Hold longer → faster spin (bounded by friction);
    release → the spin coasts to a stop.

    Per-event override via `params.torque`.
    """
    target: str               # state key, e.g. "oval_velocity_1"
    torque: float             # default torque magnitude (rad/s²)
    tag: Optional[str] = None # for choking + identification

    def on(self, event: dict, scene: SceneAPI) -> None:
        params = event.get("params") or {}
        torque = float(params.get("torque", self.torque))
        key = (event.get("pitch"), self.tag)
        try:
            scene.apply_torque(key, self.target, torque)   # type: ignore[attr-defined]
        except AttributeError:
            pass

    def off(self, event: dict, scene: SceneAPI) -> None:
        key = (event.get("pitch"), self.tag)
        try:
            scene.remove_torque(key)   # type: ignore[attr-defined]
        except AttributeError:
            pass


@dataclass
class AnchorAction:
    """Toggle a sustained state on note_on (True) / note_off (False).

    Currently bound to the ball's center-pull spring (Float Center event).
    """
    def on(self, event: dict, scene: SceneAPI) -> None:
        scene.set_center_lock(True)

    def off(self, event: dict, scene: SceneAPI) -> None:
        scene.set_center_lock(False)


@dataclass
class PullCenterAction:
    """Pull the ball to (0, 0) over a fixed musical duration. After the
    duration the ball is GUARANTEED at exact center, zero velocity —
    reliable, deterministic, doesn't depend on damping/physics tuning.

    Per-event params:
      duration_beats:    musical length of the pull (default 2.0).
      ease (str):        linear | ease_in | ease_out | ease_in_out
                         (default ease_in_quad → settles into center).
    """
    def on(self, event: dict, scene: SceneAPI) -> None:
        params = event.get("params") or {}
        duration = float(params.get("duration_beats", 2.0))
        ease = str(params.get("ease", "ease_in_out"))
        interp = _EASE_INTERP.get(ease, "ease_in_quad")
        try:
            scene.start_pull_center(   # type: ignore[attr-defined]
                duration_beats=duration, interp=interp,
            )
        except AttributeError:
            pass

    def off(self, event: dict, scene: SceneAPI) -> None:
        pass


# Back-compat — legacy import name still used by tests.
RecenterAction = PullCenterAction


@dataclass
class CompoundAction:
    """Fan note_on/note_off to multiple sub-actions in registration order."""
    actions: list = field(default_factory=list)

    def on(self, event: dict, scene: SceneAPI) -> None:
        for a in self.actions:
            a.on(event, scene)

    def off(self, event: dict, scene: SceneAPI) -> None:
        for a in self.actions:
            a.off(event, scene)


# ── EventRouter ─────────────────────────────────────────────────────

class EventRouter:
    """Maps MIDI events to registered Actions via lane configuration."""

    def __init__(self, scene_api: SceneAPI, lanes: Optional[list[dict]] = None):
        self._scene = scene_api
        self._lanes: list[dict] = list(lanes or [])
        self._events: dict[str, Action] = {}
        # Per-event default params (color, ease, cluster_count, etc.).
        # Merged into every dispatch under lane.params under event.params.
        self._event_defaults: dict[str, dict] = {}
        self._lock = threading.RLock()

    # ── Configuration ───────────────────────────────────────────────
    def register(self, name: str, action: Action) -> None:
        with self._lock:
            self._events[name] = action

    def unregister(self, name: str) -> None:
        with self._lock:
            self._events.pop(name, None)

    @property
    def events(self) -> list[str]:
        with self._lock:
            return sorted(self._events.keys())

    def set_lanes(self, lanes: list[dict]) -> None:
        with self._lock:
            self._lanes = list(lanes or [])

    @property
    def lanes(self) -> list[dict]:
        with self._lock:
            return [dict(l) for l in self._lanes]

    def set_event_default(self, name: str, params: dict) -> None:
        """Set the default params dict for an event name. Merged into every
        future dispatch (lane params and per-event params override)."""
        with self._lock:
            self._event_defaults[name] = dict(params or {})

    def set_event_defaults(self, defaults: dict[str, dict]) -> None:
        with self._lock:
            self._event_defaults = {
                k: dict(v or {}) for k, v in (defaults or {}).items()
            }

    @property
    def event_defaults(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._event_defaults.items()}

    # ── Dispatch ────────────────────────────────────────────────────
    def dispatch(self, event: dict) -> bool:
        """Receive a sequenced or live MIDI event. Routes by lane[pitch] → action.
        Returns True if an action ran."""
        pitch = event.get("pitch")
        action: Optional[Action] = None
        lane_params: dict = {}
        defaults: dict = {}
        with self._lock:
            if pitch is not None and 0 <= pitch < len(self._lanes):
                lane = self._lanes[pitch]
                name = lane.get("event")
                action = self._events.get(name)
                lane_params = dict(lane.get("params") or {})
                defaults = dict(self._event_defaults.get(name, {}))
        if action is None:
            return False
        # Param precedence (lowest → highest): event_defaults < lane.params
        # < event.params (per-trigger overrides win).
        enriched = dict(event)
        enriched.setdefault("params", {})
        merged = dict(defaults)
        merged.update(lane_params)
        merged.update(enriched["params"])
        enriched["params"] = merged
        try:
            if event["type"] == "note_on":
                action.on(enriched, self._scene)
            elif event["type"] == "note_off":
                action.off(enriched, self._scene)
            else:
                logger.warning(f"unknown event type: {event['type']}")
                return False
        except Exception:
            logger.exception(f"action {event['type']} raised")
            return False
        return True

    def dispatch_by_name(
        self,
        name: str,
        *,
        event_type: str = "note_on",
        pitch: Optional[int] = None,
        params: Optional[dict] = None,
    ) -> bool:
        """Direct trigger from admin UI / OSC / piano-roll click — bypasses lane mapping."""
        with self._lock:
            action = self._events.get(name)
            defaults = dict(self._event_defaults.get(name, {}))
        if action is None:
            logger.warning(f"unknown event name: {name}")
            return False
        beat = self._scene.current_beat()
        # event_defaults provide a baseline; explicit params override.
        merged_params = dict(defaults)
        merged_params.update(params or {})
        event = {
            "type": event_type,
            "pitch": pitch,
            "beat": beat,
            "velocity": 1.0 if event_type == "note_on" else 0.0,
            "source": "direct",
            "params": merged_params,
        }
        try:
            if event_type == "note_on":
                action.on(event, self._scene)
            elif event_type == "note_off":
                action.off(event, self._scene)
            else:
                return False
        except Exception:
            logger.exception(f"action {name} raised")
            return False
        return True
