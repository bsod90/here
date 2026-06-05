"""Nadia's Playground routes — isolated `/api/playground/*` API.

Backs the Playground admin tab: the seconds-timeline, per-animation
trigger buttons, ocean toggle, recording upload + play. Kept self-
contained so it can't affect the rest of the app. See
docs/nadia_playground.md and playground.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ._shared import safe_json

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def register(app: FastAPI, playground, audio, config, engine) -> None:
    def _disabled():
        return JSONResponse({"error": "playground disabled"}, status_code=503)

    @app.get("/api/playground")
    async def playground_snapshot():
        if playground is None:
            return _disabled()
        return playground.snapshot()

    @app.put("/api/playground")
    async def playground_set_timeline(request: Request):
        if playground is None:
            return _disabled()
        body = await safe_json(request)
        if "timeline" in body and isinstance(body["timeline"], list):
            playground.set_timeline(body["timeline"])
        return playground.snapshot()

    @app.post("/api/playground/trigger/{anim_id}")
    async def playground_trigger(anim_id: str):
        if playground is None:
            return _disabled()
        engine.mode = "playground"          # ensure her mode is showing
        playground.trigger(anim_id)
        return playground.snapshot()

    @app.post("/api/playground/play")
    async def playground_play(request: Request):
        if playground is None:
            return _disabled()
        body = await safe_json(request)
        engine.mode = "playground"
        playground.play(with_recording=bool(body.get("with_recording", False)))
        return playground.snapshot()

    @app.post("/api/playground/stop")
    async def playground_stop():
        if playground is None:
            return _disabled()
        playground.stop()
        return playground.snapshot()

    # ── Ocean backdrop (delegates to the shared AudioPlayer) ─────────
    @app.post("/api/playground/ocean")
    async def playground_ocean(request: Request):
        if audio is None:
            return JSONResponse({"error": "audio disabled"}, status_code=503)
        body = await safe_json(request)
        enabled = bool(body.get("enabled", False))
        vol = body.get("volume")
        audio.set_backdrop(enabled=enabled,
                           volume=(float(vol) if vol is not None else None))
        persist = {"backdrop_enabled": enabled}
        if vol is not None:
            persist["backdrop_volume"] = max(0.0, min(1.0, float(vol)))
        config.set("audio", persist)
        return audio.snapshot()

    # ── Recording: upload (raw body) + play/stop ─────────────────────
    @app.post("/api/playground/recording")
    async def playground_upload(request: Request):
        if playground is None:
            return _disabled()
        name = request.query_params.get("name", "recording.wav")
        name = _SAFE_NAME.sub("_", name).lstrip(".") or "recording.wav"
        if not name.lower().endswith((".mp3", ".wav")):
            return JSONResponse({"error": "only .mp3 or .wav"}, status_code=400)
        data = await request.body()
        if not data:
            return JSONResponse({"error": "empty upload"}, status_code=400)
        media_dir = Path((config.get("audio") or {}).get("media_dir", "/opt/here/media"))
        dest_dir = media_dir / "playground"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / name).write_bytes(data)
        pg = config.get("playground") or {}
        pg["recording_file"] = name
        config.set("playground", pg)
        return playground.snapshot()

    @app.post("/api/playground/recording/play")
    async def playground_recording_play():
        if playground is None:
            return _disabled()
        playground.play_recording()
        return playground.snapshot()

    @app.post("/api/playground/recording/stop")
    async def playground_recording_stop():
        if playground is None:
            return _disabled()
        playground.stop_recording()
        return playground.snapshot()
