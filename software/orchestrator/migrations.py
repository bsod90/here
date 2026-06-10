"""Config schema migrations — legacy on-disk shapes → current schema.

Every function here is IDEMPOTENT and runs on every boot (bootstrap.py
calls run_config_migrations). The rules:

  * A migration reads the legacy shape, writes the current shape, and
    neutralizes the legacy keys so the next boot skips it.
  * Never delete user data — carry it over or write it somewhere durable.
  * New migration = new small function + a call in run_config_migrations
    + a test in tests/test_migrations.py.

Mode-name aliases ("music" → "midi", …) are NOT here — the engine owns
mode validation, so they live in animation_engine.LEGACY_MODE_ALIASES.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_config_migrations(config) -> None:
    """All migrations that only need the config object."""
    migrate_scene_breathing_to_synth(config)
    migrate_audio_backdrop_to_tracks(config)


def migrate_scene_breathing_to_synth(config) -> None:
    """Scene v1 → v2: meta keys under `scene.breathing` move to
    `scene.synth`, and the active scene animation is re-pointed. Existing
    sequence files keep working unchanged — lane indices 0..10 map to
    semantically equivalent v2 events."""
    scene_cfg = config.get("scene") or {}
    legacy = scene_cfg.get("breathing") or {}
    if legacy and not (scene_cfg.get("synth") or {}):
        synth_copy = {}
        for k in ("radius_min", "radius_max", "radius_default", "brightness"):
            if k in legacy:
                synth_copy[k] = legacy[k]
        # Per-oval blur from legacy rim_width / inner_blur / outer_blur.
        for src, dst in (("rim_width", "oval_blur_0"),
                         ("inner_blur", "oval_blur_1"),
                         ("outer_blur", "oval_blur_2")):
            if src in legacy:
                synth_copy[dst] = legacy[src]
        # Per-oval skew/phase.
        for src, dst in (("rim_skew", "oval_skew_0"),
                         ("inner_skew", "oval_skew_1"),
                         ("outer_skew", "oval_skew_2"),
                         ("rim_phase", "oval_phase_0"),
                         ("inner_phase", "oval_phase_1"),
                         ("outer_phase", "oval_phase_2")):
            if src in legacy:
                synth_copy[dst] = legacy[src]
        if synth_copy:
            config.set("scene", {"synth": synth_copy})
            logger.info("migrated legacy scene.breathing → scene.synth: %s",
                        sorted(synth_copy))
    if (config.get("scene") or {}).get("animation") == "breathing":
        config.set("scene", {"animation": "synth"})
        logger.info("scene.animation auto-migrated breathing → synth")


def migrate_audio_backdrop_to_tracks(config) -> None:
    """Single `audio.backdrop_*` scalars → the `audio.tracks.ocean` entry.
    Guard on non-None values so it runs once: after migrating we null the
    legacy keys, and a later boot then skips this block."""
    audio_cfg = config.get("audio") or {}
    if (audio_cfg.get("backdrop_enabled") is None
            and audio_cfg.get("backdrop_volume") is None):
        return
    tracks = dict(audio_cfg.get("tracks") or {})
    ocean = dict(tracks.get("ocean") or {})
    if audio_cfg.get("backdrop_enabled") is not None:
        ocean["enabled"] = bool(audio_cfg["backdrop_enabled"])
    if audio_cfg.get("backdrop_volume") is not None:
        ocean["volume"] = float(audio_cfg["backdrop_volume"])
    if audio_cfg.get("backdrop_file"):
        ocean.setdefault("file", audio_cfg["backdrop_file"])
    ocean.setdefault("label", "Ocean")
    tracks["ocean"] = ocean
    config.set("audio", {"tracks": tracks,
                         "backdrop_enabled": None,
                         "backdrop_volume": None,
                         "backdrop_file": None})
    logger.info("migrated legacy audio.backdrop_* → audio.tracks.ocean")


def migrate_sequencer_notes(config, seq_store) -> str | None:
    """Legacy in-config piano-roll notes → a named sequence file on disk.
    Returns the name of the migrated sequence, or None if there was
    nothing to migrate."""
    scene_cfg = config.get("scene") or {}
    seq_cfg = scene_cfg.get("sequencer") or {}
    if seq_cfg.get("active_sequence") is not None or not (seq_cfg.get("notes") or []):
        return None
    name = seq_store.unique_name("main")
    seq_store.save(
        name,
        notes=seq_cfg.get("notes") or [],
        loop_length_beats=seq_cfg.get("loop_length_beats", 16.0),
    )
    config.set("scene", {"sequencer": {"active_sequence": name}})
    logger.info("migrated legacy sequencer notes → %s", name)
    return name
