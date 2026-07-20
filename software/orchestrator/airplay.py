"""AirPlay receiver — mirror a phone onto the LED floor.

Runs UxPlay (open-source AirPlay server) as a managed subprocess and
advertises the platform as an AirPlay target over mDNS. Custom GStreamer
sink chains carry both streams out of uxplay into the orchestrator:

  video: center square crop → 44×44 RGB → FIFO → engine "airplay" mode
  audio: S16LE 44.1 kHz stereo → FIFO → AudioPlayer aux input

Routing audio through the orchestrator's own mixer (instead of letting
uxplay talk to ALSA) matters for two reasons: the PortAudio stream owns
the output device, and the day/night master gate keeps working.

The engine mode is a runtime takeover, like the meditation controller's:
when mirrored frames start flowing the previous mode is remembered and
the engine switches to "airplay"; when the stream goes idle the previous
mode is restored. Nothing is persisted, so a reboot never boots into a
dead mirror screen.
"""
from __future__ import annotations

import logging
import os
import select
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from grid import FRAME_BYTES

logger = logging.getLogger(__name__)

_READ_CHUNK = 65536
_RELAUNCH_BACKOFF_S = 5.0     # min gap between uxplay (re)launches
_LOG_RING = 60                # uxplay output lines kept for the admin tab


