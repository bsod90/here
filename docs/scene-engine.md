# Scene Engine v2 — "synth for visuals"

A beat-locked, MIDI-style animation engine. The piano roll (or admin
trigger button, or OSC topic) produces note_on / note_off events. Each
event maps to an **Action** that schedules **Modulators** (envelope-driven
state writes), **scheduled callbacks** (pinning, lifecycle bookkeeping),
**physics impulses**, or **SFX overlays**. A single **SynthAnimation**
renders the resulting state every frame.

Source under `software/orchestrator/scene/` and
`software/orchestrator/scene/animations/`.

## Module map

```
clock.py             BeatClock — phase-preserving musical time
tap.py               TapTracker — median-of-pairwise-intervals BPM
envelopes.py         Envelope (breakpoint curves) + Modulator
                     + EASE_TO_INTERP (single source of truth for ease names)
midi_sequencer.py    Looping note → note_on/note_off event emitter
physics.py           Ball position/velocity/squash (under-damped jelly)
sfx.py               Meteors / Dust / Flash / Wipe overlay layer
events.py            EventRouter + Action protocol; concrete actions
                     (Modulator, Impulse, Anchor, Torque, PullCenter, Compound)
event_catalog.py     register_default_events() — wires every named event
                     onto the router; custom multi-phase actions for
                     Regrow / Dissolve / Respawn / Palette
scene.py             Scene — orchestrates everything, owns state dict
                     and modulator/scheduled lifecycles
animations/synth.py  SynthAnimation — 3 ovals + ball + dot-cloud render
default_presets.py   Bundled patches + sequences (breathing, etc.)
patch_store.py       Filesystem CRUD for saved synth patches
sequence_store.py    Filesystem CRUD for saved piano-roll sequences
```

## Concepts

**State** — a flat dict (`Scene._state`) holding one frame's worth of truth:
`radius`, `alpha`, `dissolve_amount`, `oval_skew_{0,1,2}`,
`oval_rotation_{0,1,2}`, `palette_idx`, `palette_blend`, etc.
`SynthAnimation.render()` reads this and produces a frame.

**Modulator** — a scheduled write into a state target shaped by an Envelope
over `duration_beats`. Three ops:
- `absolute` — combine takes the latest-start-beat mod's value
- `additive` — summed on top of the absolute baseline (e.g. Pulse)
- `multiplicative` — applied last

A modulator with a release envelope sustains at peak until `release()` is
called; without one it ends at duration.

**Scheduled callback** — `scene.schedule(beats_from_now, fn, tag=…)` queues
a closure to run at a future beat. Used for multi-phase actions
(Dissolve's fade phase, Respawn's pin) and for setting a final state value
after a Modulator completes. Tagged callbacks can be scrubbed en masse via
`clear_scheduled_by_tag_prefix(prefix)`.

**Baseline** — the rest value of a target. Captured the first time any
modulator on that target is added, restored when all mods on that target
have completed. `set_state(target, value)` purges modulators *and* the
baseline (so the next modulator re-captures from the new value).

**Choke** — when two modulators share a `(tag,)` or `(pitch,)` key, the
new one immediately drops the old (replace semantics). Used so rapid
retriggers don't pile up.

**Lifecycle scrubbing** — `_scrub_dissolve_lifecycle()` is called by
Dissolve, Respawn, and Regrow at the start of `.on()` to clear stale
dissolve-* / respawn-* mods + scheduled callbacks so multi-phase cycles
can't get stuck halfway. Regrow additionally clears `regrow-*`.

## Tick + render phases

```
Scene.tick(time_ms):
  1. dt; clock.tick(dt)
  2. physics.tick(dt) (ball position + squash)
  3. time-integrated pushes; pull-center animation
  4. torques → oval velocity + friction
  5. animation.tick(state, beat, dt) (per-anim integration)
  6. evaluate modulators → combine() into state from baseline
  7. prune done modulators; restore baselines for unmodulated targets
  8. snapshot "due" scheduled callbacks (still inside lock)
  9. sequencer.tick(clock, router)  — OUTSIDE lock
 10. SFX tick (inside lock)
 11. fire due callbacks — OUTSIDE lock

Scene.render(frame, time_ms, params):
  - snapshot state + ball_state
  - animation.render(...)
  - composite each active SFX on top
```

The ordering "modulators evaluated → sequencer dispatch → callbacks fired"
is load-bearing: when a sequencer note adds a modulator, it's evaluated on
the *next* tick, not the current one. Scheduled callbacks fire AFTER
sequencer dispatch so a callback's "check for competing mods" logic sees
mods just added by the same tick's notes (used by Regrow's pin guard).

## Events catalog

