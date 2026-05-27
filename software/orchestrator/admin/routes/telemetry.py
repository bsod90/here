"""Telemetry routes — system snapshot, temp history, per-minute rollup,
clock/NTP status."""
from __future__ import annotations

import subprocess
import time as _time

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def register(app: FastAPI, telemetry, telemetry_history) -> None:
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

    @app.get("/api/telemetry/history")
    async def telemetry_history_query(range: str = "24h"):
        """Per-minute rollup history. Accepts `Nh` / `Nm` / `Nd` / raw
        seconds (clamped 1 min to 14 d)."""
        if telemetry_history is None:
            return JSONResponse({"error": "telemetry history disabled"},
                                status_code=503)
        try:
            r = range.strip().lower()
            if r.endswith("h"):
                seconds = int(float(r[:-1]) * 3600)
            elif r.endswith("m"):
                seconds = int(float(r[:-1]) * 60)
            elif r.endswith("d"):
                seconds = int(float(r[:-1]) * 86400)
            else:
                seconds = int(float(r))
        except (TypeError, ValueError):
            return JSONResponse({"error": "bad range"}, status_code=400)
        seconds = max(60, min(seconds, 14 * 86400))
        return telemetry_history.query(seconds)

    @app.get("/api/telemetry/clock")
    async def telemetry_clock():
        """Server time + NTP status so the dashboard can warn if the
        Pi's clock is drifting."""
        out: dict = {"server_unix_ts": int(_time.time())}
        try:
            raw = subprocess.check_output(
                ["timedatectl", "show", "--no-pager"], timeout=2).decode()
            parsed = {}
            for line in raw.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    parsed[k.strip()] = v.strip()
            out["ntp_enabled"] = parsed.get("NTP") == "yes"
            out["ntp_synchronized"] = parsed.get("NTPSynchronized") == "yes"
            out["timezone"] = parsed.get("Timezone")
            out["local_rtc"] = parsed.get("LocalRTC") == "yes"
        except Exception as e:
            out["error"] = str(e)
        return out
