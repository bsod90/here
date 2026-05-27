"""Tests for telemetry_history.

Focus is on the unit accounting — the original bug was the UI labeling
average power (W) as "total" while displaying total energy (Wh) as
"average", so a longer range appeared to have a *lower* total than a
shorter range. Tests below pin down the contract:

  * energy_wh in totals is monotonically non-decreasing as you widen the
    range (it's a sum of non-negative per-minute energies).
  * avg_watts in totals = energy_wh / range_hours.
  * mode_durations sum per-mode seconds across samples.
  * The in-progress bucket is included in queries without double-counting
    flushed rows.
"""
from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from telemetry_history import TelemetryHistory


# ── Fakes ─────────────────────────────────────────────────────
class _Engine:
    """Engine stub: constant power, named mode."""
    def __init__(self, total_watts: float = 25.0, mode: str = "breathing"):
        self.power_estimate = {"total_watts": total_watts}
        self.mode = mode


class _Scale:
    def __init__(self, l1_g: float = 0.0, l2_g: float = 0.0):
        self._l1, self._l2 = l1_g, l2_g

    def snapshot(self) -> dict:
        return {"legs": [{"grams": self._l1}, {"grams": self._l2}]}


@pytest.fixture
def tmpdb():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ── totals() — the bug live here ──────────────────────────────
def test_totals_sums_energy_wh():
    samples = [
        {"ts": 1, "energy_wh": 0.10, "mode_durations": {}, "leg1_g": 0, "leg2_g": 0},
        {"ts": 2, "energy_wh": 0.20, "mode_durations": {}, "leg1_g": 0, "leg2_g": 0},
        {"ts": 3, "energy_wh": 0.05, "mode_durations": {}, "leg1_g": 0, "leg2_g": 0},
    ]
    t = TelemetryHistory.totals(samples)
    assert t["energy_wh"] == pytest.approx(0.35)


def test_totals_avg_watts_uses_recorded_duration():
    """avg_watts = energy_wh / recorded_hours (not over the requested
    range). Each sample's recorded duration comes from the sum of its
    mode_durations — so the average reflects only minutes we actually
    had data for."""
    # 1 sample with 1 Wh and 60s of recording = 1 Wh per minute = 60 W
    samples = [{"ts": 1, "energy_wh": 1.0,
                "mode_durations": {"breathing": 60.0},
                "leg1_g": 0, "leg2_g": 0}]
    t = TelemetryHistory.totals(samples, range_seconds=3600)
    assert t["avg_watts"] == pytest.approx(60.0)
    assert t["recorded_seconds"] == pytest.approx(60.0)
    # Two such minutes = 2 Wh in 120s, still 60 W avg.
    t = TelemetryHistory.totals(samples * 2)
    assert t["avg_watts"] == pytest.approx(60.0)


def test_totals_avg_excludes_no_data_gaps():
    """The user-reported gap: querying a wide window with only a few
    recorded minutes inside it should yield avg_watts based on those
    minutes alone, not on the whole window. Power-off / not-yet-
    recorded gaps must not drag the average down."""
    # 10 minutes of data inside a 6-hour query window.
    samples = [{"ts": i, "energy_wh": 0.5,
                "mode_durations": {"breathing": 60.0}}
               for i in range(10)]
    t = TelemetryHistory.totals(samples, range_seconds=6 * 3600)
    # 5 Wh consumed in 10 minutes = 30 W average — independent of
    # the 6-hour query window.
    assert t["energy_wh"] == pytest.approx(5.0)
    assert t["avg_watts"] == pytest.approx(30.0)
    assert t["recorded_seconds"] == pytest.approx(600.0)
    assert t["range_seconds"] == pytest.approx(6 * 3600)


def test_totals_partial_in_progress_bucket_uses_actual_duration():
    """The in-progress bucket may have less than 60s of data. Use its
    actual recorded duration (= sum of its mode_durations) so the
    fraction-of-a-minute case doesn't fake a slower rate."""
    # 30 seconds of "breathing" at high energy density.
    samples = [{"ts": 1, "energy_wh": 0.5,
                "mode_durations": {"breathing": 30.0},
                "in_progress": True}]
    t = TelemetryHistory.totals(samples)
    # 0.5 Wh in 30s → 0.5 / (30/3600) = 60 W
    assert t["avg_watts"] == pytest.approx(60.0)
    assert t["recorded_seconds"] == pytest.approx(30.0)