| Event | Action | Targets | Tag |
|---|---|---|---|
| `expand` | _PersistAction | radius → radius_max | "radius" |
| `contract` | _PersistAction | radius → radius_min | "radius" |
| `pulse` | ModulatorAction (additive) | alpha (+1) | "pulse" |
| `blow_out` | CompoundAction | radius → max·1.4, alpha → 0 | "blowout-radius" / "-alpha" |
| `regrow` | RegrowAction | snap-zero + growback + aux scrub | "regrow-*" |
| `dissolve` | DissolveAction | dissolve_amount 0→1, then alpha →0 | "dissolve-*" |
| `respawn` | RespawnAction | snap-disperse, then alpha 0→1, dissolve_amount 1→0 | "respawn-*" |
| `rotate_cw` / `rotate_ccw` | CompoundAction(TorqueAction × 3) | oval_velocity_{0,1,2} | "rotate-cw/ccw-{i}" |
| `rotate_*_outer/middle/inner` | TorqueAction | one oval | "rotate-cw/ccw-{i}" |
| `stop_rotation*` | _StopAction | set oval velocities to 0 | n/a |
| `push_left/right/up/down` | ImpulseAction | ball velocity | n/a |
| `pull_center` | PullCenterAction | ball position (deterministic land) | n/a |
| `push_random` | RandomImpulseAction | ball velocity (random dir) | n/a |
| `show_outer/middle/inner` / `hide_*` | _OvalToggle | oval_enabled_{i} | n/a |
| `meteors` / `dust` / `flash` / `wipe` | _SfxAction | adds SFX to overlay layer | n/a |
| `color_palette` | PaletteAction | palette_blend, palette_idx | "palette" / "palette-commit" |

Per-event default params (`color`, `ease`, `cluster_count`, etc.) live in
`router._event_defaults[event_name]` — set by the admin UI, persisted in
`config.scene.event_defaults`, merged into both direct trigger and lane
dispatch under per-trigger params.

## Renderer (SynthAnimation)

Three independently configured ovals (outer / middle / inner), drawn
back-to-front (middle on top). Each oval reads `oval_skew_i`,
`oval_phase_i`, `oval_rotation_i`, `oval_radius_offset_i`, `oval_color_i`
(palette slot 0..7), `oval_segments_i`, `oval_gap_i`, `oval_side_i`
(inside/outside/both).

When `dissolve_amount > 0`, a deterministic dot-cloud crossfades in:
particles with brownian motion + orbital convergence, with head + tapering
tail. Tail spacing scales with `dissolve_amount` to prevent "explosion".

`alpha` and `brightness` multiply the final RGB. The ball overlay
translates the geometry by `(cx, cy)` and warps by squash tensor
`(sx, sy)` for a jelly effect.

## Test layout

`software/orchestrator/tests/` — 175+ tests, run from that directory with
`python3 -m unittest discover tests`:

- `test_clock.py`, `test_tap.py` — musical time + tap tempo
- `test_envelopes.py` — Envelope sampling, Modulator value_at, combine()
- `test_events.py` — router dispatch, action types, choke
- `test_midi_sequencer.py` — note crossings, wrap, play-immediate, choked retrigger
- `test_physics.py` — ball impulses, walls, squash, center-lock anchor
- `test_scene.py` — Scene basics, sequencer integration, snapshot
- `test_sequence_store.py` — filesystem CRUD
- `test_sequential_events.py` — Dissolve/Respawn/Regrow multi-cycle correctness, Regrow→Expand loop-boundary bug
- `test_animation_correctness.py` — dissolve fade base-value, event_defaults merging, palette commit scrubbing, set_animation cleanup
- `test_breathing_recreation.py` — bundled breathing patch vs OG renderer similarity
- `test_e2e_pixels.py` — deterministic event → pixel assertions

## Known design notes

- **Set_state purges mods**: `set_state(target, v)` drops all modulators on
  that target and clears its baseline. Use this when you genuinely want
  to reset the channel; otherwise use `clear_modulators_by_tag_prefix()`.
- **Scheduled callbacks fire outside the lock**: they can re-enter Scene
  methods safely (lock is re-acquired), but should not assume state was
  identical when the callback was scheduled. Defensive callbacks (e.g.
  Regrow's `_pin_grown`) re-check current mods before acting.
- **Live alpha read in dissolve fade**: `_begin_fade` reads `state.alpha`
  at callback time, not closure time, so a Pulse during the disperse
  phase doesn't make the fade ramp jump backward.
- **Ovals → renderer indexing**: 0 = outer, 1 = middle, 2 = inner. Render
  loop iterates (0, 2, 1) so middle is drawn on top.

See `docs/scene-engine-audit.md` for a deeper architectural audit
(lifecycle correctness, tag conventions, edge cases, refactor opportunities).
