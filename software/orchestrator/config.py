"""Configuration manager with defaults, persistence, and thread-safe access.

Schema overview
===============

The `DEFAULT_CONFIG` dict below is the canonical schema for everything
the orchestrator persists between runs. Sections fall into one of
three roles — the role tells future-you which keys are safe to delete,
which need migration, and which are written from where.

INFRASTRUCTURE  (set at provisioning time, rarely changed at runtime)
  * targets        — list of WLED endpoints the transport sends to.
                     Written: admin Run-tab "Targets" + restore-defaults.
  * transport      — UDP framing knobs (fps, inter_packet_ms).
                     Written: admin Tune-tab (currently hidden, see note).
  * osc            — OSC server bind + envelope tunings.
                     Written: cold-start only; no UI editor.

TUNING PARAMETERS  (driven by sliders / knobs on the admin Tune tab)
  * breathing      — inhale/hold/exhale/hold + radii + palettes + spin
                     + session phase durations + preview_phase.
  * standby        — sparkle density / max_brightness / spawn_rate / palette.
  * fireplace      — body geometry, turbulence, flare + ember knobs
                     (mirrors DEFAULT_PARAMS in animations/fireplace.py).
  * scene          — synth-for-visuals framework: BPM, curves, physics,
                     synth meta (oval geometry), event defaults, default
                     durations, sequencer config. The Scene class +
                     /api/scene/* routes own this section.
  * scale.shadows  — weight-overlay rendering (color, radii, leg pos).

LIVE / RUNTIME STATE  (engine writes, persisted for reload survival)
  * mode                            — current top-level animation mode.
                                      Engine writes via animation_engine.py
                                      mode setter; migrated from legacy
                                      names ("scene" → "midi" etc.) at
                                      startup. Validated against
                                      MODE_REGISTRY in animation_engine.py.
  * scale.tare / counts_per_gram /
    sign / threshold_grams /
    release_seconds / occupied_mode /
    idle_mode / auto_engage /
    weight_overlay                  — ScaleSensor.update_settings persists
                                      these via its persist_cb.
  * scene.sequencer.active_sequence — pointer to the loaded sequence file
                                      (notes themselves live on disk in
                                      data/sequences/<name>.json).

LEGACY / MIGRATIONS
  * `mode` values "weight", "music", "scene" are migrated to current
    names by animation_engine.__init__ (see LEGACY_MODE_ALIASES).
  * `scale.shadows.leg_positions` (old nested array) is read as a
    fallback in animations/weight_shadows.py if `legN_row/col` are
    missing — old configs still work without explicit migration.

Anything not in the above lists is stale and can probably be removed.
"""
import json
import copy
import threading
from pathlib import Path

