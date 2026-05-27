"""Per-minute telemetry rollup with SQLite persistence.

Architecture:
  * A background thread samples engine power, current mode, and scale
    readings ~1 Hz and accumulates into an in-memory bucket keyed by
    the current minute (UTC, minute-aligned unix timestamp).
  * On each minute boundary the bucket is flushed to a single SQLite
    row and a fresh bucket starts. This keeps disk writes at ~1/min.
  * Reads (GET /api/telemetry/history?range=…) hit SQLite directly;
    they also tack on the in-progress current-minute bucket so the
    chart includes "right now" instead of stopping at the last
    completed minute.

Schema is intentionally narrow — we don't need indexes beyond the PK
because queries always scan a time-bounded range and the table holds
≤ 7 d × 1440 min = ~10 k rows.

Times are stored as unix timestamps (UTC). Presentation timezone is
the client's concern.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry_minutes (
    ts              INTEGER PRIMARY KEY,
    energy_wh       REAL    NOT NULL,
    mode_durations  TEXT    NOT NULL,
    leg1_g          REAL    NOT NULL,
    leg2_g          REAL    NOT NULL,
    total_g         REAL    NOT NULL
);
"""


class TelemetryHistory:
    SAMPLE_INTERVAL_S = 1.0
    RETENTION_DAYS = 14

    def __init__(self, db_path: str, engine, scale=None) -> None:
        self._db_path = db_path
        self._engine = engine
        self._scale = scale
        self._stop = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        # In-progress minute bucket
        self._bucket_ts: int | None = None
        self._energy_wh: float = 0.0
        self._mode_seconds: dict[str, float] = {}
        self._leg1_samples: list[float] = []
        self._leg2_samples: list[float] = []
        # Ensure parent dir exists; init schema on a dedicated writer connection.
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._writer = sqlite3.connect(db_path, check_same_thread=False)
        self._writer.executescript(_SCHEMA)
        self._writer.commit()

    # ── Lifecycle ───────────────────────────────────────────
    def start(self) -> None:
        self._bucket_ts = self._minute_floor(int(time.time()))
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="telemetry-history")
        self._thread.start()
        logger.info(
            f"telemetry history started (db={self._db_path}, "
            f"retention={self.RETENTION_DAYS}d)")

    def stop(self) -> None:
        self._stop = True
        # Best-effort flush of the in-flight minute so a clean shutdown
        # doesn't lose the last partial bucket.
        try:
            with self._lock:
                if self._bucket_ts is not None and self._has_data():
                    self._flush(self._bucket_ts)
        except Exception:
            logger.exception("telemetry final flush failed")
        try:
            self._writer.close()
        except Exception:
            pass

    # ── Sampling ────────────────────────────────────────────
    @staticmethod
    def _minute_floor(unix_ts: int) -> int:
        return (unix_ts // 60) * 60

    def _has_data(self) -> bool:
        return bool(self._mode_seconds or self._energy_wh
                    or self._leg1_samples or self._leg2_samples)

    def _loop(self) -> None:
        last_t = time.monotonic()
        while not self._stop:
            time.sleep(self.SAMPLE_INTERVAL_S)
            now = time.monotonic()
            dt_s = max(0.0, now - last_t)
            last_t = now
            try:
                with self._lock:
                    self._sample(dt_s)
                    cur_minute = self._minute_floor(int(time.time()))
                    if self._bucket_ts is not None and cur_minute > self._bucket_ts:
                        self._flush(self._bucket_ts)
                        self._bucket_ts = cur_minute
            except Exception:
                logger.exception("telemetry sample loop error")

    def _sample(self, dt_s: float) -> None:
        # Energy from the engine's rolling-average estimate. Use total
        # (LEDs + system idle) so the user's "energy consumption" line
        # already includes the Pi/amp/fan margin.
        try:
            est = self._engine.power_estimate or {}
            total_w = float(est.get("total_watts", 0.0))
            self._energy_wh += total_w * (dt_s / 3600.0)
        except Exception:
            pass

        # Mode duration — accumulate seconds against whichever mode is
        # active right now.
        try:
            mode = self._engine.mode or "unknown"
            self._mode_seconds[mode] = self._mode_seconds.get(mode, 0.0) + dt_s
        except Exception:
            pass

        # Weight (per leg). The snapshot returns grams already in the
        # post-tare, post-calibration space.
        if self._scale is not None:
            try:
                snap = self._scale.snapshot()
                legs = snap.get("legs") or []
                if len(legs) >= 2:
                    self._leg1_samples.append(float(legs[0].get("grams", 0.0)))
                    self._leg2_samples.append(float(legs[1].get("grams", 0.0)))
            except Exception:
                pass

    # ── Persistence ────────────────────────────────────────
    def _flush(self, ts: int) -> None:
        leg1 = (sum(self._leg1_samples) / len(self._leg1_samples)
                if self._leg1_samples else 0.0)
        leg2 = (sum(self._leg2_samples) / len(self._leg2_samples)
                if self._leg2_samples else 0.0)
        try:
            with self._writer:
                self._writer.execute(
                    "INSERT OR REPLACE INTO telemetry_minutes "
                    "(ts, energy_wh, mode_durations, leg1_g, leg2_g, total_g) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (ts, self._energy_wh,
                     json.dumps(self._mode_seconds),
                     leg1, leg2, leg1 + leg2),
                )
                cutoff = int(time.time()) - self.RETENTION_DAYS * 86400
                self._writer.execute(
                    "DELETE FROM telemetry_minutes WHERE ts < ?", (cutoff,))
        except Exception:
            logger.exception("telemetry flush failed")
        # Reset bucket for next minute.
        self._energy_wh = 0.0
        self._mode_seconds = {}
        self._leg1_samples = []
        self._leg2_samples = []

    # ── Query ──────────────────────────────────────────────
    def _bucket_snapshot(self) -> dict:
        leg1 = (sum(self._leg1_samples) / len(self._leg1_samples)
                if self._leg1_samples else 0.0)
        leg2 = (sum(self._leg2_samples) / len(self._leg2_samples)
                if self._leg2_samples else 0.0)
        return {
            "ts": self._bucket_ts,
            "energy_wh": self._energy_wh,
            "mode_durations": dict(self._mode_seconds),
            "leg1_g": leg1,
            "leg2_g": leg2,
            "total_g": leg1 + leg2,
            "in_progress": True,
        }

    def query(self, range_seconds: int) -> dict:
        """Return persisted minute rows within the last `range_seconds`
        plus the in-progress bucket if it falls in range. Caller can use
        `totals()` to roll up energy and mode time."""
        end = int(time.time())
        start = end - max(60, range_seconds)
        # Per-thread connection: SQLite forbids cross-thread reuse by
        # default, and FastAPI hops between threads.
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        try:
            cur = conn.execute(
                "SELECT ts, energy_wh, mode_durations, leg1_g, leg2_g, total_g "
                "FROM telemetry_minutes WHERE ts >= ? AND ts <= ? "
                "ORDER BY ts ASC",
                (start, end),
            )
            samples: list[dict] = []
            for row in cur:
                try:
                    modes = json.loads(row[2] or "{}")
                except json.JSONDecodeError:
                    modes = {}
                samples.append({
                    "ts": row[0],
                    "energy_wh": row[1],
                    "mode_durations": modes,
                    "leg1_g": row[3],
                    "leg2_g": row[4],
                    "total_g": row[5],
                })
        finally:
            conn.close()

        # Tack on the in-progress bucket if it's in range.
        with self._lock:
            if self._bucket_ts is not None and start <= self._bucket_ts <= end:
                # Skip if the writer already persisted this minute.
                if not samples or samples[-1]["ts"] != self._bucket_ts:
                    samples.append(self._bucket_snapshot())

        return {
            "samples": samples,
            "totals": self.totals(samples, range_seconds=end - start),
            "range_start_ts": start,
            "range_end_ts": end,
        }

    @staticmethod
    def totals(samples: Iterable[dict],
               range_seconds: float | None = None) -> dict:
        """Roll up `samples` into engineering totals.

        Returns:
            energy_wh:        Σ sample.energy_wh       — units: Wh (energy)
            mode_durations:   Σ per-mode seconds       — units: s
            recorded_seconds: Σ time we actually had a sample for; equals
                              the sum of all per-mode seconds across all
                              samples. Persisted rows contribute 60s,
                              the in-progress bucket contributes less.
            avg_watts:        energy_wh / recorded_hours — units: W
                              ONLY counts time we actually recorded, so
                              power-off / not-yet-recorded gaps don't
                              drag the average down.
            range_seconds:    pass-through of the caller-supplied window
                              (informational; not used for avg_watts).

        Notes on units (the original bug — labels and meaning were
        swapped in the UI):
          * Watt (W) is a *rate* (power). It can go up or down across
            a wider range depending on what activity sits inside it.
          * Watt-hour (Wh) is a *quantity* (energy). Total energy over
            a longer range is always >= total over a shorter contained
            range — it's a sum of non-negative terms.
        """
        energy_wh = 0.0
        modes: dict[str, float] = {}
        recorded_s = 0.0
        for s in samples:
            energy_wh += float(s.get("energy_wh", 0.0))
            sample_modes = s.get("mode_durations") or {}
            for m, secs in sample_modes.items():
                v = float(secs)
                # Mode rename scene → midi. Old SQLite rows (written
                # before the rename) still have the "scene" key; merge
                # them under "midi" at read time so the chart legend
                # doesn't show both. Drop this remap after the 14-day
                # retention has aged out all "scene" rows.
                if m == "scene":
                    m = "midi"
                modes[m] = modes.get(m, 0.0) + v
                recorded_s += v
        out: dict = {
            "energy_wh": energy_wh,
            "mode_durations": modes,
            "recorded_seconds": recorded_s,
        }
        if recorded_s > 0:
            out["avg_watts"] = energy_wh / (recorded_s / 3600.0)
        if range_seconds is not None:
            out["range_seconds"] = range_seconds
        return out
