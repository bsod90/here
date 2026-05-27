"""Event catalog — registers the default Scene event set with an EventRouter.

This is the "synth-for-visuals" instrument definition: every event that
the Scene knows how to respond to, what action it dispatches, default
curve assignments, default durations, and any custom behavior (regrow's
phased fade-then-respawn, palette crossfade's pre-state setup).

Re-running `register_default_events(router, scene)` rebuilds the catalog;
the Scene calls this at construction.

Curve assignments default to one of the four ENVELOPES in
`scene.envelopes.default_envelopes()`:
  * curve_id="pulse_default"      — quick spike + decay
  * curve_id="transition_default" — cosine ease 0→1
  * curve_id="release_default"    — cosine fall 1→0
  * curve_id="instant"            — constant 1.0
The user reassigns these per-event from the Curves tab in the UI.
"""
from __future__ import annotations

import math

from .envelopes import Envelope, Modulator
from .events import (
    Action,
    AnchorAction,
    CompoundAction,
    EventRouter,
    ImpulseAction,
    ModulatorAction,
    PullCenterAction,
    RandomImpulseAction,
    RecenterAction,
    TorqueAction,
)


# ── Default per-event tunables ───────────────────────────────────────
# `_dur = 0` means "inherit from the curve" — most events leave it 0 so
# editing a curve's duration field naturally re-times every event that
# uses it. Tune per-event by either overriding `_dur` here, by passing
# `duration_beats` in lane params, or by adding the explicit param at
# trigger time.

_DEFAULTS = {
    "radius_min":     2.5,
    "radius_max":    16.0,
    "radius_default": 8.0,
    "spin_speed":     2.5,           # rad/s for rotate_cw/ccw events
    "pulse_amp":      1.0,
    "pulse_radius_amp": 1.2,         # LED bump on radius during Pulse
    # Inherit-from-curve defaults — keep at 0 so curves are source of truth.
    "transition_dur": 0.0,
    "release_dur":    0.0,
    "regrow_dur":     3.0,           # regrow snap-disperse + smooth gather
    "palette_dur":    0.0,
    "rotate_torque":  4.0,           # angular torque (rad/s²) per rotate event
                                     # — held while note_on; friction decays
                                     # the spin once the event is released.
    # Dissolve / Respawn — total duration in beats. Disperse phase is the
    # first ~30%, float phase the middle ~40%, fade phase the last ~30%.
    # Dissolve length lets particles drift visibly; respawn 4× longer so
    # the materialize-in feels deliberate.
    "dissolve_dur":   8.0,
    "respawn_dur":   16.0,
}


# ── Custom actions for events that don't fit the basic Action types ──

class RegrowAction:
    """Animated re-appearance: the ring is snapped to invisible at the
    center, then SMOOTHLY grows out to radius_default + alpha=1 over
    `duration_beats`. Visual: a tiny dot at the origin blooms into the
    full ring. Aux state (rotations, ball, torques, dissolve) is also
    scrubbed so the final state is fully fresh.

    Distinct from Respawn (which uses the dot cloud reassembly path).
    Regrow is the "ring-based" reset — the actual ring shrinks-to-zero-
    then-grows-back. Keep `duration_beats` short (1-2 beats) if you have
    Expand fires close after — Regrow's grow phase will override Expand's
    radius modulation otherwise.
    """
    def __init__(self, scene):
        self._scene = scene

    def on(self, event, scene):
        params = event.get("params") or {}
        total = float(params.get("duration_beats", _DEFAULTS["regrow_dur"]))
        ease = str(params.get("ease", "ease_out"))
        env = _envelope_ease(scene, ease)
        meta = getattr(getattr(scene, "_animation", None), "meta", {}) or {}
        target_radius = float(params.get("radius",
                                         meta.get("radius_default",
                                                  _DEFAULTS["radius_default"])))

        # Cancel any prior regrow/dissolve/respawn lifecycle.
        _scrub_dissolve_lifecycle(scene)
        try:
            scene.clear_modulators_by_tag_prefix("regrow-")
            scene.clear_scheduled_by_tag_prefix("regrow-")
        except AttributeError:
            pass

        # Scrub aux state.
        for i in range(3):
            scene.set_state(f"oval_velocity_{i}", 0.0)
            scene.set_state(f"oval_rotation_{i}", 0.0)
        scene.set_state("dissolve_amount", 0.0)
        try:
            scene.clear_torques()                       # type: ignore[attr-defined]
        except AttributeError:
            pass
        try:
            scene.physics.reset()                       # type: ignore[attr-defined]
            scene.physics.set_center_lock(False)        # type: ignore[attr-defined]
        except AttributeError:
            pass

        # Snap invisible at center, then grow back smoothly.
        scene.set_state("radius", 0.0)
        scene.set_state("alpha", 0.0)
        beat = scene.current_beat()
        scene.add_modulator(Modulator(
            target="radius", op="absolute",
            base_value=0.0, peak_value=target_radius,
            envelope=env, start_beat=beat,
            duration_beats=max(0.05, total),
            tag="regrow-grow-radius",
        ))
        scene.add_modulator(Modulator(
            target="alpha", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=env, start_beat=beat,
            duration_beats=max(0.05, total),
            tag="regrow-grow-alpha",
        ))
        regrow_start_beat = beat
        def _pin_grown(sc, r=target_radius, my_start=regrow_start_beat):
            # Per-TARGET bail. Pin radius UNLESS another event owns
            # radius now (e.g. an Expand fired at the loop wrap);
            # pin alpha UNLESS something else owns alpha. Previously
            # a single global bail meant Expand on radius would also
            # block the alpha pin — leaving alpha stuck at baseline=0
            # (causing the "pulse goes from 0 to full" symptom).
            pin_radius = True
            pin_alpha = True
            for m in getattr(sc, "_modulators", []):
                if m.target not in ("radius", "alpha"):
                    continue
                if m.tag and m.tag.startswith("regrow-"):
                    continue
                if m.op != "absolute":
                    continue
                if m.start_beat < my_start:
                    continue
                if m.target == "radius":
                    pin_radius = False
                elif m.target == "alpha":
                    pin_alpha = False
            if pin_radius:
                sc.set_state("radius", r)
            if pin_alpha:
                sc.set_state("alpha", 1.0)
        scene.schedule(max(0.0, total - 0.02), _pin_grown,
                       tag="regrow-pin-grown")

    def off(self, event, scene):
        pass


