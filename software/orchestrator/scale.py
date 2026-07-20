"""Load-cell scale: dual HX711 + auto-occupancy state machine.

Wiring (per HX711):
    VCC → 3.3V, GND → GND
    DT  → independent GPIO per chip (default 16, 19)
    SCK → shared GPIO (default 21)

Two background threads:
    * `_read_loop` — bit-bangs the HX711s ~10 Hz, exponentially smooths.
    * `_state_loop` — applies threshold + 60 s release to drive
      `engine.mode` between occupied / idle, respecting an
      `auto_engage` toggle (so manual mode changes stick when desired).

On non-RPi hosts (no `lgpio`) the chip layer is replaced with a stub
that returns zeros, so the orchestrator still boots locally and the
UI tab still renders.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import lgpio  # type: ignore
    HAS_LGPIO = True
except ImportError:
    HAS_LGPIO = False
    logger.warning("scale: lgpio not available — running in stub mode (readings = 0)")


SAMPLES_PER_READ = 3
GAIN_PULSES = 1            # 1 = 128× on channel A
SMOOTH_ALPHA = 0.35        # EMA factor; higher = snappier, lower = smoother
DEFAULT_POLL_HZ = 10
STATE_TICK_S = 0.5


@dataclass
class LegReading:
    raw: float = 0.0        # raw HX711 counts (post-EMA)
    grams: float = 0.0      # tared + calibrated
    last_ts: float = 0.0
    ok: bool = False        # last read succeeded
    battery_mv: Optional[int] = None  # leg node battery (serial source only)
    charging: bool = False  # leg node battery is rising (serial source only)


@dataclass
class ScaleConfig:
    enabled: bool = True
    dt_pins: tuple[int, int] = (16, 19)
    sck_pin: int = 21
    # Per-leg tare offset (raw counts) and counts-per-gram calibration.
    tare: list[float] = field(default_factory=lambda: [0.0, 0.0])
    counts_per_gram: list[float] = field(default_factory=lambda: [1.0, 1.0])
    # Per-leg display polarity. The HX711 sign depends on the load cell's
    # E+/E- + A+/A- wiring; both legs of HERE's bench read negative under
    # load with the current wiring, so flip them by default. Set to +1 if
    # you ever swap the cell leads.
    sign: list[int] = field(default_factory=lambda: [-1, -1])
    # Auto-occupancy.
    auto_engage: bool = True
    threshold_grams: float = 15000.0
    # Dwell on both edges of the threshold so single-sample noise on
    # one leg can't flip the bench state:
    #   engage_seconds  — weight must sit ≥ threshold continuously
    #                     for this long before switching to occupied.
    #   release_seconds — weight must sit  < threshold continuously
    #                     for this long before switching to idle.
    engage_seconds: float = 5.0
    release_seconds: float = 60.0
    occupied_mode: str = "breathing"
    idle_mode: str = "standby"
    # Weight overlay — when on, the engine layers the leg-glow shadows
    # on top of whatever mode is currently rendering.
    weight_overlay: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "ScaleConfig":
        out = cls()
        if not d:
            return out
        for k, v in d.items():
            if hasattr(out, k):
                if k == "dt_pins":
                    v = tuple(int(x) for x in v)[:2]
                elif k in ("tare", "counts_per_gram"):
                    v = [float(x) for x in (v or [])][:2]
                    while len(v) < 2:
                        v.append(0.0 if k == "tare" else 1.0)
                elif k == "sign":
                    v = [1 if int(x) >= 0 else -1 for x in (v or [])][:2]
                    while len(v) < 2:
                        v.append(-1)
                elif k in ("occupied_mode", "idle_mode") and v == "scene":
                    # Mode renamed scene → midi.
                    v = "midi"
                setattr(out, k, v)
        return out

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "dt_pins": list(self.dt_pins),
            "sck_pin": self.sck_pin,
            "tare": list(self.tare),
            "counts_per_gram": list(self.counts_per_gram),
            "sign": list(self.sign),
            "auto_engage": self.auto_engage,
            "threshold_grams": self.threshold_grams,
            "engage_seconds": self.engage_seconds,
            "release_seconds": self.release_seconds,
            "occupied_mode": self.occupied_mode,
            "idle_mode": self.idle_mode,
            "weight_overlay": self.weight_overlay,
        }


class _HX711:
    """Bit-banged HX711, one per chip. SCK may be shared across instances."""

    def __init__(self, chip_handle: int, dt: int, sck: int) -> None:
        self.chip = chip_handle
        self.dt = dt
        self.sck = sck
        lgpio.gpio_claim_input(chip_handle, dt)
        try:
            lgpio.gpio_claim_output(chip_handle, sck, 0)
        except lgpio.error:
            # Shared SCK — second claim is fine; ignore.
            pass

    def _ready(self) -> bool:
        return lgpio.gpio_read(self.chip, self.dt) == 0

    def read_raw(self, timeout_s: float = 0.25) -> Optional[int]:
        deadline = time.monotonic() + timeout_s
        while not self._ready():
            if time.monotonic() > deadline:
                return None
            time.sleep(0.001)
        value = 0
        for _ in range(24):
            lgpio.gpio_write(self.chip, self.sck, 1)
            value = (value << 1) | lgpio.gpio_read(self.chip, self.dt)
            lgpio.gpio_write(self.chip, self.sck, 0)
        for _ in range(GAIN_PULSES):
            lgpio.gpio_write(self.chip, self.sck, 1)
            lgpio.gpio_write(self.chip, self.sck, 0)
        if value & 0x800000:
            value -= 0x1000000
        return value

    def read_avg(self, n: int = SAMPLES_PER_READ) -> Optional[float]:
        samples = []
        for _ in range(n):
            v = self.read_raw()
            if v is not None:
                samples.append(v)
        return sum(samples) / len(samples) if samples else None


class ScaleSensor:
    """Public surface used by main.py and the admin routes."""

    # Callback signature: (new_mode: str, reason: str) -> None
    ModeSwitcher = Callable[[str, str], None]

    def __init__(self, cfg: ScaleConfig, mode_switcher: ModeSwitcher,
                 current_mode_getter: Callable[[], str],
                 persist_cb: Optional[Callable[[dict], None]] = None,
                 raw_provider: Optional[Callable[[int], Optional[float]]] = None,
                 battery_provider: Optional[Callable[[int], Optional[int]]] = None,
                 charging_provider: Optional[Callable[[int], bool]] = None,
                 tare_cmd: Optional[Callable[[int], bool]] = None,
                 threshold_cmd: Optional[Callable[[int, int], bool]] = None,
                 link_snapshot: Optional[Callable[[], dict]] = None) -> None:
        self.cfg = cfg
        self._mode_switcher = mode_switcher
        self._get_mode = current_mode_getter
        self._persist = persist_cb
        # Optional remote data source (bench_link). When set, raw weight
        # comes from the ESP-NOW legs over serial instead of the on-Pi
        # HX711 GPIO; everything downstream (EMA, sign, tare, calibration,
        # occupancy) is unchanged.
        self._raw_provider = raw_provider
        self._battery_provider = battery_provider
        self._charging_provider = charging_provider
        # Commands pushed back to the leg nodes over the two-way link.
        self._tare_cmd = tare_cmd
        self._threshold_cmd = threshold_cmd
        self._link_snapshot = link_snapshot
        self._lock = threading.Lock()
        self._legs: list[LegReading] = [LegReading(), LegReading()]
        # State-machine bookkeeping. Both dwell timers are timestamps
        # of when the threshold was last crossed (monotonic). They get
        # reset when the signal recovers within the dwell window —
        # noise on one leg can't trip the state.
        self._occupied = False
        self._above_since: Optional[float] = None     # → switch to occupied
        self._empty_since: Optional[float] = None     # → switch to idle
        # Live, NON-persisted release-dwell override (meditation uses it to be
        # forgiving while a recording plays). Kept separate from cfg so it can
        # never leak into the saved config via a persist of cfg.to_dict().
        self._release_override: Optional[float] = None
        self._running = False
        self._chip_handle: Optional[int] = None
        self._sensors: list[_HX711] = []
        self._stub_phase = 0.0
        self._read_thread: Optional[threading.Thread] = None
        self._state_thread: Optional[threading.Thread] = None

    # ── Lifecycle ───────────────────────────────────────────
    def start(self) -> None:
        # Only claim the on-Pi HX711 GPIOs when there's no serial source. The
        # bench legs now report weight over ESP-NOW → serial (raw_provider), so
        # the legacy on-Pi sensors are vestigial; claiming their pins (incl.
        # GPIO21) would otherwise block other peripherals (e.g. SPI1 used for
        # the floor-border LED strip).
        if HAS_LGPIO and self._raw_provider is None:
            try:
                self._chip_handle = lgpio.gpiochip_open(0)
                self._sensors = [
                    _HX711(self._chip_handle, dt, self.cfg.sck_pin)
                    for dt in self.cfg.dt_pins
                ]
            except Exception:
                logger.exception("scale: failed to init HX711s — falling back to stub")
                self._sensors = []
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True,
                                             name="scale-read")
        self._state_thread = threading.Thread(target=self._state_loop, daemon=True,
                                              name="scale-state")
        self._read_thread.start()
        self._state_thread.start()
        logger.info(
            f"scale started — DT={list(self.cfg.dt_pins)} SCK={self.cfg.sck_pin} "
            f"threshold={self.cfg.threshold_grams:.0f}g release={self.cfg.release_seconds:.0f}s"
        )

    def stop(self) -> None:
        self._running = False
        if self._chip_handle is not None and HAS_LGPIO:
            try:
                lgpio.gpiochip_close(self._chip_handle)
            except Exception:
                pass
            self._chip_handle = None

    # ── Public read API ─────────────────────────────────────
    @property
    def occupied(self) -> bool:
        """Whether the bench is currently occupied (debounced by the
        engage/release dwell). Read by the meditation controller to drive
        the one-shot recording per occupancy."""
        return self._occupied

    def simulate_occupancy(self, occupied: bool) -> None:
        """Debug hook for the admin's sensor simulator: force the debounced
        occupancy state as if the engage/release dwell had already elapsed —
        so everything keyed to PHYSICAL occupancy (the meditation controller's
        play-once flow, sequenced visuals) runs exactly like a real sit.
        The weight loop keeps running; the next genuine threshold crossing
        (or the release dwell, on a 0 kg bench) takes over from here."""
        self._occupied = bool(occupied)
        self._above_since = None
        self._empty_since = None

    def set_release_override(self, seconds) -> None:
        """Live, non-persisted release-dwell override. The meditation
        controller bumps this to ~60 s while a recording plays; passing None
        clears it so the dwell falls back to the user's saved release_seconds.
        Crucially this never touches self.cfg, so a later persist of the
        config can't bake the temporary value in as the new base."""
        with self._lock:
            self._release_override = (None if seconds is None
                                      else max(1.0, float(seconds)))

    def _effective_release(self) -> float:
        """The release dwell actually in force: the override if one is set,
        otherwise the configured base."""
        return (self._release_override if self._release_override is not None
                else self.cfg.release_seconds)

    def snapshot(self) -> dict:
        with self._lock:
            legs = [
                {
                    "raw": round(l.raw, 1),
                    "grams": round(l.grams, 1),
                    "ok": l.ok,
                    "last_ts": l.last_ts,
                    "battery_mv": l.battery_mv,
                    "charging": l.charging,
                }
                for l in self._legs
            ]
            total = sum(l.grams for l in self._legs)
            # Where raw weight is coming from: the ESP-NOW legs over serial,
            # the on-Pi HX711 GPIO, or the laptop stub.
            if self._raw_provider is not None:
                source = "serial"
            elif HAS_LGPIO and self._sensors:
                source = "hx711"
            else:
                source = "stub"
            out = {
                "enabled": self.cfg.enabled,
                "hardware": source in ("serial", "hx711"),
                "source": source,
                "auto_engage": self.cfg.auto_engage,
                "weight_overlay": self.cfg.weight_overlay,
                "threshold_grams": self.cfg.threshold_grams,
                "engage_seconds": self.cfg.engage_seconds,
                "release_seconds": self.cfg.release_seconds,   # saved base
                "release_effective": self._effective_release(),  # in force now
                "occupied_mode": self.cfg.occupied_mode,
                "idle_mode": self.cfg.idle_mode,
                "occupied": self._occupied,
                "empty_for_s": (
                    round(time.monotonic() - self._empty_since, 1)
                    if self._empty_since is not None else None
                ),
                "legs": legs,
                "total_grams": round(total, 1),
                "tare": list(self.cfg.tare),
                "counts_per_gram": list(self.cfg.counts_per_gram),
                "sign": list(self.cfg.sign),
                "dt_pins": list(self.cfg.dt_pins),
                "sck_pin": self.cfg.sck_pin,
            }
        if self._link_snapshot is not None:
            try:
                out["link"] = self._link_snapshot()
            except Exception:
                out["link"] = None
        return out

    # ── Live config updates ─────────────────────────────────
    def update_settings(self, **kw) -> None:
        """Hot-update threshold / release / auto / modes / enabled /
        weight_overlay. Pins are NOT runtime-mutable (would require
        re-init); change them in config.json + restart.

        Only persists if something actually changed — keeps the
        admin-poll feedback loop from re-broadcasting identical state."""
        changed = False
        thr_changed = False
        with self._lock:
            for k in ("enabled", "auto_engage", "weight_overlay",
                      "threshold_grams", "engage_seconds", "release_seconds",
                      "occupied_mode", "idle_mode"):
                if k not in kw or kw[k] is None:
                    continue
                old = getattr(self.cfg, k)
                target = type(old)
                new = bool(kw[k]) if target is bool else target(kw[k])
                if new != old:
                    setattr(self.cfg, k, new)
                    changed = True
                    if k == "threshold_grams":
                        thr_changed = True
        if thr_changed:
            self._sync_node_thresholds()   # push the equivalent raw to the legs
        if changed and self._persist:
            self._persist(self.cfg.to_dict())

    def _sync_node_thresholds(self) -> None:
        """Derive each leg node's raw-count occupancy threshold from the
        bench threshold (kg, sum of both legs) and that leg's calibration,
        and push it over the two-way link. Half the total per leg (a centred
        sitter loads both legs roughly equally). No-op without the link."""
        if self._threshold_cmd is None:
            return
        n = max(1, len(self._legs))
        per_leg_g = self.cfg.threshold_grams / n
        for i in range(len(self._legs)):
            cpg = self.cfg.counts_per_gram[i]
            # Uncalibrated (cpg == default 1.0) → the kg→raw conversion is
            # meaningless; leave the node on its own default until calibrated.
            if not cpg or abs(cpg - 1.0) < 1e-6:
                continue
            raw = int(round(abs(per_leg_g * cpg)))
            try:
                self._threshold_cmd(i, raw)
            except Exception:
                logger.exception("scale: node threshold sync failed")

    def tare(self) -> dict:
        """Snapshot the current raw EMA as the zero offset for each leg."""
        with self._lock:
            for i, leg in enumerate(self._legs):
                self.cfg.tare[i] = leg.raw
                # Recompute grams now so the display zeroes immediately even
                # for a leg that's currently stale (no fresh packet would
                # otherwise trigger the read loop to refresh it).
                cpg = self.cfg.counts_per_gram[i] or 1.0
                leg.grams = (leg.raw - self.cfg.tare[i]) / cpg
        logger.info(f"scale: tared at {self.cfg.tare}")
        # Also tell the leg nodes to re-zero their own occupancy baseline so
        # the bench and the UI stay in sync (best-effort over the two-way link).
        if self._tare_cmd:
            for i in range(len(self._legs)):
                try:
                    self._tare_cmd(i)
                except Exception:
                    logger.exception("scale: leg tare command failed")
        if self._persist:
            self._persist(self.cfg.to_dict())
        return {"tare": list(self.cfg.tare)}

    def calibrate(self, known_grams: float) -> dict:
        """Compute counts_per_gram for each leg from the current (tared)
        raw reading and a known weight on the bench. Caller is expected
        to have run tare() with the bench empty first, then to have
        placed the calibration weight before calling this."""
        if known_grams <= 0:
            raise ValueError("known_grams must be > 0")
        with self._lock:
            for i, leg in enumerate(self._legs):
                delta = leg.raw - self.cfg.tare[i]
                # Half the known weight per leg (assumes weight is centered);
                # close enough to set a sane gram scale. Users can refine
                # later by editing config.json.
                cpg = delta / (known_grams / 2.0)
                self.cfg.counts_per_gram[i] = cpg if abs(cpg) > 1e-6 else 1.0
        logger.info(
            f"scale: calibrated counts_per_gram={self.cfg.counts_per_gram} "
            f"@ {known_grams}g"
        )
        # Calibration changed the kg→raw mapping, so refresh the legs' raw
        # occupancy thresholds derived from the bench threshold.
        self._sync_node_thresholds()
        if self._persist:
            self._persist(self.cfg.to_dict())
        return {"counts_per_gram": list(self.cfg.counts_per_gram)}

    # ── Read loop ───────────────────────────────────────────
    def _read_one(self, idx: int) -> Optional[float]:
        # Remote serial source (ESP-NOW legs) takes priority when wired.
        if self._raw_provider is not None:
            return self._raw_provider(idx)
        if self._sensors and idx < len(self._sensors):
            return self._sensors[idx].read_avg()
        # Stub: idle drift + a synthetic occupancy burst every 30 s so the
        # state machine + UI can be exercised on a laptop.
        self._stub_phase += 0.05
        import math
        baseline = math.sin(self._stub_phase + idx) * 50.0
        cyc = (time.monotonic() % 30.0)
        if 10.0 < cyc < 20.0:
            baseline += 30000.0  # "someone is sitting"
        return baseline

    def _read_loop(self) -> None:
        interval = 1.0 / DEFAULT_POLL_HZ
        while self._running:
            t0 = time.monotonic()
            for i in range(2):
                val = self._read_one(i)
                batt = (self._battery_provider(i)
                        if self._battery_provider is not None else None)
                charging = (self._charging_provider(i)
                            if self._charging_provider is not None else False)
                with self._lock:
                    leg = self._legs[i]
                    if batt is not None:
                        leg.battery_mv = batt
                    leg.charging = charging
                    if val is None:
                        leg.ok = False
                    else:
                        # Apply per-leg display polarity. After this point
                        # tare + counts_per_gram are in the post-sign space.
                        val *= self.cfg.sign[i]
                        leg.raw = (
                            val if leg.raw == 0.0
                            else (SMOOTH_ALPHA * val + (1 - SMOOTH_ALPHA) * leg.raw)
                        )
                        cpg = self.cfg.counts_per_gram[i] or 1.0
                        leg.grams = (leg.raw - self.cfg.tare[i]) / cpg
                        leg.last_ts = time.time()
                        leg.ok = True
            dt = time.monotonic() - t0
            sleep_for = interval - dt
            if sleep_for > 0:
                time.sleep(sleep_for)

    # ── State machine ───────────────────────────────────────
    def _state_loop(self) -> None:
        while self._running:
            time.sleep(STATE_TICK_S)
            if not self.cfg.enabled or not self.cfg.auto_engage:
                # Drop both dwell timers so a re-enable doesn't trip
                # immediately on stale state.
                self._above_since = None
                self._empty_since = None
                continue
            with self._lock:
                total = sum(l.grams for l in self._legs)
                any_ok = any(l.ok for l in self._legs)
            if not any_ok:
                continue
            now = time.monotonic()
            if total >= self.cfg.threshold_grams:
                # We're above threshold. Cancel any pending "going-idle"
                # timer and start (or continue) the engage dwell.
                self._empty_since = None
                if not self._occupied:
                    if self._above_since is None:
                        self._above_since = now
                    elif now - self._above_since >= self.cfg.engage_seconds:
                        self._occupied = True
                        self._above_since = None
                        self._safe_switch(
                            self.cfg.occupied_mode,
                            f"scale: occupied ({total:.0f}g ≥ "
                            f"{self.cfg.threshold_grams:.0f}g for "
                            f"{self.cfg.engage_seconds:.0f}s)",
                        )
            else:
                # Below threshold. Cancel the engage dwell — any noise
                # spike that took us above just needs to fall back here
                # to be ignored.
                self._above_since = None
                if self._occupied:
                    release_s = self._effective_release()
                    if self._empty_since is None:
                        self._empty_since = now
                    elif now - self._empty_since >= release_s:
                        self._occupied = False
                        self._empty_since = None
                        self._safe_switch(
                            self.cfg.idle_mode,
                            f"scale: idle ({release_s:.0f}s "
                            f"below threshold)",
                        )

    def _safe_switch(self, mode: str, reason: str) -> None:
        try:
            current = self._get_mode()
            if current == mode:
                return
            self._mode_switcher(mode, reason)
        except Exception:
            logger.exception("scale: mode switch failed")