class AirPlayReceiver:
    def __init__(self, config, engine=None, audio=None,
                 frame_bytes: int = FRAME_BYTES) -> None:
        self.config = config
        self.engine = engine
        self.audio = audio
        self.frame_bytes = frame_bytes

        self._stop = threading.Event()
        self._poke = threading.Event()     # wake the monitor immediately
        self._threads: list[threading.Thread] = []
        self._proc: subprocess.Popen | None = None
        self._proc_cmd: list[str] | None = None   # args uxplay was launched with
        self._launch_at = 0.0
        self._test_proc: subprocess.Popen | None = None

        self._lock = threading.Lock()
        self._frame: bytes | None = None   # latest 44×44 RGB frame
        self._frame_ts = 0.0
        self._frames_total = 0
        self._fps = 0.0
        self._streaming = False
        self._prev_mode: str | None = None
        self._log: deque[str] = deque(maxlen=_LOG_RING)
        self._last_error: str | None = None

    # ── Config helpers ──────────────────────────────────────
    def _cfg(self) -> dict:
        return self.config.get("airplay") or {}

    @property
    def _data_dir(self) -> Path:
        return Path(self._cfg().get("data_dir", "/opt/here/data"))

    @property
    def video_fifo(self) -> Path:
        return self._data_dir / "airplay-video.fifo"

    @property
    def audio_fifo(self) -> Path:
        return self._data_dir / "airplay-audio.fifo"

    def enabled(self) -> bool:
        return bool(self._cfg().get("enabled", False))

    # ── Lifecycle ───────────────────────────────────────────
    def start(self) -> None:
        if self._threads:
            return
        self._stop.clear()
        for name, target in (("airplay-monitor", self._monitor_loop),
                             ("airplay-video", self._video_loop),
                             ("airplay-audio", self._audio_loop)):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        self._poke.set()
        self._kill_proc()
        self._kill_test()
        self._set_idle()
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads = []

    def poke(self) -> None:
        """Config changed — converge the uxplay process now, not in 2 s."""
        self._poke.set()

    # ── Status (admin tab) ──────────────────────────────────
    def status(self) -> dict:
        with self._lock:
            proc = self._proc
            return {
                "enabled":       self.enabled(),
                "installed":     shutil.which("uxplay") is not None,
                "running":       proc is not None and proc.poll() is None,
                "streaming":     self._streaming,
                "fps":           round(self._fps, 1),
                "frames":        self._frames_total,
                "name":          self._cfg().get("name", "HERE"),
                "volume":        float(self._cfg().get("volume", 1.0)),
                "test_running":  (self._test_proc is not None
                                  and self._test_proc.poll() is None),
                "last_error":    self._last_error,
                "log":           list(self._log),
            }

    def latest_frame(self) -> bytes | None:
        """Most recent mirrored frame (44×44 RGB), or None before first."""
        return self._frame

    # ── Test pattern (end-to-end check without a phone) ─────
    def start_test(self, seconds: float = 5.0, audio: bool = False) -> bool:
        """Inject a moving test pattern (and optionally a tone) into the
        same FIFOs uxplay writes to — proves the whole receive path
        (FIFO → reader → engine mode → matrix / mixer) minus AirPlay
        itself. Requires the receiver to be enabled (FIFOs exist)."""
        if not self.enabled() or not self._ensure_fifos():
            return False
        self._kill_test()
        seconds = max(1.0, min(60.0, float(seconds)))
        n_vbuf = int(seconds * 30)
        side = int(round((self.frame_bytes // 3) ** 0.5))
        parts = [
            "videotestsrc", "is-live=true", "pattern=ball",
            f"num-buffers={n_vbuf}", "!",
            f"video/x-raw,width={side},height={side},format=RGB,framerate=30/1",
            "!", "filesink", f"location={self.video_fifo}",
            "append=true", "buffer-mode=unbuffered",
        ]
        if audio:
            n_abuf = int(seconds * 44100 / 1024)
            parts += [
                "audiotestsrc", "is-live=true", "wave=sine", "freq=440",
                "volume=0.2", f"num-buffers={n_abuf}", "!",
                "audioconvert", "!",
                "audio/x-raw,format=S16LE,rate=44100,channels=2", "!",
                "filesink", f"location={self.audio_fifo}",
                "append=true", "buffer-mode=unbuffered",
            ]
        cmd = ["gst-launch-1.0", "-q"] + parts
        try:
            self._test_proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=self._gst_env(), start_new_session=True)
            logger.info("airplay: test pattern started (%.0fs%s)",
                        seconds, ", +tone" if audio else "")
            return True
        except Exception:
            logger.exception("airplay: failed to start test pattern")
            self._test_proc = None
            return False

    # ── uxplay process management ───────────────────────────
    def _cmd(self) -> list[str]:
        cfg = self._cfg()
        side = int(round((self.frame_bytes // 3) ** 0.5))
        # The floor is watched from the bench, i.e. from the "top" edge of
        # the matrix — flip so the mirror reads right-side-up from there.
        # Any GStreamer videoflip method works (rotate-180, none, …).
        flip = str(cfg.get("video_flip", "vertical-flip")).strip()
        flip_el = f"videoflip method={flip} ! " if flip and flip != "none" else ""
        vsink = ("videoconvert ! aspectratiocrop aspect-ratio=1/1 ! "
                 f"{flip_el}videoscale ! "
                 f"video/x-raw,width={side},height={side},format=RGB ! "
                 f"filesink location={self.video_fifo} append=true "
                 "buffer-mode=unbuffered")
        asink = ("audioconvert ! audioresample ! "
                 "audio/x-raw,format=S16LE,rate=44100,channels=2 ! "
                 f"filesink location={self.audio_fifo} append=true "
                 "buffer-mode=unbuffered")
        cmd = ["uxplay", "-n", str(cfg.get("name", "HERE")), "-nh",
               "-fps", "30", "-vs", vsink, "-as", asink]
        dec = cfg.get("video_decoder")
        if dec:
            cmd += ["-vd", str(dec)]
        cmd += [str(a) for a in (cfg.get("extra_args") or [])]
        return cmd

    def _gst_env(self) -> dict:
        # The service runs under ProtectHome=read-only — GStreamer's
        # registry cache (normally ~/.cache) must live somewhere writable
        # or every launch pays a full plugin rescan.
        env = dict(os.environ)
        cache = self._data_dir / "cache"
        try:
            cache.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        env["XDG_CACHE_HOME"] = str(cache)
        env["GST_REGISTRY"] = str(cache / "gst-registry.bin")
        return env

    def _ensure_fifos(self) -> bool:
        for p in (self.video_fifo, self.audio_fifo):
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    os.mkfifo(p)
                elif not p.is_fifo():
                    p.unlink()
                    os.mkfifo(p)
            except OSError as e:
                self._last_error = f"cannot create FIFO {p}: {e}"
                logger.warning("airplay: %s", self._last_error)
                return False
        return True

    def _launch(self) -> None:
        if shutil.which("uxplay") is None:
            if self._last_error != "uxplay is not installed":
                self._last_error = "uxplay is not installed"
                logger.warning("airplay: uxplay is not installed — "
                               "run install.sh (apt install uxplay)")
            return
        if not self._ensure_fifos():
            return
        cmd = self._cmd()
        # stdbuf: uxplay's stdout is block-buffered when piped, so without
        # line buffering the admin tab's log tail would lag by kilobytes.
        run = (["stdbuf", "-oL"] + cmd) if shutil.which("stdbuf") else cmd
        try:
            self._proc = subprocess.Popen(
                run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=self._gst_env(), start_new_session=True)
        except Exception as e:
            self._last_error = f"uxplay launch failed: {e}"
            logger.exception("airplay: uxplay launch failed")
            self._proc = None
            return
        self._proc_cmd = cmd
        self._launch_at = time.monotonic()
        self._last_error = None
        threading.Thread(target=self._log_pump, args=(self._proc,),
                         name="airplay-log", daemon=True).start()
        logger.info("airplay: uxplay started (advertised as %r)",
                    self._cfg().get("name", "HERE"))

    def _kill_proc(self) -> None:
        proc, self._proc = self._proc, None
        self._proc_cmd = None
        _kill_group(proc)

    def _kill_test(self) -> None:
        proc, self._test_proc = self._test_proc, None
        _kill_group(proc)

    def _log_pump(self, proc: subprocess.Popen) -> None:
        try:
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").rstrip()
                if line:
                    self._log.append(line)
        except Exception:
            pass

    def _monitor_loop(self) -> None:
        """Converge the uxplay process toward the config: launch when
        enabled (relaunch on crash, backoff-limited), kill when disabled
        or when the launch args went stale (e.g. renamed receiver). Also
        owns the stream-idle timeout."""
        while not self._stop.is_set():
            self._poke.wait(timeout=2.0)
            self._poke.clear()
            if self._stop.is_set():
                break
            alive = self._proc is not None and self._proc.poll() is None
            if self.enabled():
                # FIFOs exist whenever the receiver is enabled, so the
                # readers (and the test-pattern injector) don't depend on
                # uxplay having launched successfully.
                self._ensure_fifos()
                if alive and self._proc_cmd != self._cmd():
                    logger.info("airplay: settings changed — restarting uxplay")
                    self._kill_proc()
                    alive = False
                if not alive:
                    if self._proc is not None:      # crashed — surface it
                        code = self._proc.poll()
                        self._last_error = f"uxplay exited (code {code})"
                        logger.warning("airplay: uxplay exited with code %s "
                                       "— relaunching", code)
                        self._proc = None
                    if time.monotonic() - self._launch_at >= _RELAUNCH_BACKOFF_S:
                        self._launch()
            elif alive:
                logger.info("airplay: disabled — stopping uxplay")
                self._kill_proc()

            # Stream-idle detection → hand the engine mode back.
            idle_s = float(self._cfg().get("idle_timeout_s", 3.0))
            if self._streaming and time.time() - self._frame_ts > idle_s:
                self._set_idle()

    # ── Engine mode takeover ────────────────────────────────
    def _set_streaming(self) -> None:
        with self._lock:
            if self._streaming:
                return
            self._streaming = True
        eng = self.engine
        if eng is not None and eng.mode != "airplay":
            self._prev_mode = eng.mode
            eng.mode = "airplay"
            logger.info("airplay: stream started → mode airplay "
                        "(was %s)", self._prev_mode)

    def _set_idle(self) -> None:
        with self._lock:
            if not self._streaming:
                return
            self._streaming = False
            self._fps = 0.0
        eng = self.engine
        # Only restore if we still own the mode — the user (or the
        # meditation controller) may have switched away meanwhile.
        if eng is not None and eng.mode == "airplay":
            restore = self._prev_mode or self.config.get("mode") or "standby"
            eng.mode = restore
            logger.info("airplay: stream idle → mode restored to %s", restore)
        self._prev_mode = None

    # ── FIFO readers ────────────────────────────────────────
    def _video_loop(self) -> None:
        buf = bytearray()

        def on_data(chunk: bytes) -> None:
            buf.extend(chunk)
            while len(buf) >= self.frame_bytes:
                frame = bytes(buf[:self.frame_bytes])
                del buf[:self.frame_bytes]
                now = time.time()
                with self._lock:
                    dt = now - self._frame_ts
                    if 0.0 < dt < 2.0:
                        inst = 1.0 / max(dt, 1e-3)
                        self._fps = (0.85 * self._fps + 0.15 * inst
                                     if self._fps else inst)
                    self._frame = frame
                    self._frame_ts = now
                    self._frames_total += 1
                self._set_streaming()

        self._fifo_loop(self.video_fifo, on_data, on_gap=buf.clear)

    def _audio_loop(self) -> None:
        buf = bytearray()

        def on_data(chunk: bytes) -> None:
            if self.audio is None:
                return
            buf.extend(chunk)
            # Feed whole S16LE stereo sample-frames (4 bytes) only, so a
            # split read never shifts the channel/byte alignment.
            usable = len(buf) - (len(buf) % 4)
            if usable:
                vol = float(self._cfg().get("volume", 1.0))
                self.audio.feed_aux(bytes(buf[:usable]), volume=vol)
                del buf[:usable]

        self._fifo_loop(self.audio_fifo, on_data, on_gap=buf.clear)

    def _fifo_loop(self, path: Path, on_data, on_gap) -> None:
        """Robust non-blocking FIFO consumer: opens lazily (the writer —
        uxplay's filesink — connects whenever a stream starts), survives
        writer EOFs (client disconnects) without reopening, and drops any
        partial tail at a gap so frame alignment can never drift."""
        fd = None
        try:
            while not self._stop.is_set():
                if not self.enabled():
                    if fd is not None:
                        os.close(fd)
                        fd = None
                    on_gap()
                    time.sleep(0.5)
                    continue
                if fd is None:
                    if not path.is_fifo():
                        time.sleep(0.5)
                        continue
                    try:
                        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                    except OSError:
                        time.sleep(0.5)
                        continue
                try:
                    ready, _, _ = select.select([fd], [], [], 0.25)
                except OSError:
                    os.close(fd)
                    fd = None
                    continue
                if not ready:
                    continue
                try:
                    chunk = os.read(fd, _READ_CHUNK)
                except BlockingIOError:
                    continue
                except OSError:
                    os.close(fd)
                    fd = None
                    on_gap()
                    continue
                if not chunk:
                    # EOF: no writer right now. The fd stays valid for the
                    # next writer; just don't spin on the EOF condition.
                    on_gap()
                    time.sleep(0.2)
                    continue
                on_data(chunk)
        finally:
            if fd is not None:
                os.close(fd)


def _kill_group(proc: subprocess.Popen | None) -> None:
    """Terminate a start_new_session subprocess and its children."""
    if proc is None:
        return
    import signal as _signal
    try:
        os.killpg(os.getpgid(proc.pid), _signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            return
    try:
        proc.wait(timeout=2.0)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
