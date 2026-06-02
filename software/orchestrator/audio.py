"""Audio playback for the orchestrator.

Today it does one thing: an ocean backdrop loop the user can toggle on
and off. The implementation is intentionally simple — `ffplay` (ships
with ffmpeg, already installed via install.sh) as a subprocess, with
`-loop 0` for infinite looping and `-volume` for level. We don't pull
in pygame / SDL just to start a single file.

The architecture is designed to grow, though. The public surface is:

    set_backdrop(on, volume)        → toggle the always-on loop
    play_oneshot(name, volume)      → fire-and-forget short SFX (future)
    snapshot()                       → state dict for the admin panel

When we add more sounds (intro voice, SFX synced to events) we'll add
extra named "channels" on top of the same subprocess model — ALSA's
dmix lets multiple `ffplay` processes share the audio device without
fighting. If/when we need tight animation-sync we'll switch the
backend to a Python audio library (pygame.mixer or sounddevice) so we
can query playback position; the public API above doesn't change.

Volume: ffplay's `-volume` is a launch-time flag with no runtime knob,
so naively re-applying volume meant killing and restarting the process
— an audible gap/click on every slider step. Instead we drive the ALSA
hardware mixer with `amixer` (from alsa-utils, already installed), which
changes the output level live with no glitch. ffplay then runs at a
fixed 100% and the mixer is the single source of truth. If no usable
mixer control is found (odd sound card, container, etc.) we fall back to
the old restart-with-`-volume` path so volume still works, just not
gaplessly. `mixer_control` can be set explicitly in config to override
auto-detection.
"""
from __future__ import annotations

import logging
import re
import shlex
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Simple-mixer controls to try, best first. The Pi's 3.5mm analog out
# (where the amp lives) exposes "PCM"; USB/HDMI cards vary, hence the list.
_MIXER_PREFS = ("PCM", "Master", "Speaker", "Headphone", "Digital",
                "Lineout", "Playback")
_UNSET = object()  # "mixer not yet detected" sentinel, distinct from None


