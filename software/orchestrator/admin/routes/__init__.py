"""FastAPI admin panel — composition root.

Each domain lives in its own submodule; this file only wires them into
the FastAPI app and serves the static UI / simulator WebSocket.

Architectural notes:
  * `create_app` is pure composition. Business logic lives in the owning
    services (Scene, ScaleSensor, TelemetryHistory…), endpoint plumbing
    in the submodules (core, scene, scale, telemetry, ap, audio,
    playground, wled).
  * Submodules each expose `register(app, *services)` and return None.
    They never share state with each other through this file.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from ._shared import LogHandler, NoCacheStaticFiles
from . import core as core_routes
from . import scene as scene_routes
from . import scale as scale_routes
from . import telemetry as telemetry_routes
from . import ap as ap_routes
from . import audio as audio_routes
from . import playground as playground_routes
from . import wled as wled_routes

# Re-export so existing `from admin.routes import create_app, LogHandler`
# import paths keep working without any caller edits.
__all__ = ["create_app", "LogHandler"]


logger = logging.getLogger(__name__)


def create_app(config, engine, transport, telemetry=None, sim_bus=None,
               osc_state=None, scene=None, sequence_store=None,
               patch_store=None, tap_tracker=None, scale=None,
               telemetry_history=None, audio=None, playground=None) -> FastAPI:

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
        # no-store so a normal reload always re-fetches the entry page and
        # picks up the latest admin.js?v=NN — otherwise a cached index keeps
        # pointing at a stale script version (and stale bug fixes never load).
        return HTMLResponse((static_dir / "index.html").read_text(),
                            headers={"Cache-Control": "no-store"})

    # ── Domain submodules ──────────────────────────────────────
    core_routes.register(app, config, engine, transport,
                         scene=scene, osc_state=osc_state)
    scene_routes.register(app, config, engine, scene, sequence_store,
                          patch_store, tap_tracker)
    scale_routes.register(app, scale)
    telemetry_routes.register(app, telemetry, telemetry_history)
    ap_routes.register(app)
    audio_routes.register(app, audio, config)
    playground_routes.register(app, playground, audio, config, engine)
    wled_routes.register(app, config)

    return app