def _scrub_dissolve_lifecycle(scene):
    """Clear every dissolve + respawn modulator AND scheduled callback.
    Called by both DissolveAction.on and RespawnAction.on so retriggering
    starts with a clean slate — no stale "pin alpha=0" callbacks from an
    earlier dissolve about to fire during a respawn, etc."""
    try:
        scene.clear_modulators_by_tag_prefix("dissolve-")   # type: ignore[attr-defined]
        scene.clear_modulators_by_tag_prefix("respawn-")    # type: ignore[attr-defined]
        scene.clear_scheduled_by_tag_prefix("dissolve-")    # type: ignore[attr-defined]
        scene.clear_scheduled_by_tag_prefix("respawn-")     # type: ignore[attr-defined]
    except AttributeError:
        pass


def _envelope_ease(scene, ease_kind: str) -> "Envelope":
    """Thin shim around `envelopes.ease_envelope` — kept as a wrapper so
    existing call sites that pass `scene` (for future scene-aware curve
    lookup) don't break."""
    from .envelopes import ease_envelope
    return ease_envelope(ease_kind)


class DissolveAction:
    """Comet-trail dissolve — particles whip around the rings then
    gradually diverge into brownian dispersal then fade to empty.

    Phases (fractions of total):
      0.00–0.70  disperse: dissolve_amount 0 → 1 with ease-IN
                 (slow start so the fast-spin phase reads visually;
                 orbital rotation in `_render_dots` is FAST at low
                 dissolve_amount and slows quadratically as it ramps)
      0.70–0.80  settle:   particles brownian-drift at the dispersed
                 position; alpha still at peak (you see the settled
                 cloud before it begins to fade)
      0.80–1.00  fade:     alpha → 0 with ease-out

    Sequential calls are safe: each trigger first cancels any in-flight
    dissolve/respawn lifecycle (mods + scheduled callbacks) so state
    can't get stuck halfway through a previous cycle.
    """
    def on(self, event, scene):
        params = event.get("params") or {}
        total = float(params.get("duration_beats", _DEFAULTS["dissolve_dur"]))
        # ease-IN by default — slow at the start of the dispersal so
        # the fast spinning-comet phase has time to read on screen.
        ease = str(params.get("ease", "ease_in"))
        env = _envelope_ease(scene, ease)
        beat = scene.current_beat()

        # Clean any prior dissolve/respawn so we don't get stuck mid-cycle.
        _scrub_dissolve_lifecycle(scene)

        disperse_dur = max(0.1, total * 0.70)
        float_dur    = max(0.05, total * 0.10)
        fade_dur     = max(0.05, total * 0.20)

        # Lock the dispersal-range radius to whatever the ring is now,
        # so a Contract/Expand fired mid-dissolve doesn't snap the dot
        # cloud inward/outward. Cleared at fade-end by _pin_dark.
        lock_r = float(scene.get_state("radius", 0.0))
        if lock_r > 0:
            scene.set_state("dissolve_radius_lock", lock_r)

        # Seed particles ON the rings at trigger time so they don't
        # pop into existence — at low dissolve_amount they're locked
        # to the ring tangent and look like the rings themselves.
        anim = getattr(scene, "_animation", None)
        if anim is not None and hasattr(anim, "spawn_particles_on_rings"):
            anim.spawn_particles_on_rings(scene.state)

        # Snap to "particles active, locked on rings". The renderer
        # now ties ring opacity to dot_orbit_lock^3 (so rings fade
        # exactly as the particles diverge from them) — dissolve_amount
        # is just a "particles exist" flag here, no longer driving
        # ring visibility. set_state(dissolve_amount, 1) ensures the
        # particle path renders for the full lifecycle.
        scene.set_state("dissolve_amount", 1.0)
        scene.set_state("dot_orbit_lock", 1.0)
        scene.set_state("dot_speed", 1.0)

        # ── DOT MOTION ORCHESTRATION ──────────────────────────────
        # dot_orbit_lock — steering strength toward ring tangent.
        # Shortened locked window (20% of total) so the dissolve
        # spends MORE time in the flying-away phase. Particles only
        # need to read as "on the ring" for one revolution; the rest
        # is divergence + escape.
        #   t=0.0  → 1.0   (locked, particles ARE the rings)
        #   t=0.20 → 1.0   (locked — short visible spin)
        #   t=0.35 → 0.40  (DIVERGE starts early)
        #   t=0.55 → 0.05  (mostly random)
        #   t=1.0  → 0.0   (pure wander)
        orbit_env = Envelope(points=[
            (0.0,  1.0), (0.20, 1.0), (0.35, 0.40),
            (0.55, 0.05), (1.0, 0.0),
        ], interp="linear")
        scene.add_modulator(Modulator(
            target="dot_orbit_lock", op="absolute",
            base_value=0.0, peak_value=1.0,   # env carries the actual curve
            envelope=orbit_env, start_beat=beat,
            duration_beats=total,
            tag="dissolve-orbit",
        ))

        # dot_speed envelope. Boost speed EARLIER (right as the
        # diverge phase starts) and hold the high-speed flying-away
        # window LONGER. With locked phase now 20%, the boost kicks
        # in at 35% and stays elevated until 85% of total — gives
        # particles a long sustained "escape velocity" window.
        #   t=0.0  → 1.0   (spinning on rings)
        #   t=0.20 → 1.0   (still locked)
        #   t=0.35 → 1.8   (BOOST early — flying off fast)
        #   t=0.85 → 1.5   (still going strong through random phase)
        #   t=1.0  → 0.7   (momentum carries them past the frame)
        speed_env = Envelope(points=[
            (0.0, 1.0), (0.20, 1.0), (0.35, 1.8),
            (0.85, 1.5), (1.0, 0.7),
        ], interp="linear")
        scene.add_modulator(Modulator(
            target="dot_speed", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=speed_env, start_beat=beat,
            duration_beats=total,
            tag="dissolve-speed",
        ))

        # Phase 3: alpha fade, scheduled to start after disperse + float.
        # Read alpha LIVE inside the callback (not closed-over at on() time)
        # so the fade doesn't snap backwards if another event (Pulse, etc.)
        # modified alpha during the disperse/float phases.
        def _begin_fade(sc, dur=fade_dur, e=env):
            live_alpha = float(sc.get_state("alpha", 1.0))
            sc.add_modulator(Modulator(
                target="alpha", op="absolute",
                base_value=live_alpha, peak_value=0.0,
                envelope=e, start_beat=sc.current_beat(),
                duration_beats=dur,
                tag="dissolve-fade",
            ))
        scene.schedule(disperse_dur + float_dur, _begin_fade,
                       tag="dissolve-begin-fade")

        # Pin alpha to 0 right before the fade mod completes; release
        # the dispersal-radius lock; AND clear the particle simulation
        # state so the tick loop stops advancing invisible particles
        # forever after the dissolve finishes.
        def _pin_dark(sc):
            sc.set_state("alpha", 0.0)
            sc.set_state("dissolve_radius_lock", 0.0)
            sc.set_state("dissolve_amount", 0.0)
            anim_inner = getattr(sc, "_animation", None)
            if anim_inner is not None and hasattr(anim_inner, "clear_particles"):
                anim_inner.clear_particles()
        scene.schedule(disperse_dur + float_dur + fade_dur - 0.02, _pin_dark,
                       tag="dissolve-pin-dark")

    def off(self, event, scene):
        pass


