"""Core admin endpoints — mode, status, config/defaults, targets,
transport settings, logs, and OSC test injection.

These are the cross-cutting controls that don't belong to a single
domain service. Everything domain-specific (scene, scale, telemetry,
audio, playground, wled, AP) lives in its sibling module.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import get_defaults
from animation_engine import MODE_REGISTRY

from ._shared import safe_json, get_logs

logger = logging.getLogger(__name__)


def register(app: FastAPI, config, engine, transport,
             scene=None, osc_state=None, scale=None, meditation=None,
             scheduler=None) -> None:

    # ── Config / defaults ──────────────────────────────────────
    @app.get("/api/config")
    async def get_config():
        return config.get_all()

    @app.put("/api/config")
    async def update_config(request: Request):
        data = await safe_json(request)
        for key, value in data.items():
            config.set(key, value)
        return {"ok": True}

    @app.get("/api/defaults")
    async def get_default_config():
        return get_defaults()

    @app.post("/api/defaults/restore/{section}")
    async def restore_defaults(section: str):
        defaults = get_defaults()
        if section == "all":
            for key, value in defaults.items():
                config.set(key, value)
            engine.mode = defaults["mode"]
            transport.update_targets(defaults["targets"])
            logger.info("All settings restored to defaults")
        elif section in defaults:
            config.set(section, defaults[section])
            logger.info(f"Restored {section} defaults")
        else:
            return JSONResponse({"error": "unknown section"}, status_code=400)
        return config.get_all()

    # ── Mode ───────────────────────────────────────────────────
    @app.post("/api/mode/{mode}")
    async def set_mode(mode: str):
        if mode not in MODE_REGISTRY:
            return JSONResponse({"error": "invalid mode"}, status_code=400)
        prev = engine.mode
        config.set("mode", mode)
        engine.mode = mode
        logger.info(f"Mode changed to: {mode}")
        # Entering MIDI mode auto-plays the sequencer unless the user
        # has turned autoplay off (e.g. when driving the engine from
        # Ableton OSC — orchestrator becomes a pure renderer).
        if mode == "midi" and prev != "midi" and scene is not None:
            scn_cfg = config.get("scene") or {}
            seq_cfg = scn_cfg.get("sequencer") or {}
            autoplay = bool(seq_cfg.get("autoplay", True))
            if autoplay and not scene.sequencer.playing:
                scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
                logger.info("MIDI mode auto-play started")
            elif not autoplay:
                logger.info("MIDI mode auto-play disabled — sequencer left stopped")
        return {"mode": mode}

    # ── Sensor simulation ──────────────────────────────────────
    @app.post("/api/sensor/{state}")
    async def simulate_sensor(state: str):
        if state == "occupied":
            # When the meditation controller is enabled, IT picks the
            # occupied visuals (sequenced track or breathing fallback) off
            # the forced occupancy below — setting breathing here first
            # flashed the circle at the start of every sequenced sit.
            if meditation is not None and meditation.enabled():
                logger.info("Sensor: bench occupied (meditation drives visuals)")
            else:
                engine.mode = "breathing"
                config.set("mode", "breathing")
                logger.info("Sensor: bench occupied → breathing")
        elif state == "empty":
            # A started meditation plays to its end — the controller makes
            # the idle switch itself once the clip finishes.
            if meditation is not None and meditation.busy():
                logger.info("Sensor: bench empty (meditation playing to its end)")
            else:
                engine.mode = "standby"
                config.set("mode", "standby")
                logger.info("Sensor: bench empty → standby")
        else:
            return JSONResponse({"error": "invalid state"}, status_code=400)
        # Also force the scale's debounced occupancy, so everything keyed
        # to PHYSICAL occupancy (the meditation play-once flow and its
        # sequenced playground visuals) runs exactly like a real sit.
        if scale is not None:
            scale.simulate_occupancy(state == "occupied")
        return {"sensor": state, "mode": engine.mode}

    # ── Status ─────────────────────────────────────────────────
    @app.get("/api/status")
    async def get_status():
        out = {
            "mode": engine.mode,
            "fps": engine.actual_fps,
            "uptime_s": engine.uptime_seconds,
            "power": engine.power_estimate,
        }
        if scheduler is not None:
            out["schedule"] = scheduler.state()
        if hasattr(transport, "limiter_state"):
            out["power_limit"] = transport.limiter_state()
        return out

    # ── Targets (WLED endpoints) ───────────────────────────────
    @app.get("/api/targets")
    async def get_targets():
        return transport.get_targets()

    @app.post("/api/targets")
    async def add_target(request: Request):
        data = await safe_json(request)
        targets = config.get("targets") or []
        targets.append({
            "name": data.get("name", "New Target"),
            "ip": data["ip"],
            "port": data.get("port", 21324),
            "enabled": data.get("enabled", True),
        })
        config.set("targets", targets)
        transport.update_targets(targets)
        logger.info(f"Target added: {data.get('name')} @ {data['ip']}:{data.get('port', 21324)}")
        return {"ok": True, "targets": transport.get_targets()}

    @app.put("/api/targets/{idx}")
    async def update_target(idx: int, request: Request):
        data = await safe_json(request)
        targets = config.get("targets") or []
        if idx < 0 or idx >= len(targets):
            return JSONResponse({"error": "invalid index"}, status_code=404)
        targets[idx].update(data)
        config.set("targets", targets)
        transport.update_targets(targets)
        logger.info(f"Target updated: {targets[idx]['name']}")
        return {"ok": True, "targets": transport.get_targets()}

    @app.delete("/api/targets/{idx}")
    async def delete_target(idx: int):
        targets = config.get("targets") or []
        if idx < 0 or idx >= len(targets):
            return JSONResponse({"error": "invalid index"}, status_code=404)
        removed = targets.pop(idx)
        config.set("targets", targets)
        transport.update_targets(targets)
        logger.info(f"Target removed: {removed['name']}")
        return {"ok": True, "targets": transport.get_targets()}

    # ── Transport settings ─────────────────────────────────────
    @app.get("/api/transport")
    async def get_transport():
        return config.get("transport")

    @app.put("/api/transport")
    async def update_transport(request: Request):
        data = await safe_json(request)
        config.set("transport", data)
        logger.info(f"Transport updated: {data}")
        return config.get("transport")

    # ── Logs (in-memory ring) ──────────────────────────────────
    @app.get("/api/logs")
    async def get_logs_endpoint():
        return {"logs": get_logs(100)}

    # ── OSC test injection (manual band/trigger drive) ─────────
    @app.get("/api/osc/state")
    async def osc_snapshot():
        if osc_state is None:
            return {}
        # Snapshot at the engine's current frame clock so the envelope
        # state is read at the same instant the renderer would see it.
        return osc_state.snapshot(engine.time_ms())

    @app.post("/api/osc/band/{name}")
    async def osc_test_band(name: str, request: Request):
        if osc_state is None:
            return JSONResponse({"error": "osc disabled"}, status_code=503)
        if name not in ("low", "mid", "high"):
            return JSONResponse({"error": "invalid band"}, status_code=400)
        body = await safe_json(request)
        osc_state.set_band(name, float(body.get("value", 0.0)))
        return {"ok": True}

    @app.post("/api/osc/trigger/{name}")
    async def osc_test_trigger(name: str, request: Request):
        if osc_state is None:
            return JSONResponse({"error": "osc disabled"}, status_code=503)
        body = await safe_json(request)
        osc_state.fire_trigger(name, velocity=float(body.get("velocity", 1.0)),
                               t_ms=engine.time_ms())
        return {"ok": True}
