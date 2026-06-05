"""Audio playback + live monitor tap for the orchestrator.

A DAW-style in-memory mixer. Every track is decoded once into RAM as
float32 stereo at the device rate; a single real-time PortAudio callback
sums the enabled tracks (each with its own smoothly-ramped gain) and
writes the mix straight to the sound card. Because mixing happens in one
always-running stream:

  * toggling or re-leveling ONE track never touches the others — no
    restart, no gap (only that track's gain ramps);
  * volume changes are a gain ramp, not a process restart (no click);
  * triggering a sound is instant (samples are already in RAM) — latency
    is one audio block (~23 ms at blocksize 1024 / 44.1 kHz);
  * the browser monitor is a *decoupled* tap: the mix is fed to one
    long-lived PCM→MP3 encoder that never restarts when tracks change,
    so the monitor stream stays stable.

      tracks (RAM) ──mix in callback──┬─▶ PortAudio ─▶ ALSA ─▶ amp ─▶ speakers
                                      └─▶ MP3 encoder ─▶ browser monitor

Public API (unchanged, so callers don't change):
    set_track(name, enabled, volume)  → ramp a track on/off / to a level
    set_backdrop(enabled, volume)     → alias for the "ocean" track
    start() / stop()                  → open / close the audio stream
    snapshot()                        → state dict for the admin panel
    add_listener(loop, queue) / remove_listener(id)  → browser monitor
"""
from __future__ import annotations

import logging
import queue
import subprocess
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# PortAudio binding — soft import so the orchestrator still boots (and the
# test suite imports) on a box without it; playback just no-ops then.
try:
    import sounddevice as _sd
except Exception:  # pragma: no cover - dev box without portaudio
    _sd = None

_MIXER_PREFS = ("PCM", "Master", "Speaker", "Headphone", "Digital",
                "Lineout", "Playback")
_UNSET = object()

_OCEAN = "ocean"                 # the legacy single-backdrop track name
_SR = 44100                      # device + mix sample rate
_CHANNELS = 2
_BLOCKSIZE = 1024                # ~23 ms/block — 0 underflows on the Pi 4
_RAMP_S = 0.08                   # gain glide time (smooth, click-free)
_MON_PCM_QMAX = 32               # blocks of mix buffered for the encoder
_MON_CHUNK = 4096                # bytes per read from the encoder's mp3 pipe


