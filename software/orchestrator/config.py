"""Configuration manager with defaults, persistence, and thread-safe access."""
import json
import copy
import threading
from pathlib import Path

DEFAULT_CONFIG = {
    "targets": [
        {"name": "Simulator", "ip": "127.0.0.1", "port": 21324, "enabled": True},
    ],
    "mode": "breathing",

    "breathing": {
        "inhale_ms": 3500,
        "hold_top_ms": 500,
        "exhale_ms": 3500,
        "hold_bottom_ms": 500,
        "min_radius": 3.0,
        "max_radius": 18.0,
        "rim_width": 1.8,
        "inner_blur": 4.0,
        "outer_blur": 1.2,
        "rim_color": [120, 80, 255],
        "inner_color": [40, 220, 220],
        "outer_color": [200, 40, 180],
        "trail_delay_ms": 400,
        "trail_blur": 3.0,
        "trail_opacity": 0.3,
        "trail_color": [80, 50, 200],
        "brightness": 1.0,
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
