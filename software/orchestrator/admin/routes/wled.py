"""WLED reverse-proxy — re-serves the WLED UI/API/WebSocket under /wled/.

Topology: the WLED controller lives on the Pi's *ethernet* segment
(e.g. 192.168.10.20) and is NOT reachable from the browser's WiFi LAN —
only the Pi can reach it. So we proxy WLED's web UI + JSON API + live
WebSocket through this app under `/wled/`.

This works with zero HTML/JS rewriting because WLED's own UI is built
for sub-path hosting: its `onLoad()` inspects `window.location.pathname`,
and when served from a sub-path it sets `loc=true` and
`locip="<host>:<port>/wled"`. Every subsequent request goes through
`getURL("/json/si")` → `http://<host>/wled/json/si`, and the live socket
is `getURL("/ws").replace("http","ws")` → `ws://<host>/wled/ws`. All of
those land back on the routes below.

Pairs with the engine's `wled` mode (suppress_output=True): that mode
stops the DDP stream so WLED drops out of realtime override (after its
configured realtime timeout) and runs the effect picked in this UI.

Self-contained: only needs `config` (to find the WLED target IP). No
state shared with other route modules.
"""
from __future__ import annotations

import asyncio
import gzip
import logging
import urllib.error
import urllib.request

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse, Response

logger = logging.getLogger(__name__)

# Hop-by-hop request headers a proxy must not forward (RFC 7230 §6.1),
# plus content-length (urllib recomputes it from the body) and host
# (urllib derives it from the target URL).
_DROP_REQ = {
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding",
    "upgrade", "content-length",
    # Conditional-request validators. WLED serves common.js/settings with
    # `Cache-Control: no-cache` + a static ETag, so the browser revalidates
    # and WLED answers 304 Not Modified — handing the browser back its OLD,
    # un-rewritten copy (with a stale getURL → settings load the config
    # script from the wrong path → "Incomplete page data!"). Stripping these
    # forces a full 200 every time so our rewrite always reaches the browser.
    "if-none-match", "if-modified-since",
}
# Response headers we strip before relaying: hop-by-hop, framing (the
# Response layer recomputes content-length), content-type (passed back
# via media_type so it isn't duplicated), and the frame-blocking headers
# so the UI can live in our <iframe>.
_DROP_RESP = {
    "connection", "keep-alive", "transfer-encoding", "upgrade",
    "content-length", "content-type",
    "x-frame-options", "content-security-policy",
}

_PROXY_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

# WLED builds *every* URL (assets, JSON API, navigation, form actions, the
# live WebSocket) through its `getURL()` helper, which prepends
# `loc ? locproto+"//"+locip : ""`. When the UI is proxied under a sub-path,
# WLED derives `locip` from the *current page path* — fine for the single-
# page main UI, but on deeper pages (e.g. /wled/settings/leds) it doubles
# the path ("Incomplete page data!") or escapes back to our origin root
# (FastAPI's {"detail":"Not found"}). We sidestep all of that by rewriting
# getURL itself in the HTML/JS we relay: pin the base to "<origin>/wled" so
# every URL — at any depth — routes back through this proxy. WLED's source
# uses two param names (e/t), so we anchor on the shared prefix expression.
_GETURL_FROM = '(loc?locproto+"//"+locip:"")'
_GETURL_TO = '(location.protocol+"//"+location.host+"/wled")'


def _wled_host(config) -> str | None:
    """Host of the first enabled WLED target (IP without any CIDR suffix)."""
    targets = config.get("targets") or []
    for t in targets:
        if t.get("enabled", True) and t.get("ip"):
            return t["ip"].split("/")[0].strip()
    return targets[0]["ip"].split("/")[0].strip() if targets else None


