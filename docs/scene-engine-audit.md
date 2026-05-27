Excellent. Now I have a comprehensive understanding of the codebase. Let me create a detailed architectural audit report:

---

# Architectural Audit: Scene Engine v2 (Synth-for-Visuals)

## 1. Module Roles & Dependencies

### `clock.py` — **BeatClock**
- **Role**: Monotonic musical time + gradual phase drift correction
- **Main Types**: `BeatClock` (owns `_bpm`, `_t0_seconds`, `_phase_correction`, pause state)
- **Public API**: `now_beat()`, `set_bpm()`, `request_phase_correction()`, `tick(dt)`, `pause()`/`resume()`
- **Dependencies**: `threading`, `math`, `time`
- **Key Design**: Large phase corrections snap most of delta to t0, leaving small residual for smooth drift over ~1.5s. Negative corrections capped at 50% speed to prevent stalling.

### `tap.py` — **TapTracker**
- **Role**: Converts tap events into BPM estimation + phase corrections
- **Main Types**: `TapTracker` (3-second rolling tap window, ~8 taps max)
- **Public API**: `tap(monotonic_t, clock)`, `reset()`
- **Dependencies**: `threading`
- **Key Design**: Median of pairwise intervals (robust to one off-tempo tap). Phase error snapped to nearest beat integer and queued as gradual drift.

### `envelopes.py` — **Envelope & Modulator**
- **Role**: Normalized breakpoint curves + scheduled state-writes shaped over time
- **Main Types**: 
  - `Envelope` (points, interp, duration_beats) — samples `t ∈ [0,1]`
  - `Modulator` (target, op, base/peak, envelope, start/duration/release lifecycle, **tag**, pitch)
- **Public API**: `Envelope.sample(t)`, `Modulator.value_at(beat)`, `Modulator.release(beat)`, `combine(target, base, mods, beat)`
- **Dependencies**: `dataclasses`, `math`
- **Key Design**: 
  - Three ops: `absolute` (last-writer-wins), `additive` (sum), `multiplicative` (product, applied last)
  - Optional release envelope → holds at sustain until note_off, then ramps back to base
  - One-shot mods (no release envelope) → auto-complete at duration end
  - **Combine logic**: abs mods sorted by start_beat (later overwrites), then additive, then multiplicative
  - **Baselines**: Scene captures state[target] when first modulator added; `combine()` rebuilds from baseline each frame so additive/mult don't accumulate

### `events.py` — **EventRouter & Action Types**
- **Role**: MIDI→action dispatch bridge; defines action protocols
- **Main Types**:
  - `SceneAPI` (Protocol) — what actions can ask from Scene
  - `Action` (Protocol) — `.on(event, scene)` / `.off(event, scene)`
  - `ModulatorAction` — on→create Modulator, off→release or ignore
  - `ImpulseAction` — on→instant or duration-integrated ball impulse, off→no-op
  - `AnchorAction` — on→center-lock True, off→False
  - `TorqueAction` — on→add to active torques dict, off→remove
  - `PullCenterAction` — on→start duration-bounded pull to (0,0)
  - `CompoundAction` — fans out to sub-actions
  - `EventRouter` (lanes, registered events, event_defaults, dispatch logic)
- **Public API**: `router.register()`, `router.dispatch()`, `router.dispatch_by_name()`
- **Dependencies**: `envelopes`, `dataclasses`, `threading`
- **Key Design**:
  - Param precedence: event_defaults < lane.params < event.params (per-trigger highest)
  - ModulatorAction: ease/curve_id legacy support; per-event duration override
  - **Choke logic** (in Scene, not here): tag > pitch; "replace" policy cuts existing instantly
  - **Impulse duration**: timed via envelope curve × magnitude, accumulates force each frame

### `event_catalog.py` — **Action Registration & Custom Events**
- **Role**: Registers the synth's full event set; implements multi-phase lifecycle events
- **Main Classes**:
  - `RegrowAction` — snap invisible at center, grow back over duration, scrub aux state
  - `DissolveAction` — 3-phase: disperse (dissolve_amount 0→1), float, fade (alpha→0)
  - `RespawnAction` — reverse of dissolve: fade-in + gather (dissolve_amount 1→0)
  - `_PersistAction` — attack-only modulator + scheduled pin (used by Expand/Contract)
  - `PaletteAction` — crossfade palette_blend 0→1, then snap palette_idx on completion
- **Public API**: `register_default_events(router, scene)`, `catalog_event_names()`
- **Dependencies**: `envelopes`, `events`, `sfx`
- **Key Design**:
  - **Scrubbing**: `_scrub_dissolve_lifecycle()` clears dissolve-*/respawn-* tags + scheduled
  - **Regrow**: scrubs all aux (rotations, velocity, dissolve_amount, ball, torques), pins radius/alpha with scheduled callback that checks for conflicting absolute mods
  - **Dissolve**: captures cur_alpha NOW, phases as disperse (0.3) + float (0.3) + fade (0.4), pins at each phase end
  - **Respawn**: mirrors dissolve with ease-in (slow start) instead of ease-out; snaps initial state (dissolve_amount=1, alpha=0, zero rotations/velocity, ball reset)
  - **Palette**: commits any in-flight crossfade at 0.5 blend before starting new one
  - All events read curves from scene.curves; `_envelope_ease()` maps ease strings to interp types

### `midi_sequencer.py` — **MidiSequencer**
- **Role**: Looping piano-roll playback; emits note_on/note_off at beat crossings
- **Main Types**: `MidiSequencer` (notes as {pitch, start_beat, length_beats}, loop_length_beats)
- **Public API**: `set_notes()`, `play()`, `stop()`, `tick()`, `snapshot()`
- **Dependencies**: `threading`, `logging`
- **Key Design**:
  - Notes stored as start+length for backwards compat; expanded to on/off events at tick time
  - Wrap-around: note_off at `(start + length) % loop`
  - Play-immediate: fires note_on for any note within ±0.1 beats of playhead when `play()` called
  - `resync_to_playhead()` clears `_last_pos` so clock snap doesn't trigger wrap-detection false positive
  - Frozen playhead while stopped (UI timeline freezes; engine clock continues)

### `physics.py` — **BallPhysics**
- **Role**: Position (cx, cy) + velocity (vx, vy) + squash tensor (sx, sy) dynamics
- **Main Types**: 
  - `PhysicsParams` (speed, radial_offset, squishiness, damping, bounce, center_pull, tau_squash, max_velocity, angular_friction, squash_damping)
  - `BallPhysics` (state + derivatives + center_lock, auto-anchor logic)
- **Public API**: `impulse(dx, dy, magnitude)`, `reset()`, `tick(dt, bound_x, bound_y)`, `set_center_lock()`
- **Dependencies**: `dataclasses`, `math`
- **Key Design**:
  - Verlet-style: forces → velocity integration → position integration → wall collisions (bounce + squash kick)
  - Squash spring: under-damped 2nd-order oscillator (ζ < 1 → wobble/"jelly" feel)
  - Wall collisions: perpendicular velocity inverted × bounce ratio; impact kicks sx_dot/-sy_dot and sy_dot/+sx_dot (perpendicular bulge)
  - Auto-anchor: snaps to (0,0) after 3 consecutive frames within distance 0.6 + velocity 0.4
  - Center-pull spring: optional, strength scales like `p.center_pull × (cx, cy)` (no damping term, relies on velocity damping)
  - Angular friction: applied per-tick as multiplicative decay `cur *= (1 - friction × dt)`

### `sfx.py` — **SFX Overlays**
- **Role**: Short-lived additive visual effects (Meteors, Dust, Flash, Wipe)
- **Main Types**:
  - `_SfxBase` (start_beat, duration_beats, color_idx, ease, progress(), is_done())
  - `MeteorsSfx` — streaks across grid, heads + trails
  - `DustPulseSfx` — scattered dots at random cluster location, brownian drift
  - `FlashSfx` — full-screen color flash
  - `WipeSfx` — gradient band sweep
