"""HERE Experience Orchestrator — entry point."""
import argparse
import logging
import uvicorn

from config import ConfigManager
from transport import UDPTransport
from animation_engine import AnimationEngine
from telemetry import Telemetry
from simulator_ws import SimulatorBus
from osc_input import OscState, OscServer
from scene import Scene, SequenceStore, PatchStore
from scene.envelopes import Envelope, default_envelopes
from scene.physics import PhysicsParams
from scene.tap import TapTracker
from scene.animations import REGISTRY as SCENE_ANIMATION_REGISTRY
from admin.routes import create_app, LogHandler
from scale import ScaleSensor, ScaleConfig
from telemetry_history import TelemetryHistory


def main():
    parser = argparse.ArgumentParser(description="HERE Experience Orchestrator")
    parser.add_argument("--host", default="0.0.0.0", help="Admin panel bind address")
    parser.add_argument("--port", type=int, default=8000, help="Admin panel port")
    parser.add_argument("--config", default="config.json", help="Config file path")
    args = parser.parse_args()

    # Logging
    log_handler = LogHandler()
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), log_handler],
    )
    logger = logging.getLogger("here")

    # Init
    config = ConfigManager(path=args.config)
    transport = UDPTransport(config.get("targets") or [], config)
    sim_bus = SimulatorBus()
    osc_state = OscState()
    osc_cfg = config.get("osc") or {}
    osc_state.attack_s = max(0.001, osc_cfg.get("attack_ms", 20) / 1000.0)
    osc_state.release_s = max(0.001, osc_cfg.get("release_ms", 180) / 1000.0)
    # Scene engine — synth-for-visuals (MIDI-driven, modulator-based).
    scene_cfg = config.get("scene") or {}
    # ── Legacy v1 → v2 migration ───────────────────────────────────
    # If the user's saved config still points at "breathing" (the v1
    # scene-mode animation) or has its meta keys under `scene.breathing`,
    # carry the compatible values into `scene.synth` and re-point the
    # active animation. Existing sequence files keep working unchanged —
    # lane indices 0..10 map to semantically equivalent v2 events.
    legacy_breathing = scene_cfg.get("breathing") or {}
    if legacy_breathing and not (scene_cfg.get("synth") or {}):
        synth_copy = {}
        for k in ("radius_min", "radius_max", "radius_default", "brightness"):
            if k in legacy_breathing:
                synth_copy[k] = legacy_breathing[k]
        # Per-oval blur from legacy rim_width / inner_blur / outer_blur.
        for src, dst in (("rim_width", "oval_blur_0"),
                         ("inner_blur", "oval_blur_1"),
                         ("outer_blur", "oval_blur_2")):
            if src in legacy_breathing:
                synth_copy[dst] = legacy_breathing[src]
        # Per-oval skew/phase.
        for src, dst in (("rim_skew", "oval_skew_0"),
                         ("inner_skew", "oval_skew_1"),
                         ("outer_skew", "oval_skew_2"),
                         ("rim_phase", "oval_phase_0"),
                         ("inner_phase", "oval_phase_1"),
                         ("outer_phase", "oval_phase_2")):
            if src in legacy_breathing:
                synth_copy[dst] = legacy_breathing[src]
        if synth_copy:
            config.set("scene", {"synth": synth_copy})
            logger.info(f"migrated legacy scene.breathing → scene.synth: {sorted(synth_copy)}")
            scene_cfg = config.get("scene") or {}
    if scene_cfg.get("animation") == "breathing":
        config.set("scene", {"animation": "synth"})
        scene_cfg = config.get("scene") or {}
        logger.info("scene.animation auto-migrated breathing → synth")
    anim_name = scene_cfg.get("animation") or next(iter(SCENE_ANIMATION_REGISTRY.keys()))
    AnimationCls = SCENE_ANIMATION_REGISTRY.get(anim_name) or next(iter(SCENE_ANIMATION_REGISTRY.values()))
    animation = AnimationCls(scene_cfg.get(anim_name) or {})
    # Load curves config; fall back to defaults for any missing names.
    saved_curves = scene_cfg.get("curves") or {}
    defaults = default_envelopes()
    curves = {name: Envelope.from_dict(saved_curves[name]) if name in saved_curves else env
              for name, env in defaults.items()}
    # Allow extra user-defined curves alongside the defaults.
    for name, raw in saved_curves.items():
        if name not in curves:
            curves[name] = Envelope.from_dict(raw)
    physics_params = PhysicsParams.from_dict(scene_cfg.get("physics") or {})
    scene = Scene(animation, bpm=scene_cfg.get("bpm", 120.0),
                  curves=curves, physics_params=physics_params)
    # Per-event default params (color, ease, cluster_count, etc.) — merged
    # into every dispatch under lane.params under per-trigger params.
    scene.router.set_event_defaults(scene_cfg.get("event_defaults") or {})
    # Sequence + patch storage — named files on disk, survive deploys.
    seq_cfg = scene_cfg.get("sequencer") or {}
    seq_store = SequenceStore(seq_cfg.get("sequences_dir", "/opt/here/data/sequences"))
    patch_store = PatchStore(scene_cfg.get("patches_dir", "/opt/here/data/patches"))
    # Seed bundled defaults (patches + sequences) on first boot. Idempotent —
    # if the user has already saved their own, we won't overwrite.
    from scene.default_presets import seed_defaults
    seed_defaults(patch_store, seq_store, logger)
    # Cold-start preference: if there's no active sequence yet, point at
    # the bundled "breathing" so the orchestrator boots into a playing scene.
    if not seq_cfg.get("active_sequence") and seq_store.exists("breathing"):
        config.set("scene", {"sequencer": {"active_sequence": "breathing"}})
        scene_cfg = config.get("scene") or {}
        seq_cfg = scene_cfg.get("sequencer") or {}
    # Migration: if no active sequence is set but legacy notes exist in the
    # config, write them out as a "main" sequence so the user's work isn't lost.
    active_name = seq_cfg.get("active_sequence")
    if active_name is None and (seq_cfg.get("notes") or []):
        active_name = seq_store.unique_name("main")
        seq_store.save(
            active_name,
            notes=seq_cfg.get("notes") or [],
            loop_length_beats=seq_cfg.get("loop_length_beats", 16.0),
        )
        logger.info(f"migrated legacy sequencer notes → {active_name}")
        config.set("scene", {"sequencer": {"active_sequence": active_name}})
    # Load active sequence into the live sequencer. Fallback chain so we
    # don't accidentally boot into an empty roll when files exist on disk:
    #   1. The named `active_sequence` if its file exists
    #   2. The first sequence file in the store (alphabetically)
    #   3. Legacy `config.scene.sequencer.notes`
    #   4. Empty.
    loaded = False
    if active_name and seq_store.exists(active_name):
        data = seq_store.load(active_name)
        if data is not None:
            scene.sequencer.set_loop_length(float(data.get("loop_length_beats", 16.0)))
            scene.sequencer.set_notes(data.get("notes") or [])
            logger.info(f"loaded active sequence: {active_name} ({len(data.get('notes') or [])} notes)")
            loaded = True
    if not loaded:
        available = seq_store.list()
        if available:
            fallback = available[0]["name"]
            data = seq_store.load(fallback)
            if data is not None:
                scene.sequencer.set_loop_length(float(data.get("loop_length_beats", 16.0)))
                scene.sequencer.set_notes(data.get("notes") or [])
                config.set("scene", {"sequencer": {"active_sequence": fallback}})
                logger.info(f"active_sequence missing — fell back to {fallback}")
                loaded = True
    if not loaded:
        # Cold start: legacy field or empty.
        scene.sequencer.set_loop_length(seq_cfg.get("loop_length_beats", 16.0))
        scene.sequencer.set_notes(seq_cfg.get("notes") or [])

    # If the saved mode is "midi" AND the user hasn't disabled
    # autoplay, start the sequencer at boot. Turning autoplay OFF
    # is the right call when driving the engine from Ableton OSC —
    # the orchestrator becomes a pure renderer with Ableton holding
    # the transport.
    autoplay = bool(seq_cfg.get("autoplay", True))
    if config.get("mode") == "midi" and autoplay:
        scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
        logger.info("midi mode at boot — auto-play on")
    elif config.get("mode") == "midi":
        logger.info("midi mode at boot — auto-play disabled (waiting for external trigger)")

    telemetry = Telemetry()

    # Bench occupancy sensor (dual HX711). The scale's state machine
    # drives engine.mode between occupied/idle when auto_engage is on,
    # so a user is just an "occupied" signal — no UI poll needed.
    def _scale_switch(mode: str, reason: str) -> None:
        engine.mode = mode
        config.set("mode", mode)
        logger.info(f"{reason} → mode={mode}")

    def _scale_persist(d: dict) -> None:
        config.set("scale", d)

    scale = ScaleSensor(
        cfg=ScaleConfig.from_dict(config.get("scale") or {}),
        mode_switcher=_scale_switch,
        current_mode_getter=lambda: engine.mode,
        persist_cb=_scale_persist,
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
    # Per-minute rollup persisted to SQLite (24 h / 7 d charts).
    telemetry_history = TelemetryHistory(
        db_path=(config.get("telemetry_db_path") or "/opt/here/data/telemetry.db"),
        engine=engine,
        scale=scale,
    )

    app = create_app(config, engine, transport, telemetry, sim_bus,
                     osc_state=osc_state, scene=scene,
                     sequence_store=seq_store, patch_store=patch_store,
                     tap_tracker=tap_tracker, scale=scale,
                     telemetry_history=telemetry_history)

    # Start background workers
    engine.start()
    telemetry.start()
    osc_server.start()
    scale.start()
    telemetry_history.start()
    logger.info(f"HERE Experience running — admin at http://{args.host}:{args.port}")

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        telemetry_history.stop()
        scale.stop()
        osc_server.stop()
        telemetry.stop()
        engine.stop()
        transport.stop()


if __name__ == "__main__":
    main()