def register(app: FastAPI, config) -> None:

    def _blocking_request(method: str, url: str, headers: dict, body: bytes):
        req = urllib.request.Request(url, data=(body or None), method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status, dict(resp.getheaders()), resp.read()
        except urllib.error.HTTPError as e:
            # WLED legitimately returns some 4xx (e.g. 404 for absent
            # presets) — relay them rather than masking as a proxy error.
            return e.code, dict(e.headers.items()), e.read()

    # ── WebSocket bridge: browser /wled/ws  ↔  WLED /ws ──────────────
    # Registered before the HTTP catch-all (different scope type, but
    # we mirror the sim_ws ordering convention).
    @app.websocket("/wled/ws")
    async def wled_ws(ws: WebSocket):
        host = _wled_host(config)
        await ws.accept()
        if not host:
            await ws.close(code=1011)
            return
        import websockets  # available in the venv; lazy import keeps
                           # module load cheap for callers that never hit /wled.
        try:
            async with websockets.connect(
                f"ws://{host}/ws", open_timeout=5, max_size=None,
                ping_interval=None,
            ) as upstream:

                async def client_to_wled():
                    while True:
                        msg = await ws.receive()
                        if msg["type"] == "websocket.disconnect":
                            break
                        if msg.get("text") is not None:
                            await upstream.send(msg["text"])
                        elif msg.get("bytes") is not None:
                            await upstream.send(msg["bytes"])

                async def wled_to_client():
                    async for m in upstream:
                        if isinstance(m, (bytes, bytearray)):
                            await ws.send_bytes(m)
                        else:
                            await ws.send_text(m)

                t1 = asyncio.create_task(client_to_wled())
                t2 = asyncio.create_task(wled_to_client())
                _, pending = await asyncio.wait(
                    {t1, t2}, return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
        except Exception as e:
            logger.info(f"WLED ws bridge closed: {e}")
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    # ── Bare /wled → /wled/ so WLED's onLoad sees the sub-path ───────
    @app.get("/wled")
    async def wled_root():
        return RedirectResponse("/wled/")

    # ── HTTP catch-all: everything else under /wled/ → WLED ──────────
    @app.api_route("/wled/{path:path}", methods=_PROXY_METHODS)
    async def wled_proxy(path: str, request: Request):
        host = _wled_host(config)
        if not host:
            return JSONResponse({"error": "no WLED target configured"},
                                status_code=503)
        qs = request.url.query
        url = f"http://{host}/{path}" + (f"?{qs}" if qs else "")
        body = await request.body()
        fwd = {k: v for k, v in request.headers.items()
               if k.lower() not in _DROP_REQ}
        try:
            status, headers, content = await asyncio.to_thread(
                _blocking_request, request.method, url, fwd, body)
        except Exception as e:
            logger.warning(f"WLED proxy error for {url}: {e}")
            return JSONResponse({"error": f"WLED unreachable: {e}"},
                                status_code=502)

        # Rewrite getURL() in HTML/JS so the UI stays inside /wled/ at any
        # depth. WLED gzips these, so decompress first and relay plain
        # (dropping Content-Encoding) — simpler than recompressing.
        ctype = (headers.get("Content-Type") or "").lower()
        if "text/html" in ctype or "javascript" in ctype:
            if "gzip" in (headers.get("Content-Encoding") or "").lower():
                content = gzip.decompress(content)
            text = content.decode("utf-8", "replace")
            if _GETURL_FROM in text:
                text = text.replace(_GETURL_FROM, _GETURL_TO)
            content = text.encode("utf-8")
            # Drop content-encoding (we decompressed) and the cache
            # validators (the rewritten body no longer matches WLED's
            # ETag); tell the browser never to cache our rewritten copy.
            headers = {k: v for k, v in headers.items()
                       if k.lower() not in
                       ("content-encoding", "etag", "last-modified",
                        "cache-control")}
            headers["Cache-Control"] = "no-store"

        out = {k: v for k, v in headers.items()
               if k.lower() not in _DROP_RESP}
        return Response(content=content, status_code=status, headers=out,
                        media_type=headers.get("Content-Type"))
