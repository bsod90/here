"""FastAPI admin panel routes."""
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from config import get_defaults

logger = logging.getLogger(__name__)

# Ring buffer for log capture
_log_buffer: list[str] = []
_MAX_LOGS = 200


class LogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        _log_buffer.append(msg)
        if len(_log_buffer) > _MAX_LOGS:
            _log_buffer.pop(0)


def create_app(config, engine, transport) -> FastAPI:
    app = FastAPI(title="HERE Admin")

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (static_dir / "index.html").read_text()

    # ── Config ──────────────────────────────────────────────
    @app.get("/api/config")
    async def get_config():
        return config.get_all()

    @app.put("/api/config")
    async def update_config(request: Request):
        data = await request.json()
        for key, value in data.items():
            config.set(key, value)
        return {"ok": True}

    # ── Defaults ────────────────────────────────────────────
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

    # ── Mode ────────────────────────────────────────────────
    @app.post("/api/mode/{mode}")
    async def set_mode(mode: str):
        if mode not in ("breathing", "standby", "off"):
            return JSONResponse({"error": "invalid mode"}, status_code=400)
        config.set("mode", mode)
        engine.mode = mode
        logger.info(f"Mode changed to: {mode}")
        return {"mode": mode}

    # ── Sensor simulation ───────────────────────────────────
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

    # ── Status ──────────────────────────────────────────────
    @app.get("/api/status")
    async def get_status():
        return {
            "mode": engine.mode,
            "fps": engine.actual_fps,
            "uptime_s": engine.uptime_seconds,
            "power": engine.power_estimate,
        }

    # ── Targets ─────────────────────────────────────────────
    @app.get("/api/targets")
    async def get_targets():
        return transport.get_targets()

    @app.post("/api/targets")
    async def add_target(request: Request):
        data = await request.json()
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
        data = await request.json()
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

    # ── Transport settings ───────────────────────────────────
    @app.get("/api/transport")
    async def get_transport():
        return config.get("transport")

    @app.put("/api/transport")
    async def update_transport(request: Request):
        data = await request.json()
        config.set("transport", data)
        logger.info(f"Transport updated: {data}")
        return config.get("transport")

    # ── Logs ────────────────────────────────────────────────
    @app.get("/api/logs")
    async def get_logs():
        return {"logs": _log_buffer[-100:]}

    return app
