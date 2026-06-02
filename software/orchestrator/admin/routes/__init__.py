"""FastAPI admin panel — composition root.

Each domain (scene/MIDI, scale, telemetry, AP) lives in its own
submodule; this file wires them into the FastAPI app and keeps the
small mode/status/targets/transport/osc/logs endpoints inline.

Architectural notes:
  * `create_app` is a thin closure. Business logic lives in the owning
    services (Scene, ScaleSensor, TelemetryHistory…), not here.
  * Submodules each expose `register(app, *services)` and return None.
    They never share state with each other through this file.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from config import get_defaults
from animation_engine import MODE_REGISTRY

from ._shared import LogHandler, get_logs, safe_json, NoCacheStaticFiles
from . import scene as scene_routes
from . import scale as scale_routes
from . import telemetry as telemetry_routes
from . import ap as ap_routes
from . import audio as audio_routes

# Re-export so existing `from admin.routes import create_app, LogHandler`
# import paths keep working without any caller edits.
__all__ = ["create_app", "LogHandler"]


logger = logging.getLogger(__name__)


def create_app(config, engine, transport, telemetry=None, sim_bus=None,
               osc_state=None, scene=None, sequence_store=None,
               patch_store=None, tap_tracker=None, scale=None,
               telemetry_history=None, audio=None) -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Hand the running asyncio loop to the simulator bus so the
        # (sync) animation thread can dispatch broadcasts onto it.
        if sim_bus is not None:
            sim_bus.attach_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(title="HERE Admin", lifespan=lifespan)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ── Simulator WebSocket — must be registered BEFORE the /sim mount
    # so FastAPI's router catches it instead of the static handler.
    @app.websocket("/sim/ws")
    async def sim_ws(ws: WebSocket):
        await ws.accept()
        if sim_bus is None:
            await ws.close(code=1011)
            return
        await sim_bus.register(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await sim_bus.unregister(ws)

    # Simulator static UI — populated by install.sh from software/simulator/public/.
    sim_dir = Path("/opt/here/sim")
    if not sim_dir.exists():
        # local dev: try the repo path relative to this file
        sim_dir = Path(__file__).resolve().parents[4] / "simulator" / "public"
    if sim_dir.exists():
        app.mount("/sim", NoCacheStaticFiles(directory=str(sim_dir), html=True), name="sim")
        logger.info(f"Simulator UI mounted at /sim/ from {sim_dir}")
    else:
        logger.warning(f"Simulator UI directory not found ({sim_dir}); /sim tab will 404")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (static_dir / "index.html").read_text()

    # ── Domain submodules ──────────────────────────────────────
    scene_routes.register(app, config, engine, scene, sequence_store,
                          patch_store, tap_tracker)
    scale_routes.register(app, scale)
    telemetry_routes.register(app, telemetry, telemetry_history)
    ap_routes.register(app)
    audio_routes.register(app, audio, config)

    # ── Inline: config / defaults ──────────────────────────────
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

    # ── Inline: mode ───────────────────────────────────────────
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

    # ── Inline: sensor simulation ──────────────────────────────
    @app.post("/api/sensor/{state}")
    async def simulate_sensor(state: str):
        if state == "occupied":
            engine.mode = "breathing"
            config.set("mode", "breathing")
            logger.info("Sensor: bench occupied → breathing")
        elif state == "empty":
            engine.mode = "standby"
            config.set("mode", "standby")
            logger.info("Sensor: bench empty → standby")
        else:
            return JSONResponse({"error": "invalid state"}, status_code=400)
        return {"sensor": state, "mode": engine.mode}

    # ── Inline: status ─────────────────────────────────────────
    @app.get("/api/status")
    async def get_status():
        return {
            "mode": engine.mode,
            "fps": engine.actual_fps,
            "uptime_s": engine.uptime_seconds,
            "power": engine.power_estimate,
        }

    # ── Inline: targets (WLED endpoints) ───────────────────────
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

    # ── Inline: transport settings ─────────────────────────────
    @app.get("/api/transport")
    async def get_transport():
        return config.get("transport")

    @app.put("/api/transport")
    async def update_transport(request: Request):
        data = await safe_json(request)
        config.set("transport", data)
        logger.info(f"Transport updated: {data}")
        return config.get("transport")

    # ── Inline: logs (in-memory ring) ──────────────────────────
    @app.get("/api/logs")
    async def get_logs_endpoint():
        return {"logs": get_logs(100)}

    # ── Inline: OSC test injection (manual band/trigger drive) ─
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
        osc_state.fire_trigger(name, velocity=float(body.get("velocity", 1.0)), t_ms=engine.time_ms())
        return {"ok": True}

    return app
