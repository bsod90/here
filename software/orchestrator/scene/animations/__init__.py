"""Scene-driven animations registry.

Each animation implements:
  - `name`: str
  - `initial_state() -> dict`
  - `render(frame, state, time_ms, params, *, ball_state, beat, grid)`
  - optional `tick(state, beat, dt_seconds)`
  - optional `NOTE_LANES`: list of `{label, event, params?}` for the
    sequencer / piano-roll.
"""
from .synth import SynthAnimation

REGISTRY = {
    SynthAnimation.name: SynthAnimation,
}

__all__ = ["SynthAnimation", "REGISTRY"]
