"""PatchStore — filesystem-backed CRUD for named "synth patches".

A patch is a snapshot of the scene's synth-side configuration:
  * `synth`            — animation meta (radius defaults, oval params, brightness)
  * `curves`           — full envelope library (points + interp + duration)
  * `physics`          — ball params (speed, damping, etc.)
  * `default_durations` — per-event UI knob values (musical lengths)
  * `event_defaults`   — per-event default params (color, ease, dust density…)
  * `bpm`              — saved tempo
  * `palette_idx`      — saved active palette index

Patches save under `<root>/<safe_name>.json` and survive deploys (same
mechanism as SequenceStore — the install script excludes `data/`).
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
from pathlib import Path

from .sequence_store import sanitize_name

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# Whitelist of patch sections — anything else in the body is dropped on save.
# `active_sequence` is a pointer (not data); when a patch carries one, loading
# the patch also switches the live sequencer to that named sequence.
PATCH_SECTIONS = ("synth", "curves", "physics", "default_durations",
                  "event_defaults", "bpm", "palette_idx", "active_sequence")


class PatchStore:
    def __init__(self, root: Path | str):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def root(self) -> Path:
        return self._root

    def _path(self, name: str) -> Path:
        return self._root / f"{sanitize_name(name)}.json"

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    def list(self) -> list[dict]:
        out: list[dict] = []
        with self._lock:
            for p in sorted(self._root.glob("*.json")):
                try:
                    data = json.loads(p.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                out.append({
                    "name": data.get("name", p.stem),
                    "modified_at": data.get("modified_at"),
                    "has_curves": "curves" in data,
                    "has_synth": "synth" in data,
                    "has_physics": "physics" in data,
                })
        return out

    def load(self, name: str) -> dict | None:
        p = self._path(name)
        with self._lock:
            if not p.is_file():
                return None
            try:
                return json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                logger.exception(f"patch file unreadable: {p}")
                return None

    def save(self, name: str, body: dict) -> str:
        """Write a patch. Only known sections are kept."""
        safe = sanitize_name(name)
        out = {"name": safe, "modified_at": _utcnow()}
        for k in PATCH_SECTIONS:
            if k in body:
                out[k] = body[k]
        with self._lock:
            self._path(safe).write_text(json.dumps(out, indent=2))
        return safe

    def delete(self, name: str) -> bool:
        p = self._path(name)
        with self._lock:
            if not p.is_file():
                return False
            try:
                p.unlink()
                return True
            except OSError:
                logger.exception(f"failed to delete patch file: {p}")
                return False

    def unique_name(self, base: str) -> str:
        safe = sanitize_name(base)
        if not self.exists(safe):
            return safe
        n = 2
        while self.exists(f"{safe}-{n}"):
            n += 1
        return f"{safe}-{n}"
