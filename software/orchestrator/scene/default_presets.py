"""Bundled default patches + sequences seeded at first boot.

The orchestrator writes these out to the data dirs (which are excluded
from rsync delete, so they survive deploys but the user can edit, delete
or replace them freely after that).

Currently ships:
  * `breathing`  — recreates the meditation breathing animation. Smooth
    4-4-4-4 cycle (4s inhale, 4s hold, 4s exhale, 4s hold) at 60 BPM. The
    patch sets `transition_default` + `release_default` curves to 4-beat
    cosine eases; the sequence has one `Expand` note of length 8 beats
    on a 16-beat loop. Loading the patch switches to its bundled
    sequence and starts playback.
"""

BREATHING_PATCH = {
    "name": "breathing",
    "bpm": 60.0,
    "synth": {
        "radius_min":     3.0,
        "radius_max":    17.0,
        "radius_default": 3.0,
        "alpha_default":  1.0,
        "brightness":     1.0,
        "oval_enabled_0": True, "oval_enabled_1": True, "oval_enabled_2": True,
        # All three ovals blur both inward + outward — the soft halo
        # wraps the rim symmetrically (no clipped sides).
        # Index meaning: 0=outer (back), 1=middle (on top), 2=inner.
        "oval_blur_0": 1.2, "oval_blur_1": 1.8, "oval_blur_2": 3.0,
        "oval_side_0": "both", "oval_side_1": "both", "oval_side_2": "both",
        # Nest the rings via radius offsets × gap_coefficient. gap=2.0
        # gives noticeable separation; tune via the synth meta.
        "gap_coefficient": 2.0,
        "oval_radius_offset_0":  1.0,
        "oval_radius_offset_1":  0.0,
        "oval_radius_offset_2": -1.0,
        # Per-oval color (palette slot index 0..7).
        "oval_color_0": 2,   # outer  → outer_color
        "oval_color_1": 0,   # middle → rim_color (on top)
        "oval_color_2": 1,   # inner  → inner_color
        # Slight skew so rings are visibly elliptical (rotation visible).
        "oval_skew_0": 0.20, "oval_skew_1": 0.12, "oval_skew_2": 0.16,
        "oval_phase_0": 2.1,  "oval_phase_1": 0.0,  "oval_phase_2": 1.0,
        "oval_velocity_0": 0.0, "oval_velocity_1": 0.0, "oval_velocity_2": 0.0,
    },
    "curves": {
        "pulse_default":      {"points": [[0, 0], [0.08, 1.0], [1.0, 0]],
                               "interp": "ease_out_quad", "duration_beats": 0.5},
        # 4-beat cosine eases — 4 s @ 60 bpm = the inhale/exhale phase of
        # the breathing cycle. Both attack + release run over exactly the
        # same musical length the OG breathing uses.
        "transition_default": {"points": [[0, 0], [1, 1]],
                               "interp": "cosine", "duration_beats": 4.0},
        "release_default":    {"points": [[0, 1], [1, 0]],
                               "interp": "cosine", "duration_beats": 4.0},
        "instant":            {"points": [[0, 1], [1, 1]],
                               "interp": "linear", "duration_beats": 0.1},
        # Dedicated curve for Dissolve / Respawn — independent of Expand/
        # Contract so the user can shape the particle slow-fast curve
        # without touching the breathing transitions.
        "dissolve_default":   {"points": [[0, 0], [1, 1]],
                               "interp": "linear", "duration_beats": 4.0},
    },
    "physics": {
        "speed": 25.0, "radial_offset": 0.12, "squishiness": 0.35,
        "damping": 0.3, "bounce": 0.75, "center_pull": 3.0,
        "tau_squash": 0.25, "max_velocity": 40.0,
    },
    "default_durations": {
        "expand":   8,   # full inhale + hold (note held for 8 beats)
        "contract": 8,
    },
    "palette_idx": 0,
    # The patch references its preferred sequence — loading the patch
    # via the admin UI also switches the active sequence to this name
    # and starts playback.
    "active_sequence": "breathing",
}


BREATHING_SEQUENCE = {
    "name": "breathing",
    "loop_length_beats": 16.0,    # 16 beats @ 60 bpm = 16 s = full 4-4-4-4 cycle
    "notes": [
        # Expand pitch 0 — pushes radius from min to max over the curve's
        # 4-beat cosine ramp (inhale), then pins at max for the hold_top.
        # Note length is decorative (Expand is push-and-hold; note_off is
        # a no-op) but matches the 4-beat inhale phase visually.
        {"pitch": 0, "start_beat": 0.0, "length_beats": 4.0},
        # Contract pitch 1 at beat 8 — pushes radius from max to min over
        # 4 beats (exhale), then pins at min for the hold_bottom.
        {"pitch": 1, "start_beat": 8.0, "length_beats": 4.0},
    ],
}


def seed_defaults(patch_store, seq_store, logger):
    """Idempotently write bundled patches + sequences if they're missing
    on disk. Called once at boot from main.py."""
    if not patch_store.exists(BREATHING_PATCH["name"]):
        patch_store.save(BREATHING_PATCH["name"], BREATHING_PATCH)
        logger.info(f"seeded default patch: {BREATHING_PATCH['name']}")
    if not seq_store.exists(BREATHING_SEQUENCE["name"]):
        seq_store.save(
            BREATHING_SEQUENCE["name"],
            notes=BREATHING_SEQUENCE["notes"],
            loop_length_beats=BREATHING_SEQUENCE["loop_length_beats"],
        )
        logger.info(f"seeded default sequence: {BREATHING_SEQUENCE['name']}")
