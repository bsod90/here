"""Envelopes and modulators — the synth-style abstraction that drives the
Scene state from MIDI note-on / note-off events.

`Envelope` is a normalized breakpoint curve (t ∈ [0,1] → v ∈ [0,1]) sampled
with a chosen interpolation. Curves are stored in `config.scene.curves` and
the user edits them in the UI.

`Modulator` is a *scheduled application* of an envelope to a single state
target. It owns the actual musical/visual semantics: an attack/sustain
phase driven by the chosen envelope over `duration_beats`, an optional
release phase driven by a second envelope when `note_off` arrives, and a
final "done" state. The Scene collects active Modulators and folds them
into the state dict every frame (absolute = last writer wins, additive
and multiplicative = combine).

This replaces the old `Transition` + `PulseEnvelope` pair — both of which
were special cases of this single, more general model.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ── Interpolation easings used between breakpoints ────────────────────────

def _linear(t: float) -> float:
    return t


def _cosine(t: float) -> float:
    return (1.0 - math.cos(t * math.pi)) * 0.5


def _ease_in_quad(t: float) -> float:
    return t * t


def _ease_out_quad(t: float) -> float:
    return 1.0 - (1.0 - t) * (1.0 - t)


def _ease_in_cubic(t: float) -> float:
    return t * t * t


def _ease_out_cubic(t: float) -> float:
    u = 1.0 - t
    return 1.0 - u * u * u


def _smootherstep(t: float) -> float:
    """6t^5 - 15t^4 + 10t^3 — much steeper S-curve than cosine. Flat
    near both endpoints, very fast through the middle."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


_INTERPS = {
    "linear": _linear,
    "cosine": _cosine,
    "ease_in_quad": _ease_in_quad,
    "ease_out_quad": _ease_out_quad,
    "ease_in_cubic": _ease_in_cubic,
    "ease_out_cubic": _ease_out_cubic,
    "smootherstep": _smootherstep,
}


# Maps short UI-friendly ease labels to the interp name used by Envelope.
# Single source of truth — actions in event_catalog, sfx tick code, and
# the events router all dereference here so there's no drift.
#
# Cubic / smootherstep instead of quadratic / cosine — the quadratic
# versions were too gentle (barely distinguishable from linear at most
# musical durations). Cubic gives a clearly readable accel/decel; the
# 5th-order smootherstep gives a much more pronounced S-curve.
EASE_TO_INTERP = {
    "linear":      "linear",
    "ease_in":     "ease_in_cubic",
    "ease_out":    "ease_out_cubic",
    "ease_in_out": "smootherstep",
}


def ease_envelope(ease_kind: str) -> "Envelope":
    """Build a normalized 0→1 envelope with the requested ease shape.
    Defaults to cosine ('ease_in_out') for unknown values."""
    interp = EASE_TO_INTERP.get(ease_kind, "cosine")
    return Envelope(points=[(0.0, 0.0), (1.0, 1.0)], interp=interp)


# ── Envelope ──────────────────────────────────────────────────────────────

