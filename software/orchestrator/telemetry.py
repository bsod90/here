"""System telemetry collector for the HERE Pi.

Background thread samples cheap /proc + /sys files frequently and runs
`vcgencmd` / `journalctl` less often. Snapshots are cached so the admin
endpoint can return without blocking.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from collections import deque
from pathlib import Path
from threading import Lock, Thread


# Sample every 30 s; 120 samples = 1 hour of history for the temp chart.
SAMPLE_INTERVAL_S = 30
HISTORY_LEN = 120


class Telemetry:
    def __init__(self) -> None:
        self._temp_history: deque[dict] = deque(maxlen=HISTORY_LEN)
        self._lock = Lock()
        self._snapshot: dict = {}
        self._stop = False
        self._thread = Thread(target=self._sample_loop, daemon=True, name="telemetry")
        self._started_at = time.time()

    # ------------------------------------------------------------------
    def start(self) -> None:
        # First sample synchronously so the first /api/telemetry hit isn't empty.
        try:
            self._snapshot = self._collect()
            ct = self._snapshot.get("cpu_temp_c")
            if ct is not None:
                self._temp_history.append({"t": int(time.time()), "c": ct})
        except Exception:
            pass
        self._thread.start()

    def stop(self) -> None:
        self._stop = True

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._snapshot)

    def temp_history(self) -> list[dict]:
        with self._lock:
            return list(self._temp_history)

    # ------------------------------------------------------------------
    def _sample_loop(self) -> None:
        while not self._stop:
            try:
                snap = self._collect()
                with self._lock:
                    self._snapshot = snap
                    ct = snap.get("cpu_temp_c")
                    if ct is not None:
                        self._temp_history.append({"t": int(time.time()), "c": ct})
            except Exception:
                pass
            # Coarse sleep — this loop is best-effort, no need for precision.
            for _ in range(SAMPLE_INTERVAL_S):
                if self._stop:
                    return
                time.sleep(1)

    # ------------------------------------------------------------------
    def _collect(self) -> dict:
        snap: dict = {"sampled_at": time.time()}

        # CPU temp from sysfs (cheaper than spawning vcgencmd)
        try:
            raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
            snap["cpu_temp_c"] = round(int(raw) / 1000, 1)
        except Exception:
            pass

        # System uptime (kernel-tracked, not service-tracked)
        try:
            with open("/proc/uptime") as f:
                snap["system_uptime_s"] = int(float(f.read().split()[0]))
        except Exception:
            pass

        # Loadavg
        try:
            with open("/proc/loadavg") as f:
                la = f.read().split()
                snap["loadavg"] = [float(la[0]), float(la[1]), float(la[2])]
        except Exception:
            pass

        # Memory (KB)
        try:
            mem: dict[str, int] = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem[parts[0].rstrip(":")] = int(parts[1])
            snap["mem_total_kb"] = mem.get("MemTotal")
            snap["mem_avail_kb"] = mem.get("MemAvailable")
        except Exception:
            pass

        # Disk for / (the SD card)
        try:
            st = os.statvfs("/")
            snap["disk_total_b"] = st.f_blocks * st.f_frsize
            snap["disk_free_b"] = st.f_bfree * st.f_frsize
        except Exception:
            pass

        # Throttle status — critical signal in playa heat.
        # Bits 0–3: currently happening; bits 16–19: ever happened since boot.
        try:
            out = subprocess.check_output(
                ["vcgencmd", "get_throttled"], timeout=2
            ).decode().strip()
            m = re.match(r"throttled=0x([0-9a-fA-F]+)", out)
            if m:
                bits = int(m.group(1), 16)
                snap["throttle_raw"] = m.group(1)
                snap["throttle"] = {
                    "undervoltage_now":     bool(bits & 0x1),
                    "freq_capped_now":      bool(bits & 0x2),
                    "throttled_now":        bool(bits & 0x4),
                    "soft_temp_limit_now":  bool(bits & 0x8),
                    "undervoltage_ever":    bool(bits & 0x10000),
                    "freq_capped_ever":     bool(bits & 0x20000),
                    "throttled_ever":       bool(bits & 0x40000),
                    "soft_temp_limit_ever": bool(bits & 0x80000),
                }
        except Exception:
            pass

        # WiFi: SSID + signal
        try:
            out = subprocess.check_output(["iwgetid", "-r"], timeout=2).decode().strip()
            snap["wifi_ssid"] = out or None
        except Exception:
            pass
        try:
            with open("/proc/net/wireless") as f:
                for line in f:
                    if line.lstrip().startswith("wlan0"):
                        parts = line.split()
                        # /proc/net/wireless: link, level (dBm), noise
                        snap["wifi_signal_dbm"] = int(float(parts[3]))
                        break
        except Exception:
            pass

        # Network IPs per interface
        try:
            out = subprocess.check_output(
                ["ip", "-4", "-o", "addr"], timeout=2
            ).decode()
            ifaces: dict[str, str] = {}
            for line in out.splitlines():
                m = re.match(r"\d+:\s+(\S+)\s+inet\s+(\S+)", line)
                if m:
                    ifaces[m.group(1)] = m.group(2)
            snap["addrs"] = ifaces
        except Exception:
            pass

        # eth0 link state (WLED cable)
        try:
            with open("/sys/class/net/eth0/operstate") as f:
                snap["eth0_state"] = f.read().strip()
        except Exception:
            pass

        # AP clients (count stations on any AP-mode interface)
        try:
            out = subprocess.check_output(["iw", "dev"], timeout=2).decode()
            ap_ifaces = []
            cur_iface = None
            for line in out.splitlines():
                line = line.strip()
                m = re.match(r"Interface\s+(\S+)", line)
                if m:
                    cur_iface = m.group(1)
                if line.startswith("type AP") and cur_iface:
                    ap_ifaces.append(cur_iface)
            client_count = 0
            for iface in ap_ifaces:
                try:
                    out = subprocess.check_output(
                        ["iw", "dev", iface, "station", "dump"], timeout=2
                    ).decode()
                    client_count += out.count("Station ")
                except Exception:
                    pass
            snap["ap_active"] = bool(ap_ifaces)
            snap["ap_clients"] = client_count
        except Exception:
            pass

        # Boots: count + timestamps of last 5
        try:
            out = subprocess.check_output(
                ["journalctl", "--list-boots", "--no-pager", "--quiet"],
                timeout=3,
            ).decode().strip()
            lines = out.splitlines() if out else []
            snap["boot_count"] = len(lines)
            recent: list[dict] = []
            # Format varies a bit between versions; grab last column-ish chunks.
            for line in lines[-5:]:
                # Lines look like: "  -2 a1b2c3 Mon 2026-05-05 10:00:00 PDT—Mon 2026-05-05 13:00:00 PDT"
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    recent.append({"idx": parts[0], "id": parts[1], "range": parts[2]})
            snap["recent_boots"] = recent
        except Exception:
            pass

        return snap