- **Public API**: `tick(dt, beat, grid)`, `render(frame, grid, time_ms, params, beat)`, `is_done(beat)`
- **Dependencies**: `numpy`, `dataclasses`, `math`, `random`
- **Key Design**:
  - Each has per-frame motion (`tick`) and composited render (additive, never zeroes pixels)
  - DustPulseSfx tracks module-level `_DUST_HISTORY` to avoid cluster overlap
  - All read palette via color_idx (0–7 maps to slots 0–7)
  - **No state clearing on Scene reset** — Scene.reset() calls `self._active_sfx.clear()` but doesn't touch SFX instances' internal `_meteors`, `_dots` lists (benign since they're re-initialized on first tick, but leaks memory if SFX outlive Scene)

### `scene.py` — **Scene**
- **Role**: Master orchestrator — owns state, clock, modulators, physics, sequencer, router, SFX, scheduled callbacks; drives tick/render phases
- **Main Types**: `Scene` (comprehensive state machine)
- **Public API**: 
  - Lifecycle: `__init__()`, `reset()`, `pause()`/`resume()`, `set_animation()`
  - Clock: `set_bpm()`, `reset_phase()`, `align_to_loop_zero()`
  - State: `state` property, `set_state()`, `get_state()`, `snapshot()`
  - Modulators: `add_modulator()`, `release_pitch()`, `clear_modulators_by_tag_prefix()`
  - Physics: `apply_impulse()`, `set_center_lock()`, `apply_torque()`, `remove_torque()`, `start_pull_center()`, `clear_torques()`
  - SFX: `add_sfx()`
  - Scheduling: `schedule()`, `clear_scheduled_by_tag_prefix()`
  - Sequencer: `sequencer` property
  - Router: `router` property, `trigger()`, `refresh_event_catalog()`
  - Per-frame: `tick(time_ms)`, `render(frame, time_ms, params)`
- **Dependencies**: All scene modules; `threading`, `logging`, `grid`
- **Key Design**:
  - **Baselines dict**: captures state[target] when first modulator added; combine() rebuilds from baseline so additive/mult don't accumulate across frames
  - **Choke policy**: "replace" → instantly zero release, OR "release" (code path exists but `_CHOKE_POLICY = "replace"`)
  - **Tick() phase order**:
    1. Timing (dt_seconds)
    2. Physics (ball position/squash) with bound adjustment per radius
    3. Time-integrated pushes (duration-bounded impulses)
    4. Pull-to-center animation (override physics for duration-bounded deterministic pull)
    5. Torques → angular velocity (sum per target, apply friction)
    6. Per-animation tick (integration work, e.g., rotation = velocity × dt)
    7. Evaluate modulators → combine() into state (from baseline)
    8. Prune done modulators + restore baselines
    9. *Scheduled callbacks due now (STILL INSIDE LOCK)*
    10. SFX tick (inside lock)
    11. Sequencer dispatch (OUTSIDE lock)
    12. SFX render prep (inside lock)
    13. Scheduled callbacks fire (OUTSIDE lock)
  - **Render phase**: copies state + ball_state, calls animation.render(), then SFX overlays

### `animations/synth.py` — **SynthAnimation**
- **Role**: Pure rendering of 3 ovals + ball overlay + dot cloud (dissolve/respawn)
- **Main Types**: `SynthAnimation` (meta dict, STATE_KEYS, geometry cache)
- **Public API**: `initial_state()`, `tick(state, beat, dt)`, `render(frame, state, time_ms, params, ball_state, beat, grid)`
- **Dependencies**: `numpy`, `grid`, `dataclasses`, `math`
- **Key Design**:
  - STATE_KEYS: all required state variables with defaults (radius, alpha, 3× oval configs, dissolve_amount, palette blend, etc.)
  - **Ring rendering**: 2-fold oval (cos(2θ)) with Gaussian blur, side masking (inside/outside/both), dashed mode, gap offsets
  - **Dot-cloud rendering** (dissolve/respawn path): 
    - Motion model: orbital (locked to ring) ↔ brownian (random) crossfade via dissolve_amount
    - Tail rendering: past-position samples tapered in size + alpha; tail spacing scales with dissolve_amount (prevents "tail explosion")
    - Seed-per-SFX deterministic randomness
  - **Palette**: builds 8-slot swatch from crossfade of two palettes; each oval picks by index via state[oval_color_i]
  - **Geometry cache**: per-grid precomputed (dist, angle, dx, dy) arrays
  - **Ball overlay**: translates center (cx, cy), stretches by squash scale (1+sx, 1+sy), warps ring geometry
  - **meta dict**: allows per-instance tuning (radius defaults, blur widths, dot_count, trail_steps, motion_speed, etc.)

### `default_presets.py` — **Bundled Patches & Sequences**
- **Role**: Seed default patch + sequence at boot
- **Main Types**: Dicts (BREATHING_PATCH, BREATHING_SEQUENCE)
- **Key Design**: Breathing patch sets 4-beat transition/release curves @ 60 BPM; sequence has Expand note 0–4 beats, Contract note 8–12 beats on a 16-beat loop

---

## 2. Lifecycle Correctness: Events & State Mutation

### **expand** / **contract**
- **Registered as**: `_PersistAction(target="radius", peak_value=radius_max/min, tag="radius")`
- **on**: Creates `Modulator` (absolute, base=current state, peak=radius_max/min, start_beat=now), schedules pin callback at end
- **off**: No-op (push-and-hold semantics)
- **State written**: `radius` (modulator) + state mutation via scheduled pin
- **Scheduled callbacks**: `_pin` callback (tag=none) — no tag, so doesn't interact with other lifecycle scrubbing
- **Clearance**: Only cleared if user calls `clear_modulators_by_tag_prefix("radius")` or `set_state("radius", ...)`
- **Edge case**: Multiple Expand events rapidly retriggered — second Modulator with tag="radius" chokes first via Scene's choke logic; scheduled pin from first still fires but re-enters Scene outside lock (no conflict, just redundant)

### **contract**
- Identical to expand but peak_value = radius_min
- **No conflict** with expand because same tag → choke replaces

### **pulse**
- **Registered as**: `ModulatorAction(target="alpha", op="additive", peak_value=1.0, duration_beats=0.5, release_envelope=None, tag="pulse", ease="pulse")`
- **on**: Creates `Modulator` (additive, base=0, peak=1, env=pulse_default, start_beat=now, duration=0.5 beats)
- **off**: No-op (one-shot envelope already decays)
- **State written**: `alpha` (additive contribution)
- **Scheduled callbacks**: None
- **Clearance**: None (self-contained one-shot)
- **Edge case**: Rapid pulses stack additively — each contributes ≤1.0 to alpha, so multiple pulses in flight sum. If 3 pulses overlap at peak, alpha gets +3.0 additive, which is fine (alpha clamped in render, not state)

### **blow_out**
- **Registered as**: `CompoundAction([ModulatorAction(...radius..., tag="blowout-radius"), ModulatorAction(...alpha..., tag="blowout-alpha")])`
- **on**: Fires both Modulators
  - Radius: absolute, peak=radius_max×1.4, duration=0 (inherit from curve), release=inherit, tag="blowout-radius"
  - Alpha: absolute, peak=0.0, same duration/release, tag="blowout-alpha"
- **off**: Releases both if they have release envelopes (default release_default)
- **State written**: `radius`, `alpha` (both absolute)
- **Scheduled callbacks**: None
- **Clearance**: Via choke (both have tags, so any new radius/alpha modulator would choke *both* in theory — but choke checks tag match, not just target)

Wait, let me clarify the choke logic from the code:

```python
my_key = _choke_key(mod)  # ("tag", mod.tag) if tag else ("pitch", mod.pitch) or None
if my_key is not None:
    for existing in self._modulators:
        if _choke_key(existing) == my_key:  # if same key, choke
```

So two mods with tag="blowout-radius" (both targeting radius) *would* choke each other if the second one has the same tag. But Expand has tag="radius" and blow_out has tag="blowout-radius", so they don't choke — both can be active simultaneously. **This is a potential conflict**: if you fire Expand then Blow Out mid-flight, both target radius (absolute) and the later modulator wins in the combine() call... but the baseline was captured from the first modulator, so combine() rebuilds from that baseline each frame. **Result**: later modulator's value overwrites per frame (last-writer-wins), but both contribute to the baseline issue if they had different base_values.

Actually, let's trace through: 
1. Expand fires → Modulator A (target="radius", op="absolute", base=8, peak=16, tag="radius") added
2. Baseline captured: `_baselines["radius"] = 8.0`
3. Combine evaluates A → writes radius to state
4. Blow Out fires mid-Expand → Modulator B (target="radius", op="absolute", base=8, peak=22.4, tag="blowout-radius") added
5. Both A and B are active; neither choked because tags differ
6. Combine sorts by start_beat (A then B) → evaluates A, then B overwrites (last wins)
7. **Problem**: baseline is still 8.0; A and B both wrote based on that. If A finishes before B, baseline is restored from _baselines, breaking B's visual

**Actual flow**: Baseline is per-target, not per-modulator. So if both A and B target "radius":
- After A done: remaining_targets won't include "radius" if B is also done → baseline restored
- If B still active: "radius" in remaining_targets → baseline NOT restored → baseline stays at 8.0, B continues from there

**No actual conflict** because combine() evaluates all active mods sorted by start_beat, last wins. The baseline isn't overwritten; it's used as the starting point for combine().

### **regrow**
- **Custom class**: `RegrowAction`
- **on**: 
  1. `_scrub_dissolve_lifecycle()` — clears dissolve-*, respawn-* mods + scheduled callbacks
  2. `scene.clear_modulators_by_tag_prefix("regrow-")`  + scheduled
  3. Scrubs aux: zero oval_velocity_*, oval_rotation_*, dissolve_amount, ball, torques, center_lock
  4. Snaps radius=0, alpha=0
  5. Creates two Modulators (tag="regrow-grow-radius" and "regrow-grow-alpha") with absolute op
  6. Schedules `_pin_grown` callback to pin radius + alpha IF no newer absolute mods exist
- **off**: No-op
- **State written**: radius, alpha (modulator) + all aux state (snap), all torques (clear), ball (reset)
- **Scheduled callbacks**: `_pin_grown` (tag="regrow-pin-grown") — checks for conflicting absolute mods and pins only if safe
- **Clearance**: `_scrub_dissolve_lifecycle()` clears dissolve/respawn; `clear_modulators_by_tag_prefix("regrow-")` clears prior regrow
- **Edge case**: 
  - Regrow fires, then Expand fires mid-grow → Expand's absolute mod on "radius" (tag="radius") doesn't conflict with regrow's (tag="regrow-*") because different tags. Both active; Expand wins in combine() since later start_beat. Regrow's `_pin_grown` callback checks `if m.start_beat >= my_start and not m.tag.startswith("regrow-")` → sees Expand's radius mod with later start_beat, so **doesn't pin**. ✓ Correct.
  - Regrow fires, another Regrow fires → first `_scrub_dissolve_lifecycle()` is no-op, second `clear_modulators_by_tag_prefix("regrow-")` clears first regrow's mods. Callbacks might still be scheduled; second regrow fires its own mods. Callbacks from first regrow still fire later and may re-pin. **Minor issue**: stale callbacks from first regrow could conflict, but unlikely to matter since they check current mod state at callback time.

### **rotate_cw** / **rotate_ccw**
- **Registered as**: `CompoundAction([TorqueAction(...oval_velocity_i..., tag="rotate-cw-i") for i in range(3)])`
- **on**: Fires all 3 TorqueActions → `scene.apply_torque(key, target, torque)` where key=(pitch, tag)
- **off**: Fires all 3 → `scene.remove_torque(key)`
- **State written**: `_active_torques[key] = (target, torque_value)` (on); remove (off)
- **Modulation**: Each tick, torques summed per target → `_state[oval_velocity_i] += torque_sums[i] × dt`, then friction applied
- **Scheduled callbacks**: None
- **Clearance**: Via `remove_torque()` on note_off
- **Edge case**: User holds Rotate CW, then fires Rotate CCW before releasing CW — both (pitch, "rotate-cw") and (pitch, "rotate-ccw") are active, torques sum. This is intentional (let them cancel or compound).

### **rotate_cw_outer** / **rotate_cw_middle** / **rotate_cw_inner** (and ccw variants)
- **Registered as**: `TorqueAction(..., tag=f"rotate-cw-{i}")`
- Same lifecycle as rotate_cw but per-ring

### **push_left** / **push_right** / **push_up** / **push_down**
- **Registered as**: `ImpulseAction(dx=..., dy=...)`
- **on**: 
  - If duration_beats=0 (default): `scene.apply_impulse(dx × scale, dy × scale)` → one-shot
  - If duration_beats>0: `scene.add_push(dx, dy, magnitude, duration_beats, interp)` → time-integrated force
- **off**: No-op
- **State written**: Ball velocity (vx, vy) via impulse or push force accumulation
- **Scheduled callbacks**: None
- **Clearance**: Instant impulses don't persist; duration-integrated pushes auto-expire when elapsed >= duration

### **pull_center** / **float_center** (alias)
- **Registered as**: `PullCenterAction()`
- **on**: `scene.start_pull_center(duration_beats, interp)` → sets `_active_pull` dict
- **off**: No-op
- **State written**: Ball cx, cy, vx, vy (direct override in tick phase 4)
- **Scheduled callbacks**: None
- **Clearance**: Auto-expires when `elapsed >= duration` (set `_active_pull = None`)

### **dissolve**
- **Custom class**: `DissolveAction`
- **on**: 
  1. `_scrub_dissolve_lifecycle()` → clears prior dissolve/respawn mods + scheduled
  2. Captures cur_alpha NOW
  3. Creates Modulator for dissolve_amount (absolute, 0→1, tag="dissolve-disperse") over disperse_dur (30% of total)
  4. Schedules `_pin_dispersed` (tag="dissolve-pin-dispersed") to snap dissolve_amount=1 after disperse
  5. Schedules `_begin_fade` (tag="dissolve-begin-fade") to fire after disperse+float duration, creates second Modulator for alpha (absolute, cur_alpha→0, tag="dissolve-fade")
  6. Schedules `_pin_dark` (tag="dissolve-pin-dark") to snap alpha=0 at end
- **off**: No-op
- **State written**: 
  - Immediately: none (mods created later)
  - Modulator phase 1: dissolve_amount 0→1
  - Modulator phase 3: alpha cur_alpha→0
- **Scheduled callbacks**: `_pin_dispersed`, `_begin_fade`, `_pin_dark` (all tagged "dissolve-*")
- **Clearance**: Full scrub on retrigger via `_scrub_dissolve_lifecycle()`
- **Edge case**: 
  - Dissolve mid-dissolve → scrub clears first; second dissolve's phases proceed independently. ✓ Safe.
  - Dissolve then Respawn before dissolve completes → respawn's scrub clears dissolve mods + scheduled. ✓ Safe.
  - **Critical issue**: cur_alpha captured at dissolve.on() time. If alpha was modified after dissolve starts but before _begin_fade fires, _begin_fade creates a new modulator with a *stale* `cur` value (closed over at on() time). This means if Pulse fires during disperse phase (0–30%), alpha peaks mid-dissolve, then during float phase (30–60%) when _begin_fade fires, it uses the OLD cur_alpha (before pulse), not the current state alpha. **Result**: fade ramp might snap backwards or skip. **Severity**: Low in practice because dissolve + pulse aren't usually combined, but technically incorrect.

### **respawn**
- **Custom class**: `RespawnAction`
- **on**: 
  1. `_scrub_dissolve_lifecycle()` → clears prior dissolve/respawn mods + scheduled
  2. Snaps: dissolve_amount=1, alpha=0, zero rotations/velocity, ball reset, torques clear
  3. Creates Modulator for alpha (absolute, 0→1, tag="respawn-alpha") over fade_in_dur (30% of total)
  4. Creates Modulator for dissolve_amount (absolute, 1→0, tag="respawn-gather") over gather_dur (100% of total)
  5. Schedules `_pin_alpha` (tag="respawn-pin-alpha") and `_pin_amount` (tag="respawn-pin-amount")
- **off**: No-op
- **State written**: 
  - Immediately: dissolve_amount=1, alpha=0, zero rotations/velocity, ball reset
  - Modulators: alpha 0→1, dissolve_amount 1→0
- **Scheduled callbacks**: `_pin_alpha`, `_pin_amount`
- **Clearance**: Full scrub on retrigger
- **Edge case**: 
  - Respawn immediately after Dissolve → dissolve's `_pin_dark` callback fires BEFORE respawn's modulators are evaluated. Sequence: dissolve triggers → scheduled callbacks queued → tick evaluates modulators (alpha from dissolve) → Phase 5 restores baseline? No, modulators still active. → Phase 9 fires scheduled callbacks outside lock → if `_pin_dark` fires and snap alpha=0, then respawn's modulators (which start fresh) begin next tick. **Potential race**: If respawn triggers at beat T and `_pin_dark` was scheduled for beat T-epsilon, `_pin_dark` might fire *after* respawn's modulators are added. **Order**: Scene.tick() fires scheduled callbacks Phase 9 (outside lock); respawn can trigger mid-tick at Phase 11 (sequencer dispatch) or directly via trigger(). Let me re-check the tick order...

Looking at tick order again:
1–6: Physics, torques, animation tick (inside lock)
7–8: Modulator eval, prune, baseline restore (inside lock)
9: Scheduled callbacks snapshot (inside lock)
10: SFX tick (inside lock)
11: Sequencer dispatch (OUTSIDE lock)
12: SFX render prep (inside lock)
13: Scheduled callbacks fire (OUTSIDE lock)

So if dissolve schedules `_pin_dark` for beat 4.5 and respawn is triggered at beat 4.5:
- Respawn trigger at beat 4.5 → `trigger()` calls `dispatch_by_name()` → immediately calls `respawn.on()` (phase 11, outside lock)
- `respawn.on()` grabs the lock, scrubs dissolve mods + scheduled, so `_pin_dark` is removed
- ✓ Safe — scrub prevents callback from firing

**However**: If respawn is sequencer-triggered at beat 4.5, and dissolve's `_begin_fade` callback is scheduled for beat 4.45:
- Tick at beat 4.45: Phase 9 snapshots due callbacks including `_begin_fade`
- Phase 13 fires `_begin_fade` (outside lock) → creates alpha modulator (tag="dissolve-fade")
- Sequencer tick (phase 11) fires respawn note_on → `respawn.on()` scrubs dissolve-* mods, INCLUDING the just-created dissolve-fade modulator
- Result: Fade modulator is removed before it evaluates. ✓ Correct (respawn takes over).

**Actual edge case**: Dissolve scheduled at beat 0, respawn triggered at beat 0.5 (sequencer overlap):
- Tick at 0.5: disperse phase active (dissolve-disperse modulator evaluates)
- Respawn.on() called → scrubs dissolve-disperse → no longer active
- Respawn creates alpha 0→1, dissolve_amount 1→0
- **Result**: dissolve_amount gets clobbered from whatever partial value (0.5×0.3=0.15 if 30% through) back to 1. Respawn's modulator then ramps 1→0 from beat 0.5. ✓ Correct.

### **color_palette** / **color_palette 1-N**
- **Custom class**: `PaletteAction`
- **on**: 
  1. Check cur_blend: if ≥0.5, commit by snapping palette_idx = palette_target_idx
  2. Snap palette_target_idx = target, palette_blend = 0
  3. Creates Modulator (absolute, palette_blend, 0→1, tag="palette") over dur (default 0.5 if dur≤0)
  4. Schedules `_commit` callback (tag=none) to snap palette_idx = target, palette_blend = 0
- **off**: No-op
- **State written**: 
  - Immediately: palette_target_idx, palette_blend (snap)
  - Modulator: palette_blend 0→1
  - Scheduled: palette_idx (snap at end)
- **Scheduled callbacks**: `_commit` (no tag!)
- **Clearance**: No prefix clearing; old palettes auto-replace via Modulator choke (same tag="palette") or manual trigger
- **Edge case**: 
  - Palette A, then Palette B rapid-fire → first palette's modulator (tag="palette") is choked by second's (same tag). First's scheduled `_commit` still fires, setting palette_idx = A. Then second's `_commit` fires, setting palette_idx = B. **Result**: Final state is B (correct), but A's commit fired unnecessarily (benign because it's overwritten immediately).
  - **No tag on scheduled callbacks** — different from dissolve/respawn! This means `clear_scheduled_by_tag_prefix("palette")` won't work because the callback tuple is `(beat, fn)` with no tag field. **Inconsistency**: palette callbacks don't participate in lifecycle scrubbing.

