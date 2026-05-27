"""SequenceStore — filesystem-backed CRUD for named sequencer sequences.

Each saved sequence is a JSON file under `<root>/<safe_name>.json`. The store
sanitises names, lists what's on disk, and round-trips through `Sequencer.set_*`
when loading/saving the active one.

File schema:
    {
        "name": "first-jam",
        "loop_length_beats": 16.0,
        "notes": [{"pitch": int, "start_beat": float, "length_beats": float}, ...],
        "modified_at": "<ISO 8601>"
    }
"""
from __future__ import annotations

import datetime
import json
import logging
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_name(name: str) -> str:
    """Lower-case-ish slug; preserves underscores/dashes/dots."""
    if not name:
        return "untitled"
    cleaned = _SAFE_NAME_RE.sub("-", name.strip())
    # Collapse runs of dashes.
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-.")
    return cleaned or "untitled"


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class SequenceStore:
    def __init__(self, root: Path | str):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def root(self) -> Path:
        return self._root

    # ── Naming ──────────────────────────────────────────────────
    def _path(self, name: str) -> Path:
        return self._root / f"{sanitize_name(name)}.json"

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    # ── List ────────────────────────────────────────────────────
    def list(self) -> list[dict]:
        """Return a summary of every saved sequence, sorted by name."""
        out: list[dict] = []
        with self._lock:
            for p in sorted(self._root.glob("*.json")):
                try:
                    data = json.loads(p.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                out.append({
                    "name": data.get("name", p.stem),
                    "loop_length_beats": float(data.get("loop_length_beats", 16.0)),
                    "note_count": len(data.get("notes") or []),
                    "modified_at": data.get("modified_at"),
                })
        return out

    # ── Read ────────────────────────────────────────────────────
    def load(self, name: str) -> dict | None:
        p = self._path(name)
        with self._lock:
            if not p.is_file():
                return None
            try:
                return json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                logger.exception(f"sequence file unreadable: {p}")
                return None

    # ── Write ───────────────────────────────────────────────────
    def save(self, name: str, *, notes: list[dict], loop_length_beats: float) -> str:
        """Write a sequence file. Returns the sanitized name actually used."""
        safe = sanitize_name(name)
        body = {
            "name": safe,
            "loop_length_beats": float(loop_length_beats),
            "notes": list(notes or []),
            "modified_at": _utcnow(),
        }
        with self._lock:
            self._path(safe).write_text(json.dumps(body, indent=2))
        return safe

    # ── Duplicate / delete ──────────────────────────────────────
    def duplicate(self, source_name: str, new_name: str) -> str | None:
        data = self.load(source_name)
        if data is None:
            return None
        return self.save(new_name, notes=data.get("notes") or [],
                         loop_length_beats=data.get("loop_length_beats", 16.0))

    def delete(self, name: str) -> bool:
        p = self._path(name)
        with self._lock:
            if not p.is_file():
                return False
            try:
                p.unlink()
                return True
            except OSError:
                logger.exception(f"failed to delete sequence file: {p}")
                return False

    def unique_name(self, base: str) -> str:
        """Return `<base>` if free, else `<base>-2`, `-3`, etc."""
        safe = sanitize_name(base)
        if not self.exists(safe):
            return safe
        n = 2
        while self.exists(f"{safe}-{n}"):
            n += 1
        return f"{safe}-{n}"