class RespawnAction:
    """Mirror of Dissolve. Starts from dispersed-invisible, eases back
    into the clean ring state. Ease-IN curve — slow start, fast finish
    (everything snaps into focus near the end).

    On trigger, snaps these state vars to a known starting condition:
      * dissolve_amount = 1.0 (fully dispersed)
      * alpha           = 0.0 (invisible)
      * oval_rotation_{0..2} = 0.0
      * oval_velocity_{0..2} = 0.0
      * ball physics    → reset (cx, cy, vx, vy, sx, sy = 0)
      * center_lock     → False
      * all held torques cleared

    Does NOT touch (deliberately — Expand/Contract own these and a user
    composing Expand+Respawn shouldn't have the respawn clobber them):
      * radius / radius_offset_{0..2}
      * oval_enabled_{0..2}, oval_skew_{0..2}, oval_phase_{0..2},
        oval_side_{0..2}, oval_segments_{0..2}, oval_gap_{0..2}
      * palette_idx, palette_blend, palette_target_idx
      * brightness, gap_coefficient

    End state after the animation completes:
      alpha=1, dissolve_amount=0, plus whatever the above untouched
      vars were at trigger time.
    """
    def on(self, event, scene):
        params = event.get("params") or {}
        total = float(params.get("duration_beats", _DEFAULTS["respawn_dur"]))
        ease = str(params.get("ease", "ease_in"))
        env = _envelope_ease(scene, ease)
        beat = scene.current_beat()

        _scrub_dissolve_lifecycle(scene)

        fade_in_dur = max(0.05, total * 0.3)
        gather_dur  = max(0.05, total * 1.0)

        # Snap to the starting condition (dispersed-invisible) so the
        # respawn always plays its full "fade-in + gather" animation
        # regardless of where the scene was when triggered. Scrub aux
        # state at the same time — same intent as Regrow's aux scrub.
        scene.set_state("dissolve_amount", 1.0)
        scene.set_state("alpha", 0.0)
        # Lock dispersal-range radius to current radius so a
        # Contract/Expand fired mid-respawn doesn't snap the cloud.
        # Cleared on respawn-gather completion via _pin_amount.
        lock_r = float(scene.get_state("radius", 0.0))
        if lock_r > 0:
            scene.set_state("dissolve_radius_lock", lock_r)

        # Seed particles at the GRID EDGES — they fly inward (heading
        # set in spawn_particles_random) as the respawn orchestration
        # accelerates them and locks them onto the rings.
        anim = getattr(scene, "_animation", None)
        if anim is not None and hasattr(anim, "spawn_particles_random"):
            grid = getattr(scene, "_grid", None)
            anim.spawn_particles_random(scene.state, grid=grid)

        # Snap motion to "wandering, no coherence". Speed will be
        # derived from orbit_lock by the renderer — at lock=0 it
        # automatically sits at speed_min.
        scene.set_state("dot_orbit_lock", 0.0)
        scene.set_state("dot_speed", 1.0)

        try:
            scene.clear_torques()                       # type: ignore[attr-defined]
        except AttributeError:
            pass
        try:
            scene.physics.reset()                       # type: ignore[attr-defined]
            scene.physics.set_center_lock(False)        # type: ignore[attr-defined]
        except AttributeError:
            pass
        for _i in range(3):
            scene.set_state(f"oval_rotation_{_i}", 0.0)
            scene.set_state(f"oval_velocity_{_i}", 0.0)

        scene.add_modulator(Modulator(
            target="alpha", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=env, start_beat=beat,
            duration_beats=fade_in_dur,
            tag="respawn-alpha",
        ))
        # dissolve_amount is just a "particles render" flag now (ring
        # opacity is dot_orbit_lock^3). Stays at 1 throughout respawn
        # so particles render the whole time. Pinned to 0 at the end
        # via _pin_amount — the final handoff to ring-only rendering
        # (which visually matches since particles are locked onto the
        # ring tangent at that point).

        # ── DOT MOTION ORCHESTRATION (reverse of dissolve) ─────────
        # User feedback (2026-05-25): "Same for respawn — at least one
        # circle aligned before finishing". So orbit_lock should reach
        # 1.0 by ~70% of total and HOLD for the last 30% (≥1 full
        # revolution at typical durations).
        #   t=0.0  → 0.0   (wandering, flying in from off-grid)
        #   t=0.30 → 0.15  (still mostly wandering, biased inward)
        #   t=0.55 → 0.55  (clearly curving toward orbit)
        #   t=0.70 → 1.0   (LOCKED)
        #   t=1.0  → 1.0   (held — visible spinning rings)
        orbit_env = Envelope(points=[
            (0.0, 0.0), (0.30, 0.15), (0.55, 0.55),
            (0.70, 1.0), (1.0, 1.0),
        ], interp="linear")
        scene.add_modulator(Modulator(
            target="dot_orbit_lock", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=orbit_env, start_beat=beat,
            duration_beats=gather_dur,
            tag="respawn-orbit",
        ))

        # dot_speed envelope for respawn — particles fly in from grid
        # edges (need decent speed even at orbit_lock=0 to actually
        # reach the visible area), then full speed as they lock into
        # orbital motion.
        #   t=0.0  → 0.70  (flying in fast from edges)
        #   t=0.35 → 0.90
        #   t=0.65 → 1.0   (full orbital speed as lock saturates)
        #   t=1.0  → 1.0
        speed_env = Envelope(points=[
            (0.0, 0.70), (0.35, 0.90), (0.65, 1.0), (1.0, 1.0),
        ], interp="linear")
        scene.add_modulator(Modulator(
            target="dot_speed", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=speed_env, start_beat=beat,
            duration_beats=gather_dur,
            tag="respawn-speed",
        ))

        # dot_visibility envelope — particles render at full intensity
        # for most of respawn, then fade out at the end so they hand
        # off smoothly to the ring rendering (which is also taking
        # over via the orbit_lock → 1 → ring_weight = 1 path).
        #   t=0.0  → 1.0
        #   t=0.80 → 1.0   (full vis throughout convergence)
        #   t=1.0  → 0.0   (faded out, ring rendering takes over)
        vis_env = Envelope(points=[
            (0.0, 1.0), (0.80, 1.0), (1.0, 0.0),
        ], interp="linear")
        scene.add_modulator(Modulator(
            target="dot_visibility", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=vis_env, start_beat=beat,
            duration_beats=gather_dur,
            tag="respawn-vis",
        ))

        def _pin_alpha(sc):
            sc.set_state("alpha", 1.0)
        def _pin_amount(sc):
            sc.set_state("dissolve_amount", 0.0)
            sc.set_state("dissolve_radius_lock", 0.0)
            # Lock orbit + speed at their target values so the
            # modulators ending doesn't drop them back to the
            # baseline captured at trigger time (0 for orbit_lock).
            # Without this, the rings (whose opacity = orbit_lock^3)
            # would vanish the moment the modulator expires.
            sc.set_state("dot_orbit_lock", 1.0)
            sc.set_state("dot_speed", 1.0)
        scene.schedule(fade_in_dur - 0.02, _pin_alpha, tag="respawn-pin-alpha")
        scene.schedule(gather_dur - 0.02,  _pin_amount, tag="respawn-pin-amount")

    def off(self, event, scene):
        pass