### **meteors** / **dust** / **flash** / **wipe** (SFX)
- **Registered as**: `_make_sfx_action(SfxClass, default_duration)`
- **on**: Creates SFX instance, calls `scene.add_sfx(sfx)`
- **off**: No-op
- **State written**: None (SFX is external)
- **Scheduled callbacks**: None
- **Clearance**: SFX auto-expires when `is_done(beat)` returns True (scene.tick() prunes each frame)
- **Edge case**: 
  - SFX outlive Scene.reset() — Scene.reset() clears `_active_sfx` list, but SFX instances' internal state (_meteors, _dots) isn't cleared. If SFX were somehow retained elsewhere, next spawn would see stale positions. **Non-issue in practice** because SFX are only referenced in `_active_sfx`.
  - **More serious**: If Scene.reset() is called mid-SFX, the SFX list is cleared. Next animation render might miss them. But render reads from `_active_sfx`, so no dangling pointers.

---

## 3. Tag Conventions

**All tags used in codebase**:

| Tag Prefix | Used By | Purpose |
|---|---|---|
| `"radius"` | Expand, Contract | Chokes Radius events; persists across multiple notes |
| `"pulse"` | Pulse | One-shot accent; chokes same tag; additive so overlaps sum |
| `"blowout-radius"` | Blow Out | Absolute radius in blow-out; choked by same tag |
| `"blowout-alpha"` | Blow Out | Absolute alpha in blow-out; choked by same tag |
| `"regrow-grow-radius"` | Regrow | Grow phase radius; cleared on retrigger |
| `"regrow-grow-alpha"` | Regrow | Grow phase alpha; cleared on retrigger |
| `"regrow-pin-grown"` (scheduled) | Regrow | Scheduled callback; cleared on retrigger |
| `"dissolve-disperse"` | Dissolve | Phase 1: dissolve_amount 0→1 |
| `"dissolve-pin-dispersed"` (scheduled) | Dissolve | Snap after disperse |
| `"dissolve-begin-fade"` (scheduled) | Dissolve | Start fade phase (creates fade modulator) |
| `"dissolve-fade"` | Dissolve (via scheduled callback) | Phase 3: alpha→0 |
| `"dissolve-pin-dark"` (scheduled) | Dissolve | Snap alpha=0 at end |
| `"respawn-alpha"` | Respawn | Alpha 0→1 |
| `"respawn-gather"` | Respawn | Dissolve_amount 1→0 |
| `"respawn-pin-alpha"` (scheduled) | Respawn | Snap alpha=1 at end |
| `"respawn-pin-amount"` (scheduled) | Respawn | Snap dissolve_amount=0 at end |
| `"palette"` | PaletteAction | Modulator only; crossfade palette_blend 0→1 |
| None (scheduled) | PaletteAction | `_commit` callback has no tag! |
| `"rotate-cw-{i}"` | Rotate CW per-ring | Per-oval torque; key=(pitch, tag) |
| `"rotate-ccw-{i}"` | Rotate CCW per-ring | Per-oval torque; key=(pitch, tag) |

