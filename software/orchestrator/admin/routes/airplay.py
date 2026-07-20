"""AirPlay receiver routes — status, toggle/settings, and a test-pattern
injection that exercises the whole receive path without a phone."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ._shared import safe_json


def register(app: FastAPI, airplay, config) -> None:
    @app.get("/api/airplay")
    async def airplay_get():
        if airplay is None:
            return JSONResponse({"error": "airplay disabled"}, status_code=503)
        return airplay.status()

    @app.put("/api/airplay")
    async def airplay_put(request: Request):
        if airplay is None:
            return JSONResponse({"error": "airplay disabled"}, status_code=503)
        body = await safe_json(request)
        patch: dict = {}
        if "enabled" in body:
            patch["enabled"] = bool(body["enabled"])
        if "name" in body:
            name = str(body["name"]).strip()
            if not name or len(name) > 40:
                return JSONResponse({"error": "name must be 1-40 chars"},
                                    status_code=400)
            patch["name"] = name
        if "volume" in body:
            try:
                patch["volume"] = max(0.0, min(1.0, float(body["volume"])))
            except (TypeError, ValueError):
                return JSONResponse({"error": "volume must be a number"},
                                    status_code=400)
        if "video_decoder" in body:
            patch["video_decoder"] = str(body["video_decoder"]).strip()
        if patch:
            config.set("airplay", patch)
            airplay.poke()          # converge the uxplay process now
        return airplay.status()

    @app.post("/api/airplay/test")
    async def airplay_test(request: Request):
        if airplay is None:
            return JSONResponse({"error": "airplay disabled"}, status_code=503)
        body = await safe_json(request)
        seconds = body.get("seconds", 5)
        with_audio = bool(body.get("audio", False))
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return JSONResponse({"error": "seconds must be a number"},
                                status_code=400)
        if not airplay.start_test(seconds=seconds, audio=with_audio):
            return JSONResponse(
                {"error": "receiver must be enabled to run a test"},
                status_code=409)
        return airplay.status()