class AudioPlayer:
    def __init__(self, media_dir: str | Path,
                 tracks: dict | None = None,
                 mixer_control: str | None = None,
                 alsa_device: str | None = None) -> None:
        self.media_dir = Path(media_dir)
        self.device = alsa_device            # None → PortAudio default
        self._mixer_override = mixer_control or None
        self._mixer_control = _UNSET
        self._lock = threading.Lock()

        # Track model. `data` is the decoded float32 (N,2) buffer (None
        # until the background loader fills it). `gain` is the live mixer
        # gain; `volume`/`enabled` are the targets the callback ramps to.
        # `pos` is the loop playhead, owned by the callback.
        self._tracks: dict[str, dict] = {}
        for name, spec in (tracks or {}).items():
            self._tracks[name] = {
                "file":    str(spec.get("file", "")),
                "label":   str(spec.get("label", name.title())),
                "enabled": bool(spec.get("enabled", False)),
                "volume":  max(0.0, min(1.0, float(spec.get("volume", 0.5)))),
                "loop":    bool(spec.get("loop", True)),
                "data":    None,
                "gain":    0.0,
                "pos":     0,
            }

        self._stream = None
        self._running = False

        # Monitor: decoupled PCM→MP3 encoder fed by the mixer tap.
        self._mon_pcm_q: queue.Queue = queue.Queue(maxsize=_MON_PCM_QMAX)
        self._enc_proc: subprocess.Popen | None = None
        self._enc_writer: threading.Thread | None = None
        self._enc_reader: threading.Thread | None = None
        self._sub_lock = threading.Lock()
        self._subs: dict[int, tuple] = {}
        self._next_sub_id = 1

        # Decode samples into RAM off the boot path so the LED engine isn't
        # blocked for seconds; tracks join the mix as they finish loading.
        self._loader = threading.Thread(target=self._load_all, name="audio-load",
                                         daemon=True)
        self._loader.start()

    # ── Sample loading ──────────────────────────────────────
    def _load_all(self) -> None:
        for name, tr in list(self._tracks.items()):
            path = self.media_dir / tr["file"]
            if not path.exists():
                logger.warning("audio: track %r file missing: %s", name, path)
                continue
            data = self._decode(path)
            if data is not None:
                tr["data"] = data
                logger.info("audio: loaded %s (%.1f s) for track %r",
                            tr["file"], len(data) / _SR, name)

    @staticmethod
    def _decode(path: Path) -> np.ndarray | None:
        """Decode any audio file to float32 stereo @ _SR via a one-shot
        ffmpeg, returned as an (N, 2) array. ffmpeg handles arbitrary
        source rates/channels (e.g. the 96 kHz fireplace sample)."""
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
               "-ar", str(_SR), "-ac", str(_CHANNELS), "-f", "f32le", "pipe:1"]
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=True)
        except Exception:
            logger.exception("audio: ffmpeg decode failed for %s", path)
            return None
        buf = np.frombuffer(r.stdout, dtype=np.float32)
        if buf.size < _CHANNELS:
            return None
        return buf.reshape(-1, _CHANNELS).copy()

    # ── Public API ──────────────────────────────────────────
    def set_track(self, name: str, enabled: bool | None = None,
                  volume: float | None = None) -> None:
        """Ramp a track on/off and/or to a new level. Live and gapless —
        only this track's gain target changes; nothing restarts."""
        with self._lock:
            tr = self._tracks.get(name)
            if tr is None:
                logger.warning("audio: unknown track %r", name)
                return
            if volume is not None:
                tr["volume"] = max(0.0, min(1.0, float(volume)))
            if enabled is not None:
                tr["enabled"] = bool(enabled)
        # The callback picks up the new targets on its next block.

    def set_backdrop(self, enabled: bool, volume: float | None = None) -> None:
        """Back-compat alias for the 'ocean' track."""
        self.set_track(_OCEAN, enabled=enabled, volume=volume)

    def start(self) -> None:
        """Open the output stream (idempotent)."""
        with self._lock:
            if self._running:
                return
            if _sd is None:
                logger.warning("audio: sounddevice unavailable — no playback")
                return
            self._pin_hardware_mixer_locked()
            try:
                self._stream = _sd.OutputStream(
                    samplerate=_SR, blocksize=_BLOCKSIZE, channels=_CHANNELS,
                    dtype="float32", latency="low", device=self.device,
                    callback=self._callback)
                self._stream.start()
                self._running = True
                logger.info("audio: mixer stream started (%d Hz, block=%d, "
                            "~%.0f ms)", _SR, _BLOCKSIZE,
                            1000.0 * _BLOCKSIZE / _SR)
            except Exception:
                logger.exception("audio: failed to open output stream")
                self._stream = None

    def stop(self) -> None:
        with self._lock:
            self._running = False
            st = self._stream
            self._stream = None
        if st is not None:
            try:
                st.stop(); st.close()
            except Exception:
                pass
        self._stop_encoder()

    def snapshot(self) -> dict:
        with self._lock:
            with self._sub_lock:
                listeners = len(self._subs)
            tracks = {}
            for name, tr in self._tracks.items():
                tracks[name] = {
                    "file":    tr["file"],
                    "label":   tr["label"],
                    "enabled": tr["enabled"],
                    "volume":  tr["volume"],
                    "present": tr["data"] is not None,
                }
            snap = {
                "tracks":            tracks,
                "running":           self._running,
                "monitor_listeners": listeners,
            }
            ocean = tracks.get(_OCEAN)
            if ocean is not None:
                snap.update({
                    "backdrop_enabled": ocean["enabled"],
                    "backdrop_volume":  ocean["volume"],
                    "backdrop_file":    ocean["file"],
                    "backdrop_present": ocean["present"],
                })
            return snap

    # ── Real-time mix callback ──────────────────────────────
    def _callback(self, outdata, frames, time_info, status) -> None:
        # Runs on PortAudio's thread — keep it allocation-light and never
        # block. GIL makes plain float/bool reads of the track targets safe.
        mix = np.zeros((frames, _CHANNELS), dtype=np.float32)
        step = frames / (_RAMP_S * _SR)          # max gain change this block
        for tr in self._tracks.values():
            data = tr["data"]
            if data is None:
                continue
            target = tr["volume"] if tr["enabled"] else 0.0
            g0 = tr["gain"]
            if g0 == 0.0 and target == 0.0:
                continue                          # fully silent — skip & freeze
            # Glide gain toward the target across the block.
            if g0 < target:
                g1 = min(target, g0 + step)
            elif g0 > target:
                g1 = max(target, g0 - step)
            else:
                g1 = g0
            n = len(data)
            pos = tr["pos"]
            idx = (np.arange(frames) + pos) % n   # wraps = seamless loop
            seg = data[idx]
            gains = np.linspace(g0, g1, frames, endpoint=False,
                                dtype=np.float32)[:, None]
            mix += seg * gains
            tr["gain"] = g1
            tr["pos"] = (pos + frames) % n
        np.clip(mix, -1.0, 1.0, out=mix)
        outdata[:] = mix
        # Tee to the monitor encoder (drop if it's backed up — monitor is
        # best-effort and must never stall the audio thread).
        try:
            self._mon_pcm_q.put_nowait(mix.tobytes())
        except queue.Full:
            try:
                self._mon_pcm_q.get_nowait()
                self._mon_pcm_q.put_nowait(mix.tobytes())
            except Exception:
                pass

    # ── Browser monitor (decoupled MP3 encoder) ─────────────
    def add_listener(self, loop, q) -> int:
        with self._sub_lock:
            sid = self._next_sub_id
            self._next_sub_id += 1
            self._subs[sid] = (loop, q)
            first = len(self._subs) == 1
        if first:
            self._start_encoder()
        return sid

    def remove_listener(self, sid: int) -> None:
        with self._sub_lock:
            self._subs.pop(sid, None)
            empty = not self._subs
        if empty:
            self._stop_encoder()

    def _start_encoder(self) -> None:
        if self._enc_proc is not None and self._enc_proc.poll() is None:
            return
        # Drain stale PCM so the new listener starts near real-time.
        try:
            while True:
                self._mon_pcm_q.get_nowait()
        except queue.Empty:
            pass
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
               "-f", "f32le", "-ar", str(_SR), "-ac", str(_CHANNELS), "-i", "pipe:0",
               "-c:a", "libmp3lame", "-b:a", "128k", "-flush_packets", "1",
               "-f", "mp3", "pipe:1"]
        try:
            self._enc_proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL)
        except Exception:
            logger.exception("audio: failed to start monitor encoder")
            self._enc_proc = None
            return
        self._enc_writer = threading.Thread(target=self._encoder_feed,
                                            args=(self._enc_proc,),
                                            name="audio-enc-feed", daemon=True)
        self._enc_reader = threading.Thread(target=self._encoder_pump,
                                            args=(self._enc_proc,),
                                            name="audio-enc-pump", daemon=True)
        self._enc_writer.start()
        self._enc_reader.start()

    def _stop_encoder(self) -> None:
        proc = self._enc_proc
        self._enc_proc = None
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=1.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._broadcast(None)

    def _encoder_feed(self, proc: subprocess.Popen) -> None:
        # Pump mix PCM from the callback's queue into the encoder. The
        # callback fills the queue at real time, so this paces naturally.
        stdin = proc.stdin
        try:
            while proc.poll() is None:
                try:
                    chunk = self._mon_pcm_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                stdin.write(chunk)
        except Exception:
            pass

    def _encoder_pump(self, proc: subprocess.Popen) -> None:
        stream = proc.stdout
        try:
            while True:
                chunk = stream.read(_MON_CHUNK)
                if not chunk:
                    break
                self._broadcast(chunk)
        except Exception:
            pass
        finally:
            self._broadcast(None)

    def _broadcast(self, chunk) -> None:
        with self._sub_lock:
            subs = list(self._subs.values())
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(self._enqueue, q, chunk)
            except RuntimeError:
                pass

    @staticmethod
    def _enqueue(q, chunk) -> None:
        try:
            q.put_nowait(chunk)
        except Exception:
            try:
                q.get_nowait()
                q.put_nowait(chunk)
            except Exception:
                pass

    # ── ALSA hardware mixer (pinned to 100%) ────────────────
    def _pin_hardware_mixer_locked(self) -> None:
        ctrl = self._mixer_control_name()
        if not ctrl:
            return
        try:
            subprocess.run(["amixer", "-M", "set", ctrl, "100%"],
                           capture_output=True, text=True, timeout=3)
        except Exception:
            logger.exception("audio: amixer pin failed")

    def _mixer_control_name(self) -> str | None:
        if self._mixer_control is _UNSET:
            self._mixer_control = self._detect_mixer_control()
            logger.info("audio: hardware mixer control: %r", self._mixer_control)
        return self._mixer_control

    def _detect_mixer_control(self) -> str | None:
        if self._mixer_override:
            return self._mixer_override
        try:
            r = subprocess.run(["amixer", "scontrols"],
                               capture_output=True, text=True, timeout=3)
        except Exception:
            return None
        if r.returncode != 0:
            return None
        import re
        names = re.findall(r"Simple mixer control '([^']+)'", r.stdout)
        for pref in _MIXER_PREFS:
            if pref in names:
                return pref
        return names[0] if names else None