class _PersistAction:
    """Push-and-hold an absolute state value. Attack-only modulator that
    pins the target to its peak on completion so the value sticks — the
    next event of the same `tag` overrides it.

    Used for Expand / Contract / similar "set the radius to X and leave it
    there" semantics. Distinct from `ModulatorAction` which auto-releases
    back to base on note_off.
    """
    def __init__(self, *, target: str, peak_value: float,
                 curve_id: str = "transition_default",
                 ease: str = "ease_in_out",
                 duration_beats: float = 1.0,
                 tag: str | None = None):
        self.target = target
        self.peak_value = float(peak_value)
        self.curve_id = curve_id          # kept for back-compat; unused now
        self.ease = ease
        self.duration_beats = float(duration_beats)
        self.tag = tag

    def on(self, event, scene):
        params = event.get("params") or {}
        # Per-event ease override; otherwise use action's default ease.
        ease = str(params.get("ease", getattr(self, "ease", None) or "ease_in_out"))
        env = _envelope_ease(scene, ease)
        # Duration: per-event > action default > 1 beat fallback.
        if "duration_beats" in params:
            duration = float(params["duration_beats"])
        else:
            duration = float(getattr(self, "duration_beats", None) or 1.0)
        peak = float(params.get("peak", self.peak_value))
        beat = scene.current_beat()
        base = scene.get_state(self.target, 0.0)
        scene.add_modulator(Modulator(
            target=self.target, op="absolute",
            base_value=base, peak_value=peak,
            envelope=env, start_beat=beat,
            duration_beats=max(0.05, duration),
            tag=self.tag,
            pitch=event.get("pitch"),
        ))
        # Pin to peak when the attack completes — BUT bail if a newer
        # absolute mod on this target started after us. The race we're
        # guarding against: this Expand's mod finishes (Phase 5 prune),
        # then a sequencer note fires another Expand (Phase 11), then
        # our stale pin runs (Phase 13) and stomps the new attack's
        # baseline. Same fix shape as RegrowAction's _pin_grown.
        my_start = beat
        target = self.target
        def _pin(sc, peak=peak, my_start=my_start, target=target):
            for m in getattr(sc, "_modulators", []):
                if m.target != target or m.released:
                    continue
                if m.op != "absolute":
                    continue
                if m.start_beat > my_start:
                    return
            sc.set_state(target, peak)
        scene.schedule(max(0.0, duration - 0.02), _pin,
                       tag=f"persist-pin-{target}")

    def off(self, event, scene):
        pass


