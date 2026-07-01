"""Border LED routes — GET the current state + available animations/palettes,
PUT a partial patch (on/off, colour, brightness, speed, animation, palette,
segment LED counts). Changes persist to config and apply live."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ._shared import safe_json


def _state(config, border) -> dict:
    cfg = (config.get("border") or {})
    st = border.status() if border is not None else {}
    return {
        "enabled":    bool(cfg.get("enabled")),
        "animation":  cfg.get("animation", "pulse"),
        "color":      cfg.get("color", [80, 120, 255]),
        "palette":    cfg.get("palette", []),
        "brightness": float(cfg.get("brightness", 0.25)),
        "speed":      float(cfg.get("speed", 0.5)),
        "fps":        int(cfg.get("fps", 60)),
        "color_order": cfg.get("color_order", "GRB"),
        "segments":   cfg.get("segments", []),
        **st,        # total, strips, hardware, animations, palettes
    }


def register(app: FastAPI, border, config) -> None:
    @app.get("/api/border")
    async def border_get():
        if border is None:
            return JSONResponse({"error": "border disabled"}, status_code=503)
        return _state(config, border)

    @app.put("/api/border")
    async def border_put(request: Request):
        if border is None:
            return JSONResponse({"error": "border disabled"}, status_code=503)
        body = await safe_json(request)
        patch: dict = {}

        if "enabled" in body:
            patch["enabled"] = bool(body["enabled"])
        if "animation" in body:
            anims = border.status().get("animations", [])
            if body["animation"] not in anims:
                return JSONResponse({"error": "unknown animation"}, status_code=400)
            patch["animation"] = body["animation"]
        for key in ("brightness", "speed"):
            if key in body:
                try:
                    patch[key] = max(0.0, min(1.0, float(body[key])))
                except (TypeError, ValueError):
                    return JSONResponse({"error": f"{key} must be a number"},
                                        status_code=400)
        if "fps" in body:
            try:
                patch["fps"] = max(1, min(120, int(body["fps"])))
            except (TypeError, ValueError):
                return JSONResponse({"error": "fps must be an integer"},
                                    status_code=400)
        if "color_order" in body:
            orders = border.status().get("color_orders", [])
            if body["color_order"] not in orders:
                return JSONResponse({"error": "unknown color_order"}, status_code=400)
            patch["color_order"] = body["color_order"]
        if "color" in body:
            c = _rgb(body["color"])
            if c is None:
                return JSONResponse({"error": "color must be [r,g,b]"},
                                    status_code=400)
            patch["color"] = c
        if "palette" in body:
            pal = body["palette"]
            if not isinstance(pal, list) or not pal:
                return JSONResponse({"error": "palette must be a non-empty list"},
                                    status_code=400)
            cols = [_rgb(c) for c in pal]
            if any(c is None for c in cols):
                return JSONResponse({"error": "palette entries must be [r,g,b]"},
                                    status_code=400)
            patch["palette"] = cols

        segs_changed = False
        if "segments" in body and isinstance(body["segments"], list):
            segs = []
            for s in body["segments"]:
                try:
                    segs.append({"spi": str(s["spi"]), "num": max(0, int(s["num"]))})
                except (KeyError, TypeError, ValueError):
                    return JSONResponse({"error": "bad segment"}, status_code=400)
            patch["segments"] = segs
            segs_changed = True

        if patch:
            config.set("border", patch)
            if segs_changed:
                border.reload()       # re-open SPI strips
        return _state(config, border)


def _rgb(v):
    try:
        if len(v) != 3:
            return None
        return [max(0, min(255, int(round(float(x))))) for x in v]
    except (TypeError, ValueError):
        return None
