#!/usr/bin/env python3
"""HX711 wiring probe + diagnostic.

Two phases:
  1. Diagnostics — for each chip, observe DOUT statically + run a
     power-down/wake test that proves the Pi is actually talking to
     real silicon (not a floating GPIO).
  2. Live readings — raw, tared deltas, sum.

If the orchestrator is running it owns the GPIO pins; stop it first:
    sudo systemctl stop here-orchestrator
    sudo /opt/here/.venv/bin/python rpi/scripts/hx711_probe.py
    sudo systemctl start here-orchestrator

Wiring (per HX711):
    VCC → Pi 3.3V (pin 1)         — *not* 5V, DOUT is push-pull
    GND → Pi GND  (pin 6 or 9)
    DT  → BCM 16 (phys 36) / BCM 19 (phys 35)
    SCK → BCM 21 (phys 40)  (shared between both chips)

BCM ↔ physical pin map for the pins this script uses:
    BCM 16  →  physical pin 36
    BCM 19  →  physical pin 35
    BCM 21  →  physical pin 40
    3.3V    →  physical pin 1  (or 17)
    GND     →  physical pin 6  (or 9, 14, 20, 25, 30, 34, 39)
"""
from __future__ import annotations

import sys
import time

try:
    import lgpio
except ImportError:
    print("lgpio missing — install with: pip install lgpio", file=sys.stderr)
    sys.exit(1)


DT_PINS = (16, 19)
SCK_PIN = 21
SAMPLES_PER_READ = 5
GAIN_PULSES = 1  # 1 → 128 (ch A), 2 → 32 (ch B), 3 → 64 (ch A)