def test_totals_no_samples_means_no_avg():
    t = TelemetryHistory.totals([])
    assert t["energy_wh"] == 0.0
    assert t["recorded_seconds"] == 0.0
    assert "avg_watts" not in t


def test_totals_legacy_scene_key_remapped_to_midi():
    """SQLite rows written before the scene→midi rename use the old
    'scene' key in mode_durations. They should merge with current
    'midi' entries at read time so the chart isn't split."""
    samples = [
        {"ts": 1, "mode_durations": {"scene": 60.0}},          # pre-rename row
        {"ts": 2, "mode_durations": {"midi": 60.0}},           # post-rename row
        {"ts": 3, "mode_durations": {"scene": 30.0, "midi": 30.0}},  # mixed
    ]
    t = TelemetryHistory.totals(samples)
    assert t["mode_durations"] == {"midi": 180.0}
    assert "scene" not in t["mode_durations"]


def test_totals_energy_is_monotonic_in_range():
    """The reported user bug: widening the range showed a *lower*
    total. That was a label swap (avg labeled total). The actual
    total-energy roll-up must increase with included samples."""
    minutes = [{"ts": i, "energy_wh": 0.05, "mode_durations": {}, "leg1_g": 0, "leg2_g": 0}
               for i in range(0, 360)]   # 360 one-minute samples = 6h
    one_hour = minutes[-60:]              # last 60 = 1h
    six_hour = minutes                    # all 360 = 6h
    t1 = TelemetryHistory.totals(one_hour)["energy_wh"]
    t6 = TelemetryHistory.totals(six_hour)["energy_wh"]
    assert t6 >= t1
    assert t6 == pytest.approx(0.05 * 360)
    assert t1 == pytest.approx(0.05 * 60)


def test_totals_sums_mode_durations():
    samples = [
        {"ts": 1, "energy_wh": 0, "mode_durations": {"breathing": 30, "standby": 30}},
        {"ts": 2, "energy_wh": 0, "mode_durations": {"breathing": 60}},
        {"ts": 3, "energy_wh": 0, "mode_durations": {"standby": 60}},
    ]
    t = TelemetryHistory.totals(samples)
    assert t["mode_durations"] == {"breathing": 90, "standby": 90}


def test_totals_handles_missing_keys_gracefully():
    samples = [
        {"ts": 1},                                # bare row, no recording
        {"ts": 2, "energy_wh": 0.1},              # no modes → no recorded time
        {"ts": 3, "mode_durations": {"x": 5}},    # 5s of "x", no energy
    ]
    t = TelemetryHistory.totals(samples, range_seconds=180)
    assert t["energy_wh"] == pytest.approx(0.1)
    assert t["mode_durations"] == {"x": 5.0}
    # 5s of recording total. 0.1 Wh / (5/3600) h = 72 W.
    assert t["recorded_seconds"] == pytest.approx(5.0)
    assert t["avg_watts"] == pytest.approx(72.0)


# ── Per-minute accumulation ──────────────────────────────────
def test_sample_accumulates_energy_per_dt(tmpdb):
    th = TelemetryHistory(tmpdb, _Engine(total_watts=60.0), _Scale())
    # Manually accumulate 60 seconds of samples at 60 W.
    for _ in range(60):
        th._sample(dt_s=1.0)
    snap = th._bucket_snapshot()
    # 60 W for 60 s = 1 Wh
    assert snap["energy_wh"] == pytest.approx(1.0, rel=0.001)
    th.stop()


def test_sample_tracks_mode_seconds(tmpdb):
    eng = _Engine(mode="breathing")
    th = TelemetryHistory(tmpdb, eng, _Scale())
    for _ in range(30):
        th._sample(dt_s=1.0)
    eng.mode = "standby"
    for _ in range(15):
        th._sample(dt_s=1.0)
    snap = th._bucket_snapshot()
    assert snap["mode_durations"] == pytest.approx({"breathing": 30.0, "standby": 15.0})
    th.stop()


