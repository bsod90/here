"""Multi-target UDP DNRGB transport with health checking."""
import socket
import threading
import time
import logging
import urllib.request
from grid import FRAME_BYTES

logger = logging.getLogger(__name__)

DNRGB_PROTOCOL = 2
MAX_LEDS_PER_PACKET = 489  # (1472 MTU - 3 header) // 3 bytes per LED
HEALTH_CHECK_INTERVAL = 5  # seconds


class UDPTransport:
    def __init__(self, targets: list[dict]):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._lock = threading.Lock()
        self._targets = []  # [{name, ip, port, enabled, status}]
        self.update_targets(targets)

        # Start health checker
        self._running = True
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()

    def update_targets(self, targets: list[dict]):
        with self._lock:
            self._targets = [
                {
                    "name": t.get("name", "Unknown"),
                    "ip": t["ip"],
                    "port": t["port"],
                    "enabled": t.get("enabled", True),
                    "status": "unknown",
                }
                for t in targets
            ]

    def get_targets(self) -> list[dict]:
        with self._lock:
            return [t.copy() for t in self._targets]

    def send_frame(self, frame: bytearray):
        with self._lock:
            enabled = [(t["ip"], t["port"]) for t in self._targets if t["enabled"]]

        total_leds = len(frame) // 3
        led_index = 0
        offset = 0

        while led_index < total_leds:
            chunk_leds = min(MAX_LEDS_PER_PACKET, total_leds - led_index)
            chunk_bytes = chunk_leds * 3

            packet = bytearray(3 + chunk_bytes)
            packet[0] = DNRGB_PROTOCOL
            packet[1] = (led_index >> 8) & 0xFF
            packet[2] = led_index & 0xFF
            packet[3:] = frame[offset:offset + chunk_bytes]

            for ip, port in enabled:
                try:
                    self._sock.sendto(packet, (ip, port))
                except OSError:
                    pass  # fire and forget

            led_index += chunk_leds
            offset += chunk_bytes

    def _health_loop(self):
        while self._running:
            with self._lock:
                targets = [(i, t.copy()) for i, t in enumerate(self._targets)]

            for i, t in targets:
                status = self._check_health(t["ip"], t["port"])
                with self._lock:
                    if i < len(self._targets):
                        self._targets[i]["status"] = status

            time.sleep(HEALTH_CHECK_INTERVAL)

    @staticmethod
    def _check_health(ip: str, port: int) -> str:
        """Probe target reachability.

        WLED: try HTTP GET /json/info on port 80.
        Simulator: try HTTP GET on port 3000 (UDP is on 21324).
        Generic: try connecting TCP to the HTTP port.
        """
        # Try WLED JSON API (port 80)
        for http_port in (80, 3000, 3443):
            try:
                url = f"http://{ip}:{http_port}/"
                req = urllib.request.Request(url, method="HEAD")
                urllib.request.urlopen(req, timeout=2)
                return "online"
            except Exception:
                continue

        return "offline"

    def stop(self):
        self._running = False
