"""Simulator broadcast bus.

The animation engine renders frames on a worker thread and hands each
one to the LED transport (UDP→WLED). To let the simulator UI mirror
exactly what WLED sees, we also push every frame to any WebSocket
clients connected at /sim/ws.

The bridge across the thread/asyncio boundary is `run_coroutine_threadsafe`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SimulatorBus:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._latest: Optional[bytes] = None
        self._lock = asyncio.Lock()

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at FastAPI startup so push_frame (running on the
        animation thread) can schedule sends on the asyncio loop.
        """
        self._loop = loop

    # ------------------------------------------------------------------
    # WebSocket lifecycle (called from FastAPI handlers)
    # ------------------------------------------------------------------
    async def register(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)
        # Prime the new client with the most recent frame so it doesn't
        # render a black scene until the next animation tick.
        if self._latest is not None:
            try:
                await ws.send_bytes(self._latest)
            except Exception:
                await self.unregister(ws)

    async def unregister(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    # ------------------------------------------------------------------
    # Producer (animation thread → asyncio loop)
    # ------------------------------------------------------------------
    def push_frame(self, frame: bytes | bytearray) -> None:
        """Called from the animation engine. Cheap, non-blocking."""
        # Capture latest unconditionally so freshly-connecting clients
        # always get the current state.
        data = bytes(frame)
        self._latest = data

        if self._loop is None or not self._clients:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._broadcast(data), self._loop)
        except RuntimeError:
            # Loop closed during shutdown — ignore.
            pass

    async def _broadcast(self, data: bytes) -> None:
        # Snapshot the client set under the lock, but send outside it
        # so a slow client doesn't block fast ones.
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_bytes(data)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
