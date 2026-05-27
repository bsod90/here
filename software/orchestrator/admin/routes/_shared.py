"""Helpers shared by the route submodules.

Kept tiny — anything more substantial should live in its owning service
(scale.py, telemetry_history.py, scene/scene.py) rather than in the HTTP
layer."""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

# Shared logger for the routes package. Submodules use their own
# `logging.getLogger(__name__)` for module-attribution in log lines;
# this one is for top-level startup messages.
logger = logging.getLogger("admin.routes")


# ── Log capture (top bar's Logs tab) ────────────────────────────
_log_buffer: list[str] = []
_MAX_LOGS = 200


class LogHandler(logging.Handler):
    """Stdlib logging Handler that buffers records into a ring of the
    last `_MAX_LOGS` lines. The Logs tab polls /api/logs to render the
    buffer."""

    def emit(self, record):
        msg = self.format(record)
        _log_buffer.append(msg)
        if len(_log_buffer) > _MAX_LOGS:
            _log_buffer.pop(0)


def get_logs(limit: int = 100) -> list[str]:
    return _log_buffer[-limit:]


# ── JSON helpers ────────────────────────────────────────────────
async def safe_json(request: Request) -> dict:
    """Read JSON body, returning {} on malformed / empty payloads so
    endpoints can `body.get(...)` defensively without 500ing."""
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ── Static-files variant ────────────────────────────────────────
class NoCacheStaticFiles(StaticFiles):
    """Serve static files with Cache-Control: no-cache so deploys take
    effect on the next refresh without manual hard-reloads. The
    simulator UI is small, so the revalidation cost is negligible."""

    async def get_response(self, path, scope):
        response: Response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response
