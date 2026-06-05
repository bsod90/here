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

        # Track identified by `track` (defaults to "ocean" so the legacy
        # backdrop_* fields keep working). Accept {enabled, volume} or the
        # legacy {backdrop_enabled, backdrop_volume}.
        name = body.get("track", "ocean")
        enabled = body.get("enabled", body.get("backdrop_enabled"))
        volume = body.get("volume", body.get("backdrop_volume"))

        vol_val = None
        if volume is not None:
            try:
                vol_val = max(0.0, min(1.0, float(volume)))
            except (TypeError, ValueError):
                return JSONResponse({"error": "volume must be a number"},
                                    status_code=400)
        en_val = None if enabled is None else bool(enabled)

        if en_val is None and vol_val is None:
            return audio.snapshot()

        # Apply both in one call so volume + enable don't ping-pong.
        audio.set_track(name, enabled=en_val, volume=vol_val)

        # Persist this track's changed fields so they survive a restart.
        patch = {}
        if en_val is not None:
            patch["enabled"] = en_val
        if vol_val is not None:
            patch["volume"] = vol_val
        if patch:
            config.set("audio", {"tracks": {name: patch}})
        return audio.snapshot()
