"""Animation engine — runs the frame loop in a dedicated thread."""
import threading
import time
import logging

from grid import FRAME_BYTES, TOTAL
from animations import breathing, standby, debug

# Power constants (from docs/inventory.md)
WATTS_PER_LED_FULL_WHITE = 0.1  # WS2811 at full RGB white
SYSTEM_IDLE_WATTS = 10.5        # RPi(5W) + WLED(1W) + Fan(1.5W) + Amp idle(2W) + misc(1W)

logger = logging.getLogger(__name__)


class AnimationEngine:
    def __init__(self, config, transport):
        self.config = config
        self.transport = transport
        self.frame = bytearray(FRAME_BYTES)
        self._mode = config.get("mode") or "breathing"
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._standby_state = {}
        self._start_time = 0.0
        self._fps = 0.0
        self._frame_count = 0
        self._fps_time = 0.0
        self._led_watts = 0.0
        self._power_samples: list[float] = []  # rolling window
        self._power_window = 30.0  # seconds

    @property
    def mode(self):
        with self._lock:
            return self._mode

    @mode.setter
    def mode(self, value):
        with self._lock:
            self._mode = value
            if value == "standby":
                self._standby_state = {}

    @property
    def actual_fps(self):
        return round(self._fps, 1)

    @property
    def uptime_seconds(self):
        if self._start_time == 0:
            return 0
        return round(time.monotonic() - self._start_time)

    @property
    def power_estimate(self) -> dict:
        """Estimate current power draw from frame buffer contents."""
        led_w = self._led_watts
        total_w = SYSTEM_IDLE_WATTS + led_w
        # Daily estimate at current draw
        daily_wh = total_w * 24
        # Battery runtime (2x 48V 50Ah = 4096Wh usable at 80% DoD)
        battery_wh = 4096
        runtime_days = battery_wh / daily_wh if daily_wh > 0 else 999
        return {
            "led_watts": round(led_w, 1),
            "system_watts": round(SYSTEM_IDLE_WATTS, 1),
            "total_watts": round(total_w, 1),
            "daily_wh": round(daily_wh),
            "battery_days": round(runtime_days, 1),
        }

    def start(self):
        self._running = True
        self._start_time = time.monotonic()
        self._fps_time = self._start_time
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Animation engine started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Animation engine stopped")

    def _loop(self):
        while self._running:
            fps = self.config.get("transport").get("fps", 22)
            target_interval = 1.0 / max(fps, 1)
            frame_start = time.monotonic()
            time_ms = (frame_start - self._start_time) * 1000

            mode = self.mode

            if mode == "breathing":
                params = self.config.get("breathing")
                breathing.render(self.frame, time_ms, params)
            elif mode == "standby":
                params = self.config.get("standby")
                standby.render(self.frame, time_ms, params, self._standby_state)
            elif mode == "debug":
                debug.render(self.frame, time_ms, {})
            elif mode == "off":
                for i in range(len(self.frame)):
                    self.frame[i] = 0

            self.transport.send_frame(self.frame)

            # Power estimate: 30-second rolling average
            rgb_sum = sum(self.frame)
            instant_watts = (rgb_sum / (255 * 3)) * WATTS_PER_LED_FULL_WHITE
            now = time.monotonic()
            self._power_samples.append((now, instant_watts))
            # Trim samples older than window
            cutoff = now - self._power_window
            while self._power_samples and self._power_samples[0][0] < cutoff:
                self._power_samples.pop(0)
            # Average
            if self._power_samples:
                self._led_watts = sum(w for _, w in self._power_samples) / len(self._power_samples)
            else:
                self._led_watts = instant_watts

            # FPS tracking
            self._frame_count += 1
            now = time.monotonic()
            elapsed_fps = now - self._fps_time
            if elapsed_fps >= 1.0:
                self._fps = self._frame_count / elapsed_fps
                self._frame_count = 0
                self._fps_time = now

            # Sleep to maintain framerate
            elapsed = now - frame_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
