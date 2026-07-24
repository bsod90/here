"""Guided-meditation mode.

One-shot recordings that replace the ocean ambience while the bench is
occupied. Each meditation in `audio.meditation.items` can be toggled on/off
independently. When at least one is on:

  bench empty (standby) → ocean ambience plays
  someone sits          → pick a meditation (random; never the same one twice
                          in a row when more than one is enabled), crossfade
                          the ocean out and that recording in (5 s); the
                          VISUALS are that meditation's sequenced event-track
                          from the playground editor when one exists (played
                          live from the shared track — edits in the tab apply
                          immediately), else the classic breathing circle;
                          it plays once
  the clip finishes     → a short pause, then crossfade back to ocean and the
                          calm underwater rest screen (it does NOT replay while the
                          sitter stays)
  the sitter leaves     → mid-recording: NOTHING is cut — a started meditation
                          always plays to its end (audio + visuals). Someone
                          sitting down again joins the ongoing one instead of
                          restarting. When it finishes on an empty bench the
                          installation returns to standby + ocean (no rest
                          screen — nobody is there to rest) and re-arms.
                          After the recording (pause/rest): re-arm — the next
                          sit picks again from the top

The play-once guard is keyed to *physical occupancy* (read straight from the
scale), not engine mode changes — so forcing the visuals back to standby when
the clip ends never looks like "the person left", and the next genuine sit
always starts a fresh meditation.

Each meditation is registered as its own AudioPlayer clip ("meditation:<id>")
so switching between them is instant and sample-accurate. `sequence` per item
is reserved for per-meditation animation choreography later (unused today).
"""
from __future__ import annotations

import logging
import random
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

OCEAN = "ocean"              # track that plays at idle / standby
OCCUPIED_MODE = "breathing"  # engine mode while the recording plays (fallback)
PLAYGROUND_MODE = "playground"  # engine mode when a sequenced track exists
RIPPLES_MODE = "ripples"     # calm underwater rest screen after it finishes
IDLE_MODE = "standby"        # bench empty
FADE_S = 5.0                 # crossfade for the meditation clip / ocean-out
OCEAN_FADE_S = 12.0          # slower fade-IN for the ocean (gentler return)
PAUSE_S = 5.0                # silent hold after the recording ends, before rest
TICK_S = 0.3                 # occupancy poll period
RELEASE_PLAYING_S = 60.0     # forgiving release dwell while a recording plays
VISUAL_FADE_S = 3.5          # keep the playground track rendering this long
                             # after a mode switch away from it, so the
                             # engine's crossfade has LIVE content to fade
                             # out (stopping it instantly = snap to black)


def _clip(mid: str) -> str:
    return f"meditation:{mid}"


