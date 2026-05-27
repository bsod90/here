"""Scene engine — synth-for-visuals.

A `Scene` composes:
  * `BeatClock`  — musical time + phase drift
  * `MidiSequencer` — note_on/note_off events from a looping piano roll
  * `EventRouter` + the event catalog — events → actions
  * `BallPhysics` — squishy-ball position + squash tensor
  * a list of active `Modulator`s — envelope-driven state writes
  * an `Animation` — pure render of the state dict to LED frame

Events trigger Modulators which shape state over time; the animation
renders the state each frame. See `docs/scene-engine-v2.md` for the
architecture doc.
"""
from .clock import BeatClock
from .envelopes import Envelope, Modulator, combine, default_envelopes
from .events import (
    Action,
    AnchorAction,
    CompoundAction,
    EventRouter,
    ImpulseAction,
    ModulatorAction,
)
from .midi_sequencer import MidiSequencer
from .physics import BallPhysics, PhysicsParams
from .scene import Scene
from .patch_store import PatchStore
from .sequence_store import SequenceStore, sanitize_name

__all__ = [
    "BeatClock", "Envelope", "Modulator", "combine", "default_envelopes",
    "Action", "AnchorAction", "CompoundAction", "EventRouter",
    "ImpulseAction", "ModulatorAction",
    "MidiSequencer", "BallPhysics", "PhysicsParams",
    "Scene", "SequenceStore", "PatchStore", "sanitize_name",
]