DEFAULT_CONFIG = {
    # The embedded simulator UI consumes frames over WebSocket
    # (`/sim/ws`), so it doesn't need its own UDP target. Add other WLED
    # boxes here if there's ever more than one.
    "targets": [
        {"name": "WLED Controller", "ip": "192.168.10.20", "port": 21324, "enabled": True},
    ],
    "mode": "breathing",

    "transport": {
        "inter_packet_ms": 0,
        "fps": 30,
    },

    "breathing": {
        # A "breathing session" walks through phases: fade-in → intro
        # voice → loop → outro voice → chill → fade-out. Each non-loop
        # phase has a duration knob; `preview_phase` forces breathing
        # to render a specific phase right now (useful while we tune
        # stubs — full orchestration lands later).
        "session": {
            "preview_phase":  "auto",       # auto | intro_voice | outro_voice | chill
            "intro_voice_s":   30.0,
            "outro_voice_s":   30.0,
            "chill_s":         90.0,
            "loop_min_s":      60.0,        # minimum time spent in the loop
            "loop_max_s":     600.0,        # graceful upper bound
        },
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
                # Classic violet/teal — 8 slots: rim, inner, outer, trail + 4 extras.
                "rim_color":   [120,  80, 255],
                "inner_color": [ 40, 220, 220],
                "outer_color": [200,  40, 180],
                "trail_color": [ 80,  50, 200],
                "color4":      [255, 180, 100],
                "color5":      [180, 255, 160],
                "color6":      [255,  60,  60],
                "color7":      [255, 255, 255],
            },
            {
                "rim_color":   [ 30, 140, 255],
                "inner_color": [ 10,  80, 120],
                "outer_color": [ 60, 180, 220],
                "trail_color": [ 20,  60, 160],
                "color4":      [200, 240, 255],
                "color5":      [100, 200, 255],
                "color6":      [180,  20, 220],
                "color7":      [255, 255, 200],
            },
            {
                "rim_color":   [255, 120,  40],
                "inner_color": [180,  60,  20],
                "outer_color": [255, 180,  60],
                "trail_color": [200,  80,  30],
                "color4":      [255, 220, 140],
                "color5":      [120,  40,  20],
                "color6":      [255,  80, 200],
                "color7":      [255, 255, 240],
            },
            {
                "rim_color":   [ 50, 255, 120],
                "inner_color": [ 20, 120, 200],
                "outer_color": [100, 255,  80],
                "trail_color": [ 30, 180, 160],
                "color4":      [200, 255, 220],
                "color5":      [  0, 120, 200],
                "color6":      [255, 220,  40],
                "color7":      [255, 255, 255],
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

    "fireplace": {
        # Keep this section in sync with DEFAULT_PARAMS in
        # animations/fireplace.py — the values are duplicated so the
        # admin Tune-tab sliders have something to read on first load.
        "core_radius":          5.0,
        "outer_radius":        12.0,
        "brightness":           1.0,
        "turb_amp":             0.10,
        "turb_speed":           0.7,
        "flicker_amp":          0.025,
        "flicker_smoothing":    0.06,
        "heat_smoothing":       0.45,
        "flare_max":            5,
        "flare_spawn_hz":       2.0,
        "flare_speed_mean":    11.0,
        "flare_life_mean":      0.95,
        "flare_reach_mean":    10.0,
        "flare_base_width":     0.20,
        "flare_tip_width":      0.04,
        "flare_curl_amp":       0.18,
        "flare_curl_freq":      1.8,
        "flare_inner_factor":   0.85,
        "flare_base_heat":      0.55,
        "flare_tip_heat":       0.35,
        "flare_detach_prob":    0.08,
        "flare_detach_factor":  1.12,
        "ember_max":            6,
        "ember_spawn_hz":       2.0,
        "ember_life_mean":      1.05,
        "ember_radius_mean":   16.5,
        "ember_color":         [255, 130, 30],
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

    "osc": {
        "host": "0.0.0.0",
        "port": 9000,
        "attack_ms": 20,
        "release_ms": 180,
    },

    # Audio playback — ocean.wav backdrop loop today, more sounds later.
    # `media_dir` is the on-Pi path; deploy/install.sh syncs the repo's
    # ./media/ → /opt/here/media/ separately from the orchestrator source.
    "audio": {
        "media_dir":         "/opt/here/media",
        # Independent looping ambience tracks, mixed together. Each has its
        # own on/off + software volume (0.0–1.0). Add a track by dropping a
        # file in media/ and adding an entry here.
        "tracks": {
            "ocean":     {"file": "ocean.wav",
                          "label": "Ocean", "enabled": False, "volume": 0.5},
            "fireplace": {"file": "FireFireplace_S08FI.16.wav",
                          "label": "Fireplace", "enabled": False, "volume": 0.5},
        },
        # ALSA simple-mixer control, pinned to 100% so it doesn't attenuate
        # on top of the software volume. Empty = auto-detect (prefers
        # PCM/Master/…); set explicitly to override.
        "mixer_control":     "",
    },

    # Nadia's Playground — isolated experimentation enclave (see
    # docs/nadia_playground.md). Persists her seconds-timeline + recording
    # choice. Kept separate so it can't affect breathing/standby/scene.
    "playground": {
        # timeline clips: [{animation, start_sec, duration_sec}]
        "timeline":        [],
        # uploaded meditation recording filename (under media_dir/playground/)
        "recording_file":  None,
    },

    # Dual-HX711 bench scale. Wiring: DT → 16/19, shared SCK → 21,
    # VCC → 3.3V. counts_per_gram[i] is set by the calibrate API; until
    # then `grams` is just (raw - tare). Threshold is in grams of the
    # *sum* across both legs.
    "scale": {
        "enabled": True,
        "dt_pins": [16, 19],
        "sck_pin": 21,
        "tare": [0.0, 0.0],
        "counts_per_gram": [1.0, 1.0],
        # Per-leg polarity. With the current bench wiring both load cells
        # read negative under load, so flip both. Set to +1 if you swap
        # the cell leads.
        "sign": [-1, -1],
        "auto_engage": True,
        "threshold_grams": 15000.0,
        # Dwell on both sides of the threshold so single-leg sensor
        # noise can't flip the bench state in a single tick.
        "engage_seconds": 5.0,
        "release_seconds": 60.0,
        "occupied_mode": "breathing",
        "idle_mode": "standby",
        # Render the leg-shadow overlay on top of whatever the current
        # mode draws. Independent of auto-engage — you can have a static
        # mode with live weight feedback layered on.
        "weight_overlay": False,
        # "weight" mode rendering — orange glows under each leg.
        # leg_positions are in LED-grid coords (row, col); tune visually.
        # Below threshold no shadow renders. At threshold the shadow is at
        # base_radius; the per-leg excess that maps to max_radius is
        # span_grams (so the blob grows visibly but stays "not by much").
        "shadows": {
            "color": [255, 120, 30],
            "brightness": 0.75,
            "base_radius": 3.0,
            "max_radius":  6.5,
            "span_grams": 60000.0,
            # Flat (row, col) per leg in LED-grid coords [0, 43]. Tune
            # visually via the Weight Overlay sliders in the Tune tab.
            "leg1_row": 10, "leg1_col": 13,
            "leg2_row": 10, "leg2_col": 30,
        },
    },

    "scene": {
        # Active animation name (must exist in scene.animations.REGISTRY).
        "animation": "synth",
        # BPM (persisted; runtime changes also go through this on save).
        "bpm": 120.0,
        # Synth animation meta — geometry of the 3 ovals, brightness, etc.
        "synth": {
            "radius_min":     2.5,
            "radius_max":    16.0,
            "radius_default": 8.0,
            # Three independent ovals (rim, mid, outer) drawn back-to-front.
            "oval_enabled_0": True,  "oval_enabled_1": True,  "oval_enabled_2": True,
            "oval_skew_0":   0.12,   "oval_skew_1":   0.18,   "oval_skew_2":   0.20,
            "oval_phase_0":  0.0,    "oval_phase_1":  1.0,    "oval_phase_2":  2.1,
            "oval_blur_0":   1.8,    "oval_blur_1":   2.5,    "oval_blur_2":   1.2,
            "brightness":    1.0,
        },
        # Four named curves — the shared envelope pool. Events pick which
        # curve to use; the user edits points + interp + length in the
        # Curves tab. Each curve carries a natural duration (in beats)
        # that events inherit when they don't override.
        "curves": {
            "pulse_default":      {"points": [[0, 0], [0.08, 1.0], [1.0, 0]], "interp": "ease_out_quad", "duration_beats": 0.5},
            "transition_default": {"points": [[0, 0], [1, 1]],                "interp": "cosine",       "duration_beats": 1.0},
            "release_default":    {"points": [[0, 1], [1, 0]],                "interp": "cosine",       "duration_beats": 0.5},
            "instant":            {"points": [[0, 1], [1, 1]],                "interp": "linear",       "duration_beats": 0.1},
            # Dissolve / Respawn — separate curve so you can shape the
            # particle-cloud slow-fast feel independently of Expand/Contract.
            "dissolve_default":   {"points": [[0, 0], [1, 1]],                "interp": "linear",       "duration_beats": 4.0},
        },
        # Squishy-ball physics knobs (Float events animate this).
        "physics": {
            "speed":          25.0,
            "radial_offset":   0.12,
            "squishiness":     0.35,
            "damping":         0.3,
            "bounce":          0.75,
            "center_pull":     3.0,
            "tau_squash":      0.25,
            "max_velocity":   40.0,
        },
        # Per-event default duration in beats (used by /api/scene/event/<name>).
        # 0.25 = 1/16, 0.5 = 1/8, 1 = 1/4, 2 = 1/2, 4 = 1 bar, 8 = 2 bars.
        "default_durations": {
            "expand":         4,
            "contract":       4,
            "rotate_cw":      4,
            "rotate_ccw":     4,
            "pulse":          1,
            "blow_out":       8,
            "regrow":         8,
            "color_palette":  2,
        },
        # Piano-roll sequencer. Notes saved as named sequences in
        # `data/sequences/<name>.json` and survive deploys (install.sh
        # excludes data/ from rsync delete).
        "sequencer": {
            "loop_length_beats": 16.0,
            "notes": [],                  # LEGACY — auto-migrated on first run
            "active_sequence": None,
            "sequences_dir": "/opt/here/data/sequences",
        },
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