class AudioPlayer:
    DEFAULT_BACKDROP_FILE = "ocean.wav"

    def __init__(self, media_dir: str | Path,
                 backdrop_file: str = DEFAULT_BACKDROP_FILE,
                 mixer_control: str | None = None) -> None:
        self.media_dir = Path(media_dir)
        self.backdrop_file = backdrop_file
        self._mixer_override = mixer_control or None
        # Resolved mixer control name; _UNSET until first detection, then
        # a str (usable control) or None (no mixer — use restart fallback).
        self._mixer_control = _UNSET
        self._lock = threading.Lock()
        self._backdrop_proc: subprocess.Popen | None = None
        # Cached state for the snapshot — kept under the lock so the
        # admin poll doesn't race a stop/start.
        self._backdrop_enabled = False
        self._backdrop_volume = 0.5

    # ── Public API ──────────────────────────────────────────
    def set_backdrop(self, enabled: bool, volume: float | None = None) -> None:
        """Turn the backdrop loop on or off, optionally adjusting volume.

        If `enabled` is True and the loop is already running, restart
        it with the new volume; if False, kill the subprocess. Idempotent:
        calling with the same state is a no-op."""
        with self._lock:
            if volume is not None:
                self._backdrop_volume = max(0.0, min(1.0, float(volume)))
            target_on = bool(enabled)

            if target_on == self._backdrop_enabled:
                # No on/off transition. A volume-only change on the running
                # loop is applied live via the mixer — no restart, no glitch.
                if target_on and volume is not None:
                    self._apply_volume_locked()
                return

            # On/off transition — (re)launch or tear down the subprocess.
            self._stop_backdrop_locked()
            if target_on:
                self._start_backdrop_locked()
            self._backdrop_enabled = target_on

    def snapshot(self) -> dict:
        with self._lock:
            path = self.media_dir / self.backdrop_file
            ctrl = self._mixer_control
            return {
                "backdrop_enabled": self._backdrop_enabled,
                "backdrop_volume":  self._backdrop_volume,
                "backdrop_file":    self.backdrop_file,
                "backdrop_present": path.exists(),
                "running":          self._backdrop_proc is not None
                                    and self._backdrop_proc.poll() is None,
                # null until first volume op; str = live mixer control in
                # use; "" = no mixer (volume changes restart the player).
                "mixer_control":    None if ctrl is _UNSET else (ctrl or ""),
            }

    def stop(self) -> None:
        """Tear down on shutdown. Safe to call when nothing's playing."""
        with self._lock:
            self._stop_backdrop_locked()
            self._backdrop_enabled = False

    # ── Internals ───────────────────────────────────────────
    def _start_backdrop_locked(self) -> None:
        path = self.media_dir / self.backdrop_file
        if not path.exists():
            logger.warning(
                "audio: backdrop file not found at %s — toggle is ON but "
                "nothing will play. Make sure deploy copied media/ to "
                "the Pi.", path)
            return
        # ffplay flags:
        #   -nodisp       no GUI (we'd get an SDL window otherwise)
        #   -autoexit     exit when stream ends (with -loop 0 it doesn't,
        #                 but harmless if file becomes seekable etc.)
        #   -loop 0       loop forever
        #   -volume 0-100 software gain
        #   -hide_banner  drop the ffmpeg startup chatter
        #   -loglevel error  quieter; surface real failures only
        # Prefer the live ALSA mixer for volume; if it's available ffplay
        # runs at a fixed 100% and the mixer owns the level (so slider
        # tweaks don't restart us). Otherwise bake the level into -volume.
        if self._set_mixer_volume_locked(self._backdrop_volume):
            vol = 100
        else:
            vol = int(round(self._backdrop_volume * 100))
        cmd = [
            "ffplay", "-nodisp", "-autoexit", "-loop", "0",
            "-volume", str(vol),
            "-hide_banner", "-loglevel", "error",
            str(path),
        ]
        try:
            self._backdrop_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info(
                "audio: started backdrop %s (vol=%d%%) — pid=%d",
                path.name, vol, self._backdrop_proc.pid)
        except FileNotFoundError:
            logger.exception(
                "audio: ffplay not on PATH — install ffmpeg "
                "(apt install ffmpeg) or fall back to aplay")
            self._backdrop_proc = None
        except Exception:
            logger.exception("audio: failed to start backdrop: %s",
                             shlex.join(cmd))
            self._backdrop_proc = None

    def _stop_backdrop_locked(self) -> None:
        proc = self._backdrop_proc
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        except Exception:
            logger.exception("audio: error stopping backdrop")
        finally:
            self._backdrop_proc = None

    def _apply_volume_locked(self) -> None:
        """Apply the current volume to a running loop without a glitch.

        Tries the live mixer first; only if that's unavailable do we fall
        back to a stop/start so the new `-volume` takes effect."""
        if self._set_mixer_volume_locked(self._backdrop_volume):
            return
        # No mixer — restart so the level changes (audible gap, but rare).
        self._stop_backdrop_locked()
        self._start_backdrop_locked()

    # ── ALSA mixer (live, gapless volume) ───────────────────
    def _mixer_control_name(self) -> str | None:
        """Resolved simple-mixer control, or None if there isn't one.
        Detected once and cached (incl. the negative result)."""
        if self._mixer_control is _UNSET:
            self._mixer_control = self._detect_mixer_control()
            if self._mixer_control:
                logger.info("audio: using ALSA mixer control %r for volume",
                            self._mixer_control)
            else:
                logger.info("audio: no usable ALSA mixer control — volume "
                            "changes will restart the player")
        return self._mixer_control

    def _detect_mixer_control(self) -> str | None:
        if self._mixer_override:
            return self._mixer_override
        try:
            r = subprocess.run(["amixer", "scontrols"],
                               capture_output=True, text=True, timeout=3)
        except Exception:
            logger.exception("audio: amixer not available for volume control")
            return None
        if r.returncode != 0:
            return None
        # Lines look like:  Simple mixer control 'PCM',0
        names = re.findall(r"Simple mixer control '([^']+)'", r.stdout)
        for pref in _MIXER_PREFS:
            if pref in names:
                return pref
        return names[0] if names else None

    def _set_mixer_volume_locked(self, volume: float) -> bool:
        """Set the ALSA control to `volume` (0–1). Returns True on success,
        False if there's no control or amixer fails (→ caller falls back)."""
        ctrl = self._mixer_control_name()
        if not ctrl:
            return False
        pct = int(round(max(0.0, min(1.0, volume)) * 100))
        # -M = perceptual (mapped) volume — a linear slider then feels linear.
        cmd = ["amixer", "-M", "set", ctrl, f"{pct}%"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        except Exception:
            logger.exception("audio: amixer set failed: %s", shlex.join(cmd))
            return False
        if r.returncode != 0:
            logger.warning("audio: amixer set %s %d%% failed: %s",
                           ctrl, pct, r.stderr.strip())
            return False
        return True