**Consistency issues**:
1. **Scheduled callback tagging inconsistency**: Dissolve, Respawn, Regrow use tagged callbacks for scrubbing. Palette uses untagged callbacks — `_commit` cannot be scraped by `clear_scheduled_by_tag_prefix()`.
2. **Dissolve-fade modulator created inside scheduled callback**: Tag="dissolve-fade" but created *at callback time*, not at dissolve.on() time. If dissolve is scrubbed before callback fires, the callback still fires and tries to create the modulator. The Scene method won't fail (it just adds a modulator), but it's semantically odd — a scrubbed dissolve can still create a "fade" modulator from a stale callback.
3. **Modulators without tags** (e.g., ImpulseAction-generated ones): Can't be scraped; relies on Scene.reset() or target-based clearing. Generally fine for impulses (one-shot), but could cause issues if you wanted to scrub all ball-related state and missed untagged modulators.
4. **Choke key hierarchy**: Tag > Pitch > None. Works fine, but means tagless modulators never choke each other (each impulse is independent). This is probably intentional.

---

## 4. set_state vs Modulators

### Where `set_state()` is called:

1. **Admin UI / test code** (external)
2. **RegrowAction.on()**: Scrubs radius, alpha, dissolve_amount, oval_velocity_*, oval_rotation_*, then snaps to specific values
3. **DissolveAction.on()**: Calls `_pin_dispersed`, `_pin_dark` (scheduled callbacks) which call set_state("dissolve_amount", ...), set_state("alpha", ...)
4. **RespawnAction.on()**: Snaps dissolve_amount=1, alpha=0, oval_rotation_*, oval_velocity_*
5. **PaletteAction.on()**: Snaps palette_target_idx, palette_blend, palette_idx (via scheduled `_commit`)
6. **Various SFX actions**: Don't call set_state

