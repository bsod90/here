"""Scene / MIDI routes — BPM, taps, events, curves, physics, synth meta,
sequencer + saved sequences, patches.

Patch application uses `scene.apply_patch()` rather than open-coding the
state-mutation logic in the HTTP layer."""
from __future__ import annotations

import logging
import time as _time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ._shared import safe_json

logger = logging.getLogger(__name__)


def register(app: FastAPI, config, engine, scene, sequence_store,
             patch_store, tap_tracker) -> None:

    def _ensure_midi_mode():
        """When the user does something MIDI-tab-y (trigger an event,
        load a patch, hit Play), make sure the runtime is actually in
        MIDI mode — otherwise their action lands on a sleeping engine
        and nothing visible happens."""
        if engine.mode != "midi":
            engine.mode = "midi"
            config.set("mode", "midi")
            logger.info("auto-switched mode → midi (MIDI tab action)")

    def _auto_save_active_sequence():
        """Mirror the current sequencer state into the active sequence
        file. Called after note/loop edits so the on-disk JSON stays
        in sync."""
        if sequence_store is None or scene is None:
            return
        active = ((config.get("scene") or {}).get("sequencer") or {}).get("active_sequence")
        if not active:
            return
        try:
            sequence_store.save(
                active,
                notes=scene.sequencer.notes,
                loop_length_beats=scene.sequencer.loop_length_beats,
            )
        except Exception:
            logger.exception(f"auto-save failed for sequence '{active}'")

    def _active_sequence_name():
        return ((config.get("scene") or {}).get("sequencer") or {}).get("active_sequence")

    def _set_active_sequence(name):
        config.set("scene", {"sequencer": {"active_sequence": name}})

    def _client_tap_mono(body: dict) -> float:
        """Compute the user's tap-monotonic-time from the request body,
        compensating for JS→network delay if the client included
        `client_tap_t_ms` + `client_now_t_ms` (both performance.now() ms)."""
        now_mono = _time.monotonic()
        tap_mono = now_mono
        try:
            ct = body.get("client_tap_t_ms")
            cn = body.get("client_now_t_ms")
            if ct is not None and cn is not None:
                client_gap_s = max(0.0, (float(cn) - float(ct))) / 1000.0
                tap_mono = now_mono - client_gap_s
        except (TypeError, ValueError):
            pass
        return tap_mono

    # ── State / BPM / taps ──────────────────────────────────────
    @app.get("/api/scene/state")
    async def scene_state():
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        return scene.snapshot()

    @app.post("/api/scene/bpm")
    async def scene_set_bpm(request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        try:
            bpm = float(body.get("bpm", 120.0))
        except (TypeError, ValueError):
            return JSONResponse({"error": "bpm must be a number"}, status_code=400)
        scene.set_bpm(bpm)
        config.set("scene", {"bpm": bpm})
        return {"bpm": scene.clock.bpm}

    @app.post("/api/scene/beat")
    async def scene_set_one(request: Request):
        """Gradually drift the clock so that loop_pos == 0 at the tap moment."""
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        info = scene.align_to_loop_zero(_client_tap_mono(body))
        return {"ok": True, **info}

    @app.post("/api/scene/tap")
    async def scene_tap(request: Request):
        """Add a tap event. Updates BPM (median of the last 3-second window)
        and gradually aligns phase to the nearest integer beat."""
        if scene is None or tap_tracker is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        info = tap_tracker.tap(_client_tap_mono(body), scene.clock)
        config.set("scene", {"bpm": scene.clock.bpm})
        return {"ok": True, **info}

    # ── Event dispatch ──────────────────────────────────────────
    @app.post("/api/scene/event/{name}")
    async def scene_event(name: str, request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        _ensure_midi_mode()
        body = await safe_json(request)
        duration_beats = float(body.get("duration_beats", 1.0))
        params = body.get("params") or {}
        event_type = body.get("event_type", "note_on")
        if event_type == "note_off":
            ok = scene.router.dispatch_by_name(name, event_type="note_off",
                                               params=params)
            return ({"ok": True} if ok
                    else JSONResponse({"error": f"unknown event: {name}"}, status_code=400))
        ok = scene.trigger(name, duration_beats, params)
        if not ok:
            return JSONResponse({"error": f"unknown event: {name}"}, status_code=400)
        cur = config.get("scene") or {}
        durs = dict((cur.get("default_durations") or {}))
        durs[name] = duration_beats
        config.set("scene", {"default_durations": durs})
        return {"ok": True}

    @app.get("/api/scene/event_defaults")
    async def event_defaults_get():
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        return scene.router.event_defaults

    @app.put("/api/scene/event_defaults/{name}")
    async def event_defaults_set(name: str, request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        params = dict(body or {})
        scene.router.set_event_default(name, params)
        cur = config.get("scene") or {}
        defs = dict((cur.get("event_defaults") or {}))
        defs[name] = params
        config.set("scene", {"event_defaults": defs})
        return {"ok": True, "name": name, "params": params}

    # ── Curves ──────────────────────────────────────────────────
    @app.get("/api/scene/curves")
    async def curves_get():
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        return {name: env.to_dict() for name, env in scene.curves.items()}

    @app.put("/api/scene/curves/{name}")
    async def curves_set(name: str, request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        from scene.envelopes import Envelope
        body = await safe_json(request)
        if not body.get("points"):
            return JSONResponse(
                {"error": "envelope must have at least one point"},
                status_code=400)
        try:
            env = Envelope.from_dict(body)
        except Exception as e:
            return JSONResponse({"error": f"bad envelope: {e}"}, status_code=400)
        scene.set_curve(name, env)
        cur = (config.get("scene") or {}).get("curves") or {}
        cur[name] = env.to_dict()
        config.set("scene", {"curves": cur})
        return {"ok": True, "name": name}

    # ── Physics ─────────────────────────────────────────────────
    @app.get("/api/scene/physics")
    async def physics_get():
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        return scene.physics.params.to_dict()

    @app.put("/api/scene/physics")
    async def physics_set(request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        for k, v in body.items():
            try:
                float(v)
            except (TypeError, ValueError):
                return JSONResponse({"error": "physics params must be numeric"},
                                    status_code=400)
        scene.apply_physics_params(body)
        merged = scene.physics.params.to_dict()
        config.set("scene", {"physics": merged})
        return merged

    # ── Synth meta ──────────────────────────────────────────────
    @app.get("/api/scene/synth")
    async def synth_get():
        return (config.get("scene") or {}).get("synth") or {}

    @app.put("/api/scene/synth")
    async def synth_set(request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        cur = (config.get("scene") or {}).get("synth") or {}
        cur.update(body)
        config.set("scene", {"synth": cur})
        scene.apply_synth_meta(body)
        return cur

    # ── Sequencer ───────────────────────────────────────────────
    @app.get("/api/scene/sequencer")
    async def sequencer_state():
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        snap = scene.sequencer.snapshot(scene.clock)
        snap["lanes"] = scene.router.lanes
        return snap

    @app.put("/api/scene/sequencer/notes")
    async def sequencer_set_notes(request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        notes = body.get("notes") or []
        scene.sequencer.set_notes(notes)
        _auto_save_active_sequence()
        return {"ok": True, "count": len(scene.sequencer.notes)}

    @app.put("/api/scene/sequencer/loop_length")
    async def sequencer_set_loop_length(request: Request):
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        body = await safe_json(request)
        try:
            beats = float(body.get("loop_length_beats", 16.0))
        except (TypeError, ValueError):
            return JSONResponse({"error": "loop_length_beats must be a number"},
                                status_code=400)
        scene.sequencer.set_loop_length(beats, clock=scene.clock)
        _auto_save_active_sequence()
        return {"ok": True, "loop_length_beats": scene.sequencer.loop_length_beats}

    @app.post("/api/scene/sequencer/play")
    async def sequencer_play():
        """Start the sequencer firing its notes. ONLY drives the event
        emitter — the animation engine runs independently."""
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        _ensure_midi_mode()
        scene.reset_phase()
        scene.sequencer.resync_to_playhead()
        scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
        return {"playing": True}

    @app.post("/api/scene/reset")
    async def scene_reset():
        """Rewind to t=0: clears modulators + baselines, re-inits state,
        zeros physics, snaps clock to beat 0, then restarts the sequencer
        from beat 1 if notes are loaded."""
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        _ensure_midi_mode()
        scene.sequencer.stop(clock=scene.clock)
        scene.reset()
        if scene.sequencer.notes:
            scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
        return {"ok": True}

    @app.post("/api/scene/sequencer/stop")
    async def sequencer_stop():
        """Stop the sequencer event emitter. The animation engine
        keeps running."""
        if scene is None:
            return JSONResponse({"error": "scene disabled"}, status_code=503)
        scene.sequencer.stop(clock=scene.clock)
        return {"playing": False}

    # ── Patches ─────────────────────────────────────────────────
    def _current_patch_body() -> dict:
        scn = config.get("scene") or {}
        return {
            "synth":             scn.get("synth") or {},
            "curves":            scn.get("curves") or {},
            "physics":           scn.get("physics") or {},
            "default_durations": scn.get("default_durations") or {},
            "event_defaults":    scn.get("event_defaults") or {},
            "bpm":               scn.get("bpm") or (scene.clock.bpm if scene else 120.0),
            "palette_idx":       int(scene.state.get("palette_idx", 0)) if scene else 0,
            "active_sequence":   ((scn.get("sequencer") or {}).get("active_sequence")),
        }

    def _config_set_scene(updates: dict) -> None:
        config.set("scene", updates)

    def _sequence_loader(name: str):
        """Load a sequence file by name and persist it as active. Used
        by Scene.apply_patch when a patch references a saved sequence."""
        if sequence_store is None or not sequence_store.exists(name):
            return None
        data = sequence_store.load(name)
        if data is not None:
            config.set("scene", {"sequencer": {"active_sequence": data["name"]}})
        return data

    @app.get("/api/scene/patches")
    async def patches_list():
        if patch_store is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        return {"patches": patch_store.list()}

    @app.get("/api/scene/patches/{name}")
    async def patches_get(name: str):
        if patch_store is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        data = patch_store.load(name)
        if data is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return data

    @app.post("/api/scene/patches/{name}/load")
    async def patches_load(name: str):
        if patch_store is None or scene is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        data = patch_store.load(name)
        if data is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        _ensure_midi_mode()
        # Pure scene-state mutation lives on Scene; routes only inject
        # the persistence + sequence-load callbacks.
        scene.apply_patch(data,
                          config_set=_config_set_scene,
                          sequence_loader=_sequence_loader)
        return {"ok": True, "name": data.get("name", name)}

    @app.post("/api/scene/patches/{name}/save")
    async def patches_save(name: str):
        if patch_store is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        saved = patch_store.save(name, _current_patch_body())
        return {"ok": True, "name": saved}

    @app.post("/api/scene/patches/new")
    async def patches_new(request: Request):
        if patch_store is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        body = await safe_json(request)
        raw_name = (body.get("name") or "untitled").strip() or "untitled"
        target = patch_store.unique_name(raw_name)
        patch_store.save(target, _current_patch_body())
        return {"ok": True, "name": target}

    @app.delete("/api/scene/patches/{name}")
    async def patches_delete(name: str):
        if patch_store is None:
            return JSONResponse({"error": "patch store disabled"}, status_code=503)
        ok = patch_store.delete(name)
        if not ok:
            return JSONResponse({"error": "not found"}, status_code=404)
        return {"ok": True}

    # ── Saved sequences ─────────────────────────────────────────
    @app.get("/api/scene/sequences")
    async def sequences_list():
        if sequence_store is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        return {"sequences": sequence_store.list(), "active": _active_sequence_name()}

    @app.get("/api/scene/sequences/{name}")
    async def sequences_get(name: str):
        if sequence_store is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        data = sequence_store.load(name)
        if data is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return data

    @app.post("/api/scene/sequences/{name}/load")
    async def sequences_load(name: str):
        """Load a saved sequence + reset the animation engine."""
        if sequence_store is None or scene is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        data = sequence_store.load(name)
        if data is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        was_playing = scene.sequencer.playing
        scene.sequencer.stop(clock=scene.clock)
        scene.reset()
        scene.sequencer.set_loop_length(float(data.get("loop_length_beats", 16.0)),
                                        clock=scene.clock)
        scene.sequencer.set_notes(data.get("notes") or [])
        _set_active_sequence(data["name"])
        if was_playing:
            scene.sequencer.play(clock=scene.clock, dispatcher=scene.router)
        return {"ok": True, "active": data["name"], "note_count": len(scene.sequencer.notes)}

    @app.post("/api/scene/sequences/new")
    async def sequences_new(request: Request):
        if sequence_store is None or scene is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        body = await safe_json(request)
        raw_name = (body.get("name") or "untitled").strip() or "untitled"
        copy_from = body.get("copy_from")
        target = sequence_store.unique_name(raw_name)
        if copy_from and sequence_store.exists(copy_from):
            sequence_store.duplicate(copy_from, target)
        else:
            sequence_store.save(target, notes=[],
                                loop_length_beats=scene.sequencer.loop_length_beats)
        data = sequence_store.load(target) or {"notes": [], "loop_length_beats": 16.0}
        scene.sequencer.set_loop_length(float(data["loop_length_beats"]), clock=scene.clock)
        scene.sequencer.set_notes(data.get("notes") or [])
        _set_active_sequence(target)
        return {"ok": True, "active": target}

    @app.post("/api/scene/sequences/{name}/duplicate")
    async def sequences_duplicate(name: str, request: Request):
        if sequence_store is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        body = await safe_json(request)
        raw_new = (body.get("name") or f"{name}-copy").strip()
        target = sequence_store.unique_name(raw_new)
        result = sequence_store.duplicate(name, target)
        if result is None:
            return JSONResponse({"error": "source not found"}, status_code=404)
        return {"ok": True, "name": result}

    @app.delete("/api/scene/sequences/{name}")
    async def sequences_delete(name: str):
        if sequence_store is None or scene is None:
            return JSONResponse({"error": "store disabled"}, status_code=503)
        ok = sequence_store.delete(name)
        if not ok:
            return JSONResponse({"error": "not found"}, status_code=404)
        if _active_sequence_name() == sequence_store._path(name).stem:
            remaining = sequence_store.list()
            if remaining:
                next_name = remaining[0]["name"]
                data = sequence_store.load(next_name)
                scene.sequencer.set_loop_length(float(data["loop_length_beats"]), clock=scene.clock)
                scene.sequencer.set_notes(data.get("notes") or [])
                _set_active_sequence(next_name)
            else:
                _set_active_sequence(None)
                scene.sequencer.set_notes([])
        return {"ok": True}
