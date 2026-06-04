#!/usr/bin/env python3
"""Headless scene-state renderer — verify animations/transitions without
the bench (CLAUDE.md: "LED animations should be testable without
hardware"). Drives a real Scene with synthetic time, fires events, and
writes a contact-sheet PNG per scenario (captured frames left→right).

Usage:
    .venv/bin/python render_states.py [out_dir]   # default /tmp/here_states
"""
from __future__ import annotations

import struct
import sys
import time as _time
import zlib
from pathlib import Path

import numpy as np

# The BeatClock anchors beats to time.monotonic(). Drive a fake monotonic
# clock so the harness advances beats deterministically (not in real time).
_SIM = {"sec": 100000.0}
_time.monotonic = lambda: _SIM["sec"]   # noqa: E731  (patched before Scene use)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from grid import DEFAULT_GRID                       # noqa: E402
from scene.scene import Scene                       # noqa: E402
from scene.animations.synth import SynthAnimation   # noqa: E402

SIZE = DEFAULT_GRID.size
FPS = 30.0
DT_MS = 1000.0 / FPS

# Vivid 8-slot palette so the border's "all colours" wheel is obvious.
PALETTE = {
    "rim_color":   [120, 90, 255], "inner_color": [40, 220, 220],
    "outer_color": [230, 50, 170], "trail_color": [90, 60, 210],
    "color4":      [255, 170, 70], "color5":      [150, 255, 120],
    "color6":      [255, 70, 70],  "color7":      [120, 200, 255],
}
PARAMS = {"palettes": [PALETTE, PALETTE]}


# ── Minimal PNG writer (no PIL/matplotlib on this box) ───────────
def write_png(path: Path, img: np.ndarray) -> None:
    h, w, _ = img.shape
    raw = bytearray()
    for y in range(h):
        raw.append(0)                     # filter: none
        raw.extend(img[y].tobytes())

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _frame_to_img(frame: bytearray, scale: int = 7) -> np.ndarray:
    arr = np.frombuffer(bytes(frame), dtype=np.uint8).reshape(SIZE, SIZE, 3)
    return np.repeat(np.repeat(arr, scale, 0), scale, 1)


def _montage(imgs: list[np.ndarray], gap: int = 6) -> np.ndarray:
    h = imgs[0].shape[0]
    w = sum(i.shape[1] for i in imgs) + gap * (len(imgs) - 1)
    out = np.full((h, w, 3), 30, dtype=np.uint8)
    x = 0
    for im in imgs:
        out[:, x:x + im.shape[1]] = im
        x += im.shape[1] + gap
    return out


def run(name: str, steps: dict, n_frames: int, capture_at: list[int],
        out_dir: Path, meta: dict | None = None) -> None:
    """steps: {frame_index: callable(scene)} events to fire.
    capture_at: frame indices to snapshot into the contact sheet."""
    _SIM["sec"] += 100.0                      # fresh clock origin per scenario
    anim = SynthAnimation(meta or {})
    scene = Scene(anim, bpm=120.0, grid=DEFAULT_GRID)
    frame = bytearray(DEFAULT_GRID.frame_bytes)
    caps: list[np.ndarray] = []
    for fi in range(n_frames):
        if fi in steps:
            steps[fi](scene)
        _SIM["sec"] += DT_MS / 1000.0         # advance the fake monotonic clock
        t = _SIM["sec"] * 1000.0
        scene.tick(t)
        scene.render(frame, t, PARAMS)
        if fi in capture_at:
            caps.append(_frame_to_img(frame))
    write_png(out_dir / f"{name}.png", _montage(caps))
    print(f"  ✓ {name}.png  ({len(caps)} frames)")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/here_states")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"rendering scene states → {out_dir}")

    fire = lambda ev, **kw: (lambda s: s.trigger(ev, duration_beats=kw.pop("dur", None), params=kw or None))  # noqa: E731

    # 1) blank → border_glow (fade in), then Rotate + Pulse.
    run("01_border", {
        0:  fire("reset_scene"),
        2:  fire("border_glow", dur=1.0),
        30: fire("shimmer", dur=3.0),   # held → border shimmers
        55: fire("rotate_cw"),
        70: fire("pulse"),              # inward swell + uniform brighten
    }, 90, [4, 20, 45, 72, 88], out_dir)

    # 2) empty → floating_particles from beyond the borders (fade in).
    run("02_floating_from_empty", {
        2: fire("floating_particles", dur=2.0),
    }, 130, [4, 20, 45, 80, 125], out_dir)

    # 3) rings → dissolve → settles into floating cloud.
    run("03_dissolve_to_float", {
        2:  fire("expand", dur=0.5),
        20: fire("dissolve", dur=5.0),
    }, 170, [10, 30, 60, 110, 165], out_dir)

    # 4) dissolve→float, then respawn gathers the SAME particles to rings.
    run("04_respawn_from_float", {
        2:   fire("expand", dur=0.5),
        15:  fire("dissolve", dur=4.0),
        95:  fire("respawn", dur=5.0),
    }, 240, [10, 60, 100, 160, 235], out_dir)

    # 5) rings → fade_out + immediate regrow (ghost fades, new rings fade in).
    run("05_fadeout_then_regrow", {
        2:  fire("expand", dur=0.5),
        30: fire("fade_out", dur=3.0),
        33: fire("regrow", dur=3.0),
    }, 140, [10, 32, 50, 80, 135], out_dir)

    # 6) reset → blank canvas.
    run("06_reset", {
        2:  fire("border_glow", dur=0.5),
        40: fire("reset_scene"),
    }, 70, [10, 35, 45, 60], out_dir)

    # 7) border → dissolve_border (the border fades/recedes away).
    run("07_dissolve_border", {
        0:  fire("reset_scene"),
        2:  fire("border_glow", dur=1.0),
        40: fire("dissolve_border", dur=2.0),
    }, 90, [20, 42, 55, 70, 88], out_dir)

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