### Silent purge of modulators:

```python
def set_state(self, var: str, value) -> None:
    with self._lock:
        self._state[var] = value
        self._baselines.pop(var, None)
        self._modulators = [m for m in self._modulators if m.target != var]
```

**Consequences**:
- Any in-flight modulator on the target is dropped
- Baseline for that target is discarded
- Next modulator on that target will capture the new value as baseline

**Unexpected stomping scenarios**:

1. **Regrow.on() + competing Expand**: 
   - Expand fires → Modulator A (tag="radius") added, baseline captured
   - Regrow fires → set_state("radius", 0.0) → Modulator A DROPPED, baseline cleared
   - Later, Expand's scheduled `_pin` callback fires → checks for conflicting mods; none found (A was dropped), so pins radius=initial peak
   - **Result**: Regrow and Expand's pin conflict, but A was already gone so no actual interference
   - **Better solution**: Regrow should use `clear_modulators_by_tag_prefix()` instead of set_state() for au state scrubbing, so radius/alpha can keep their Expand modulator

2. **DissolveAction + PulseAction + other alpha modulators**:
   - Pulse fires → Modulator B (additive, tag="pulse") added
   - Dissolve fires → captures cur_alpha (which includes Pulse's contribution)
   - Dissolve's disperse phase proceeds → no set_state on alpha yet
   - Dissolve's fade phase scheduled → but if another set_state("alpha", ...) is called before fade phase, Pulse's modulator is dropped
   - **Result**: Fade phase adds Modulator C (tag="dissolve-fade"), but B is already gone
   - **Low risk** in practice; Pulse duration typically short and dissolve doesn't call set_state during active phases

3. **Scene.reset()** (not directly set_state, but similar effect):
   - Clears all modulators and baselines
   - Used when user clicks "Reset", reloads sequence, etc.
   - Safe because reset() is explicit user action

4. **PullCenterAction → start_pull_center()**: 
   - Doesn't call set_state; uses direct physics override in tick()
   - No silent modulator purge

### Recommendation:
- **Regrow** should use `clear_modulators_by_tag_prefix("regrow-")` instead of set_state() for radius/alpha scrubbing, so Expand/Contract/Blow Out modulators aren't accidentally dropped
- **Dissolve fade** should use `clear_modulators_by_tag_prefix("dissolve-")` or pre-create the fade modulator at dissolve.on() time, not inside a scheduled callback
- **Palette** should use tagged scheduled callbacks so they participate in lifecycle scrubbing

---

## 5. Baseline Restoration vs Scheduled Pins

### Phase ordering (tick method):

```
Phase 4: Evaluate modulators → write to state via combine()
Phase 5: Prune done modulators + restore baselines
Phase 9: Scheduled callbacks snapshot (inside lock)
...
Phase 13: Scheduled callbacks fire (OUTSIDE lock)
```

### Edge case: Baseline restored before scheduled pin fires

Example: Dissolve with phases:
1. Dissolve.on() at beat 0: disperse_dur=1.2
   - Modulator: dissolve_amount 0→1 (tag="dissolve-disperse", duration=1.2)
   - Scheduled: _pin_dispersed at beat 1.18 (disperse_dur - 0.02)
2. Tick at beat 1.2: 
   - Modulator "dissolve-disperse" done() returns True (elapsed=1.2, duration=1.2)
   - Phase 5: Modulator pruned, baseline["dissolve_amount"] restored (was 0.0)
   - Phase 9: Scheduled callbacks due list includes _pin_dispersed (beat 1.18 ≤ 1.2)
   - Phase 13: _pin_dispersed fires OUTSIDE lock, calls set_state("dissolve_amount", 1.0)
   - **Result**: Baseline was 0, then restored to 0 by Phase 5, then pin overwrites to 1.0
   - **Actual observed state**: 1.0 (correct), because set_state() is the last write

**However**, if a modulator is added to dissolve_amount between Phase 5 and Phase 13:
1. Tick at beat 1.15:
   - Dissolve-disperse modulator done() returns True
   - Phase 5: Baseline restored to 0
2. Between ticks, user triggers another dissolve (or RespawnAction which snaps dissolve_amount=1)
3. Tick at beat 1.2:
   - Phase 4: Combine rebuilds dissolve_amount from baseline=0 (but RespawnAction's set_state() cleared baseline, so it re-captured current 1.0 as new baseline)
   - Phase 5: Respawn's modulator still active, baseline NOT restored
   - Phase 13: First dissolve's _pin_dispersed fires, set_state("dissolve_amount", 1.0) → baseline cleared
   - **Result**: Respawn's modulator exists, but baseline was cleared; next frame, respawn modulator evaluates from 0 (default), not from the prior 1.0
   - **Symptom**: dissolve_amount jumps

Actually, let me re-trace:
- RespawnAction.on() calls set_state("dissolve_amount", 1.0)
- set_state() → state["dissolve_amount"] = 1.0, baseline.pop("dissolve_amount"), modulators = [m for m in modulators if m.target != "dissolve_amount"]
- So respawn's Modulator (target="dissolve_amount") is NOT added until after set_state()
- RespawnAction then creates new Modulator (tag="respawn-gather")
- So at the moment respawn-gather is added, baselines["dissolve_amount"] is NOT set (was popped)
- Next tick, Phase 4: combine() → base = _baselines.get("dissolve_amount", state.get("dissolve_amount", 0.0)) = state value = 1.0
- **Result**: Respawn modulator bases from the current state (1.0) correctly. ✓ Safe.

**Edge case: Scheduled callback pins wrong value if baseline changed**:
- Dissolve.on() at beat 0: cur_alpha = 1.0, schedules _pin_dark to snap alpha=0 at beat 4.0
- Tick at beat 2.0: Pulse fires → Modulator B (additive, tag="pulse", target="alpha") added, baseline NOT recaptured (already set by prior modulator)
- Tick at beat 4.0: 
  - Phase 4: Combine evaluates all alpha modulators from baseline=1.0 (captured at dissolve time) → result might be < 0 (dissolve-fade ramps to 0)
  - Phase 5: All alpha modulators done; baseline restored: state["alpha"] = 1.0
  - Phase 13: _pin_dark fires, set_state("alpha", 0.0) → overrides state to 0 ✓
- **Result**: Correct; scheduled pins override any baseline restoration

**No actual edge case**, because:
1. Phase 5 (baseline restore) happens inside lock
2. Phase 13 (scheduled callbacks) happen outside lock, but they just call set_state() which is thread-safe
3. Next tick, Phase 4 evaluates from updated state
4. Scheduled pins are expected to lock-in final state, so they naturally override baseline restoration

---

## 6. Sequencer Dispatch Ordering

Phase order:
1–6: Inside lock (clock, physics, animation)
7–8: Inside lock (modulators eval, prune, baseline restore)
9–10: Inside lock (scheduled snapshot, SFX)
11: **Sequencer dispatch OUTSIDE lock**
12: Inside lock (SFX render prep)
13: **Scheduled callbacks fire OUTSIDE lock**

### Load-bearing ordering:

1. **Sequencer dispatch (phase 11) AFTER modulator prune (phase 5)**:
   - If sequencer note fires a modulator and modulator finishes same frame, prune happens before sequencer sees the result
   - **Example**: Expand fires at beat 1.0 with duration 0.1; tick at beat 1.05 → Expand modulator done; Phase 5 prunes and restores baseline. Phase 11 sequencer doesn't see Expand's effect because it's already gone.
   - **Actually not a problem**: Sequencer fires note_on; Expand creates NEW modulator (doesn't check if one exists). If a very short Expand (0.1 beat) is triggered every tick, each tick creates a fresh modulator that evaluates and completes same frame. Baseline is restored and next frame starts fresh. Correct behavior.

2. **Scheduled callbacks (phase 13) AFTER sequencer (phase 11)**:
   - Scheduled callbacks can fire actions that create modulators
   - Example: _begin_fade schedules dissolve-fade modulator creation at the start of the fade phase
   - Phase 13 fires _begin_fade, which calls scene.add_modulator() → modulator is added to list
   - Next tick, Phase 4 evaluates the freshly-added modulator ✓
   - But if _begin_fade fires and immediately the scene is reset/paused, the modulator won't be evaluated until next tick (correct; Scene.reset clears all modulators)

3. **SFX tick (phase 10) inside lock; SFX scheduled callbacks (phase 13) outside lock**:
   - SFX tick updates positions; scheduled callbacks fire (could theoretically modify SFX)
   - In practice, no scheduled callbacks modify SFX; they only manipulate state
   - SFX render happens AFTER SFX tick but BEFORE scheduled callbacks fire (phase 12 is render prep/call)
   - Actually, let me re-check: render() is called OUTSIDE tick(), so no ordering within tick()

4. **Torques applied BEFORE animation tick (phase 3 then 3b)**:
   - Phase 3a: Torques summed and applied to oval_velocity_i
   - Phase 3b: animation.tick() integrates oval_velocity_i → oval_rotation_i
   - If animation.tick() relies on accurate velocity values, this order is correct ✓

5. **Physics (phase 2) BEFORE modulator eval (phase 4)**:
   - Physics updates ball position
   - Modulators can write radius, which affects physics bounds next frame
   - Current frame: physics uses last frame's radius; phase 4 writes new radius for next frame
   - This is correct; radius changes don't retroactively affect current frame's physics

### Surprising results:

1. **Sequencer note fires, modulator created, but baseline not captured until next frame**:
   - Note fires → scene.add_modulator() adds mod, captures baseline if needed
   - Phase 4 evaluates modulator from captured baseline
   - ✓ Correct; baseline captured inside add_modulator()

2. **Dissolve's _begin_fade callback creates fade modulator, but it doesn't evaluate until next tick**:
   - Phase 13: _begin_fade fires outside lock → scene.add_modulator() called
   - Modulator added to list for next frame evaluation
   - Alpha does NOT start fading this frame
   - Phase 2–4 of NEXT tick: modulator evaluates ✓
   - This means the "float phase" (between disperse and fade) sees alpha held constant (no fade yet), which is correct by design

3. **Scheduled callback re-enters Scene (e.g., _pin_grown checks for conflicting mods)**:
   - Phase 13: _pin_grown calls scene with NO LOCK
   - If another thread modifies _modulators concurrently, this is a data race
   - **Mitigation**: Scene methods acquire lock internally, so _pin_grown's check for conflicting mods is safe
   - But the callback itself doesn't hold the lock, so if Scene is being modified by another thread, undefined behavior
   - **In practice**: Single-threaded event loop; only concern is if admin API calls Scene.set_state() while callback fires. Unlikely but possible.
   - **No synchronization bug in current design** but fragile

---

## 7. Dissolve/Respawn Focus Area — "Garbage" Bug Analysis

### Dissolve → Respawn Cycle

**Dissolve lifecycle** (DissolveAction.on):
1. Scrub prior dissolve/respawn mods + callbacks
2. Snap nothing (no immediate state change)
3. Create Modulator: dissolve_amount 0→1 over disperse_dur (tag="dissolve-disperse")
4. Schedule _pin_dispersed: snap dissolve_amount=1.0 at beat disperse_dur
5. Schedule _begin_fade: fire at beat disperse_dur+float_dur → creates alpha fade modulator
6. Schedule _pin_dark: snap alpha=0 at beat disperse_dur+float_dur+fade_dur

**State during dissolve**:
- Dissolve_amount ramps 0→1 (drives dot cloud render path in SynthAnimation.render)
- Alpha untouched during disperse + float; only fades in the fade phase
- Ball, radius, rotations: untouched

**Respawn lifecycle** (RespawnAction.on):
1. Scrub prior dissolve/respawn mods + callbacks → **clears dissolve-fade modulator if it exists**
2. **Snap immediately**:
   - dissolve_amount = 1.0
   - alpha = 0.0
   - oval_rotation_* = 0 (all 3)
   - oval_velocity_* = 0 (all 3)
   - ball reset: cx=cy=0, vx=vy=0, sx=sy=0, sx_dot=sy_dot=0, center_lock=False
   - torques cleared
3. Create Modulator: alpha 0→1 over fade_in_dur (tag="respawn-alpha")
4. Create Modulator: dissolve_amount 1→0 over gather_dur (tag="respawn-gather")
5. Schedule _pin_alpha: snap alpha=1.0 at fade_in_dur
6. Schedule _pin_amount: snap dissolve_amount=0.0 at gather_dur

**State during respawn**:
- Alpha ramps 0→1 (fade-in phase)
- Dissolve_amount ramps 1→0 (gather phase, drives dot cloud positions back to ring)
- Rotations/velocity: zero (pinned)
- Ball: zero (pinned)

### Possible bugs:

#### 1. **Dissolve → Respawn with overlap**

Scenario: Dissolve at beat 0, Respawn at beat 2 (mid-dissolve):
- Tick beat 0: dissolve_amount mod created, tag="dissolve-disperse"
- Tick beat 1: dissolve_amount ≈ 0.33 (1/3 through disperse)
- Tick beat 2: Respawn triggered
  - Scrub: clears dissolve-disperse mod and any scheduled callbacks
  - Snap: dissolve_amount → 1.0 (overwritten)
  - New mods: alpha 0→1, dissolve_amount 1→0
- Tick beat 3: dissolve_amount ramping down from 1 (respawn path), alpha ramping up
- **Result**: Clean transition; dissolve_amount jumped from 0.33 to 1.0 at respawn trigger. **Not "garbage"; intentional reset.**

#### 2. **Modulator vs Rendered State Inconsistency**

Dissolve renders dot cloud using `dissolve_amount` state. The dot cloud position calculation in SynthAnimation._render_dots() depends on:
- `dissolve_amount` (0=ring, 1=dispersed)
- `time_s` (absolute time since render call; frame-based)
- Particle positions are **deterministic** based on seed, time, and dissolve_amount

During dissolve:
- Frame 1: dissolve_amount = 0.1, dot cloud rendered at positions corresponding to 10% dispersal
- Frame 2: dissolve_amount = 0.3, dots rendered at 30% dispersal
- Dots **physically move** due to time passing + dissolve_amount changing = smooth animation ✓

During respawn:
- Frame 1: dissolve_amount = 0.9 (just after snap), dots rendered at 90% dispersal
- Frame 2: dissolve_amount = 0.7 (1/3 through gather), dots rendered at 70% dispersal = particles move back toward ring
- **No stale positions** because render is **deterministic** based on time_s and dissolve_amount

**Edge case**: If dissolve_amount is changed by something OTHER than the respawn modulator (e.g., user calls set_state("dissolve_amount", 0.5)), the dot cloud will re-render at 50% dispersal, not "garbage". The particles have **no memory** of prior positions; they're computed fresh each frame based on time.

#### 3. **Dot cloud position calculation depends on render-time variables**

In SynthAnimation._render_dots(), particles are computed fresh based on:
- `time_s = time_ms * 0.001` (render argument)
- `dissolve_amount` (from state)
- `radius`, `skew`, `theta_off` (from state)
- Deterministic seed from animation instance

**Potential issue**: If `time_ms` is not monotonic (e.g., clock resets, pause/resume), dots can teleport or loop. But Scene.tick() uses monotonic engine time, so this shouldn't happen.

**Potential issue**: If `dissolve_amount` ramps non-monotonically (e.g., 0→1→0.5), the motion model switches:
- At dissolve_amount=1: fully brownian, particles random
- At dissolve_amount=0.5: orbital+brownian crossfade
- Orbital component depends on time-elapsed since dissolve started
- **Result**: Particles snap to new positions corresponding to the crossfade point, not smooth interpolation

Example: Dissolve for 4s ends with dissolve_amount=1. Then Respawn called immediately:
- Respawn snaps dissolve_amount → 1.0 (no change)
- Respawn modulator ramps 1→0 over 4s (gather phase)
- At time T seconds into respawn:
  - dissolve_amount = 1.0 - (T/4.0)
  - Particle position = f(time_since_respawn_start, dissolve_amount, ...)
  - Orbital component = orbit_speed × (1 - dissolve_amount) = orbit_speed × (T/4.0)
  - Brownian component = brownian(time_since_respawn_start, ...)
  - **Result**: Particles smoothly transition from pure-brownian (dissolve_amount→1) to orbital+brownian blend. ✓ Correct.

#### 4. **Dissolve-fade modulator created inside scheduled callback**

DissolveAction.on() schedules _begin_fade to fire at beat disperse_dur+float_dur:
```python
def _begin_fade(sc, cur=cur_alpha, dur=fade_dur, e=env):
    sc.add_modulator(Modulator(
        target="alpha", op="absolute",
        base_value=cur, peak_value=0.0,
        envelope=e, start_beat=sc.current_beat(),
        duration_beats=dur,
        tag="dissolve-fade",
    ))
```

**Issue**: `cur_alpha` is captured at dissolve.on() time, not at _begin_fade time. If alpha changes between dissolve.on() and _begin_fade callback:
- Pulse fires during disperse phase → alpha gets additive boost
- Alpha = 1.0 + 0.5 = 1.5 (if pulse adds 0.5)
- _begin_fade fires and creates modulator with base_value=cur=1.0 (the captured value)
- Modulator ramps 1.0 → 0.0, but alpha was actually 1.5 when fade should start
- **Result**: Alpha jumps down from 1.5 to 1.0, then ramps to 0. **Visual glitch**: dip at fade start.

**Severity**: Medium. Dissolve + Pulse in sequence are probably rare, but definitely possible (e.g., Dissolve at beat 0, Pulse at beat 1).

#### 5. **Respawn doesn't restore radius or other read-only state**

RespawnAction snaps:
- dissolve_amount, alpha, rotations, velocity, ball, torques

It does NOT snap:
- **radius** (stays at whatever Expand/Contract/Blow Out set it to)
- **oval_enabled_*, oval_phase_*, oval_skew_*, oval_side_*, oval_segments_*, oval_gap_*, oval_radius_offset_*, oval_color_* palette index** (all stay)

**Consequence**: If Dissolve was triggered while radius=16 (expanded), then Respawn fires:
- radius stays at 16 (dot cloud respawns at full expansion size)
- **This might be intentional** (respawn inside an expanded ring), but if the user expected respawn to reset to "default" radius, it won't

**No bug here**, but worth documenting.

#### 6. **Baseline capture inconsistency with Respawn snaps**

RespawnAction snaps several state variables, then creates modulators. Example:
- RespawnAction.on() → set_state("alpha", 0.0)
- set_state() clears baseline["alpha"]
- RespawnAction then creates Modulator (target="alpha", op="absolute", ...)
- add_modulator() checks if "alpha" in baselines; it's not, so captures baseline = current state = 0.0
- Modulator ramps 0→1; combine() uses baseline=0 ✓

This works correctly because set_state() clears the baseline, forcing re-capture. But the code flow is:
```
set_state("alpha", 0.0)  # baseline cleared
scene.add_modulator(Modulator(...))  # baseline re-captured from state[alpha] = 0.0
```

If state["alpha"] is 0.0 when respawn triggers, this is fine. But if there was a hidden dependency (e.g., prior modulator set alpha to 1.0, then respawn snaps to 0.0), the baseline is correctly captured as 0.0. ✓ Safe.

#### 7. **Dot positions might appear to stutter if time_ms skips**

If Scene.tick() receives non-monotonic time_ms (e.g., 100, 105, 103), dot cloud renders use `time_s = time_ms * 0.001`, which would jump backward. But Scene.tick() uses monotonic engine time, so this is only a concern if caller passes non-monotonic time_ms.

**In normal operation**: Main loop increments time_ms monotonically. ✓ Safe.

#### 8. **Rendering reads stale state if Scene is modified concurrent with render()**

Scene.render() makes a snapshot of state and ball_state at the moment of render, but if another thread modifies state between tick() and render(), render reads stale values. However:
- tick() and render() are typically called sequentially in main loop
- Scene methods acquire lock internally
- render() is pure (no side effects)
- **No data race as long as tick/render are called sequentially** ✓

#### 9. **Dot cloud motion model scales with radius but render doesn't**

In SynthAnimation._render_dots(), drift_max depends on `radius`:
```python
drift_max = 1.6 * radius * dissolve_amount
```

If radius changes during dissolve/respawn, the particle dispersal range changes. Example:
- Dissolve at radius=8 → drift_max = 1.6 × 8 = 12.8
- Mid-dissolve, user triggers Contract → radius → 3
- Drift_max now = 1.6 × 3 = 4.8
- Particles snap to closer dispersal positions
- **Result**: Visual jump; particles appear to snap inward. **This is probably a bug** — particles should disperse relative to their current radius, not jump.

**Mitigation**: Dissolve should pin radius (not allowed to change during dispersal). But currently, it doesn't. **Add-on**: Regrow scrubs radius to 0; Dissolve doesn't. This asymmetry suggests Dissolve should also pin radius.

#### 10. **SFX state not cleared on Scene.reset() or animation swap**

Scene.reset() calls `self._active_sfx.clear()`, which removes all SFX from the list. But SFX instances might have internal state:
- MeteorsSfx._meteors (list of meteor dicts)
- DustPulseSfx._dots (list of dot dicts)

If an SFX is kept alive elsewhere (e.g., referenced externally), its internal state is stale. **In practice**: SFX are only referenced in `_active_sfx`, so reset() is safe. But if SFX were ever stored in a queue or external list, this could leak memory or cause undefined behavior.

**More serious**: Scene.set_animation() calls `self._modulators.clear()`, `self._baselines.clear()`, etc., but does NOT call `self._active_sfx.clear()`. If the prior animation had active SFX and the new animation has a different grid size, the SFX's render() call might access array indices outside bounds (grid.total might be different). **This is a real bug**.

**Fix**: Scene.set_animation() should call `self._active_sfx.clear()` or iterate and mark done.

---

## 8. Dead Code & Inconsistencies

### Aliases / Legacy Names:
1. **RecenterAction** = PullCenterAction (line 308, event_catalog.py): Kept for back-compat; old tests might reference it
2. **float_left/right/up/down** = push_left/right/up/down (lines 619–622): Aliases for old naming; both registered
3. **push_center** = pull_center (line 624): Back-compat alias for Recentering
4. **rotate_*_rim** (lines 517, 540): Aliases pointing to index 0 (outer ring); old sequences use "rim" naming

### ModulatorAction legacy fields:
- `curve_id: str` (default "transition_default"): kept for backwards compat; actual curve shape determined by `ease` param
- Special case: `curve_id="instant"` → treated as legacy, maps to `ease="instant"` → flat envelope (lines 90–95)
- Logic is convoluted: `ease = str(params.get("ease", getattr(self, "ease", None) or ("instant" if legacy_instant else "ease_in_out")))`

### ImpulseAction vs PushAction:
- No PushAction class; PushCenter is PullCenterAction
- ImpulseAction handles both instant and duration-integrated pushes based on `params.duration_beats`
- Code tries to call `scene.add_push()` (line 202–207) which only exists on Scene, not SceneAPI protocol — fallback to `apply_impulse()` if AttributeError

### TorqueAction outside protocol:
- Tries to call `scene.apply_torque()` and `scene.remove_torque()` (lines 255, 262)
- These methods exist on Scene but NOT on SceneAPI protocol
- Wrapped in try/except to gracefully degrade; but SceneAPI protocol is incomplete

### PullCenterAction outside protocol:
- Tries to call `scene.start_pull_center()` (line 297)
- Method exists on Scene; not in protocol
- try/except fallback to... nothing (just pass)

### ModulatorAction release_curve_id handling:
- Default is "release_default" (line 78)
- But ModulatorAction.on() checks `if not self.release_curve_id` (line 159) to decide if one-shot or has-release
- Type is `Optional[str]`, default is "release_default" (truthy), so this check works
- However, user could set `release_curve_id=None` explicitly or pass an empty string; code handles both ✓

### _EASE_INTERP mapping duplicated:
- Defined in events.py (lines 166–171)
- Also defined in sfx.py (lines 28–33)
- Also defined implicitly in event_catalog._envelope_ease() (lines 187–192)
- Should be a shared constant to avoid divergence

### Choke policy hardcoded:
- `_CHOKE_POLICY = "replace"` (line 47 scene.py)
- Alternative "release" policy code path exists (line 266) but never taken
- Should be a config or removed

### Untagged scheduled callbacks:
- Dissolve's _pin_dispersed, _pin_dark: tagged
- Dissolve's _begin_fade: tagged
- Respawn's _pin_alpha, _pin_amount: tagged
- Palette's _commit: **NOT tagged** (just `(beat, fn)` tuple, no tag field)
- RegrowAction's _pin_grown: tagged
- This inconsistency means palette callbacks can't be scraped via `clear_scheduled_by_tag_prefix()`

### Inconsistent lifecycle scrubbing:
- Dissolve/Respawn: call `_scrub_dissolve_lifecycle()` which clears dissolve-* and respawn-* mods + scheduled
- Regrow: calls `_scrub_dissolve_lifecycle()` then `clear_modulators_by_tag_prefix("regrow-")` (not tagged lifecycle scrub!)
- Palette: no scrubbing on retrigger; relies on Modulator choke (same tag="palette")

### set_state() called explicitly in lifecycle actions:
- RegrowAction, RespawnAction: snap multiple state variables
- Better to use scheduled callbacks or targeted clears
- But works; just verbose

### ball_state parameter in render:
- Scene.render() calls animation.render(..., ball_state=self._physics.snapshot())
- SynthAnimation.render() uses ball_state; other animations might not
- Protocol not enforced; fragile if new animation doesn't expect ball_state

### SFX color_idx parameter:
- All SFX take `color_idx: int` in constructor
- _pick_color() maps 0–7 to palette slots
- If color_idx is out of range, clamped: `key = _PALETTE_KEYS[max(0, min(7, int(idx)))]`
- So invalid color_idx silently maps to 0 (rim_color) — no error, might surprise user

---

## 9. Test Gaps

Current tests cover:
- Clock/tap (unit)
- Envelopes/modulators (unit)
- Events/router (unit)
- MIDI sequencer (unit + sequential)
- Physics (unit)
- Scene basics (unit + lifecycle)
- Sequential events (Dissolve/Respawn/Regrow multi-cycles)
- Breathing recreation (e2e scenario)
- E2E pixels (rendering)

**Gaps**:

1. **Dissolve fade phase captures stale cur_alpha**:
   - Not covered: Dissolve + Pulse mid-disperse, check alpha fade ramp
   - Test: Trigger dissolve, add pulse during disperse phase, verify fade doesn't snap backward

2. **Respawn clears animation swap SFX state**:
   - Not covered: Scene.set_animation() with active SFX
   - Test: Start SFX, swap animation, verify no segfault and SFX are cleared

3. **Rapid Dissolve-Respawn-Dissolve cycles**:
   - TestSequentialEvents covers Dissolve→Respawn→Dissolve but not mid-phase retriggers
   - Test: Dissolve, wait 0.5s (mid-disperse), Respawn, wait 0.5s (mid-gather), Dissolve again — verify final state is empty

4. **Baseline restoration during multiple additive modulators**:
   - Test: Create 2 additive mods on alpha, confirm they sum; when both done, baseline restored, not accumulated

5. **Scheduled callbacks fire with stale Scene state**:
   - Test: Schedule callback that checks current state; verify state is up-to-date at callback time

6. **Radius change during Dissolve/Respawn**:
   - Not covered: Expand mid-dissolve, verify dot cloud re-scatters to new radius
   - Test: Dissolve, trigger Expand, check dissolve_amount ramps over dot cloud at contracted radius

7. **Palette callback tagging**:
   - Not covered: Palette lifecycle scrubbing (can't scrub because callback untagged)
   - Test: Palette A, scrub via clear_scheduled_by_tag_prefix(), trigger Palette B, verify no stale A callback fires

8. **SFX with different grid sizes**:
   - Not covered: Load SFX preset on grid1, swap to grid2 with different size
   - Test: MeteorsSfx with 10×10 grid, swap to 44×44, verify no array index out of bounds

9. **Choke policy "release" path**:
   - Code exists but not exercised; CHOKE_POLICY hard-coded to "replace"
   - Test: Swap policy to "release", verify smooth transitions instead of instant chops

10. **RecenterAction (pull_center) cancels prior pulls**:
   - Not covered: Pull center, trigger another pull mid-flight, verify no double-pull
   - Test: Pull over 4 beats, retrigger at 2 beats, verify ball still lands at origin after second duration

11. **Torque sum + friction decay**:
   - Tested in TestPhysicsIntegration but not full lifecycle (multiple torques on same oval, friction applied correctly)
   - Test: Rotate CW + CCW on same ring, verify torques cancel; release one, verify other decays with friction

12. **Event defaults** (router.set_event_defaults):
   - Not tested; event_defaults dict merged into every dispatch
   - Test: Set event_default for "expand" to duration_beats=2, trigger expand, verify 2-beat duration

13. **Dissolve/Respawn with `dissolve_amount` partially modified**:
   - Not covered: User calls set_state("dissolve_amount", 0.5), then triggers dissolve/respawn
   - Test: Set dissolve_amount=0.5, trigger respawn, verify gather phase starts from 0.5 (or snapped?)

14. **Baseline capture when first modulator added is additive**:
   - Not covered; baseline captured as 0.0 if additive, current state if absolute
   - Test: Add additive modulator to alpha (no prior mods), verify baseline=0 and combine works correctly

15. **Scheduled callback that creates modulator gets evaluated same tick**:
   - Not covered: _begin_fade creates modulator; is it evaluated immediately or next tick?
   - Test: Check that fade modulator's first evaluation happens at next tick, not immediately after callback

---

# Summary of Findings

## Critical Issues:
1. **Dissolve's cur_alpha captured at on() time, not fade start**: If alpha changes during disperse+float, fade ramps from stale base value → visual glitch (dip) at fade start
2. **Scene.set_animation() doesn't clear _active_sfx**: If prior animation had SFX and new animation has different grid, SFX render could access out-of-bounds indices → segfault risk
3. **Dissolve/Respawn don't pin radius**: If user Contracts during dissolve, dot cloud dispersal range changes mid-cycle → particles snap inward

## Medium Issues:
1. **Scheduled callback tagging inconsistency**: Palette's _commit callback untagged → can't be scraped; dissolve/respawn callbacks tagged → can be scraped → asymmetric lifecycle
2. **Baseline restored before scheduled pin can fire**: Edge case where baseline restored (Phase 5) before pin callback (Phase 13) overwrites it; works by accident because set_state() is last writer
3. **Choke policy "replace" vs "release" code divergence**: "release" path exists but unreachable; should be removed or made configurable
4. **TorqueAction and PullCenterAction not in SceneAPI protocol**: Methods called (apply_torque, start_pull_center) aren't defined in protocol; gracefully degraded with try/except but fragile

## Minor Issues:
1. **_EASE_INTERP mapping triplicated**: Defined in events.py, sfx.py, and inline in event_catalog._envelope_ease(); should be shared constant
2. **SFX color_idx clamped silently**: Out-of-range colors map to slot 0 without error
3. **Respawn snaps multiple state vars but doesn't document which**: radius, palette, ovals remain; only aux state resets
4. **RecenterAction / float_* / push_center aliases**: Multiple names for same actions; works but confusing
5. **ModulatorAction curve_id legacy field**: kept for backwards compat; `ease` parameter is the real control but code flow is convoluted

## Test Coverage Gaps:
- Dissolve fade + concurrent pulse
- Scene.set_animation() with active SFX
- Rapid multi-phase event retriggers
- Baseline accumulation edge cases
- Palette callback lifecycle scrubbing
- Dissolve/Respawn with radius changes
- Event defaults propagation
- Choke policy "release" path
- Scheduled callbacks creating modulators (same-tick evaluation)
