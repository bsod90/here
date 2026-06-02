"""Audio routes — backdrop loop on/off + volume, plus the monitor stream.

Mirrors the scale routes pattern: GET returns a snapshot, PUT accepts a
partial patch and applies changes via the AudioPlayer's public API.
Any state change is also persisted to config so it survives a restart.

`GET /api/audio/monitor.mp3` is a never-ending MP3 stream: a bit-identical
copy of what the bench speakers are playing (post volume/mix), which the
Simulator tab plays in an <audio> element on demand."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ._shared import safe_json


def register(app: FastAPI, audio, config) -> None:
    @app.get("/api/audio/monitor.mp3")
    async def audio_monitor():
        if audio is None:
            return JSONResponse({"error": "audio disabled"}, status_code=503)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        sid = audio.add_listener(loop, queue)

        async def gen():
            try:
                while True:
                    chunk = await queue.get()
                    if chunk is None:   # engine stopped — end the stream
                        break
                    yield chunk
            finally:
                audio.remove_listener(sid)

        # no-store so the browser never serves a stale/closed stream from
        # cache; the engine produces data only while the backdrop is on.
        return StreamingResponse(gen(), media_type="audio/mpeg",
                                 headers={"Cache-Control": "no-store"})

    @app.get("/api/audio")
    async def audio_snapshot():
        if audio is None:
            return JSONResponse({"error": "audio disabled"}, status_code=503)
        return audio.snapshot()

    @app.put("/api/audio")
    async def audio_update(request: Request):
        if audio is None:
            return JSONResponse({"error": "audio disabled"}, status_code=503)
        body = await safe_json(request)
        # Pull the two known fields; ignore anything else so we don't
        # silently accept typos.
        changes = {}
        if "backdrop_enabled" in body:
            changes["backdrop_enabled"] = bool(body["backdrop_enabled"])
        if "backdrop_volume" in body:
            try:
                changes["backdrop_volume"] = max(0.0, min(1.0,
                    float(body["backdrop_volume"])))
            except (TypeError, ValueError):
                return JSONResponse({"error": "backdrop_volume must be a number"},
                                    status_code=400)
        if not changes:
            return audio.snapshot()
        # Apply to the player (combine in one call so volume + enable
        # together don't cause a stop/start ping-pong).
        audio.set_backdrop(
            enabled=changes.get("backdrop_enabled",
                                audio.snapshot()["backdrop_enabled"]),
            volume=changes.get("backdrop_volume"),
        )
        # Persist so it survives a restart.
        config.set("audio", changes)
        return audio.snapshot()
