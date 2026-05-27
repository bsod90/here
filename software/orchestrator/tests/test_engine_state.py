"""Tests for engine_state co-objects (TransitionCoordinator, PowerEstimator)."""
from __future__ import annotations

import pytest

from engine_state import PowerEstimator, TransitionCoordinator
from grid import FRAME_BYTES


# ── PowerEstimator ─────────────────────────────────────────────
def test_power_estimator_zero_frame_is_idle_only():
    est = PowerEstimator(system_idle_watts=10.0, battery_wh=1000,
                         watts_per_led_full_white=0.1, total_leds=1936)
    est.push_frame_rgb_sum(0, now=0.0)
    e = est.estimate()
    assert e["led_watts"] == pytest.approx(0.0)
    assert e["total_watts"] == pytest.approx(10.0)
    assert e["daily_wh"] == 240   # 10 W * 24 h


def test_power_estimator_full_white_frame():
    """All 1936 LEDs at full white = 255+255+255 each = ~0.1W * 1936."""
    leds = 1936
    rgb_sum = leds * 255 * 3
    est = PowerEstimator(system_idle_watts=5.0, battery_wh=1000,
                         watts_per_led_full_white=0.1, total_leds=leds)
    est.push_frame_rgb_sum(rgb_sum, now=0.0)
    e = est.estimate()
    assert e["led_watts"] == pytest.approx(193.6)
    assert e["total_watts"] == pytest.approx(198.6)


def test_power_estimator_rolling_average_drops_old_samples():
    est = PowerEstimator(system_idle_watts=0, battery_wh=1000,
                         watts_per_led_full_white=0.1, total_leds=1936,
                         window_s=10.0)
    # Push 10 high readings at t=0..9 (one per second), then one low reading
    # at t=20 — the older samples should have aged out.
    for t in range(10):
        est.push_frame_rgb_sum(1936 * 255 * 3, now=float(t))
    # Now jump well past the window.
    est.push_frame_rgb_sum(0, now=20.0)
    assert est.led_watts == pytest.approx(0.0)


# ── TransitionCoordinator ──────────────────────────────────────
class _RecordingRenderer:
    """Capture calls so tests can assert on dispatch behaviour without
    standing up the full engine."""
    def __init__(self):
        self.calls = []

    def __call__(self, mode, frame, time_ms, fade_in, fade_out):
        self.calls.append({"mode": mode, "time_ms": time_ms,
                           "fade_in": fade_in, "fade_out": fade_out,
                           "frame_id": id(frame)})


def test_transition_idle_returns_false_without_painting():
    tc = TransitionCoordinator(fade_durations=lambda m: (1.0, 1.0))
    renderer = _RecordingRenderer()
    claimed = tc.render(time_ms=123, frame=bytearray(FRAME_BYTES),
                        render_mode=renderer)
    assert claimed is False
    assert renderer.calls == []


def test_transition_renders_both_during_overlap():
    tc = TransitionCoordinator(fade_durations=lambda m: {
        "standby":   (4.0, 4.0),
        "breathing": (16.5, 7.5),
    }[m])
    tc.start("standby", "breathing", t0_ms=0)
    frame = bytearray(FRAME_BYTES)
    r = _RecordingRenderer()
    # Mid-transition: 2s in. outgoing fade_out=2/4=0.5, incoming fade_in=2/16.5≈0.12
    assert tc.render(time_ms=2000, frame=frame, render_mode=r) is True
    by_mode = {c["mode"]: c for c in r.calls}
    assert "standby" in by_mode and "breathing" in by_mode
    assert by_mode["standby"]["fade_out"] == pytest.approx(0.5)
    assert by_mode["breathing"]["fade_in"] == pytest.approx(2 / 16.5, abs=0.001)


def test_transition_clamps_dst_fade_in_at_one_past_window():
    """If dst.fade_in_s < src.fade_out_s, dst should keep rendering at
    fade_in=1.0 (fully present) until src's fade-out completes —
    otherwise the new mode vanishes mid-handoff and re-appears at the
    transition's end."""
    tc = TransitionCoordinator(fade_durations=lambda m: {
        "breathing": (16.5, 7.5),   # outgoing — long fade-out
        "standby":   (4.0, 4.0),    # incoming — short fade-in
    }[m])
    tc.start("breathing", "standby", t0_ms=0)
    frame = bytearray(FRAME_BYTES)
    r = _RecordingRenderer()
    # Past the incoming's fade_in window but still inside outgoing's fade-out.
    tc.render(time_ms=5000, frame=frame, render_mode=r)
    standby_call = next(c for c in r.calls if c["mode"] == "standby")
    assert standby_call["fade_in"] == pytest.approx(1.0)


def test_transition_completes_and_clears_after_max_duration():
    tc = TransitionCoordinator(fade_durations=lambda m: (4.0, 4.0))
    tc.start("standby", "breathing", t0_ms=0)
    # Way past both windows: should clear and return False.
    claimed = tc.render(time_ms=10_000, frame=bytearray(FRAME_BYTES),
                        render_mode=_RecordingRenderer())
    assert claimed is False
    assert tc.active is False


def test_transition_no_fade_pair_returns_false():
    """Both fade durations zero = nothing to render."""
    tc = TransitionCoordinator(fade_durations=lambda m: (0.0, 0.0))
    tc.start("debug", "off", t0_ms=0)
    assert tc.render(time_ms=100, frame=bytearray(FRAME_BYTES),
                     render_mode=_RecordingRenderer()) is False
    assert tc.active is False
