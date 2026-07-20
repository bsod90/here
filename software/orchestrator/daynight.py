"""Day/night scheduler — what runs during the day vs during the night.

The playa sun washes the floor out completely, so daytime LEDs are pure
battery burn; nights are the show. This ticks every few seconds, decides
which period we're in from `config.schedule`, and applies three runtime
GATES (never persisted — the underlying settings keep their values, so
flipping the schedule off restores everything):

  floor  → the engine streams BLACK frames (DDP keeps flowing so WLED
           stays in realtime mode instead of waking its own effects)
  border → the border strip blacks out
  audio  → the mixer's master gain glides to zero (no pop)

Times are the Pi's local clock, "HH:MM". The day window is
[day_start, night_start); everything else is night (handles windows
that wrap midnight, e.g. day 21:00 → night 06:00 for an inverted rig).
"""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

TICK_S = 5.0


def _parse_hhmm(s, fallback_min: int) -> int:
    try:
        h, m = str(s).split(":")
        return (int(h) * 60 + int(m)) % (24 * 60)
    except (ValueError, AttributeError):
        return fallback_min


class DayNightScheduler:
    def __init__(self, config, engine=None, border=None, audio=None,
                 clock=None) -> None:
        self._config = config
        self._engine = engine
        self._border = border
        self._audio = audio
        self._clock = clock or time.localtime   # injectable for tests
        self._period: str | None = None          # "day" | "night" | None
        self._running = False
        self._thread = None

    # ── State (for /api/status + the UI pill) ───────────────
    def state(self) -> dict:
        cfg = self._config.get("schedule") or {}
        return {"enabled": bool(cfg.get("enabled")),
                "period": self._period}

    # ── One control step ────────────────────────────────────
    def tick(self) -> None:
        cfg = self._config.get("schedule") or {}
        if not cfg.get("enabled"):
            self._apply({"floor": True, "border": True, "audio": True}, None)
            return
        lt = self._clock()
        now_min = lt.tm_hour * 60 + lt.tm_min
        day0 = _parse_hhmm(cfg.get("day_start"), 9 * 60)
        night0 = _parse_hhmm(cfg.get("night_start"), 20 * 60)
        if day0 <= night0:
            is_day = day0 <= now_min < night0
        else:                                    # window wraps midnight
            is_day = now_min >= day0 or now_min < night0
        period = "day" if is_day else "night"
        gates = {"floor": True, "border": True, "audio": True,
                 **(cfg.get(period) or {})}
        self._apply(gates, period)

    def _apply(self, gates: dict, period: str | None) -> None:
        if period != self._period:
            logger.info("schedule: period → %s (floor=%s border=%s audio=%s)",
                        period or "off", gates.get("floor"),
                        gates.get("border"), gates.get("audio"))
        self._period = period
        if self._engine is not None:
            self._engine.output_on = bool(gates.get("floor", True))
        if self._border is not None:
            self._border.schedule_on = bool(gates.get("border", True))
        if self._audio is not None:
            self._audio.set_master_enabled(bool(gates.get("audio", True)))

    # ── Thread ──────────────────────────────────────────────
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="daynight")
        self._thread.start()
        logger.info("day/night scheduler started (%s)", self.state())

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                self.tick()
            except Exception:
                logger.exception("schedule: tick error")
            time.sleep(TICK_S)
