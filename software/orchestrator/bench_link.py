"""Bench link — ESP-NOW leg telemetry received over a serial UART.

The bench legs are now two battery-powered XIAO ESP32-C6 nodes (one per
leg) that read their HX711 load cell + battery voltage and broadcast it
over ESP-NOW. A third XIAO (the "receiver") is wired to the Pi's UART —
its D3/TX → Pi RXD (GPIO15), plus power and ground — and prints one JSON
line per packet:

    {"node":1,"occ":1,"batt_mv":3812,"weight":124530,"boot":42,"rssi":-47}

This module reads those lines in a background thread and keeps the latest
reading per node. `scale.py` pulls raw weight from here (raw_for_leg) in
place of the old on-Pi HX711 GPIO read, so ALL of its tare / calibration /
occupancy / overlay logic is reused unchanged — only the data source moved
off the Pi and onto the radio. Battery voltage is surfaced for the UI.

On a dev laptop (or any host without the port / without pyserial) the
reader can't open the port, logs once, and idles: raw_for_leg returns None
so scale.py falls back to its built-in stub.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Charge detection: a leg is "charging" when its battery voltage is rising.
_CHARGE_WINDOW_S = 180.0   # look back this far for the trend
_CHARGE_MIN_SPAN_S = 60.0  # need at least this much time spanned to judge
_CHARGE_RISE_MV = 15       # rise over the window that means charging
                           # (discharge falls ~8 mV/h, so a rise is unambiguous)

try:
    import serial  # pyserial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.warning("bench_link: pyserial not available — serial telemetry disabled")


@dataclass
class NodeState:
    weight_raw: Optional[float] = None
    battery_mv: Optional[int] = None
    occ: Optional[int] = None       # node's own coarse occupancy flag
    rssi: Optional[int] = None
    boot: Optional[int] = None
    threshold: Optional[int] = None  # node's current occupancy threshold (raw)
    ack: Optional[int] = None        # last command seq the node applied
    fw: Optional[int] = None         # firmware version the node reports
    reset_reason: Optional[int] = None  # esp_reset_reason() (diagnostic)
    cutoff_mv: Optional[int] = None  # node's active low-battery cutoff (mV)
    power_state: Optional[int] = None  # 0 active / 1 power-saving / 2 low-batt
    last_ts: float = 0.0            # monotonic timestamp of last packet
    # Recent (monotonic_ts, mv) for charge detection (rising voltage).
    mv_hist: list = field(default_factory=list)


class BenchLink:
    """Reads the receiver's UART stream and exposes per-leg raw weight +
    battery. Maps node_id (1, 2) → leg index (0, 1)."""

    def __init__(self, *, enabled: bool = True, serial_port: str = "/dev/serial0",
                 baud: int = 115200, stale_after_s: float = 90.0,
                 node_to_leg: Optional[dict] = None) -> None:
        self.enabled = bool(enabled)
        self.port = serial_port
        self.baud = int(baud)
        self.stale_after_s = float(stale_after_s)
        # config JSON keys are strings; normalise to int node id → int leg.
        nm = node_to_leg or {"1": 0, "2": 1}
        self._node_to_leg = {int(k): int(v) for k, v in nm.items()}
        self._leg_to_node = {v: k for k, v in self._node_to_leg.items()}
        self._lock = threading.Lock()
        self._nodes: dict[int, NodeState] = {}
        # Receiver heartbeat — independent of leg traffic, so we can tell
        # "receiver dead/unplugged" apart from "no one is transmitting".
        self._hb_ts = 0.0               # monotonic of last heartbeat (0 = never)
        self._hb_up_ms: Optional[int] = None   # receiver uptime (resets on reboot)
        self._hb_rx: Optional[int] = None      # leg packets it has forwarded
        self._hb_fw: Optional[int] = None      # receiver firmware version
        self._hb_stale_s = 6.0          # offline after ~3 missed beats (2s each)
        self._ser = None                # live serial handle (for writing cmds)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ───────────────────────────────────────────
    def start(self) -> None:
        if not self.enabled:
            logger.info("bench_link: disabled by config")
            return
        if not HAS_SERIAL:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True,
                                        name="bench-link")
        self._thread.start()
        logger.info(f"bench_link: reading {self.port} @ {self.baud} "
                    f"(node→leg {self._node_to_leg})")

    def stop(self) -> None:
        self._running = False

    # ── Providers consumed by scale.py ──────────────────────
    def _fresh(self, ns: Optional[NodeState]) -> bool:
        return ns is not None and (time.monotonic() - ns.last_ts) <= self.stale_after_s

    def raw_for_leg(self, idx: int) -> Optional[float]:
        node = self._leg_to_node.get(idx)
        if node is None:
            return None
        with self._lock:
            ns = self._nodes.get(node)
            if self._fresh(ns) and ns.weight_raw is not None:
                return float(ns.weight_raw)
        return None

    def battery_mv_for_leg(self, idx: int) -> Optional[int]:
        node = self._leg_to_node.get(idx)
        if node is None:
            return None
        with self._lock:
            ns = self._nodes.get(node)
            if self._fresh(ns):
                return ns.battery_mv
        return None

    @staticmethod
    def _power_label(ns: NodeState) -> str:
        """Coarse power state for the UI. Prefers the leg's own report
        (power_state, fw ≥ v10); falls back to the occupancy flag so older
        firmware still shows something sensible."""
        ps = ns.power_state
        if ps == 2:
            return "low-batt"
        if ps == 0:
            return "active"
        if ps == 1:
            return "saving"
        # Fallback for pre-v10 legs: derive from occupancy.
        if ns.occ is None:
            return "—"
        return "active" if ns.occ else "saving"

    @staticmethod
    def _charging(ns: NodeState) -> bool:
        h = ns.mv_hist
        if len(h) < 2:
            return False
        t0, v0 = h[0]
        t1, v1 = h[-1]
        return (t1 - t0) >= _CHARGE_MIN_SPAN_S and (v1 - v0) >= _CHARGE_RISE_MV

    def charging_for_leg(self, idx: int) -> bool:
        node = self._leg_to_node.get(idx)
        if node is None:
            return False
        with self._lock:
            ns = self._nodes.get(node)
            if self._fresh(ns):
                return self._charging(ns)
        return False

    # ── Diagnostics (folded into scale.snapshot under "link") ─
    def snapshot(self) -> dict:
        with self._lock:
            now = time.monotonic()
            nodes = {}
            for node, ns in self._nodes.items():
                age = now - ns.last_ts
                nodes[str(node)] = {
                    "leg": self._node_to_leg.get(node),
                    "battery_mv": ns.battery_mv,
                    "weight_raw": ns.weight_raw,
                    "occ": ns.occ,
                    "rssi": ns.rssi,
                    "boot": ns.boot,
                    "threshold": ns.threshold,
                    "fw": ns.fw,
                    "reset_reason": ns.reset_reason,
                    "cutoff_mv": ns.cutoff_mv,
                    "power_state": ns.power_state,
                    "power_label": self._power_label(ns),
                    "age_s": round(age, 1),
                    "fresh": age <= self.stale_after_s,
                    "charging": self._charging(ns),
                }
            hb_age = (now - self._hb_ts) if self._hb_ts else None
            receiver = {
                "ever_seen": self._hb_ts > 0,
                "online": hb_age is not None and hb_age <= self._hb_stale_s,
                "last_seen_s": round(hb_age, 1) if hb_age is not None else None,
                "up_ms": self._hb_up_ms,
                "rx": self._hb_rx,
                "fw": self._hb_fw,
            }
            return {
                "enabled": self.enabled,
                "available": HAS_SERIAL,
                "port": self.port,
                "baud": self.baud,
                "receiver": receiver,
                "nodes": nodes,
            }

    # ── Reader thread ───────────────────────────────────────
    def _read_loop(self) -> None:
        while self._running:
            try:
                with serial.Serial(self.port, self.baud, timeout=1.0) as ser:
                    self._ser = ser     # expose for command writes
                    logger.info(f"bench_link: opened {self.port}")
                    try:
                        while self._running:
                            line = ser.readline()
                            if not line:
                                continue   # read timeout — re-check _running
                            self._handle_line(
                                line.decode("utf-8", "ignore").strip())
                    finally:
                        self._ser = None
            except Exception as e:
                self._ser = None
                logger.warning(f"bench_link: serial error on {self.port}: {e}; "
                               "retrying in 3s")
                time.sleep(3.0)

    # ── Commands to the legs (Pi → receiver → leg) ──────────
    def _write_line(self, line: str) -> bool:
        ser = self._ser
        if ser is None:
            logger.warning(f"bench_link: cannot send '{line}' — port not open")
            return False
        try:
            ser.write((line + "\n").encode("ascii"))
            ser.flush()
            return True
        except Exception as e:
            logger.warning(f"bench_link: write failed: {e}")
            return False

    def send_tare(self, leg_idx: int) -> bool:
        node = self._leg_to_node.get(leg_idx)
        if node is None:
            return False
        return self._write_line(f"tare {node}")

    def send_threshold(self, leg_idx: int, value: int) -> bool:
        node = self._leg_to_node.get(leg_idx)
        if node is None:
            return False
        return self._write_line(f"thresh {node} {int(value)}")

    def send_cutoff(self, leg_idx: int, mv: int) -> bool:
        node = self._leg_to_node.get(leg_idx)
        if node is None:
            return False
        return self._write_line(f"cutoff {node} {int(mv)}")

    def send_ota_leg(self, leg_idx: int) -> bool:
        node = self._leg_to_node.get(leg_idx)
        if node is None:
            return False
        return self._write_line(f"ota {node}")

    def send_ota_receiver(self) -> bool:
        return self._write_line("ota r")

    def send_reboot_leg(self, leg_idx: int) -> bool:
        node = self._leg_to_node.get(leg_idx)
        if node is None:
            return False
        return self._write_line(f"reboot {node}")

    def send_reboot_receiver(self) -> bool:
        return self._write_line("reboot r")

    def _handle_line(self, line: str) -> None:
        if not line or line.startswith("#"):
            return   # boot banners / comments
        try:
            m = json.loads(line)
        except ValueError:
            return
        # Receiver liveness heartbeat (no "node" — it's the receiver itself).
        if m.get("hb"):
            with self._lock:
                self._hb_ts = time.monotonic()
                if "up_ms" in m:
                    self._hb_up_ms = int(m["up_ms"])
                if "rx" in m:
                    self._hb_rx = int(m["rx"])
                if "fw" in m:
                    self._hb_fw = int(m["fw"])
            return
        node = m.get("node")
        if node is None:
            return
        with self._lock:
            ns = self._nodes.setdefault(int(node), NodeState())
            if "weight" in m:
                ns.weight_raw = float(m["weight"])
            if "batt_mv" in m:
                ns.battery_mv = int(m["batt_mv"])
            if "occ" in m:
                ns.occ = int(m["occ"])
            if "rssi" in m:
                ns.rssi = int(m["rssi"])
            if "boot" in m:
                ns.boot = int(m["boot"])
            if "thr" in m:
                ns.threshold = int(m["thr"])
            if "ack" in m:
                ns.ack = int(m["ack"])
            if "fw" in m:
                ns.fw = int(m["fw"])
            if "rr" in m:
                ns.reset_reason = int(m["rr"])
            if "cut" in m:
                ns.cutoff_mv = int(m["cut"])
            if "ps" in m:
                ns.power_state = int(m["ps"])
            ns.last_ts = time.monotonic()
            # Track the recent voltage trend for charge detection.
            if ns.battery_mv is not None:
                ns.mv_hist.append((ns.last_ts, ns.battery_mv))
                cutoff = ns.last_ts - _CHARGE_WINDOW_S
                ns.mv_hist = [(t, v) for (t, v) in ns.mv_hist if t >= cutoff]
