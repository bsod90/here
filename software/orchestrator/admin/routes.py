"""FastAPI admin panel routes."""
import asyncio
import logging
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from config import get_defaults

AP_CON = "here-debug-ap"


def _ap_state() -> dict:
    """Return AP profile presence + activation state."""
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "NAME,DEVICE,STATE", "con", "show"],
            timeout=2,
        ).decode()
    except Exception:
        return {"defined": False, "active": False}
    defined = False
    active = False
    for line in out.splitlines():
        parts = line.split(":")
        if parts and parts[0] == AP_CON:
            defined = True
            if len(parts) >= 3 and parts[2] == "activated":
                active = True
    return {"defined": defined, "active": active}

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


def create_app(config, engine, transport, telemetry=None, sim_bus=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Hand the running asyncio loop to the simulator bus so the
        # (sync) animation thread can dispatch broadcasts onto it.
        if sim_bus is not None:
            sim_bus.attach_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(title="HERE Admin", lifespan=lifespan)

    static_dir = Path(__file__).parent / "static"
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
            # The simulator client doesn't send anything; we just hold
            # the socket open and serve frames from the broadcaster.
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await sim_bus.unregister(ws)

    # ── Simulator static UI — mounted at /sim/, populated by install.sh
    # from software/simulator/public/.
    sim_dir = Path("/opt/here/sim")
    if not sim_dir.exists():
        # local dev: try the repo path relative to this file
        sim_dir = Path(__file__).resolve().parents[3] / "simulator" / "public"
    if sim_dir.exists():
        app.mount("/sim", StaticFiles(directory=str(sim_dir), html=True), name="sim")
        logger.info(f"Simulator UI mounted at /sim/ from {sim_dir}")
    else:
        logger.warning(f"Simulator UI directory not found ({sim_dir}); /sim tab will 404")

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
        if mode not in ("breathing", "standby", "debug", "off"):
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

    # ── Telemetry ───────────────────────────────────────────
    @app.get("/api/telemetry")
    async def get_telemetry():
        if telemetry is None:
            return {}
        return telemetry.snapshot()

    @app.get("/api/telemetry/temp-history")
    async def get_temp_history():
        if telemetry is None:
            return {"samples": []}
        return {"samples": telemetry.temp_history()}

    # ── Field-debug AP toggle ───────────────────────────────
    # The AP and the home WiFi STA can't safely run on the same wlan0
    # vif at the same time, so the AP profile is dormant by default.
    # Activating it WILL drop the home WiFi connection — that's the
    # whole point in the field. The dashboard shows a confirmation.
    @app.get("/api/ap")
    async def ap_status():
        return _ap_state()

    @app.post("/api/ap/up")
    async def ap_up():
        try:
            subprocess.run(
                ["nmcli", "con", "up", AP_CON],
                check=True, timeout=10,
                capture_output=True,
            )
            logger.warning("Field-debug AP brought up — home WiFi will drop")
            return _ap_state()
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                {"error": "nmcli failed", "stderr": e.stderr.decode(errors="ignore")},
                status_code=500,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/ap/down")
    async def ap_down():
        try:
            subprocess.run(
                ["nmcli", "con", "down", AP_CON],
                check=True, timeout=10,
                capture_output=True,
            )
            logger.info("Field-debug AP taken down")
            return _ap_state()
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                {"error": "nmcli failed", "stderr": e.stderr.decode(errors="ignore")},
                status_code=500,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    return app
