"""Scene v2 — the stateful core of the synth-for-visuals engine.

Replaces the v1 Scene. Composes:
  * BeatClock — musical time + phase drift
  * MidiSequencer — note_on/note_off events from a looping piano roll
  * EventRouter + EventCatalog — maps events to actions (modulators, impulses, anchors)
  * BallPhysics — squishy-ball position + squash tensor
  * list of active Modulators — envelope-driven state writes
  * the active Animation (SynthAnimation)

Public API kept (mostly) compatible with v1 so admin/routes.py and
main.py don't need a major rewrite:
  * `clock`, `set_bpm(bpm)`, `reset_phase()`
  * `state` property (flat dict, one frame's worth of truth)
  * `sequencer` property (MidiSequencer; quacks like the v1 Sequencer
    for the admin code paths that just read snapshots / set notes)
  * `snapshot()` — extended JSON with new keys (modulators, ball, curves)
  * `set_state(var, value)` — instant write
  * `schedule(beats_from_now, fn)` — phased event callbacks
  * `align_to_loop_zero(monotonic_t_seconds)` — tap-tempo phase align
  * `trigger(event_name, duration_beats, params)` — dispatches by name
  * `tick(time_ms)` — frame-rate update
  * `render(frame, time_ms, params)` — paints the frame
  * `set_animation(animation)` — runtime swap
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

from grid import DEFAULT_GRID, Grid
from .clock import BeatClock
from .envelopes import Envelope, Modulator, combine, default_envelopes
from .events import EventRouter
from .midi_sequencer import MidiSequencer
from .physics import BallPhysics, PhysicsParams

logger = logging.getLogger(__name__)


# Choke policy: when a new note_on arrives for the same (pitch, tag) as
# an active modulator, drop the old one immediately and start a new one.
# (The alternative "release" path that ramped the old one down via its
# release envelope was implemented but never used — synth-style retrigger
# should snap.)


def _choke_key(mod):
    """Identifier two mods must share to choke each other.

    Tag wins (so admin-triggered and sequencer-triggered "pulse" events
    choke each other even though only one has a pitch). Pitch is the
    fallback for tagless actions (raw sequencer notes with no event tag).
    None means "don't choke anything" (trivial impulses, etc.).
    """
    if mod.tag is not None:
        return ("tag", mod.tag)
    if mod.pitch is not None:
        return ("pitch", mod.pitch)
    return None


class Scene:
    def __init__(
        self,
        animation,
        bpm: float = 120.0,
        curves: dict | None = None,
        physics_params: PhysicsParams | None = None,
        grid: Grid = DEFAULT_GRID,
    ):
        self._animation = animation
        self._grid = grid
        self._clock = BeatClock(bpm=bpm)
        self._state: dict[str, Any] = animation.initial_state()
        self._curves: dict[str, Envelope] = dict(curves or default_envelopes())
        self._physics = BallPhysics(params=physics_params or PhysicsParams())
        self._modulators: list[Modulator] = []
        # Baseline values captured at the start of each modulation episode
        # — when a target's first modulator is added, we stash the current
        # state value here. Each frame, state[target] = combine(target,
        # baseline, mods, beat). When all mods on the target finish, the
        # state reverts to its baseline. Without this, additive/mult mods
        # would silently accumulate every frame.
        self._baselines: dict[str, float] = {}
        # SceneAPI surface: the router needs an object that satisfies the
        # protocol. We satisfy it directly via methods on Scene.
        self._router = EventRouter(self, lanes=list(getattr(animation, "NOTE_LANES", [])))
        self._sequencer = MidiSequencer(loop_length_beats=16.0)
        # Phased events (regrow's fade-then-respawn etc.)
        self._scheduled: list[tuple[float, Any]] = []
        # Active torques — applied each tick until the holding event ends.
        # Keyed by (pitch, tag) so multiple events targeting the same oval
        # sum cleanly without choking each other. Each value is
        # (target_key, torque_value).
        self._active_torques: dict[Any, tuple[str, float]] = {}
        # Pull-to-center lifecycle. None when inactive; otherwise a dict
        # with start_beat / duration_beats / start_cx / start_cy / ease.
        self._active_pull: Optional[dict] = None
        # Active push impulses being applied over a duration. Each entry
        # adds force × curve(t) to ball velocity each tick until expired.
        # Instant pushes (duration_beats == 0) are applied once and not
        # tracked here.
        self._active_pushes: list[dict] = []
        # Active SFX overlays — short-lived visual effects rendered on
        # top of the main animation (Meteors, Dust pulse, Flash, Wipe).
        self._active_sfx: list = []
        # Per-frame timing.
        self._last_tick_ms: Optional[float] = None
        self._last_tick_beat: Optional[float] = None
        # Pause flag — when True, scene.tick() still updates animation.tick
        # and renders, but freezes the clock and skips modulator evaluation,
        # sequencer crossings, and physics. Lets the user tweak meta params
        # and see them live without the scene drifting around them.
        self._paused: bool = False
        self._lock = threading.RLock()
        # Wire up the event catalog now (after _state and _modulators exist
        # so the registered actions can immediately reference Scene methods).
        from .event_catalog import register_default_events
        register_default_events(self._router, self)

    # ── Clock controls ────────────────────────────────────────────
    @property
    def clock(self) -> BeatClock:
        return self._clock

    def set_bpm(self, bpm: float) -> None:
        self._clock.set_bpm(bpm)

    def reset_phase(self) -> None:
        self._clock.reset_phase()

    # ── Pause / resume ────────────────────────────────────────────
    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        """Freeze the clock + modulator state. Render still happens with the
        current state, so meta-param tweaks (blur, brightness, colors) take
        effect live. Sequencer note crossings are also skipped while paused."""
        with self._lock:
            self._paused = True
            self._clock.pause()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self._clock.resume()
            # Pretend dt = 0 on the next tick so we don't fast-forward
            # everything by however long the pause lasted.
            self._last_tick_ms = None

    def reset(self) -> None:
        """Full reset — clears modulators, baselines, scheduled callbacks,
        re-inits animation state, zeros physics, and snaps clock to beat 0.
        Sequencer playback flag is preserved (caller decides Play vs Stop)."""
        with self._lock:
            self._modulators.clear()
            self._baselines.clear()
            self._scheduled.clear()
            self._active_torques.clear()
            self._active_pushes.clear()
            self._active_pull = None
            self._active_sfx.clear()
            self._state = self._animation.initial_state()
            self._physics.reset()
            self._physics.set_center_lock(False)
            self._last_tick_ms = None
            self._last_tick_beat = None
            self._paused = False
            self._clock.reset_phase()
            self._sequencer.resync_to_playhead()

    # ── State access ──────────────────────────────────────────────
    @property
    def state(self) -> dict[str, Any]:
        return self._state

    @property
    def sequencer(self) -> MidiSequencer:
        return self._sequencer

    @property
    def router(self) -> EventRouter:
        return self._router

    @property
    def physics(self) -> BallPhysics:
        return self._physics

    @property
    def curves(self) -> dict[str, Envelope]:  # noqa: D401 — also satisfies SceneAPI
        with self._lock:
            return dict(self._curves)

    def set_curve(self, name: str, env: Envelope) -> None:
        with self._lock:
            self._curves[name] = env

    def set_curves(self, curves: dict[str, Envelope]) -> None:
        with self._lock:
            self._curves = dict(curves or {})

    def set_physics_params(self, params: PhysicsParams) -> None:
        self._physics.params = params

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            base = {
                "bpm": self._clock.bpm,
                "beat": self._clock.now_beat(),
                "paused": self._paused,
                "animation": self._animation.name,
                "anim_meta": dict(getattr(self._animation, "meta", {}) or {}),
                "modulators": [
                    {
                        "target": m.target, "op": m.op,
                        "base": m.base_value, "peak": m.peak_value,
                        "start_beat": m.start_beat,
                        "duration_beats": m.duration_beats,
                        "released": m.released,
                        "pitch": m.pitch, "tag": m.tag,
                    }
                    for m in self._modulators
                ],
                "ball": self._physics.snapshot(),
                "curves": {name: env.to_dict() for name, env in self._curves.items()},
                "physics": self._physics.params.to_dict(),
                "events": self._router.events,
                "state": dict(self._state),
            }
        base["sequencer"] = self._sequencer.snapshot(self._clock)
        # Lanes live on the router (per Scene v2 design) — copy them onto
        # the sequencer snapshot for back-compat with the admin UI.
        base["sequencer"]["lanes"] = self._router.lanes
        return base

    # ── SceneAPI implementation (used by the EventRouter actions) ──
    def add_modulator(self, mod: Modulator) -> None:
        with self._lock:
            # Capture baseline the first time a target starts being modulated.
            if mod.target not in self._baselines and not any(
                m.target == mod.target for m in self._modulators
            ):
                self._baselines[mod.target] = float(self._state.get(mod.target, 0.0))
            # Choked retrigger: two mods with the same choke-key replace
            # each other. Tag is the primary identifier (so "pulse" events
            # from the sequencer and admin button choke each other even
            # though only the sequencer one has a pitch). Pitch is the
            # fallback for untagged actions (e.g. raw sequencer notes).
            my_key = _choke_key(mod)
            if my_key is not None:
                for existing in self._modulators:
                    if existing.released:
                        continue
                    if _choke_key(existing) == my_key:
                        existing.released = True
                        existing.release_beat = mod.start_beat
                        existing.release_envelope = None
                        existing.release_duration_beats = 0.0
            self._modulators.append(mod)

    def release_pitch(self, pitch: Optional[int], tag: Optional[str], beat: float) -> None:
        with self._lock:
            for m in self._modulators:
                if m.pitch == pitch and m.tag == tag and not m.released:
                    m.release(beat)

    def apply_impulse(self, dx: float, dy: float) -> None:
        self._physics.impulse(dx, dy)

    def set_center_lock(self, lock: bool) -> None:
        self._physics.set_center_lock(bool(lock))

    def get_state(self, key: str, default: float = 0.0) -> float:
        with self._lock:
            return float(self._state.get(key, default))

    def set_state(self, var: str, value) -> None:
        """Snap a state variable (cancels any in-flight modulator on that target)."""
        with self._lock:
            self._state[var] = value
            self._baselines.pop(var, None)
            self._modulators = [m for m in self._modulators if m.target != var]

    # ── Bulk knob/meta updates (shared by HTTP PUT and OSC) ──────
    # These two methods centralise the orchestration of "apply a knob
    # change everywhere it needs to land" — meta dict, live state for
    # oval_* vars, and (when radius keys change) the event catalog. The
    # HTTP handlers and the OSC handlers both go through here so the
    # behaviour is identical regardless of transport.

    _OVAL_STATE_PREFIXES = (
        "oval_enabled_", "oval_skew_", "oval_phase_", "oval_side_",
        "oval_segments_", "oval_gap_", "oval_radius_scale_",
        "oval_color_", "oval_radius_offset_",
    )

    def apply_synth_meta(self, body: dict) -> None:
        """Update synth animation meta and propagate side effects.

        - merges into animation.meta so render-time lookups see new values
        - mirrors per-oval state vars into the live state dict
        - refreshes the event catalog when radius/spin keys change so
          future Expand/Contract/Blow Out modulators pick up new peaks
        Pure side-effects; callers persist to config separately if they
        want the change to survive a restart.
        """
        if not body:
            return
        self._animation.update_meta(dict(body))
        for k, v in body.items():
            if any(k.startswith(p) for p in self._OVAL_STATE_PREFIXES):
                self.set_state(k, v)
        if any(k in ("radius_min", "radius_max", "radius_default", "spin_speed")
               for k in body):
            self.refresh_event_catalog()

    def snapshot_patch(self) -> dict:
        """Return the patchable subset of the *current* scene state +
        config so the caller can persist it as a named patch."""
        return {
            "synth":             self._animation.meta_dict() if hasattr(self._animation, "meta_dict") else {},
            "curves":            {n: e.to_dict() for n, e in self._curves.items()},
            "physics":           self._physics.params.to_dict(),
            "bpm":               self.clock.bpm,
            "palette_idx":       int(self.state.get("palette_idx", 0)),
        }

    def apply_patch(self, body: dict, *,
                    config_set: Callable[[dict], None] | None = None,
                    sequence_loader=None) -> None:
        """Apply a previously-saved patch back into the live scene.

        Pure scene-state changes happen here (curves, physics, synth
        meta, bpm, palette, event-catalog refresh). The two cross-
        cutting effects are delegated:

          * `config_set(updates)` — called once with the patchable
            subset of `body` so the caller can persist it.
          * `sequence_loader` — optional; called with the `active_sequence`
            name + data so the route layer can switch playback. Receives
            (name, data) and should return the loaded dict.

        Keeping these as callbacks means Scene doesn't need to know
        about ConfigManager or SequenceStore — easier to test, easier
        to reuse from contexts that have different persistence."""
        from .envelopes import Envelope
        from .physics import PhysicsParams

        updates = {}
        for k in ("synth", "curves", "physics", "default_durations",
                  "event_defaults"):
            if k in body:
                updates[k] = body[k]
        if "bpm" in body:
            updates["bpm"] = float(body["bpm"])
        if updates and config_set is not None:
            config_set(updates)

        if "curves" in body:
            self.set_curves({n: Envelope.from_dict(v)
                             for n, v in body["curves"].items()})
        if "physics" in body:
            cur = self._physics.params.to_dict()
            cur.update({k: float(v) for k, v in body["physics"].items() if k in cur})
            self.set_physics_params(PhysicsParams(**cur))
        if "synth" in body:
            # Replace the animation meta wholesale and re-init state.
            # Without this, leftover state from the previous patch (e.g.
            # radius=17 frozen at the end of a sustain phase) would
            # corrupt the next event's base_value capture — new Expand
            # modulators would inherit the current state as their base,
            # giving a 17→17 "attack" that doesn't visibly animate.
            self._animation.update_meta(body["synth"], replace=True)
            self.set_animation(self._animation)
        if "bpm" in body:
            self.set_bpm(float(body["bpm"]))
        if "palette_idx" in body:
            self.set_state("palette_idx", int(body["palette_idx"]))
            self.set_state("palette_target_idx", int(body["palette_idx"]))
            self.set_state("palette_blend", 0.0)

        # refresh_event_catalog wipes registered actions; re-apply event
        # defaults after so per-event color / dust density / ease persist.
        self.refresh_event_catalog()
        if "event_defaults" in body:
            self.router.set_event_defaults(body["event_defaults"])

        # Sequence switch is a separate effect (touches sequencer +
        # persists active_sequence pointer). Caller decides if/how.
        active_seq = body.get("active_sequence")
        if active_seq and sequence_loader is not None:
            data = sequence_loader(active_seq)
            if data is not None:
                self.sequencer.set_loop_length(
                    float(data.get("loop_length_beats", 16.0)), clock=self.clock)
                self.sequencer.set_notes(data.get("notes") or [])
                self.reset_phase()
                self.sequencer.resync_to_playhead()
                self.sequencer.play(clock=self.clock, dispatcher=self.router)

    def apply_physics_params(self, body: dict) -> None:
        """Merge `body` into current physics params and apply. Numeric
        keys only; unknown keys ignored. No persistence — caller persists
        to config separately."""
        if not body:
            return
        from .physics import PhysicsParams
        merged = self._physics.params.to_dict()
        for k, v in body.items():
            if k not in merged:
                continue
            try:
                merged[k] = float(v)
            except (TypeError, ValueError):
                continue
        self.set_physics_params(PhysicsParams(**merged))

    def schedule(self, beats_from_now: float, fn, tag: Optional[str] = None) -> None:
        with self._lock:
            self._scheduled.append(
                (self._clock.now_beat() + float(beats_from_now), fn, tag)
            )

    def clear_modulators_by_tag_prefix(self, prefix: str) -> None:
        """Drop every modulator whose tag starts with `prefix`. Used to
        cancel a stale lifecycle (e.g. a previous Dissolve) when a new
        trigger fires."""
        with self._lock:
            self._modulators = [
                m for m in self._modulators
                if not (m.tag and m.tag.startswith(prefix))
            ]
            # Also clear baselines for targets that have no remaining
            # mods, so the next mod starts from a clean baseline.
            remaining_targets = {m.target for m in self._modulators}
            for t in list(self._baselines.keys()):
                if t not in remaining_targets:
                    # Don't restore — leave state at whatever it is now;
                    # the new lifecycle will set its own baseline.
                    self._baselines.pop(t, None)

    def clear_scheduled_by_tag_prefix(self, prefix: str) -> None:
        """Remove any pending scheduled callbacks tagged with `prefix*`."""
        with self._lock:
            self._scheduled = [
                s for s in self._scheduled
                if not (len(s) > 2 and s[2] and s[2].startswith(prefix))
            ]

    def current_beat(self) -> float:
        return self._clock.now_beat()

    # ── Torque API (used by TorqueAction for rotate events) ──────
    def apply_torque(self, key, target: str, torque: float) -> None:
        with self._lock:
            self._active_torques[key] = (str(target), float(torque))

    def remove_torque(self, key) -> None:
        with self._lock:
            self._active_torques.pop(key, None)

    # ── Push lifecycle (TIME-INTEGRATED IMPULSES) ────────────────
    def add_push(self, *, dx: float, dy: float, magnitude: float,
                 duration_beats: float, interp: str = "linear") -> None:
        with self._lock:
            self._active_pushes.append({
                "dx": float(dx), "dy": float(dy),
                "magnitude": float(magnitude),
                "duration_beats": max(0.05, float(duration_beats)),
                "start_beat": self.current_beat(),
                "interp": interp,
            })

    def clear_pushes(self) -> None:
        with self._lock:
            self._active_pushes.clear()

    # ── SFX overlay lifecycle ─────────────────────────────────
    def add_sfx(self, sfx) -> None:
        with self._lock:
            self._active_sfx.append(sfx)

    # ── Pull-to-center lifecycle ────────────────────────────────
    def start_pull_center(self, *, duration_beats: float,
                          interp: str = "ease_in_quad") -> None:
        """Begin a duration-bounded pull to (0, 0). Cancels any prior
        pull-center in flight. Each Scene.tick interpolates the ball
        toward origin; after `duration_beats` the ball is snapped to
        exact (0, 0, vx=0, vy=0) — reliable, deterministic."""
        with self._lock:
            self._active_pull = {
                "start_beat": self.current_beat(),
                "duration_beats": max(0.05, float(duration_beats)),
                "start_cx": float(self._physics.cx),
                "start_cy": float(self._physics.cy),
                "interp": interp,
            }
            # Kill any in-flight ball motion so the interpolation isn't
            # fighting prior velocity.
            self._physics.vx = 0.0
            self._physics.vy = 0.0
            self._physics.set_center_lock(False)

    def cancel_pull_center(self) -> None:
        with self._lock:
            self._active_pull = None

    def clear_torques(self, predicate=None) -> None:
        """Remove active torques. With no predicate, clears all. Otherwise
        predicate gets (key, target, torque) and returns True to keep."""
        with self._lock:
            if predicate is None:
                self._active_torques.clear()
                return
            self._active_torques = {
                k: v for k, v in self._active_torques.items()
                if predicate(k, v[0], v[1])
            }

    def align_to_loop_zero(self, monotonic_t_seconds: float) -> dict:
        loop = self._sequencer.loop_length_beats
        beat = self._clock.beat_at(monotonic_t_seconds)
        pos = beat % loop if loop > 0 else 0.0
        if pos < loop / 2:
            error = -pos
        else:
            error = loop - pos
        self._clock.request_phase_correction(error)
        self._sequencer.resync_to_playhead()
        return {
            "loop_pos_at_tap": pos,
            "correction_beats": error,
            "bpm": self._clock.bpm,
        }

    # ── Trigger (direct dispatch by name; bypasses lane mapping) ──
    def trigger(self, event_name: str, duration_beats: float | None = 1.0,
                params: dict | None = None) -> bool:
        """Route to a registered event by name.
        For ModulatorActions, `duration_beats` overrides the configured
        duration via the `duration_beats` param. Pass `None` to defer to
        the event's saved event_default (or the action's own default).
        """
        merged_params = dict(params or {})
        if duration_beats is not None and "duration_beats" not in merged_params:
            merged_params["duration_beats"] = float(duration_beats)
        return self._router.dispatch_by_name(event_name, params=merged_params)

    # ── Per-frame tick + render ───────────────────────────────────
    def tick(self, time_ms: float) -> None:
        # Phase 1: timing.
        with self._lock:
            if self._last_tick_ms is None:
                dt_seconds = 0.0
            else:
                dt_seconds = max(0.0, (time_ms - self._last_tick_ms) / 1000.0)
            self._last_tick_ms = time_ms
            # While paused, freeze the clock + skip physics + skip mod eval.
            # Render still runs from current state + (potentially updated)
            # meta, so the user sees live param edits.
            if self._paused:
                return
            self._clock.tick(dt_seconds)
            beat = self._clock.now_beat()
            self._last_tick_beat = beat

            # Phase 2: physics — ball position/squash. Bounds account for
            # the current ring radius so the ball "rolls" inside the matrix.
            radius = float(self._state.get("radius", 8.0))
            half = self._grid.center
            bound = max(0.5, half - radius)
            self._physics.tick(dt_seconds, bound_x=bound, bound_y=bound)

            # Push impulses with duration — accumulate force into ball
            # velocity over the configured envelope. Total impulse over
            # the duration matches `magnitude` for a normalized curve.
            if self._active_pushes:
                from .envelopes import Envelope
                still_active: list[dict] = []
                for push in self._active_pushes:
                    elapsed = beat - push["start_beat"]
                    dur = push["duration_beats"]
                    if elapsed >= dur:
                        continue
                    prog = max(0.0, elapsed / dur)
                    interp = push.get("interp", "linear")
                    weight = Envelope(
                        points=[(0.0, 0.0), (1.0, 1.0)], interp=interp
                    ).sample(prog)
                    # Force scaled so total integrated impulse ≈ magnitude
                    # (assuming a 0..1 curve with area ≈ 0.5 — factor 2).
                    force = push["magnitude"] / dur * weight * 2.0
                    sec_per_beat = 60.0 / max(1e-6, self._clock.bpm)
                    self._physics.vx += push["dx"] * force * dt_seconds * sec_per_beat
                    self._physics.vy += push["dy"] * force * dt_seconds * sec_per_beat
                    still_active.append(push)
                self._active_pushes = still_active

            # Pull-to-center animation — override physics with a direct
            # position interpolation. Guarantees the ball lands at exact
            # (0, 0) when the duration elapses (no asymptote / no auto-
            # anchor flakiness; reliable, deterministic, time-bounded).
            if self._active_pull is not None:
                pull = self._active_pull
                elapsed = beat - pull["start_beat"]
                progress = elapsed / pull["duration_beats"]
                if progress >= 1.0:
                    self._physics.cx = 0.0
                    self._physics.cy = 0.0
                    self._physics.vx = 0.0
                    self._physics.vy = 0.0
                    self._active_pull = None
                else:
                    from .envelopes import Envelope
                    interp = pull.get("interp", "ease_in_quad")
                    sample = Envelope(
                        points=[(0.0, 0.0), (1.0, 1.0)], interp=interp
                    ).sample(progress)
                    self._physics.cx = pull["start_cx"] * (1.0 - sample)
                    self._physics.cy = pull["start_cy"] * (1.0 - sample)
                    self._physics.vx = 0.0
                    self._physics.vy = 0.0

            # Phase 3a: torques → angular velocity (per-target sum), then
            # global friction. dv/dt = sum(torques) - friction · v.
            if dt_seconds > 0:
                torque_sums: dict[str, float] = {}
                for tgt, trq in self._active_torques.values():
                    torque_sums[tgt] = torque_sums.get(tgt, 0.0) + trq
                friction = float(self._physics.params.angular_friction)
                # Apply to all known oval velocity targets (so friction
                # decays leftover spin even when no torque is held).
                for i in range(3):
                    key = f"oval_velocity_{i}"
                    cur = float(self._state.get(key, 0.0))
                    cur += torque_sums.get(key, 0.0) * dt_seconds
                    if friction > 0:
                        cur *= max(0.0, 1.0 - friction * dt_seconds)
                    self._state[key] = cur

            # Phase 3b: per-animation tick (rotation integration, etc.).
            tick_fn = getattr(self._animation, "tick", None)
            if tick_fn is not None:
                tick_fn(self._state, beat, dt_seconds)

            # Phase 4: evaluate modulators → write to state. Combine into
            # the *baseline* value (captured at modulation start), not into
            # the current state — otherwise additive/multiplicative mods
            # would accumulate every frame.
            targets = {m.target for m in self._modulators}
            for t in targets:
                base = self._baselines.get(t, float(self._state.get(t, 0.0)))
                self._state[t] = combine(t, base, self._modulators, beat)

            # Phase 5: prune done modulators. When a target has no active
            # modulators left, restore its baseline and discard the entry.
            self._modulators = [m for m in self._modulators if not m.done(beat)]
            remaining_targets = {m.target for m in self._modulators}
            for t in list(self._baselines.keys()):
                if t not in remaining_targets:
                    # Restore baseline so the target returns to its rest value.
                    self._state[t] = self._baselines.pop(t)

            # Phase 7: scheduled callbacks due now.
            # Scheduled tuples are (beat, fn) or (beat, fn, tag) — handle both.
            due = [s for s in self._scheduled if s[0] <= beat]
            self._scheduled = [s for s in self._scheduled if s[0] > beat]

        # Phase 7.5: SFX tick (still inside lock).
        # Inside the with-block but after Phase 7 callbacks.

        # Phase 8: sequencer crossing detection — outside the lock so the
        # router can re-enter Scene methods (add_modulator etc.).
        self._sequencer.tick(self._clock, self._router)
        # SFX tick — outside the modulator lock too; SFX may call back
        # into Scene to remove themselves.
        with self._lock:
            for s in list(self._active_sfx):
                s.tick(dt_seconds, self._clock.now_beat(), self._grid)
            self._active_sfx = [
                s for s in self._active_sfx if not s.is_done(self._clock.now_beat())
            ]

        # Phase 9: scheduled callbacks — also outside the lock.
        for s in due:
            fn = s[1]
            try:
                fn(self)
            except Exception:
                logger.exception("scheduled scene callback raised")

    def render(self, frame: bytearray, time_ms: float, params: dict) -> None:
        with self._lock:
            ball_state = self._physics.snapshot()
            self._animation.render(
                frame, dict(self._state), time_ms, params,
                ball_state=ball_state,
                beat=self._clock.now_beat(),
                grid=self._grid,
            )
            # SFX overlays composited on top of the main animation.
            beat = self._clock.now_beat()
            for s in self._active_sfx:
                try:
                    s.render(frame, self._grid, time_ms, params, beat)
                except Exception:
                    logger.exception("sfx render raised")

    # ── For runtime swap of animation ─────────────────────────────
    def set_animation(self, animation) -> None:
        with self._lock:
            self._animation = animation
            self._state = animation.initial_state()
            self._modulators.clear()
            self._baselines.clear()
            self._scheduled.clear()
            # Drop any SFX in flight — their internal arrays were sized
            # for the prior animation/grid and would render garbage (or
            # index out of bounds) against the new state.
            self._active_sfx.clear()
            self._active_pushes.clear()
            self._active_pull = None
            self._active_torques.clear()
            self._last_tick_ms = None
            self._last_tick_beat = None
        # Rebind router lanes + re-register catalog to pick up new meta.
        self._router.set_lanes(list(getattr(animation, "NOTE_LANES", [])))
        self.refresh_event_catalog()

    def refresh_event_catalog(self) -> None:
        """Re-register the default event catalog. Call after editing the
        animation meta (radius_max, spin_speed, etc.) so the next event
        trigger picks up the new values."""
        from .event_catalog import register_default_events
        register_default_events(self._router, self)
