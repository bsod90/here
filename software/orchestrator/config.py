"""Configuration manager with defaults, persistence, and thread-safe access."""
import json
import copy
import threading
from pathlib import Path

DEFAULT_CONFIG = {
    "targets": [
        {"name": "Simulator", "ip": "127.0.0.1", "port": 21324, "enabled": True},
        {"name": "WLED Controller", "ip": "192.168.10.20", "port": 21324, "enabled": True},
    ],
    "mode": "breathing",

    "transport": {
        "protocol": "ddp",
        "inter_packet_ms": 0,
        "fps": 30,
        "timeout": 255,
        "max_leds_per_packet": 489,
    },

    "breathing": {
        "inhale_ms": 3500,
        "hold_top_ms": 2000,
        "exhale_ms": 3500,
        "hold_bottom_ms": 2000,
        "min_radius": 3.0,
        "max_radius": 17.0,
        "rim_width": 1.8,
        "inner_blur": 3.0,
        "outer_blur": 1.2,
        "active_palette": 0,
        "palettes": [
            {
                "rim_color": [120, 80, 255],
                "inner_color": [40, 220, 220],
                "outer_color": [200, 40, 180],
                "trail_color": [80, 50, 200],
            },
            {
                "rim_color": [30, 140, 255],
                "inner_color": [10, 80, 120],
                "outer_color": [60, 180, 220],
                "trail_color": [20, 60, 160],
            },
            {
                "rim_color": [255, 120, 40],
                "inner_color": [180, 60, 20],
                "outer_color": [255, 180, 60],
                "trail_color": [200, 80, 30],
            },
            {
                "rim_color": [50, 255, 120],
                "inner_color": [20, 120, 200],
                "outer_color": [100, 255, 80],
                "trail_color": [30, 180, 160],
            },
        ],
        "trail_delay_ms": 400,
        "trail_blur": 2.4,
        "trail_opacity": 0.25,
        "brightness": 1.0,
        "spin": {
            "enabled": True,
            "mode": "yoyo",
            "arms": 4,
            "depth": 0.7,
            "constant_speed": 0.3,
            "yoyo_speed": 3.0,
            "yoyo_inertia": 0.995,
            "yoyo_reverse": True,   # True=reverses on exhale, False=always same direction
        },
    },

    "standby": {
        "sparkle_density": 0.03,
        "color_palette": [
            [120, 80, 255],
            [40, 220, 220],
            [200, 40, 180],
            [80, 50, 200],
        ],
        "fade_speed": 0.02,
        "max_brightness": 0.4,
        "spawn_rate": 2,
    },
}


def get_defaults() -> dict:
    """Return a fresh deep copy of DEFAULT_CONFIG. Used by restore-defaults."""
    return copy.deepcopy(DEFAULT_CONFIG)


class ConfigManager:
    def __init__(self, path: str = "config.json"):
        self._path = Path(path)
        self._lock = threading.Lock()
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        try:
            saved = json.loads(self._path.read_text())
            self._deep_merge(self._config, saved)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str):
        with self._lock:
            return copy.deepcopy(self._config.get(key))

    def get_all(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._config)

    def set(self, key: str, value):
        with self._lock:
            if isinstance(value, dict) and key in self._config and isinstance(self._config[key], dict):
                self._deep_merge(self._config[key], value)
            else:
                self._config[key] = value
            self._save()

    def _save(self):
        self._path.write_text(json.dumps(self._config, indent=2))
