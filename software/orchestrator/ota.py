"""OTA service — serves staged firmware images to the bench boards and tracks
versions + check-ins.

The compiled binaries plus a manifest.json ({"version": N}) are staged under
`firmware_dir` by the deploy (built via rpi/scripts/build-firmware.sh). A board
updates by pulling its image with HTTPUpdate, sending its current version in the
`x-ESP32-version` header; we serve a newer image or return 304. That GET is also
the "I'm in OTA mode" handshake — every check-in is logged so the admin can show
which boards have phoned in for an update and what happened.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# kind → staged filename
KIND_FILES = {
    "leg1": "bench_node_1.bin",
    "leg2": "bench_node_2.bin",
    "receiver": "rpi_receiver.bin",
}


class OtaService:
    def __init__(self, firmware_dir: str) -> None:
        self.dir = Path(firmware_dir)
        self._lock = threading.Lock()
        self._checkins: list[dict] = []

    def available_version(self) -> Optional[int]:
        try:
            m = json.loads((self.dir / "manifest.json").read_text())
            return int(m.get("version"))
        except Exception:
            return None

    def binary_path(self, kind: str) -> Optional[Path]:
        fn = KIND_FILES.get(kind)
        if not fn:
            return None
        p = self.dir / fn
        return p if p.exists() else None

    def record_checkin(self, device: str, cur: Optional[int], action: str) -> None:
        with self._lock:
            self._checkins.insert(0, {
                "device": device, "cur": cur, "action": action,
                "ts": time.time(),
            })
            self._checkins = self._checkins[:20]
        logger.info(f"ota: {device} checked in (cur={cur}) → {action}")

    def checkins(self) -> list[dict]:
        with self._lock:
            return list(self._checkins)

    def binaries_present(self) -> dict:
        return {k: (self.binary_path(k) is not None) for k in KIND_FILES}