class HX711:
    """Tiny bit-banged HX711 driver. ~80 Hz output, blocking reads.

    Multiple instances can share a single SCK line as long as each
    read brackets its own DT line; we do that here."""

    def __init__(self, chip: int, dt: int, sck: int) -> None:
        self.chip = chip
        self.dt = dt
        self.sck = sck
        # Diagnostic phase may have already claimed these — that's fine.
        try:
            lgpio.gpio_claim_input(chip, dt)
        except lgpio.error:
            pass
        try:
            lgpio.gpio_claim_output(chip, sck, 0)
        except lgpio.error:
            pass

    def _ready(self) -> bool:
        return lgpio.gpio_read(self.chip, self.dt) == 0

    def wait_ready(self, timeout_s: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while not self._ready():
            if time.monotonic() > deadline:
                return False
            time.sleep(0.001)
        return True

    def read_raw(self) -> int | None:
        if not self.wait_ready(1.0):
            return None
        value = 0
        for _ in range(24):
            lgpio.gpio_write(self.chip, self.sck, 1)
            value = (value << 1) | lgpio.gpio_read(self.chip, self.dt)
            lgpio.gpio_write(self.chip, self.sck, 0)
        # Gain-select pulses (also latch next conversion start)
        for _ in range(GAIN_PULSES):
            lgpio.gpio_write(self.chip, self.sck, 1)
            lgpio.gpio_write(self.chip, self.sck, 0)
        # Sign-extend 24-bit two's complement
        if value & 0x800000:
            value -= 0x1000000
        return value

    def read_avg(self, n: int = SAMPLES_PER_READ) -> float | None:
        samples = []
        for _ in range(n):
            v = self.read_raw()
            if v is not None:
                samples.append(v)
        return sum(samples) / len(samples) if samples else None


def diagnose(chip: int, dt: int, sck: int) -> str:
    """Probe one chip without trusting the HX711 protocol. Returns a
    short verdict string; prints details inline.

    The whole point is to confirm the Pi is reading a real HX711 and not
    a floating GPIO. The HX711 holds DOUT high between conversions and
    drops it low when a sample is ready (~10 Hz with the speed jumper
    open, ~80 Hz with it shorted). A floating line just drifts."""
    print(f"\n── Diagnose chip on DT=BCM{dt}, SCK=BCM{sck} ──")

    # Make sure SCK is low so the chip is in normal (not power-down) mode.
    lgpio.gpio_write(chip, sck, 0)
    time.sleep(0.1)

    # Phase 1 — observe DOUT for ~1 s without clocking.
    print("  [1/3] Observing DOUT for 1 s (no clocking)...")
    lo = trans = samples = 0
    last = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 1.0:
        v = lgpio.gpio_read(chip, dt)
        if v == 0:
            lo += 1
        if last is not None and v != last:
            trans += 1
        last = v
        samples += 1
    low_pct = 100 * lo / max(samples, 1)
    print(f"        samples={samples}  low={low_pct:5.1f}%  transitions={trans}")

    # Phase 2 — power-down: SCK high >60 µs forces HX711 into low-power.
    # In that state DOUT is held high. If the line is floating, holding
    # SCK high won't change anything.
    print("  [2/3] Power-down test (SCK held high for 1 ms)...")
    lgpio.gpio_write(chip, sck, 1)
    time.sleep(0.001)
    pd_lo = pd_samples = 0
    t0 = time.monotonic()
    while time.monotonic() - t0 < 0.1:
        if lgpio.gpio_read(chip, dt) == 0:
            pd_lo += 1
        pd_samples += 1
    pd_low_pct = 100 * pd_lo / max(pd_samples, 1)
    print(f"        DOUT low during sleep: {pd_low_pct:5.1f}%   (expect ~0%)")

    # Phase 3 — wake: SCK low for >100 ms, then re-observe.
    lgpio.gpio_write(chip, sck, 0)
    time.sleep(0.1)
    print("  [3/3] Wake test (SCK back to low, observe 0.5 s)...")
    w_lo = w_trans = w_samples = 0
    last = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 0.5:
        v = lgpio.gpio_read(chip, dt)
        if v == 0:
            w_lo += 1
        if last is not None and v != last:
            w_trans += 1
        last = v
        w_samples += 1
    w_low_pct = 100 * w_lo / max(w_samples, 1)
    print(f"        samples={w_samples}  low={w_low_pct:5.1f}%  transitions={w_trans}")

    # ── Interpret ──────────────────────────────────────────────
    # Floating GPIO ≈ a lot of transitions, mid-ish duty cycle, and
    # importantly: phase 2 (SCK held high) doesn't change a thing —
    # exactly the user-reported symptom.
    drift_per_s = w_trans / 0.5
    if pd_low_pct > 5 and abs(pd_low_pct - low_pct) < 5:
        verdict = (
            "✗ SCK has no effect on DOUT — chip not responding. "
            "Likely causes: wrong pin numbering (BCM vs physical), "
            "VCC not at 3.3 V, or GND not shared."
        )
    elif drift_per_s > 50 and 5 < w_low_pct < 95 and pd_low_pct > 1:
        verdict = (
            "✗ DOUT looks like a FLOATING input (rapid noise, SCK doesn't "
            "pin it). Pi probably isn't seeing the HX711 DOUT line at all."
        )
    elif w_low_pct < 1:
        verdict = (
            "? DOUT stuck HIGH. Chip might be powered but never converting "
            "— check load-cell wiring (E+/E-/A+/A-) and that VCC really is "
            "3.3 V at the HX711 board."
        )
    elif w_low_pct > 99:
        verdict = "✗ DOUT stuck LOW. Possible short to GND or chip in a bad state."
    elif w_trans >= 1 and pd_low_pct < 1:
        verdict = "✓ Chip appears alive (DOUT pulses + SCK puts it to sleep)."
    else:
        verdict = "? Inconclusive — re-run after wiggling wires."
    print(f"  ⇒ {verdict}")
    return verdict


def main() -> int:
    chip = lgpio.gpiochip_open(0)
    print(f"Probing HX711s — DT={list(DT_PINS)} (BCM), SCK=BCM{SCK_PIN}")
    print("Physical pin map: DT BCM16=phys36, BCM19=phys35; SCK BCM21=phys40.")

    # Claim pins for the diagnostic. Re-used by HX711 instances below.
    for dt in DT_PINS:
        lgpio.gpio_claim_input(chip, dt)
    lgpio.gpio_claim_output(chip, SCK_PIN, 0)

    verdicts = [diagnose(chip, dt, SCK_PIN) for dt in DT_PINS]

    bad = [v for v in verdicts if v.startswith("✗")]
    if bad:
        print("\nDiagnostic FAILED — fix wiring before trusting any readings.")
        print("Tips:")
        print("  - Multimeter VCC pin on the HX711 board: should read 3.30 V.")
        print("  - Multimeter GND pin: should read 0 V relative to Pi GND.")
        print("  - DT/SCK wires must be on BCM pins (see physical-pin map above),")
        print("    NOT physical pin numbers 16/19/21.")
        print("  - If using a breadboard, reseat the HX711 board pins.")
        lgpio.gpiochip_close(chip)
        return 1

    cells = [HX711(chip, dt, SCK_PIN) for dt in DT_PINS]
    print(f"\nDiagnostics passed. Live readings:")
    print("Taring (keep bench empty for 3 s)...")
    time.sleep(3)
    tares = []
    for c in cells:
        avg = c.read_avg(20)
        tares.append(avg if avg is not None else 0)
        print(f"  GPIO {c.dt}: tare = {tares[-1]:>12,.0f}")
    if all(t == 0 for t in tares):
        print("⚠ all reads timed out — check wiring (VCC, GND, DT, SCK).")
        return 1

    print("\nLive readings (Ctrl-C to quit). Put weight on the bench:")
    print(f"{'time':>8}  {'cell-16':>14}  {'cell-19':>14}  {'sum':>14}")
    t0 = time.monotonic()
    try:
        while True:
            now = time.monotonic() - t0
            row = [f"{now:7.1f}s"]
            total = 0
            for i, c in enumerate(cells):
                avg = c.read_avg()
                delta = (avg - tares[i]) if avg is not None else 0
                total += delta
                row.append(f"{delta:>+14,.0f}")
            row.append(f"{total:>+14,.0f}")
            print("  ".join(row))
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nbye.")
    finally:
        lgpio.gpiochip_close(chip)
    return 0


if __name__ == "__main__":
    sys.exit(main())