class PaletteAction:
    """Crossfade palette_blend 0→1, then explicitly swap palette_idx.

    Picks the target palette from `params.palette` (int index). If a
    previous crossfade is mid-flight (blend > 0.5), commit it first so
    colors don't snap backwards. The swap happens on a scheduled callback
    at the end of the crossfade — not by reading "blend >= 1.0" each frame
    (which is fragile because the modulator returns None at exactly
    duration, so blend never reaches 1.0 in state).
    """
    def on(self, event, scene):
        params = event.get("params") or {}
        target = int(params.get("palette", 0))
        cur_blend = scene.get_state("palette_blend", 0.0)
        cur_target = int(scene.get_state("palette_target_idx", 0))
        if cur_blend >= 0.5:
            scene.set_state("palette_idx", cur_target)

        # Clear any pending palette commit from a prior crossfade.
        # Without this, the prior _commit would fire later and snap
        # palette_idx back to the OLD target — visible glitch.
        try:
            scene.clear_scheduled_by_tag_prefix("palette-")   # type: ignore[attr-defined]
        except AttributeError:
            pass

        scene.set_state("palette_target_idx", target)
        scene.set_state("palette_blend", 0.0)

        ease = str(params.get("ease", "ease_in_out"))
        env = _envelope_ease(scene, ease)
        beat = scene.current_beat()
        dur = float(params.get("duration_beats", _DEFAULTS["palette_dur"]))
        if dur <= 0:
            dur = 0.5  # sensible default
        scene.add_modulator(Modulator(
            target="palette_blend", op="absolute",
            base_value=0.0, peak_value=1.0,
            envelope=env, start_beat=beat,
            duration_beats=dur,
            tag="palette",
            pitch=event.get("pitch"),
        ))

        def _commit(sc, target=target):
            sc.set_state("palette_idx", target)
            sc.set_state("palette_blend", 0.0)
        scene.schedule(dur, _commit, tag="palette-commit")

    def off(self, event, scene):
        pass


