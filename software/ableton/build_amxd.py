#!/usr/bin/env python3
"""Build a .amxd from a patcher JSON, using the factory blank as a template.

The .amxd container is three chunks: `ampf` (header), `meta` (metadata), and
`ptch` (the patcher JSON). Each chunk is `<4-byte tag><4-byte LE length><data>`.

We copy `ampf` and `meta` from the factory blank, then swap in our own JSON
for `ptch`. This sidesteps trying to author the M4L-side wrapper from scratch.

Usage:
    build_amxd.py <input.json> <output.amxd> [--template path]
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

FACTORY = "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max MIDI Effect.amxd"


def _read_chunks(blob: bytes) -> list[tuple[bytes, bytes]]:
    """Parse <tag:4><len:LE32><data:len> chunks until exhausted."""
    out, i = [], 0
    while i < len(blob):
        tag = blob[i : i + 4]
        (length,) = struct.unpack("<I", blob[i + 4 : i + 8])
        data = blob[i + 8 : i + 8 + length]
        out.append((tag, data))
        i += 8 + length
    return out


def _write_chunks(chunks: list[tuple[bytes, bytes]]) -> bytes:
    parts = []
    for tag, data in chunks:
        parts.append(tag)
        parts.append(struct.pack("<I", len(data)))
        parts.append(data)
    return b"".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="patcher JSON file")
    ap.add_argument("output", type=Path, help="destination .amxd")
    ap.add_argument("--template", type=Path, default=Path(FACTORY))
    args = ap.parse_args()

    if not args.template.exists():
        raise SystemExit(
            f"factory template not found at {args.template} — pass --template "
            "pointing at a blank Max Audio Effect.amxd from your Live install"
        )

    template_chunks = _read_chunks(args.template.read_bytes())
    new_patcher_json = args.input.read_bytes()
    out_chunks: list[tuple[bytes, bytes]] = []
    for tag, data in template_chunks:
        if tag == b"ptch":
            out_chunks.append((tag, new_patcher_json))
        else:
            out_chunks.append((tag, data))

    args.output.write_bytes(_write_chunks(out_chunks))
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
