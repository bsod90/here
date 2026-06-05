"""Audio playback + live monitor tap for the orchestrator.

One ffmpeg process is the whole audio engine. It loops every *enabled*
track, applies a per-track software volume, mixes them, then `asplit`s
the *same* post-mix signal two ways:

    ┌─ [spk] ─▶ ALSA (default) ─▶ amp ─▶ bench speakers
    │
  tracks ─volume@vol_<name>─▶ amix ──asplit──┐
    │                                         └─ [mon] ─▶ MP3 ─▶ stdout ─▶ browser

So the browser monitor (Simulator tab) hears a bit-identical copy of what
the speakers play, *after* the volume/mix stage — not a separate parallel
playback. Multiple ambiences (ocean, fireplace, …) are independent tracks
that slot into the same filtergraph; both outputs follow automatically.

Per-track volume is changed live and gaplessly via ffmpeg's `azmq` filter:
we send `volume@vol_<name> volume <0..1>` over a ZMQ REQ socket and the
running graph updates at the next frame — no process restart, no click.
Toggling a track on/off changes the input set, so that *does* relaunch
ffmpeg. Because volume lives in software ahead of the split, the hardware
ALSA mixer is pinned to 100% at start so it doesn't attenuate on top. If
ZMQ is unavailable we fall back to restarting ffmpeg with the new level.

Public API:

    set_track(name, enabled, volume)  → toggle/volume one track
    set_backdrop(enabled, volume)     → alias for the "ocean" track (compat)
    snapshot()                        → state dict for the admin panel
    stop()                            → shutdown
    add_listener(loop, queue)         → register a browser monitor stream
    remove_listener(id)               → drop one
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

_MON_CHUNK = 4096      # bytes per read from ffmpeg's mp3 pipe
_MON_QUEUE_MAX = 128   # per-listener backlog before we drop oldest (slow client)

# Resample every track to one device-friendly rate. The ALSA card here is
# pinned at 44.1 kHz; a source at another rate (e.g. a 96 kHz fireplace
# sample) otherwise fails the ALSA link ("Cannot select sample rate") when
# it's the only track. Resampling per chain also lets amix combine tracks
# of differing native rates.
_SAMPLE_RATE = 44100

# The named track every legacy caller (main.py boot, the playground ocean
# toggle) addresses through set_backdrop()/the backdrop_* snapshot fields.
_OCEAN = "ocean"


class AudioPlayer:
    def __init__(self, media_dir: str | Path,
                 tracks: dict | None = None,
                 mixer_control: str | None = None,
                 alsa_device: str = "default") -> None:
        self.media_dir = Path(media_dir)
        self.alsa_device = alsa_device
        self._mixer_override = mixer_control or None
        # Resolved mixer control name; _UNSET until first use, then a str
        # (usable control) or None (no mixer — nothing to pin).
        self._mixer_control = _UNSET
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._monitor_thread: threading.Thread | None = None
        # Track model: ordered {name: {"file", "enabled", "volume", "label"}}.
        # Insertion order is stable, so ffmpeg input indices stay consistent.
        self._tracks: dict[str, dict] = {}
        for name, spec in (tracks or {}).items():
            self._tracks[name] = {
                "file":    str(spec.get("file", "")),
                "enabled": bool(spec.get("enabled", False)),
                "volume":  max(0.0, min(1.0, float(spec.get("volume", 0.5)))),
                "label":   str(spec.get("label", name.title())),
            }
        # Browser monitor subscribers: id → (event_loop, asyncio.Queue).
        self._sub_lock = threading.Lock()
        self._subs: dict[int, tuple] = {}
        self._next_sub_id = 1

    # ── Public API ──────────────────────────────────────────
    def set_track(self, name: str, enabled: bool | None = None,
                  volume: float | None = None) -> None:
        """Update one track. A volume-only change to a playing track is
        applied live (gapless) via ZMQ; enabling/disabling a track changes
        the ffmpeg input set, so that relaunches the engine."""
        with self._lock:
            tr = self._tracks.get(name)
            if tr is None:
                logger.warning("audio: unknown track %r", name)
                return
            prev_enabled_set = self._enabled_names_locked()
            if volume is not None:
                tr["volume"] = max(0.0, min(1.0, float(volume)))
            if enabled is not None:
                tr["enabled"] = bool(enabled)

            if self._enabled_names_locked() != prev_enabled_set:
                # Input set changed → rebuild the graph.
                self._stop_backdrop_locked()
                if self._enabled_names_locked():
                    self._start_backdrop_locked()
            elif volume is not None and tr["enabled"]:
                # Same inputs, just a level tweak → live, no restart.
                self._apply_volume_locked(name)

    def set_backdrop(self, enabled: bool, volume: float | None = None) -> None:
        """Back-compat alias: the original single 'ocean' backdrop."""
        self.set_track(_OCEAN, enabled=enabled, volume=volume)

    def start(self) -> None:
        """Boot-time: launch the engine for whatever tracks are enabled in
        the loaded config (so a backdrop left ON survives a restart)."""
        with self._lock:
            if self._proc is None and self._enabled_names_locked():
                self._start_backdrop_locked()

    def snapshot(self) -> dict:
        with self._lock:
            with self._sub_lock:
                listeners = len(self._subs)
            running = self._proc is not None and self._proc.poll() is None
            tracks = {}
            for name, tr in self._tracks.items():
                path = self.media_dir / tr["file"]
                tracks[name] = {
                    "file":    tr["file"],
                    "label":   tr["label"],
                    "enabled": tr["enabled"],
                    "volume":  tr["volume"],
                    "present": path.exists(),
                }
            snap = {
                "tracks":            tracks,
                "running":           running,
                "monitor_listeners": listeners,
            }
            # Legacy mirror of the ocean track so existing callers (the
            # playground ocean toggle, the Run-tab "Ocean backdrop" controls)
            # keep working unchanged.
            ocean = tracks.get(_OCEAN)
            if ocean is not None:
                snap.update({
                    "backdrop_enabled": ocean["enabled"],
                    "backdrop_volume":  ocean["volume"],
                    "backdrop_file":    ocean["file"],
                    "backdrop_present": ocean["present"],
                })
            return snap

    def stop(self) -> None:
        """Tear down on shutdown. Safe to call when nothing's playing."""
        with self._lock:
            self._stop_backdrop_locked()
            for tr in self._tracks.values():
                tr["enabled"] = False

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
    def _enabled_names_locked(self) -> tuple[str, ...]:
        """Names of enabled tracks whose files exist, in stable order."""
        out = []
        for name, tr in self._tracks.items():
            if tr["enabled"] and (self.media_dir / tr["file"]).exists():
                out.append(name)
        return tuple(out)

    def _build_filtergraph(self, names: tuple[str, ...]) -> str:
        """Build the ffmpeg filtergraph for the enabled tracks.

        Single track: volume → asplit directly (no amix — amix is for 2+
        inputs and a single-input amix yields no usable output). Multiple:
        one volume chain per track → amix → asplit. The azmq command
        listener sits on the first chain either way."""
        if len(names) == 1:
            name = names[0]
            vol = self._tracks[name]["volume"]
            return (f"[0:a]azmq,volume@vol_{name}={vol:.4f},"
                    f"aresample={_SAMPLE_RATE},asplit=2[spk][mon]")
        chains, labels = [], []
        for idx, name in enumerate(names):
            vol = self._tracks[name]["volume"]
            azmq = "azmq," if idx == 0 else ""
            chains.append(f"[{idx}:a]{azmq}volume@vol_{name}={vol:.4f},"
                          f"aresample={_SAMPLE_RATE}[a{idx}]")
            labels.append(f"[a{idx}]")
        # normalize=0 keeps each track's level independent (no auto-duck).
        mix = (f"{''.join(labels)}amix=inputs={len(names)}:normalize=0[mix];"
               f"[mix]asplit=2[spk][mon]")
        return ";".join(chains) + ";" + mix

    def _start_backdrop_locked(self) -> None:
        names = self._enabled_names_locked()
        if not names:
            return
        # Volume lives in software (the volume@vol_* filters), so pin the
        # hardware mixer wide open — otherwise it attenuates on top.
        self._pin_hardware_mixer_locked()

        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"]
        for name in names:
            cmd += ["-stream_loop", "-1", "-i",
                    str(self.media_dir / self._tracks[name]["file"])]
        cmd += [
            "-filter_complex", self._build_filtergraph(names),
            "-map", "[spk]", "-f", "alsa", self.alsa_device,
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
            logger.info("audio: started ffmpeg engine tracks=%s — pid=%d",
                        ",".join(names), self._proc.pid)
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

    def _apply_volume_locked(self, name: str) -> None:
        """Apply one track's current volume to the running engine without a
        glitch. ZMQ first; only restart if that path is unavailable."""
        if self._send_zmq_volume(name, self._tracks[name]["volume"]):
            return
        self._stop_backdrop_locked()
        if self._enabled_names_locked():
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
    def _send_zmq_volume(self, name: str, volume: float) -> bool:
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
            sock.send_string(f"volume@vol_{name} volume {pct:.4f}")
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
