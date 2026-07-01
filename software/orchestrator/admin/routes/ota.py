"""OTA routes — firmware download (with version gating), status, and triggers.

The boards pull their image via HTTPUpdate (GET); we 304 if they're already on
the staged version, else stream the .bin. /api/ota/status shows available vs
flashed versions (flashed comes live from bench_link) plus recent check-ins.
/api/ota/update tells a board to enter OTA mode over the two-way link.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, Response

from ._shared import safe_json


def _serve(ota, kind: str, request: Request):
    avail = ota.available_version()
    path = ota.binary_path(kind)
    cur_hdr = request.headers.get("x-ESP32-version")
    try:
        cur = int(cur_hdr) if cur_hdr is not None else None
    except ValueError:
        cur = None
    if path is None or avail is None:
        ota.record_checkin(kind, cur, "no firmware staged")
        return JSONResponse({"error": "no firmware staged"}, status_code=404)
    if cur is not None and cur >= avail:
        ota.record_checkin(kind, cur, f"up-to-date (v{avail})")
        return Response(status_code=304)
    ota.record_checkin(kind, cur, f"served v{avail}")
    return FileResponse(str(path), media_type="application/octet-stream",
                        filename=path.name)


def register(app: FastAPI, ota, bench_link, config=None) -> None:
    @app.get("/api/ota/firmware/leg/{node}")
    async def ota_leg(node: int, request: Request):
        return _serve(ota, f"leg{node}", request)

    @app.get("/api/ota/firmware/receiver")
    async def ota_receiver(request: Request):
        return _serve(ota, "receiver", request)

    @app.get("/api/ota/status")
    async def ota_status():
        flashed = {"leg1": None, "leg2": None, "receiver": None}
        if bench_link is not None:
            snap = bench_link.snapshot()
            nodes = snap.get("nodes", {})
            flashed["leg1"] = (nodes.get("1") or {}).get("fw")
            flashed["leg2"] = (nodes.get("2") or {}).get("fw")
            flashed["receiver"] = (snap.get("receiver") or {}).get("fw")
        return {
            "available": ota.available_version(),
            "flashed": flashed,
            "binaries": ota.binaries_present(),
            "checkins": ota.checkins(),
        }

    @app.post("/api/ota/update")
    async def ota_update(request: Request):
        if bench_link is None:
            return JSONResponse({"error": "link unavailable"}, status_code=503)
        body = await safe_json(request)
        target = str(body.get("target", ""))
        sent: dict = {}
        if target in ("leg1", "all"):
            sent["leg1"] = bench_link.send_ota_leg(0)
        if target in ("leg2", "all"):
            sent["leg2"] = bench_link.send_ota_leg(1)
        if target in ("receiver", "all"):
            sent["receiver"] = bench_link.send_ota_receiver()
        if not sent:
            return JSONResponse({"error": "unknown target"}, status_code=400)
        return {"sent": sent}

    @app.get("/api/bench/cutoff")
    async def bench_cutoff_get():
        cfg = (config.get("bench_link") if config else {}) or {}
        applied = {}
        if bench_link is not None:
            nodes = bench_link.snapshot().get("nodes", {})
            applied = {f"leg{int(k)}": (v or {}).get("cutoff_mv")
                       for k, v in nodes.items()}
        return {"mv": int(cfg.get("cutoff_mv", 3500)), "applied": applied}

    @app.post("/api/bench/cutoff")
    async def bench_cutoff_set(request: Request):
        if bench_link is None or config is None:
            return JSONResponse({"error": "link unavailable"}, status_code=503)
        body = await safe_json(request)
        try:
            mv = int(round(float(body.get("mv"))))
        except (TypeError, ValueError):
            return JSONResponse({"error": "mv must be a number"}, status_code=400)
        if not (3000 <= mv <= 4000):
            return JSONResponse({"error": "mv out of range (3000–4000)"},
                                status_code=400)
        config.set("bench_link", {"cutoff_mv": mv})
        # Push to both legs; the receiver queues until each leg next wakes, and
        # the legs persist it in NVS. Idempotent.
        sent = {"leg1": bench_link.send_cutoff(0, mv),
                "leg2": bench_link.send_cutoff(1, mv)}
        return {"mv": mv, "sent": sent}

    @app.post("/api/ota/reboot")
    async def ota_reboot(request: Request):
        if bench_link is None:
            return JSONResponse({"error": "link unavailable"}, status_code=503)
        body = await safe_json(request)
        target = str(body.get("target", ""))
        sent: dict = {}
        if target in ("leg1", "all"):
            sent["leg1"] = bench_link.send_reboot_leg(0)
        if target in ("leg2", "all"):
            sent["leg2"] = bench_link.send_reboot_leg(1)
        if target in ("receiver", "all"):
            sent["receiver"] = bench_link.send_reboot_receiver()
        if not sent:
            return JSONResponse({"error": "unknown target"}, status_code=400)
        return {"sent": sent}