@dataclass
class Envelope:
    """A normalized breakpoint curve. `t` and `v` both in [0,1].

    `duration_beats` is the *default musical length* this curve covers
    when an event uses it — events can override per-trigger, but in
    practice users want to dial the curve's length once and have all
    events that use it inherit (e.g. a 4-bar "transition_default" curve
    naturally produces 4-bar expand events).
    """
    points: list[tuple[float, float]]
    interp: str = "linear"
    duration_beats: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> "Envelope":
        raw = data.get("points") or []
        points = [(float(p[0]), float(p[1])) for p in raw]
        points.sort(key=lambda p: p[0])
        return cls(
            points=points,
            interp=str(data.get("interp", "linear")),
            duration_beats=float(data.get("duration_beats", 1.0)),
        )

    def to_dict(self) -> dict:
        return {
            "points": [[float(t), float(v)] for t, v in self.points],
            "interp": self.interp,
            "duration_beats": float(self.duration_beats),
        }

    def sample(self, t: float) -> float:
        """Return v at the normalized position t (clamped to [0,1])."""
        pts = self.points
        if not pts:
            return 0.0
        if t <= pts[0][0]:
            return pts[0][1]
        if t >= pts[-1][0]:
            return pts[-1][1]
        # Linear scan — envelopes have at most a handful of points.
        for i in range(len(pts) - 1):
            t0, v0 = pts[i]
            t1, v1 = pts[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v1
                local = (t - t0) / (t1 - t0)
                ease = _INTERPS.get(self.interp, _linear)
                return v0 + (v1 - v0) * ease(local)
        return pts[-1][1]


# A small library of well-known envelope shapes. The frontend ships these
# as the initial 4 curves; the user can edit them freely from the UI.
def default_envelopes() -> dict[str, Envelope]:
    return {
        # Quick onset, slow tail — classic pulse / accent.
        "pulse_default": Envelope(
            points=[(0.0, 0.0), (0.08, 1.0), (1.0, 0.0)],
            interp="ease_out_quad",
        ),
        # Smooth S-curve — generic attack/transition.
        "transition_default": Envelope(
            points=[(0.0, 0.0), (1.0, 1.0)],
            interp="cosine",
        ),
        # Gentle fall from sustained to zero — release tail.
        "release_default": Envelope(
            points=[(0.0, 1.0), (1.0, 0.0)],
            interp="cosine",
        ),
        # No-op step (always 1) — for events that just snap a value.
        "instant": Envelope(
            points=[(0.0, 1.0), (1.0, 1.0)],
            interp="linear",
        ),
        # Dissolve / respawn ramp — slower than transition_default by
        # default so dispersing/gathering reads as a deliberate motion.
        # User can reshape via the Curves tab independently of the
        # transition curve used by Expand/Contract.
        "dissolve_default": Envelope(
            points=[(0.0, 0.0), (1.0, 1.0)],
            interp="cosine",
        ),
    }


# ── Modulator ─────────────────────────────────────────────────────────────

VALID_OPS = ("absolute", "additive", "multiplicative")


@dataclass
class Modulator:
    """A scheduled, time-shaped write into the scene state.

    Lifecycle:
      attack/sustain: from `start_beat`, sample `envelope` over `duration_beats`.
        • If `release_envelope` is None → one-shot: done at end of envelope.
        • Otherwise → holds at envelope.sample(1.0) until note_off.
      release: triggered by `release(beat)`. Sample `release_envelope` over
        `release_duration_beats`, ramping the held value back toward
        `base_value`. Done at end of release envelope.

    `value_at(beat)` returns the modulator's current contribution, or None
    when fully done (Scene prunes it).
    """
    target: str
    op: str
    base_value: float
    peak_value: float
    envelope: Envelope
    start_beat: float
    duration_beats: float
    release_envelope: Optional[Envelope] = None
    release_duration_beats: float = 0.0
    released: bool = False
    release_beat: Optional[float] = None
    # Optional pitch tag — used by the Scene to support choked retrigger
    # (a fresh note_on on the same pitch replaces this modulator).
    pitch: Optional[int] = None
    # Optional metadata so the Scene can disambiguate identical pitches
    # targeting different state vars (e.g. blow_out fires two modulators).
    tag: Optional[str] = None

    def __post_init__(self):
        if self.op not in VALID_OPS:
            raise ValueError(f"Modulator op must be one of {VALID_OPS}, got {self.op!r}")
        if self.duration_beats < 0:
            raise ValueError(f"duration_beats must be >= 0, got {self.duration_beats}")
        if self.release_duration_beats < 0:
            raise ValueError(f"release_duration_beats must be >= 0, got {self.release_duration_beats}")

    # ── State transitions ────────────────────────────────────────────
    def release(self, beat: float) -> None:
        """Mark released (e.g. note_off received). Idempotent."""
        if self.released:
            return
        self.released = True
        self.release_beat = float(beat)

    def done(self, beat: float) -> bool:
        """True once the modulator no longer contributes anything."""
        return self.value_at(beat) is None

    # ── Sampling ─────────────────────────────────────────────────────
    def _attack_value(self, beat: float) -> float:
        """Compute the envelope-mapped value during attack/sustain at `beat`.
        Assumes beat >= start_beat. Clamps t to [0,1] (holds at end-of-env)."""
        if self.duration_beats <= 0:
            t = 1.0
        else:
            t = min(1.0, max(0.0, (beat - self.start_beat) / self.duration_beats))
        env_v = self.envelope.sample(t)
        return self.base_value + (self.peak_value - self.base_value) * env_v

    def value_at(self, beat: float) -> Optional[float]:
        """Modulator contribution at `beat`, or None when done."""
        if beat < self.start_beat:
            return None

        elapsed = beat - self.start_beat

        # ── No release envelope ─────────────────────────────────────
        # One-shot: plays its envelope once, then ends.
        if self.release_envelope is None or self.release_duration_beats <= 0:
            if self.released:
                return None
            if self.duration_beats > 0 and elapsed >= self.duration_beats:
                return None
            return self._attack_value(beat)

        # ── With release envelope ───────────────────────────────────
        if not self.released:
            # Attack/sustain — holds at envelope.sample(1.0) past duration.
            return self._attack_value(beat)

        # Released — possibly still in release phase.
        if self.release_beat is None:
            # Defensive: release() didn't stamp the beat. Treat as released-now.
            self.release_beat = beat

        if beat < self.release_beat:
            # Released flag set but release_beat is in the future — odd, but
            # behave as if still sustaining until release_beat arrives.
            return self._attack_value(beat)

        rel_elapsed = beat - self.release_beat
        if rel_elapsed >= self.release_duration_beats:
            return None

        # Value held at the moment of release (frozen — doesn't keep moving
        # along the attack envelope during the release).
        held = self._attack_value(self.release_beat)
        # Release envelope is expected to go 1.0 → 0.0 over its duration.
        rel_t = rel_elapsed / self.release_duration_beats
        rel_v = self.release_envelope.sample(rel_t)
        # rel_v = 1.0 → return held; rel_v = 0.0 → return base_value.
        return self.base_value + (held - self.base_value) * rel_v


# ── Combine multiple active modulators into a single value ───────────────

def combine(target: str, base: float, modulators: list[Modulator], beat: float) -> float:
    """Fold a target's active modulators into a single value.

    Order:
      1. `base` is the resting/configured value of the target.
      2. Each absolute modulator OVERWRITES the running value (later wins).
      3. Each additive modulator ADDS its contribution.
      4. Each multiplicative modulator MULTIPLIES the running value.
    """
    value = base
    # Pass 1 — absolute (start_beat order, later wins by virtue of overwrite).
    abs_mods = sorted((m for m in modulators if m.target == target and m.op == "absolute"),
                      key=lambda m: m.start_beat)
    for m in abs_mods:
        v = m.value_at(beat)
        if v is not None:
            value = v
    # Pass 2 — additive.
    for m in modulators:
        if m.target != target or m.op != "additive":
            continue
        v = m.value_at(beat)
        if v is not None:
            value += v
    # Pass 3 — multiplicative.
    for m in modulators:
        if m.target != target or m.op != "multiplicative":
            continue
        v = m.value_at(beat)
        if v is not None:
            value *= v
    return value
