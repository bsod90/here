"""Nadia's Playground routes — isolated `/api/playground/*` API.

Backs the Playground admin tab: the seconds-timeline, per-animation
trigger buttons, ocean toggle, recording upload + play. Kept self-
contained so it can't affect the rest of the app. See
docs/nadia_playground.md and playground.py.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from ._shared import safe_json

logger = logging.getLogger(__name__)

# Waveform overview: decode the audio cheaply (mono, low rate) and reduce to
# this many max-abs buckets for the editor background. Cached to disk.
_WAVE_BUCKETS = 1600
_WAVE_RATE = 2000


def _compute_peaks(path: Path) -> dict:
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
           "-ar", str(_WAVE_RATE), "-ac", "1", "-f", "f32le", "pipe:1"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=True)
    a = np.frombuffer(r.stdout, dtype=np.float32)
    if a.size == 0:
        return {"peaks": [], "duration_sec": 0.0}
    dur = a.size / float(_WAVE_RATE)
    n = min(_WAVE_BUCKETS, a.size)
    pad = (-a.size) % n
    if pad:
        a = np.concatenate([a, np.zeros(pad, np.float32)])
    buckets = np.abs(a).reshape(n, -1).max(axis=1)
    peak = float(buckets.max()) or 1.0
    return {"peaks": [round(float(x) / peak, 3) for x in buckets],
            "duration_sec": round(dur, 2)}


def _waveform(path: Path) -> dict:
    """Peaks for `path`, cached next to it keyed by (size, mtime)."""
    cache = path.with_suffix(path.suffix + ".peaks.json")
    try:
        stat = path.stat()
        sig = f"{stat.st_size}:{int(stat.st_mtime)}"
        if cache.is_file():
            cached = json.loads(cache.read_text())
            if cached.get("sig") == sig:
                return {"peaks": cached["peaks"], "duration_sec": cached["duration_sec"]}
        data = _compute_peaks(path)
        try:
            cache.write_text(json.dumps({"sig": sig, **data}))
        except OSError:
            pass
        return data
    except Exception:
        logger.exception("playground: waveform failed for %s", path)
        return {"peaks": [], "duration_sec": 0.0}


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
        try:
            start_sec = max(0.0, float(body.get("start_sec", 0.0)))
        except (TypeError, ValueError):
            start_sec = 0.0
        playground.play(with_recording=bool(body.get("with_recording", False)),
                        start_sec=start_sec)
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

    # ── Meditation selection (which event-track the editor edits) ────
    @app.post("/api/playground/select/{med_id}")
    async def playground_select(med_id: str):
        if playground is None:
            return _disabled()
        if not playground.select(med_id):
            return JSONResponse({"error": "unknown meditation"}, status_code=404)
        return playground.snapshot()

    # ── Waveform overview for the selected (or given) meditation ─────
    @app.get("/api/playground/waveform/{med_id}")
    async def playground_waveform(med_id: str):
        if playground is None:
            return _disabled()
        med = next((m for m in playground.meditations() if m["id"] == med_id), None)
        if med is None or not med.get("present"):
            return JSONResponse({"error": "no audio"}, status_code=404)
        media_dir = Path((config.get("audio") or {}).get("media_dir", "/opt/here/media"))
        path = media_dir / med["file"]
        data = await run_in_threadpool(_waveform, path)
        return {"id": med_id, **data}

    # ── Transcript (time-aligned words) for the given meditation ─────
    # Sidecar file next to the audio: <file>.transcript.json, produced
    # offline (whisper) and rsynced with the media dir. Schema:
    # {"language": "en", "segments": [{"start": s, "end": s, "text": ...}]}
    @app.get("/api/playground/transcript/{med_id}")
    async def playground_transcript(med_id: str):
        if playground is None:
            return _disabled()
        med = next((m for m in playground.meditations() if m["id"] == med_id), None)
        if med is None or not med.get("present"):
            return JSONResponse({"error": "no audio"}, status_code=404)
        media_dir = Path((config.get("audio") or {}).get("media_dir", "/opt/here/media"))
        path = media_dir / med["file"]
        tpath = path.with_suffix(path.suffix + ".transcript.json")
        if not tpath.is_file():
            return JSONResponse({"error": "no transcript"}, status_code=404)
        try:
            data = json.loads(tpath.read_text())
        except (OSError, ValueError):
            logger.exception("playground: unreadable transcript for %s", med_id)
            return JSONResponse({"error": "bad transcript"}, status_code=500)
        return {"id": med_id, "language": data.get("language"),
                "segments": data.get("segments") or []}

    # ── Recording (the selected meditation's audio) play/stop ────────
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
