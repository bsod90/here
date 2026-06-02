"""Audio playback + live monitor tap for the orchestrator.

One ffmpeg process is the whole audio engine. It reads the ocean backdrop
loop, applies a software volume, then `asplit`s the *same* post-volume
signal two ways:

    ┌─ [spk] ─▶ ALSA (default) ─▶ amp ─▶ bench speakers
    │
  volume@vol ──asplit──┐
    │                  └─ [mon] ─▶ MP3 ─▶ stdout ─▶ orchestrator ─▶ browser

So the browser monitor (Simulator tab) hears a bit-identical copy of what
the speakers play, *after* the volume/mix stage — not a separate parallel
playback. When we add more sources later (intro voice, phone music) they
slot into the same filtergraph (e.g. `amix`) ahead of the split and both
outputs follow automatically.

Volume is changed live and gaplessly via ffmpeg's `azmq` filter: we send
`volume@vol volume <0..1>` over a ZMQ REQ socket and the running graph
updates at the next frame — no process restart, no click. Because volume
now lives in software ahead of the split, the hardware ALSA mixer is
pinned to 100% at start so it doesn't attenuate on top (which would make
the speakers quieter than the monitor stream). If ZMQ is unavailable we
fall back to restarting ffmpeg with the new level.

Public API:

    set_backdrop(on, volume)   → toggle/volume the loop
    snapshot()                 → state dict for the admin panel
    stop()                     → shutdown
    add_listener(loop, queue)  → register a browser monitor stream
    remove_listener(id)        → drop one
"""
from __future__ import annotations

import logging
import shlex
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# pyzmq is the only way to nudge volume on the running graph. Import
# softly so the orchestrator still boots on a box without it (volume
# then falls back to the restart path).
try:
    import zmq
except Exception:  # pragma: no cover - dev box without pyzmq
    zmq = None

# Simple-mixer controls to try, best first. We only use this to pin the
# hardware level to 100% so the software volume is the single authority.
_MIXER_PREFS = ("PCM", "Master", "Speaker", "Headphone", "Digital",
                "Lineout", "Playback")
_UNSET = object()  # "mixer not yet detected" sentinel, distinct from None

# azmq binds here by default; we send volume commands to it as a REQ client.
# (We pass the bare `azmq` filter — escaping a custom bind_address through
# the filtergraph parser is far more trouble than it's worth.)
_ZMQ_ADDR = "tcp://127.0.0.1:5555"
_ZMQ_TIMEOUT_MS = 500
# The named volume-filter instance we target with live commands.
_VOLUME_FILTER = "volume@vol"

_MON_CHUNK = 4096      # bytes per read from ffmpeg's mp3 pipe
_MON_QUEUE_MAX = 128   # per-listener backlog before we drop oldest (slow client)


