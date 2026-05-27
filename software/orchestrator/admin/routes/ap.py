"""Field-debug WiFi-AP toggle routes.

The AP and the home-WiFi STA can't safely share wlan0 at the same time
on RPi OS Trixie, so the AP profile is dormant by default. Activating
it WILL drop the home WiFi — that's intentional in the field. The
dashboard surfaces a confirmation."""
from __future__ import annotations

import logging
import subprocess

from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

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


def register(app: FastAPI) -> None:
    @app.get("/api/ap")
    async def ap_status():
        return _ap_state()

    @app.post("/api/ap/up")
    async def ap_up():
        try:
            subprocess.run(
                ["nmcli", "con", "up", AP_CON],
                check=True, timeout=10, capture_output=True,
            )
            logger.warning("Field-debug AP brought up — home WiFi will drop")
            return _ap_state()
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                {"error": "nmcli failed",
                 "stderr": e.stderr.decode(errors="ignore")},
                status_code=500,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/ap/down")
    async def ap_down():
        try:
            subprocess.run(
                ["nmcli", "con", "down", AP_CON],
                check=True, timeout=10, capture_output=True,
            )
            logger.info("Field-debug AP taken down")
            return _ap_state()
        except subprocess.CalledProcessError as e:
            return JSONResponse(
                {"error": "nmcli failed",
                 "stderr": e.stderr.decode(errors="ignore")},
                status_code=500,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
