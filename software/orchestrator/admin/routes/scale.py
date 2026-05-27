"""Bench-scale (HX711) routes — read snapshot, tweak settings,
tare/calibrate."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ._shared import safe_json


def register(app: FastAPI, scale) -> None:
    @app.get("/api/scale")
    async def scale_snapshot():
        if scale is None:
            return JSONResponse({"error": "scale disabled"}, status_code=503)
        return scale.snapshot()

    @app.put("/api/scale")
    async def scale_update(request: Request):
        if scale is None:
            return JSONResponse({"error": "scale disabled"}, status_code=503)
        body = await safe_json(request)
        scale.update_settings(**body)
        return scale.snapshot()

    @app.post("/api/scale/tare")
    async def scale_tare():
        if scale is None:
            return JSONResponse({"error": "scale disabled"}, status_code=503)
        return scale.tare()

    @app.post("/api/scale/calibrate")
    async def scale_calibrate(request: Request):
        if scale is None:
            return JSONResponse({"error": "scale disabled"}, status_code=503)
        body = await safe_json(request)
        try:
            grams = float(body.get("grams", 0))
        except (TypeError, ValueError):
            return JSONResponse({"error": "grams must be a number"}, status_code=400)
        try:
            return scale.calibrate(grams)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
