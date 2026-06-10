"""Service composition — builds, wires, starts, and stops every
orchestrator service in one place.

main.py stays a thin CLI entry point; tests build the fully-wired stack
against a temp config with `build_services(config)` and never touch
uvicorn or real sockets (nothing is started until Services.start()).

Adding a service:
  1. construct it in build_services (order matters only for real
     dependencies — keep the wiring linear and obvious)
  2. add a field to Services
  3. start/stop it in Services.start()/stop() (stop in reverse order)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from animation_engine import AnimationEngine
from audio import AudioPlayer
from osc_input import OscState, OscServer
from playground import Playground
from scale import ScaleSensor, ScaleConfig
from scene import Scene, SequenceStore, PatchStore
from scene.animations import REGISTRY as SCENE_ANIMATION_REGISTRY
from scene.default_presets import seed_defaults
from scene.envelopes import Envelope, default_envelopes
from scene.physics import PhysicsParams
from scene.tap import TapTracker
from simulator_ws import SimulatorBus
from telemetry import Telemetry
from telemetry_history import TelemetryHistory
from transport import UDPTransport
import migrations

logger = logging.getLogger("here.bootstrap")


@dataclass
class Services:
    """Everything the orchestrator runs, wired and ready to start."""
    config: Any
    transport: UDPTransport
    sim_bus: SimulatorBus
    osc_state: OscState
    osc_server: OscServer
    scene: Scene
    sequence_store: SequenceStore
    patch_store: PatchStore
    tap_tracker: TapTracker
    telemetry: Telemetry
    telemetry_history: TelemetryHistory
    scale: ScaleSensor
    engine: AnimationEngine
    audio: AudioPlayer
    playground: Playground

    def start(self) -> None:
        """Start the background workers (idempotence is each service's
        own concern). The admin app is served separately by uvicorn."""
        self.audio.start()
        self.engine.start()
        self.telemetry.start()
        self.osc_server.start()
        self.scale.start()
        self.telemetry_history.start()

    def stop(self) -> None:
        self.audio.stop()
        self.telemetry_history.stop()
        self.scale.stop()
        self.osc_server.stop()
        self.telemetry.stop()
        self.engine.stop()
        self.transport.stop()

    def create_admin_app(self):
        """FastAPI app for the admin panel, wired to these services."""
        from admin.routes import create_app
        return create_app(self.config, self.engine, self.transport,
                          self.telemetry, self.sim_bus,
                          osc_state=self.osc_state, scene=self.scene,
                          sequence_store=self.sequence_store,
                          patch_store=self.patch_store,
                          tap_tracker=self.tap_tracker, scale=self.scale,
                          telemetry_history=self.telemetry_history,
                          audio=self.audio, playground=self.playground)


def build_services(config) -> Services:
    """Construct + wire the whole service graph. Pure composition: no
    threads, subprocesses (beyond the audio sample loader), or sockets
    are started here — that happens in Services.start()."""
    migrations.run_config_migrations(config)

    transport = UDPTransport(config.get("targets") or [], config)
    sim_bus = SimulatorBus()

    osc_cfg = config.get("osc") or {}
    osc_state = OscState()
    osc_state.attack_s = max(0.001, osc_cfg.get("attack_ms", 20) / 1000.0)
    osc_state.release_s = max(0.001, osc_cfg.get("release_ms", 180) / 1000.0)

    scene = _build_scene(config)
    sequence_store, patch_store = _build_stores(config)
    seed_defaults(patch_store, sequence_store, logger)
    _load_active_sequence(config, scene, sequence_store)
    _maybe_autoplay(config, scene)

    telemetry = Telemetry()

    # Bench occupancy sensor (dual HX711). The scale's state machine
    # drives engine.mode between occupied/idle when auto_engage is on.
    # NOTE: the closures capture `engine`, which is constructed a few
    # lines below — they only run once the scale thread is started.
    def _scale_switch(mode: str, reason: str) -> None:
        engine.mode = mode
        config.set("mode", mode)
        logger.info(f"{reason} → mode={mode}")

    scale = ScaleSensor(
        cfg=ScaleConfig.from_dict(config.get("scale") or {}),
        mode_switcher=_scale_switch,
        current_mode_getter=lambda: engine.mode,
        persist_cb=lambda d: config.set("scale", d),
    )

    engine = AnimationEngine(config, transport, sim_bus=sim_bus,
                             osc_state=osc_state, scene=scene, scale=scale)

    osc_server = OscServer(
        osc_state,
        time_provider=engine.time_ms,
        host=osc_cfg.get("host", "0.0.0.0"),
        port=osc_cfg.get("port", 9000),
        scene=scene,
    )
    tap_tracker = TapTracker()
    telemetry_history = TelemetryHistory(
        db_path=(config.get("telemetry_db_path") or "/opt/here/data/telemetry.db"),
        engine=engine,
        scale=scale,
    )

    audio_cfg = config.get("audio") or {}
    audio = AudioPlayer(
        media_dir=audio_cfg.get("media_dir", "/opt/here/media"),
        tracks=audio_cfg.get("tracks") or {},
        mixer_control=audio_cfg.get("mixer_control") or None,
    )
    _couple_fireplace_audio(config, engine, audio)

    # Nadia's Playground — isolated experimentation mode (see
    # docs/nadia_playground.md). Attached to the engine for its render.
    playground = Playground(config, audio=audio)
    engine.playground = playground

    return Services(
        config=config, transport=transport, sim_bus=sim_bus,
        osc_state=osc_state, osc_server=osc_server, scene=scene,
        sequence_store=sequence_store, patch_store=patch_store,
        tap_tracker=tap_tracker, telemetry=telemetry,
        telemetry_history=telemetry_history, scale=scale, engine=engine,
        audio=audio, playground=playground,
    )


# ── Scene wiring ─────────────────────────────────────────────────────

def _build_scene(config) -> Scene:
    scene_cfg = config.get("scene") or {}
    anim_name = scene_cfg.get("animation") or next(iter(SCENE_ANIMATION_REGISTRY.keys()))
    AnimationCls = SCENE_ANIMATION_REGISTRY.get(anim_name) or next(iter(SCENE_ANIMATION_REGISTRY.values()))
    animation = AnimationCls(scene_cfg.get(anim_name) or {})
    # Load curves config; fall back to defaults for any missing names,
    # and allow extra user-defined curves alongside the defaults.
    saved_curves = scene_cfg.get("curves") or {}
    curves = {name: Envelope.from_dict(saved_curves[name]) if name in saved_curves else env
              for name, env in default_envelopes().items()}
    for name, raw in saved_curves.items():
        if name not in curves:
            curves[name] = Envelope.from_dict(raw)
    scene = Scene(animation, bpm=scene_cfg.get("bpm", 120.0),
                  curves=curves,
                  physics_params=PhysicsParams.from_dict(scene_cfg.get("physics") or {}))
    # Per-event default params (color, ease, cluster_count, etc.) — merged
    # into every dispatch under lane.params under per-trigger params.
    scene.router.set_event_defaults(scene_cfg.get("event_defaults") or {})
    return scene


def _build_stores(config) -> tuple[SequenceStore, PatchStore]:
    scene_cfg = config.get("scene") or {}
    seq_cfg = scene_cfg.get("sequencer") or {}
    return (SequenceStore(seq_cfg.get("sequences_dir", "/opt/here/data/sequences")),
            PatchStore(scene_cfg.get("patches_dir", "/opt/here/data/patches")))


def _load_active_sequence(config, scene, seq_store) -> None:
    """Point the live sequencer at saved content. Fallback chain so we
    don't accidentally boot into an empty roll when files exist on disk:
      1. The named `active_sequence` if its file exists
      2. The first sequence file in the store (alphabetically)
      3. Legacy `config.scene.sequencer.notes`
      4. Empty.
    """
    seq_cfg = (config.get("scene") or {}).get("sequencer") or {}
    # Cold-start preference: if there's no active sequence yet, point at
    # the bundled "breathing" so the orchestrator boots into a playing scene.
    if not seq_cfg.get("active_sequence") and seq_store.exists("breathing"):
        config.set("scene", {"sequencer": {"active_sequence": "breathing"}})
        seq_cfg = (config.get("scene") or {}).get("sequencer") or {}
    active_name = seq_cfg.get("active_sequence")
    if active_name is None:
        active_name = migrations.migrate_sequencer_notes(config, seq_store)

    if active_name and seq_store.exists(active_name):
        data = seq_store.load(active_name)
        if data is not None:
            scene.sequencer.set_loop_length(float(data.get("loop_length_beats", 16.0)))
            scene.sequencer.set_notes(data.get("notes") or [])
            logger.info(f"loaded active sequence: {active_name} "
                        f"({len(data.get('notes') or [])} notes)")
            return
    available = seq_store.list()
    if available:
        fallback = available[0]["name"]
        data = seq_store.load(fallback)
        if data is not None:
            scene.sequencer.set_loop_length(float(data.get("loop_length_beats", 16.0)))
            scene.sequencer.set_notes(data.get("notes") or [])
            config.set("scene", {"sequencer": {"active_sequence": fallback}})
            logger.info(f"active_sequence missing — fell back to {fallback}")
            return
    # Cold start: legacy field or empty.
    scene.sequencer.set_loop_length(seq_cfg.get("loop_length_beats", 16.0))
    scene.sequencer.set_notes(seq_cfg.get("notes") or [])


def _maybe_autoplay(config, scene) -> None:
    """If the saved mode is "midi" AND the user hasn't disabled autoplay,
    start the sequencer at boot. Turning autoplay OFF is the right call
    when driving the engine from Ableton OSC — the orchestrator becomes a
    pure renderer with Ableton holding the transport."""
    seq_cfg = (config.get("scene") or {}).get("sequencer") or {}
    if config.get("mode") != "midi":
        return
    if bool(seq_cfg.get("autoplay", True)):
        scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
        logger.info("midi mode at boot — auto-play on")
    else:
        logger.info("midi mode at boot — auto-play disabled (waiting for external trigger)")


# ── Audio/mode coupling ──────────────────────────────────────────────

def _couple_fireplace_audio(config, engine, audio) -> None:
    """Fireplace ambience follows fireplace mode: entering turns the
    sound on, leaving turns it off. Fires on every mode change path
    (admin button, scale auto-engage, sensor)."""
    def on_mode_change(prev_mode, new_mode) -> None:
        if new_mode == "fireplace":
            audio.set_track("fireplace", enabled=True)
            config.set("audio", {"tracks": {"fireplace": {"enabled": True}}})
            logger.info("fireplace mode → fireplace sound ON")
        elif prev_mode == "fireplace":
            audio.set_track("fireplace", enabled=False)
            config.set("audio", {"tracks": {"fireplace": {"enabled": False}}})
            logger.info("left fireplace mode → fireplace sound OFF")

    engine.on_mode_change = on_mode_change
    # Boot already in fireplace mode → make the ambience match.
    if engine.mode == "fireplace":
        on_mode_change(None, "fireplace")