def test_flush_resets_and_persists(tmpdb):
    eng = _Engine(total_watts=120.0)
    th = TelemetryHistory(tmpdb, eng, _Scale(l1_g=100.0, l2_g=50.0))
    ts = (int(time.time()) // 60) * 60
    th._bucket_ts = ts
    for _ in range(60):
        th._sample(dt_s=1.0)
    th._flush(ts)
    # Bucket should be empty now
    assert th._energy_wh == 0.0
    assert th._mode_seconds == {}
    assert th._leg1_samples == []
    # Row should be on disk
    import sqlite3
    conn = sqlite3.connect(tmpdb)
    rows = list(conn.execute(
        "SELECT ts, energy_wh, leg1_g, leg2_g, total_g, mode_durations "
        "FROM telemetry_minutes WHERE ts = ?", (ts,)))
    conn.close()
    assert len(rows) == 1
    row_ts, energy_wh, l1, l2, total, modes_json = rows[0]
    assert row_ts == ts
    # 120 W for 60 s = 2 Wh
    assert energy_wh == pytest.approx(2.0, rel=0.001)
    assert l1 == pytest.approx(100.0)
    assert l2 == pytest.approx(50.0)
    assert total == pytest.approx(150.0)
    assert json.loads(modes_json) == pytest.approx({"breathing": 60.0})
    th.stop()


# ── Query ────────────────────────────────────────────────────
def test_query_returns_persisted_rows(tmpdb):
    th = TelemetryHistory(tmpdb, _Engine(), _Scale())
    now = int(time.time())
    # Insert three minute-bucketed rows directly.
    import sqlite3
    conn = sqlite3.connect(tmpdb)
    for offset_min, energy in [(2, 0.1), (1, 0.2), (0, 0.3)]:
        ts = ((now - offset_min * 60) // 60) * 60
        conn.execute(
            "INSERT INTO telemetry_minutes "
            "(ts, energy_wh, mode_durations, leg1_g, leg2_g, total_g) "
            "VALUES (?, ?, '{}', 0, 0, 0)",
            (ts, energy))
    conn.commit(); conn.close()
    q = th.query(range_seconds=600)
    energies = [s["energy_wh"] for s in q["samples"]]
    assert pytest.approx(0.6) == sum(energies)
    assert q["totals"]["energy_wh"] == pytest.approx(0.6)
    # 3 inserted rows × 0 mode_durations = 0 recorded_seconds. So no
    # avg_watts in totals (we don't fake an average over time we never
    # actually had data for). The bare-INSERT path used in this test
    # bypasses mode tracking; queries against real flushed buckets
    # always have mode_durations summing to ≥60s per row.
    assert q["totals"]["recorded_seconds"] == pytest.approx(0.0)
    assert "avg_watts" not in q["totals"]
    th.stop()


def test_query_includes_in_progress_bucket(tmpdb):
    th = TelemetryHistory(tmpdb, _Engine(total_watts=60.0), _Scale())
    th._bucket_ts = ((int(time.time())) // 60) * 60
    for _ in range(30):
        th._sample(dt_s=1.0)
    q = th.query(range_seconds=120)
    in_prog = [s for s in q["samples"] if s.get("in_progress")]
    assert len(in_prog) == 1
    # 60 W for 30 s = 0.5 Wh
    assert in_prog[0]["energy_wh"] == pytest.approx(0.5, rel=0.001)
    th.stop()


def test_query_avoids_double_count_after_flush(tmpdb):
    th = TelemetryHistory(tmpdb, _Engine(total_watts=60.0), _Scale())
    ts = ((int(time.time())) // 60) * 60
    th._bucket_ts = ts
    for _ in range(60):
        th._sample(dt_s=1.0)
    th._flush(ts)
    # Now set up the in-progress bucket at the SAME ts (writer just
    # flushed but the loop hasn't bumped the bucket to the next
    # minute yet). The query path must not return both copies.
    th._bucket_ts = ts
    q = th.query(range_seconds=300)
    matching = [s for s in q["samples"] if s["ts"] == ts]
    assert len(matching) == 1
    th.stop()


# ── End-to-end shape ──────────────────────────────────────────
def test_query_shape(tmpdb):
    th = TelemetryHistory(tmpdb, _Engine(), _Scale())
    q = th.query(range_seconds=3600)
    assert set(q.keys()) == {"samples", "totals", "range_start_ts", "range_end_ts"}
    assert q["range_end_ts"] - q["range_start_ts"] == 3600
    assert "energy_wh" in q["totals"]
    assert "recorded_seconds" in q["totals"]
    assert "mode_durations" in q["totals"]
    assert "range_seconds" in q["totals"]
    # avg_watts is only present when there's data
    if q["totals"]["recorded_seconds"] > 0:
        assert "avg_watts" in q["totals"]
    th.stop()
