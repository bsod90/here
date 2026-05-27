#!/usr/bin/env python3
"""Generate the M4L device's metadata JSONs from the orchestrator's
canonical sources.

- `here_events.json` lists the events the device exposes as MIDI pads.
  Source of truth: `SynthAnimation.NOTE_LANES` in
  `software/orchestrator/scene/animations/synth.py`. The patcher embeds
  this list so each pad knows its label and the v8 logic knows which
  pitch maps to which OSC note_on address.

- `here_knobs.json` lists every automatable parameter the device exposes.
  Mirrors the admin UI's SYNTH_MASTER_SLIDERS / OVAL_KNOBS / PHYSICS_KNOBS
  arrays — if you add a knob to admin.js, add it here too. The patcher
  generator reads this file to lay out `live.dial` objects.

Run from `software/ableton/`:
    python3 gen_metadata.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
ORCH_DIR = REPO_ROOT / "software" / "orchestrator"

# Make NOTE_LANES importable without dragging numpy in.
if str(ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(ORCH_DIR))

from scene.animations.synth import SynthAnimation  # noqa: E402


# MIDI C1 — Drum Rack's first pad. NOTE_LANES[0] → pitch 36.
BASE_PITCH = 36


def build_events() -> list[dict]:
    """One entry per NOTE_LANES lane, in lane order. Each entry has
    pitch, label, event name, and any built-in params (e.g. palette index
    for the Palette N pads). The patcher uses `pitch` for routing and
    `label` for pad text."""
    out = []
    for i, lane in enumerate(SynthAnimation.NOTE_LANES):
        out.append({
            "index": i,
            "pitch": BASE_PITCH + i,
            "label": lane["label"],
            "event": lane["event"],
            "params": dict(lane.get("params") or {}),
        })
    return out


# Knob lists — kept in sync with admin.js by convention. Each entry
# becomes one `live.dial` in the patcher and emits an OSC topic of the
# form `/here/scene/<prefix>/<key>` (or `/here/scene/oval/<i>/<key>` for
# per-ring).
#
# Schema: { key, label, min, max, step, default (optional) }.
#
# IMPORTANT: keep this aligned with
#   software/orchestrator/admin/static/admin.js
# SYNTH_MASTER_SLIDERS / OVAL_KNOBS / PHYSICS_KNOBS.

MASTER_KNOBS = [
    {"key": "radius_min",          "label": "Radius Min",     "min": 0,    "max": 12,  "step": 0.1,  "default": 2.5},
    {"key": "radius_max",          "label": "Radius Max",     "min": 8,    "max": 22,  "step": 0.1,  "default": 16.0},
    {"key": "radius_default",      "label": "Radius Default", "min": 2,    "max": 20,  "step": 0.1,  "default": 8.0},
    {"key": "brightness",          "label": "Brightness",     "min": 0,    "max": 2,   "step": 0.05, "default": 1.0},
    {"key": "gap_coefficient",     "label": "Ring Gap",       "min": 0,    "max": 6,   "step": 0.1,  "default": 1.0},
    {"key": "dot_orbit_speed",     "label": "Comet Spin",     "min": 0.5,  "max": 8,   "step": 0.1,  "default": 2.5},
    {"key": "trail_steps",         "label": "Tail Length",    "min": 4,    "max": 40,  "step": 1,    "default": 14},
    {"key": "dot_speed_min",       "label": "Speed Min",      "min": 0,    "max": 1,   "step": 0.02, "default": 0.10},
    {"key": "dot_speed_max",       "label": "Speed Max",      "min": 0.3,  "max": 2.5, "step": 0.05, "default": 1.30},
    {"key": "dot_speed_lock_exp",  "label": "Speed Curve",    "min": 0.3,  "max": 4,   "step": 0.05, "default": 1.6},
    {"key": "shimmer_intensity",   "label": "Shimmer Amp",    "min": 0,    "max": 0.6, "step": 0.01, "default": 0.18},
]

PHYSICS_KNOBS = [
    {"key": "speed",            "label": "Impulse Speed",  "min": 5,    "max": 80,  "step": 0.5,  "default": 25},
    {"key": "radial_offset",    "label": "Jitter",         "min": 0,    "max": 0.6, "step": 0.01, "default": 0.12},
    {"key": "squishiness",      "label": "Squishiness",    "min": 0,    "max": 1,   "step": 0.01, "default": 0.35},
    {"key": "damping",          "label": "Viscosity",      "min": 0,    "max": 5,   "step": 0.05, "default": 0.3},
    {"key": "bounce",           "label": "Bounce",         "min": 0.1,  "max": 1,   "step": 0.01, "default": 0.75},
    {"key": "center_pull",      "label": "Center Pull",    "min": 0,    "max": 15,  "step": 0.1,  "default": 3},
    {"key": "tau_squash",       "label": "Squash τ", "min": 0.05, "max": 1,   "step": 0.01, "default": 0.25},
    {"key": "max_velocity",     "label": "Max Velocity",   "min": 10,   "max": 120, "step": 1,    "default": 40},
    {"key": "angular_friction", "label": "Rot Friction",   "min": 0,    "max": 4,   "step": 0.05, "default": 0.6},
    {"key": "squash_damping",   "label": "Squash ζ", "min": 0.05, "max": 1.5, "step": 0.05, "default": 0.35},
]

# Per-ring knobs — replicated 3× in the patcher with the ring index
# baked in (oval_<key>_<i>). Defaults differ per ring.
OVAL_KNOBS = [
    {"key": "skew",         "label": "Skew",  "min": 0,    "max": 0.5,    "step": 0.01,
     "defaults": [0.12, 0.18, 0.20]},
    {"key": "phase",        "label": "Phase", "min": 0,    "max": 3.14159, "step": 0.05,
     "defaults": [0.0, 1.0, 2.1]},
    {"key": "blur",         "label": "Blur",  "min": 0.3,  "max": 8,       "step": 0.1,
     "defaults": [1.8, 2.5, 1.2]},
    {"key": "radius_scale", "label": "Scale", "min": 0.2,  "max": 2.0,     "step": 0.05,
     "defaults": [1.0, 1.0, 1.0]},
    {"key": "segments",     "label": "Dash",  "min": 0,    "max": 32,      "step": 1,
     "defaults": [0, 0, 0]},
    {"key": "gap",          "label": "Gap",   "min": 0,    "max": 0.95,    "step": 0.05,
     "defaults": [0.4, 0.4, 0.4]},
]


def build_knobs() -> dict:
    return {
        "master": MASTER_KNOBS,
        "physics": PHYSICS_KNOBS,
        "oval": OVAL_KNOBS,
    }


def main() -> None:
    events = build_events()
    knobs = build_knobs()

    (HERE / "here_events.json").write_text(
        json.dumps({"base_pitch": BASE_PITCH, "events": events}, indent=2) + "\n"
    )
    (HERE / "here_knobs.json").write_text(
        json.dumps(knobs, indent=2) + "\n"
    )

    n_master = len(knobs["master"])
    n_physics = len(knobs["physics"])
    n_oval = len(knobs["oval"]) * 3
    print(f"wrote here_events.json ({len(events)} lanes, base pitch {BASE_PITCH})")
    print(f"wrote here_knobs.json ({n_master} master + {n_physics} physics + "
          f"{n_oval} per-ring = {n_master + n_physics + n_oval} dials)")


if __name__ == "__main__":
    main()