class MeditationController:
    def __init__(self, config, engine, audio, media_dir,
                 occupancy_getter=None, release_setter=None, clock=None,
                 rng=None) -> None:
        self._config = config
        self._engine = engine
        self._audio = audio
        self._media_dir = Path(media_dir)
        self._occupancy = occupancy_getter or (lambda: False)
        self._release_setter = release_setter   # callable(seconds) | None
        self._clock = clock or time.monotonic   # injectable for tests
        self._rng = rng or random.Random()      # injectable for tests
        self._lock = threading.Lock()
        # Occupancy-edge state (single source of truth for "play once").
        self._prev_occ = False
        self._played = False        # recording started for this occupancy
        self._finished = False      # recording reached its end (in pause/rest)
        self._finished_at = 0.0     # when it ended (for the post-clip pause)
        self._rest_started = False  # rain rest screen + ocean have come back
        self._current = None        # clip name of the meditation now playing
        self._last_id = None        # last meditation id picked (no-repeat)
        self._pg_visuals = False    # visuals driven by a playground track
        self._stop_visuals_at = 0.0  # deferred pg.stop deadline (0 = none)
        self._running = False
        self._thread = None
        self.reload()

    # ── Config / item helpers ───────────────────────────────
    def _cfg(self) -> dict:
        return ((self._config.get("audio") or {}).get("meditation")) or {}

    def _items(self) -> list[dict]:
        """Normalised list of meditation items. Tolerates the legacy single
        {file,label,mode_enabled} shape so old configs keep working."""
        med = self._cfg()
        raw = med.get("items")
        out = []
        if isinstance(raw, list) and raw:
            for it in raw:
                mid = str(it.get("id") or it.get("file") or "").strip()
                if not mid or not it.get("file"):
                    continue
                out.append({"id": mid, "label": it.get("label", mid),
                            "file": it.get("file"),
                            "enabled": bool(it.get("enabled")),
                            "sequence": it.get("sequence")})
            return out
        # Legacy single meditation.
        if med.get("file"):
            out.append({"id": "med1", "label": med.get("label", "Meditation 1"),
                        "file": med["file"],
                        "enabled": bool(med.get("mode_enabled")),
                        "sequence": None})
        return out

    def _present(self, it: dict) -> bool:
        return bool(it.get("file")) and (self._media_dir / it["file"]).is_file()

    def _available(self) -> list[dict]:
        """Enabled meditations whose audio file is actually on disk."""
        return [it for it in self._items() if it["enabled"] and self._present(it)]

    def enabled(self) -> bool:
        return bool(self._available())

    def _volume(self) -> float:
        try:
            return max(0.0, min(1.0, float(self._cfg().get("volume", 1.0))))
        except (TypeError, ValueError):
            return 1.0

    # ── Clip lifecycle ──────────────────────────────────────
    def reload(self) -> None:
        """(Re)register a clip per meditation whose file exists, so toggling
        one on plays instantly."""
        if self._audio is None:
            return
        vol = self._volume()
        for it in self._items():
            if self._present(it):
                self._audio.register_clip(_clip(it["id"]),
                                          self._media_dir / it["file"], volume=vol)
            else:
                logger.warning("meditation: file missing for %s: %s",
                               it["id"], it.get("file"))

    def set_volume(self, vol: float) -> None:
        """Persist + apply the shared playback volume to every meditation clip."""
        v = max(0.0, min(1.0, float(vol)))
        self._config.set("audio", {"meditation": {"volume": v}})
        if self._audio is not None:
            for it in self._items():
                self._audio.set_track(_clip(it["id"]), volume=v)

    def set_enabled(self, mid: str, on: bool) -> bool:
        """Toggle one meditation on/off (persists), then re-sync audio."""
        items = self._items()
        found = False
        for it in items:
            if it["id"] == mid:
                it["enabled"] = bool(on)
                found = True
        if not found:
            return False
        # Persist the whole list (lists replace wholesale on config.set).
        self._config.set("audio", {"meditation": {"items": [
            {"id": it["id"], "label": it["label"], "file": it["file"],
             "enabled": it["enabled"], "sequence": it.get("sequence")}
            for it in items]}})
        self.apply_settings()
        return True

    def apply_settings(self) -> None:
        """Re-sync after a config change (volume / toggle / file)."""
        self.reload()
        if self._audio is None:
            return
        if not self.enabled():
            # Mode fully off: crossfade any playing recording out, ocean back.
            if self._current is not None:
                self._audio.stop_clip(self._current, fade=FADE_S)
            self._audio.set_track(OCEAN, enabled=True, fade=OCEAN_FADE_S)
            with self._lock:
                self._played = self._finished = self._rest_started = False
                self._current = None
        elif not bool(self._occupancy()):
            # Idle and at least one is on → ocean is the ambience.
            self._audio.set_track(OCEAN, enabled=True)

    # ── Selection ───────────────────────────────────────────
    def _select(self) -> dict | None:
        avail = self._available()
        if not avail:
            return None
        if len(avail) == 1:
            choice = avail[0]
        else:
            # Never the same one twice in a row.
            pool = [it for it in avail if it["id"] != self._last_id] or avail
            choice = self._rng.choice(pool)
        self._last_id = choice["id"]
        return choice

    # ── Occupancy state machine ─────────────────────────────
    def tick(self) -> None:
        """One control step (~3×/s). Public so it's unit-testable without
        the watcher thread."""
        if self._audio is None:
            return
        # A deferred visuals stop (rest hand-off / vacate) comes due once
        # the engine's crossfade away from the playground has finished.
        if self._stop_visuals_at and self._clock() >= self._stop_visuals_at:
            self._stop_pg_visuals()
        occ = bool(self._occupancy())
        if not self.enabled():
            self._prev_occ = occ
            return
        if occ and not self._prev_occ:
            self._on_occupied()
        elif not occ and self._prev_occ:
            self._on_vacated()
        # Finish/rest progression runs regardless of occupancy — a started
        # meditation keeps playing after the sitter leaves, so its ending
        # must still be detected on an empty bench.
        if self._played:
            if not self._finished:
                self._check_finished()
            elif not self._rest_started:
                self._maybe_start_rest()
        self._prev_occ = occ

    def _set_release(self, seconds) -> None:
        # `seconds=None` clears the override → the scale falls back to the
        # user's saved release_seconds (the snappy idle dwell).
        if self._release_setter is not None:
            try:
                self._release_setter(seconds)
            except Exception:
                logger.exception("meditation: release_setter failed")

    def busy(self) -> bool:
        """A meditation clip is mid-play (the sitter may have walked away).
        Mode switchers (scale auto-engage, sensor sim) defer their idle
        switch while this is true so a started meditation isn't cut."""
        return self._current is not None and self._played and not self._finished

    def _on_occupied(self) -> None:
        if self.busy():
            # The previous sitter walked away mid-clip and it's still
            # playing — the new sit joins the ongoing meditation instead
            # of restarting it.
            self._set_release(RELEASE_PLAYING_S)
            logger.info("meditation: sit during ongoing playback → continuing")
            return
        choice = self._select()
        if choice is None:
            return
        with self._lock:
            self._played = True
            self._finished = False
            self._rest_started = False
            self._current = _clip(choice["id"])
        # Visuals: when this meditation has a sequenced event-track built in
        # the playground editor, play THAT — straight from the playground's
        # live track object, so edits in the tab apply to the very next sit
        # (or even mid-play). No track yet → the classic breathing circle.
        pg = getattr(self._engine, "playground", None)
        if pg is not None and pg.has_track(choice["id"]):
            self._stop_visuals_at = 0.0            # cancel any pending stop
            pg.select(choice["id"])
            self._engine.mode = PLAYGROUND_MODE
            pg.play(with_recording=False)          # audio stays OURS below
            self._pg_visuals = True
        else:
            self._engine.mode = OCCUPIED_MODE      # breathing circle
            self._pg_visuals = False
        # Be forgiving while the recording plays: a shift in the seat shouldn't
        # cut the meditation short.
        self._set_release(RELEASE_PLAYING_S)
        self._audio.set_track(OCEAN, enabled=False, fade=FADE_S)
        self._audio.set_track(self._current, volume=self._volume())
        self._audio.play_clip(self._current, 0.0, fade=FADE_S)
        logger.info("meditation: occupied → %s (visuals=%s, ocean fading out)",
                    choice["id"],
                    "playground track" if self._pg_visuals else "breathing")

    def _on_vacated(self) -> None:
        if self.busy():
            # Once started, a meditation plays to its end — leaving no
            # longer cuts it short. Audio and visuals keep running; the
            # ending (finish → idle) is handled by the tick's finish path.
            logger.info("meditation: sitter left mid-play → letting it finish")
            return
        if self._current is not None:
            self._audio.stop_clip(self._current, fade=FADE_S)
        # Deferred: the playground keeps rendering inside the crossfade
        # to standby, easing the timeline out instead of snapping black.
        self._stop_pg_visuals(defer_s=VISUAL_FADE_S)
        self._audio.set_track(OCEAN, enabled=True, fade=OCEAN_FADE_S)  # slow in
        self._engine.mode = IDLE_MODE
        self._config.set("mode", IDLE_MODE)
        self._set_release(None)                     # snappy again (saved base)
        with self._lock:
            self._played = self._finished = self._rest_started = False
            self._current = None
        logger.info("meditation: vacated → ocean ON, re-armed")

    def _stop_pg_visuals(self, defer_s: float = 0.0) -> None:
        """End a playground-track playback we started (visuals only).

        With `defer_s` the actual stop happens that many seconds later
        (via tick) — the mode has already switched away, so the timeline
        keeps rendering ONLY inside the engine's crossfade, easing out
        instead of snapping to black."""
        if not self._pg_visuals:
            return
        if defer_s > 0.0:
            self._stop_visuals_at = self._clock() + defer_s
            return
        self._pg_visuals = False
        self._stop_visuals_at = 0.0
        pg = getattr(self._engine, "playground", None)
        if pg is not None:
            try:
                pg.stop(hold_black=True)   # no ghost animation after the end
            except Exception:
                logger.exception("meditation: playground stop failed")

    def _check_finished(self) -> None:
        if self._current is None:
            return
        st = self._audio.clip_status(self._current)
        if not st or not st.get("loaded"):
            return
        dur = float(st.get("duration_sec") or 0.0)
        pos = float(st.get("position_sec") or 0.0)
        if dur > 0 and not st.get("playing") and pos >= dur - 0.3:
            with self._lock:
                self._finished = True
                self._finished_at = self._clock()
            logger.info("meditation: clip finished → %.0fs pause (breathing holds)",
                        PAUSE_S)

    def _maybe_start_rest(self) -> None:
        if self._clock() - self._finished_at < PAUSE_S:
            return                                  # still in the silent pause
        if not bool(self._occupancy()):
            # Finished on an empty bench (the sitter walked away mid-play):
            # nobody is there to rest, so return to standby + ocean and
            # re-arm for the next sit.
            self._stop_pg_visuals(defer_s=VISUAL_FADE_S)
            self._audio.set_track(OCEAN, enabled=True, fade=OCEAN_FADE_S)
            self._engine.mode = IDLE_MODE
            self._config.set("mode", IDLE_MODE)
            self._set_release(None)                 # snappy again (saved base)
            with self._lock:
                self._played = self._finished = self._rest_started = False
                self._current = None
            logger.info("meditation: finished on empty bench → standby + ocean, re-armed")
            return
        with self._lock:
            self._rest_started = True
        self._stop_pg_visuals(defer_s=VISUAL_FADE_S)  # ease out, don't snap
        self._audio.set_track(OCEAN, enabled=True, fade=OCEAN_FADE_S)
        self._engine.mode = RIPPLES_MODE
        # Persist standby (not ripples) so a restart with an empty bench comes
        # up calm, not mid-rest.
        self._config.set("mode", IDLE_MODE)
        self._set_release(None)                     # snappy again (saved base)
        logger.info("meditation: pause over → underwater rest + ocean (slow fade)")

    # ── Snapshot (for the admin UI) ─────────────────────────
    def state(self) -> dict:
        items = []
        for it in self._items():
            st = self._audio.clip_status(_clip(it["id"])) if self._audio else None
            items.append({
                "id": it["id"], "label": it["label"], "file": it["file"],
                "enabled": it["enabled"],
                "present": self._present(it),
                "loaded": bool(st and st.get("loaded")),
                "playing": bool(st and st.get("playing")),
            })
        return {
            "volume": self._volume(),
            "mode_enabled": self.enabled(),
            "items": items,
        }

    # ── Watcher thread ──────────────────────────────────────
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._watch, daemon=True,
                                        name="meditation")
        self._thread.start()
        if self.enabled() and self._audio is not None \
                and not bool(self._occupancy()):
            self._audio.set_track(OCEAN, enabled=True)
        logger.info("meditation controller started (enabled=%s, %d available)",
                    self.enabled(), len(self._available()))

    def stop(self) -> None:
        self._running = False

    def _watch(self) -> None:
        while self._running:
            time.sleep(TICK_S)
            try:
                self.tick()
            except Exception:
                logger.exception("meditation: tick error")