# ── Builder ──────────────────────────────────────────────────────────

def register_default_events(router: EventRouter, scene) -> None:
    """Register the full event catalog on a fresh or existing router.

    Reads radius/spin defaults from the active animation's `meta` dict so
    catalog events scale with the synth config — radius_max from `meta`
    will be the actual peak of an Expand event, not a hardcoded 16. The
    Scene calls this again whenever the animation meta changes so live
    edits to radius_max etc. take effect on the next trigger.
    """
    meta = getattr(getattr(scene, "_animation", None), "meta", {}) or {}
    radius_max     = float(meta.get("radius_max",     _DEFAULTS["radius_max"]))
    radius_min     = float(meta.get("radius_min",     _DEFAULTS["radius_min"]))
    radius_default = float(meta.get("radius_default", _DEFAULTS["radius_default"]))
    spin_speed     = float(meta.get("spin_speed",     _DEFAULTS["spin_speed"]))

    # Expand / Contract — push-and-hold. Ramps radius to its target over
    # the curve's attack duration, then pins state to the target so it
    # stays there until another event overrides. note_off is a no-op
    # (length on the piano roll doesn't matter — the next event is what
    # changes the radius again).
    router.register("expand", _PersistAction(
        target="radius", peak_value=radius_max,
        curve_id="transition_default", tag="radius",
    ))
    router.register("contract", _PersistAction(
        target="radius", peak_value=radius_min,
        curve_id="transition_default", tag="radius",
    ))

    # Pulse: simultaneous additive bumps on alpha AND radius. The
    # alpha bump brightens; the radius bump makes the rings "breathe"
    # outward briefly. Both use the same spike envelope (fast rise,
    # slow decay) so they pulse in sync.
    router.register("pulse", CompoundAction(actions=[
        ModulatorAction(
            target="alpha", op="additive",
            peak_value=_DEFAULTS["pulse_amp"],
            duration_beats=0.5,
            curve_id="pulse_default",
            release_curve_id=None,
            tag="pulse-alpha",
            ease="pulse",
        ),
        # Radius bump: ~10% of typical radius. Additive on top of
        # whatever Expand/Contract has set. Default peak 1.0 LED.
        ModulatorAction(
            target="radius", op="additive",
            peak_value=_DEFAULTS.get("pulse_radius_amp", 1.2),
            duration_beats=0.5,
            curve_id="pulse_default",
            release_curve_id=None,
            tag="pulse-radius",
            ease="pulse",
        ),
    ]))

    # Shimmer: sustains a voice-vibration wobble on the rings while
    # the MIDI note is held. note_on ramps shimmer_amount up; note_off
    # releases. The vibration FREQUENCY scales inversely with the
    # note's duration_beats — short stabs vibrate fast (vibrato),
    # long held notes shimmer slowly (rumble).
    class _ShimmerAct:
        _inner = ModulatorAction(
            target="shimmer_amount", op="absolute",
            peak_value=1.0,
            duration_beats=0.15,        # quick attack
            release_beats=0.25,         # short decay on note_off
            curve_id="transition_default",
            release_curve_id="release_default",
            tag="shimmer",
            ease="ease_out",
        )
        def on(self, event, scene):
            params = event.get("params") or {}
            # User-set note duration controls vibrato speed.
            #   dur 0.25 → ~2× speed (fast vibrato)
            #   dur 1.0 → 1× speed (default)
            #   dur 4.0 → 0.5× speed (slow rumble)
            dur = float(params.get("duration_beats", 1.0))
            speed_mult = (1.0 / max(0.1, dur)) ** 0.5
            scene.set_state("shimmer_speed_mult", speed_mult)
            self._inner.on(event, scene)
        def off(self, event, scene):
            self._inner.off(event, scene)
    router.register("shimmer", _ShimmerAct())

    # Blow out: radius → very large AND alpha → 0 simultaneously.
    router.register("blow_out", CompoundAction(actions=[
        ModulatorAction(
            target="radius", op="absolute",
            peak_value=radius_max * 1.4,
            duration_beats=_DEFAULTS["transition_dur"],
            release_beats=_DEFAULTS["release_dur"],
            curve_id="transition_default",
            release_curve_id="release_default",
            tag="blowout-radius",
        ),
        ModulatorAction(
            target="alpha", op="absolute",
            peak_value=0.0,
            duration_beats=_DEFAULTS["transition_dur"],
            release_beats=_DEFAULTS["release_dur"],
            curve_id="transition_default",
            release_curve_id="release_default",
            tag="blowout-alpha",
        ),
    ]))

    # Regrow: snap-to-invisible then ease back. Custom multi-phase.
    router.register("regrow", RegrowAction(scene))

    # Rotate CW / CCW — torque-based. Holding the event applies angular
    # torque to the oval's velocity; releasing it lets global friction
    # spin it down. Each oval has its own velocity, so per-ring events
    # spin only that ring; the global variant drives all three. Param
    # override: pass `params.torque` to apply a stronger/weaker push.
    # Index convention: 0 = outer ring (back), 1 = middle (drawn on top),
    # 2 = inner. Label kept stable for back-compat in the route URLs.
    oval_labels = {0: "outer", 1: "middle", 2: "inner"}
    # Back-compat: old "rim" name (used to be index 0). Keep an alias so
    # saved sequences referencing rotate_cw_rim still work.
    oval_labels_back_compat = {0: "rim"}
    torque_default = float(_DEFAULTS["rotate_torque"])
    for sign, dir_name in ((+1.0, "cw"), (-1.0, "ccw")):
        # Global — applies torque to all 3 ovals simultaneously.
        router.register(f"rotate_{dir_name}", CompoundAction(actions=[
            TorqueAction(
                target=f"oval_velocity_{i}",
                torque=sign * torque_default,
                tag=f"rotate-{dir_name}-{i}",
            )
            for i in range(3)
        ]))
        # Per-ring — torque applied to just that oval.
        for i, label in oval_labels.items():
            router.register(f"rotate_{dir_name}_{label}", TorqueAction(
                target=f"oval_velocity_{i}",
                torque=sign * torque_default,
                tag=f"rotate-{dir_name}-{i}",
            ))
        # Back-compat: rotate_*_rim alias (now points at outer ring).
        for i, label in oval_labels_back_compat.items():
            router.register(f"rotate_{dir_name}_{label}", TorqueAction(
                target=f"oval_velocity_{i}",
                torque=sign * torque_default,
                tag=f"rotate-{dir_name}-{i}",
            ))
    # Stop rotation — clears any held rotate torques on the target ring
    # AND snaps its velocity to 0 (instant brake). Friction would
    # eventually decay it anyway, but Stop is meant to be immediate.
    def _make_stop(oval_indices):
        class _StopAction:
            def on(self, event, scene):
                for i in oval_indices:
                    tgt = f"oval_velocity_{i}"
                    scene.clear_torques(   # type: ignore[attr-defined]
                        predicate=lambda k, t, q, _t=tgt: t != _t)
                    scene.set_state(tgt, 0.0)
            def off(self, event, scene):
                pass
        return _StopAction()
    router.register("stop_rotation", _make_stop(range(3)))
    for i, label in oval_labels.items():
        router.register(f"stop_rotation_{label}", _make_stop((i,)))
    for i, label in oval_labels_back_compat.items():
        router.register(f"stop_rotation_{label}", _make_stop((i,)))

    # Push impulses — each note_on adds a velocity impulse to the ball.
    # All push events go through the same physics.impulse() path so
    # they're consistent (same speed/jitter knobs apply).
    router.register("push_left",  ImpulseAction(dx=-1.0, dy=0.0))
    router.register("push_right", ImpulseAction(dx=+1.0, dy=0.0))
    router.register("push_up",    ImpulseAction(dx=0.0, dy=-1.0))   # screen-up = -y
    router.register("push_down",  ImpulseAction(dx=0.0, dy=+1.0))
    # Pull center: smooth duration-bounded pull to (0, 0). The ball
    # GUARANTEES it lands at exact origin after the configured beats.
    router.register("pull_center", PullCenterAction())
    # Push random: each note_on picks a fresh random direction.
    router.register("push_random", RandomImpulseAction())

    # ── Per-circle show / hide events ──────────────────────────
    # Index meaning: 0 = outer, 1 = middle (top), 2 = inner.
    _oval_idx = {"outer": 0, "middle": 1, "inner": 2, "rim": 0}   # rim → outer alias
    for label, idx in _oval_idx.items():
        def _show(_i=idx):
            class _ShowAct:
                def on(self, event, scene):  scene.set_state(f"oval_enabled_{_i}", True)
                def off(self, event, scene): pass
            return _ShowAct()
        def _hide(_i=idx):
            class _HideAct:
                def on(self, event, scene):  scene.set_state(f"oval_enabled_{_i}", False)
                def off(self, event, scene): pass
            return _HideAct()
        router.register(f"show_{label}", _show())
        router.register(f"hide_{label}", _hide())

    # ── SFX overlays ──────────────────────────────────────────
    # Each takes:  duration_beats (musical length), color (0..7 palette
    # slot index), ease (curve shape). Render as additive overlays on
    # top of the synth animation.
    from .sfx import MeteorsSfx, DustPulseSfx, FlashSfx, WipeSfx
    def _make_sfx_action(cls, default_duration=4.0):
        class _SfxAct:
            def on(self, event, scene):
                params = event.get("params") or {}
                dur = float(params.get("duration_beats", default_duration))
                color = int(params.get("color", 0))
                ease = str(params.get("ease", "linear"))
                sfx = cls(
                    start_beat=scene.current_beat(),
                    duration_beats=max(0.1, dur),
                    color_idx=color,
                    ease=ease,
                )
                # Per-class extras from params.
                if cls is MeteorsSfx:
                    if "count" in params:      sfx.count = int(params["count"])
                    if "angle_deg" in params:  sfx.angle_deg = float(params["angle_deg"])
                elif cls is DustPulseSfx:
                    if "cluster_count" in params:
                        sfx.cluster_count = int(params["cluster_count"])
                    if "cluster_radius" in params:
                        sfx.cluster_radius = float(params["cluster_radius"])
                    if "min_distance" in params:
                        sfx.min_distance_from_last = float(params["min_distance"])
                elif cls is WipeSfx:
                    if "angle_deg" in params:  sfx.angle_deg = float(params["angle_deg"])
                    if "band_width" in params: sfx.band_width = float(params["band_width"])
                try:
                    scene.add_sfx(sfx)                   # type: ignore[attr-defined]
                except AttributeError:
                    pass
            def off(self, event, scene):
                pass
        return _SfxAct()
    router.register("meteors", _make_sfx_action(MeteorsSfx, default_duration=4.0))
    router.register("dust",    _make_sfx_action(DustPulseSfx, default_duration=3.0))
    router.register("flash",   _make_sfx_action(FlashSfx, default_duration=0.6))
    router.register("wipe",    _make_sfx_action(WipeSfx, default_duration=2.0))

    # ── Back-compat aliases ────────────────────────────────────
    # Old sequences referencing float_* / push_center keep working but
    # log a one-shot deprecation warning per name so the user knows to
    # update to the canonical push_* / pull_center spelling.
    _DEPRECATED_ALIASES = {
        "float_left":   ("push_left",   ImpulseAction(dx=-1.0, dy=0.0)),
        "float_right":  ("push_right",  ImpulseAction(dx=+1.0, dy=0.0)),
        "float_up":     ("push_up",     ImpulseAction(dx=0.0, dy=-1.0)),
        "float_down":   ("push_down",   ImpulseAction(dx=0.0, dy=+1.0)),
        "float_center": ("pull_center", PullCenterAction()),
        "push_center":  ("pull_center", PullCenterAction()),
    }
    _warned_aliases: set[str] = set()
    def _make_deprecated(old_name: str, new_name: str, inner_action):
        import logging
        log = logging.getLogger(__name__)
        class _Deprecated:
            def on(self, event, scene):
                if old_name not in _warned_aliases:
                    log.warning("event %r is deprecated; use %r", old_name, new_name)
                    _warned_aliases.add(old_name)
                inner_action.on(event, scene)
            def off(self, event, scene):
                inner_action.off(event, scene)
        return _Deprecated()
    for _old, (_new, _inner) in _DEPRECATED_ALIASES.items():
        router.register(_old, _make_deprecated(_old, _new, _inner))

    # Color palette: crossfade to params.palette.
    router.register("color_palette", PaletteAction())

    # Dissolve / Respawn — particle-cloud effects on the synth ovals.
    router.register("dissolve", DissolveAction())
    router.register("respawn",  RespawnAction())


# Convenience export — list every event the catalog knows about.
def catalog_event_names() -> list[str]:
    return [
        "expand", "contract", "pulse", "blow_out", "regrow",
        "rotate_cw", "rotate_ccw",
        "rotate_cw_outer", "rotate_ccw_outer",
        "rotate_cw_middle", "rotate_ccw_middle",
        "rotate_cw_inner", "rotate_ccw_inner",
        "stop_rotation", "stop_rotation_outer",
        "stop_rotation_middle", "stop_rotation_inner",
        "push_left", "push_right", "push_up", "push_down", "pull_center",
        "push_random",
        "color_palette", "dissolve", "respawn", "shimmer",
        "show_outer", "hide_outer",
        "show_middle", "hide_middle",
        "show_inner", "hide_inner",
        "meteors", "dust", "flash", "wipe",
    ]