class AudioPlayer:
    DEFAULT_BACKDROP_FILE = "ocean.wav"

    def __init__(self, media_dir: str | Path,
                 backdrop_file: str = DEFAULT_BACKDROP_FILE,
                 mixer_control: str | None = None,
                 alsa_device: str = "default") -> None:
        self.media_dir = Path(media_dir)
        self.backdrop_file = backdrop_file
        self.alsa_device = alsa_device
        self._mixer_override = mixer_control or None
        # Resolved mixer control name; _UNSET until first use, then a str
        # (usable control) or None (no mixer — nothing to pin).
        self._mixer_control = _UNSET
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._monitor_thread: threading.Thread | None = None
        # Cached state for the snapshot — kept under the lock so the
        # admin poll doesn't race a stop/start.
        self._backdrop_enabled = False
        self._backdrop_volume = 0.5
        # Browser monitor subscribers: id → (event_loop, asyncio.Queue).
        # Guarded by its own lock so the ffmpeg pump thread never contends
        # with playback start/stop.
        self._sub_lock = threading.Lock()
        self._subs: dict[int, tuple] = {}
        self._next_sub_id = 1

    # ── Public API ──────────────────────────────────────────
    def set_backdrop(self, enabled: bool, volume: float | None = None) -> None:
        """Turn the backdrop loop on or off, optionally adjusting volume.

        A volume-only change on the running loop is applied live (gapless)
        via ZMQ; on/off transitions (re)launch or tear down ffmpeg."""
        with self._lock:
            if volume is not None:
                self._backdrop_volume = max(0.0, min(1.0, float(volume)))
            target_on = bool(enabled)

            if target_on == self._backdrop_enabled:
                if target_on and volume is not None:
                    self._apply_volume_locked()
                return

            self._stop_backdrop_locked()
            if target_on:
                self._start_backdrop_locked()
            self._backdrop_enabled = target_on

    def snapshot(self) -> dict:
        with self._lock:
            path = self.media_dir / self.backdrop_file
            with self._sub_lock:
                listeners = len(self._subs)
            return {
                "backdrop_enabled": self._backdrop_enabled,
                "backdrop_volume":  self._backdrop_volume,
                "backdrop_file":    self.backdrop_file,
                "backdrop_present": path.exists(),
                "running":          self._proc is not None
                                    and self._proc.poll() is None,
                "monitor_listeners": listeners,
            }

    def stop(self) -> None:
        """Tear down on shutdown. Safe to call when nothing's playing."""
        with self._lock:
            self._stop_backdrop_locked()
            self._backdrop_enabled = False

    # ── Monitor stream (browser) ────────────────────────────
    def add_listener(self, loop, queue) -> int:
        """Register a browser monitor stream. `queue` is an asyncio.Queue
        owned by `loop`; the ffmpeg pump pushes mp3 chunks into it (and a
        None sentinel when the stream ends). Returns an id for removal."""
        with self._sub_lock:
            sid = self._next_sub_id
            self._next_sub_id += 1
            self._subs[sid] = (loop, queue)
        return sid

    def remove_listener(self, sid: int) -> None:
        with self._sub_lock:
            self._subs.pop(sid, None)

    # ── Internals ───────────────────────────────────────────
    def _start_backdrop_locked(self) -> None:
        path = self.media_dir / self.backdrop_file
        if not path.exists():
            logger.warning(
                "audio: backdrop file not found at %s — toggle is ON but "
                "nothing will play. Make sure deploy copied media/ to "
                "the Pi.", path)
            return
        # Volume now lives in software (the volume@vol filter), so pin the
        # hardware mixer wide open — otherwise it attenuates on top and the
        # speakers end up quieter than the monitor stream.
        self._pin_hardware_mixer_locked()

        vol = self._backdrop_volume
        # filtergraph: live-controllable volume, then split the identical
        # post-volume signal to the speaker + monitor branches.
        fgraph = (f"[0:a]azmq,{_VOLUME_FILTER}={vol:.4f},"
                  f"asplit=2[spk][mon]")
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-stream_loop", "-1", "-i", str(path),
            "-filter_complex", fgraph,
            # Speaker branch → the real card (amp/speakers).
            "-map", "[spk]", "-f", "alsa", self.alsa_device,
            # Monitor branch → MP3 on stdout, drained by the pump thread
            # and fanned out to browser listeners.
            "-map", "[mon]", "-c:a", "libmp3lame", "-b:a", "128k",
            "-flush_packets", "1", "-f", "mp3", "pipe:1",
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.info("audio: started ffmpeg engine %s (vol=%.0f%%) — pid=%d",
                        path.name, vol * 100, self._proc.pid)
        except FileNotFoundError:
            logger.exception("audio: ffmpeg not on PATH — install ffmpeg")
            self._proc = None
            return
        except Exception:
            logger.exception("audio: failed to start engine: %s",
                             shlex.join(cmd))
            self._proc = None
            return
        # Drain stdout → listeners. Daemon so it never blocks shutdown.
        self._monitor_thread = threading.Thread(
            target=self._pump_monitor, args=(self._proc,),
            name="audio-monitor", daemon=True)
        self._monitor_thread.start()

    def _stop_backdrop_locked(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is not None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1.0)
            except Exception:
                logger.exception("audio: error stopping engine")
        # Close out any browser streams — they break their loop on None.
        self._broadcast(None)
        t = self._monitor_thread
        self._monitor_thread = None
        if t is not None and t is not threading.current_thread():
            t.join(timeout=2.0)

    def _apply_volume_locked(self) -> None:
        """Apply the current volume to the running engine without a glitch.
        ZMQ first; only restart if that path is unavailable."""
        if self._send_zmq_volume(self._backdrop_volume):
            return
        self._stop_backdrop_locked()
        self._start_backdrop_locked()

    # ── ffmpeg monitor pump ─────────────────────────────────
    def _pump_monitor(self, proc: subprocess.Popen) -> None:
        """Read MP3 bytes off ffmpeg's stdout and fan them out to every
        listener. Always runs (even with zero listeners) so the pipe never
        backpressures and stalls the speaker output."""
        stream = proc.stdout
        if stream is None:
            return
        try:
            while True:
                chunk = stream.read(_MON_CHUNK)
                if not chunk:
                    break
                self._broadcast(chunk)
        except Exception:
            logger.exception("audio: monitor pump error")
        finally:
            self._broadcast(None)

    def _broadcast(self, chunk) -> None:
        with self._sub_lock:
            subs = list(self._subs.values())
        for loop, queue in subs:
            try:
                loop.call_soon_threadsafe(self._enqueue, queue, chunk)
            except RuntimeError:
                pass  # listener's loop already closed

    @staticmethod
    def _enqueue(queue, chunk) -> None:
        # Runs on the listener's event loop. Bounded queue: drop the oldest
        # chunk if a slow/stalled client falls behind, keeping latency sane.
        try:
            queue.put_nowait(chunk)
        except Exception:
            try:
                queue.get_nowait()
                queue.put_nowait(chunk)
            except Exception:
                pass

    # ── Live volume over ZMQ ────────────────────────────────
    def _send_zmq_volume(self, volume: float) -> bool:
        if zmq is None or self._proc is None or self._proc.poll() is not None:
            return False
        pct = max(0.0, min(1.0, volume))
        sock = None
        try:
            sock = zmq.Context.instance().socket(zmq.REQ)
            sock.setsockopt(zmq.LINGER, 0)
            sock.setsockopt(zmq.RCVTIMEO, _ZMQ_TIMEOUT_MS)
            sock.setsockopt(zmq.SNDTIMEO, _ZMQ_TIMEOUT_MS)
            sock.connect(_ZMQ_ADDR)
            sock.send_string(f"{_VOLUME_FILTER} volume {pct:.4f}")
            reply = sock.recv_string()
        except Exception:
            # azmq not up yet, port not bound, timeout — caller restarts.
            return False
        finally:
            if sock is not None:
                sock.close()
        # azmq replies "0 Success" / "<errno> <msg>".
        return reply.startswith("0 ")

    # ── ALSA hardware mixer (pinned to 100%) ────────────────
    def _pin_hardware_mixer_locked(self) -> None:
        ctrl = self._mixer_control_name()
        if not ctrl:
            return
        cmd = ["amixer", "-M", "set", ctrl, "100%"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if r.returncode != 0:
                logger.warning("audio: amixer set %s 100%% failed: %s",
                               ctrl, r.stderr.strip())
        except Exception:
            logger.exception("audio: amixer pin failed: %s", shlex.join(cmd))

    def _mixer_control_name(self) -> str | None:
        if self._mixer_control is _UNSET:
            self._mixer_control = self._detect_mixer_control()
            logger.info("audio: hardware mixer control for pinning: %r",
                        self._mixer_control)
        return self._mixer_control

    def _detect_mixer_control(self) -> str | None:
        if self._mixer_override:
            return self._mixer_override
        try:
            r = subprocess.run(["amixer", "scontrols"],
                               capture_output=True, text=True, timeout=3)
        except Exception:
            logger.exception("audio: amixer not available")
            return None
        if r.returncode != 0:
            return None
        import re
        names = re.findall(r"Simple mixer control '([^']+)'", r.stdout)
        for pref in _MIXER_PREFS:
            if pref in names:
                return pref
        return names[0] if names else None
