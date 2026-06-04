#!/usr/bin/env python3
"""Validate a HERE Max for Live device WITHOUT opening Ableton.

This is the "does it load / is the UI sane" gate. Opening Live by hand on
every rebuild is slow and Max has no headless batch mode, so we check the
two things that actually break a generated device — the .amxd container
and the patcher JSON structure — statically. It catches the large
majority of "device won't load / renders broken" regressions in <100ms.

Layers (see software/ableton/README.md → Testing):
  L3  .amxd container integrity   — chunk parse, MIDI-effect type, valid ptch
  L2  .maxpat structural lint     — wiring, ids, params, MIDI pass-through,
                                     presentation layout fits Live's 169px

Format facts are from Ableton's own parser, maxdevtools/maxdiff/
amxd_textconv.py: the file is a flat sequence of <tag:4><len:LE32><data>
chunks; `ampf` holds a 4-char device-type code (mmmm=MIDI, aaaa=Audio,
iiii=Instrument); `ptch` is the patcher JSON (or a frozen `mx@c` blob);
`ciph` means encrypted. We mirror those names here.

Usage:
    ./lint_device.py [HERE.amxd|HERE.maxpat] [--factory <blank.amxd>]
    # exit 0 = clean, 1 = errors. Warnings never fail the build.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

# One device "rack unit" is 169px. Devices may be several units tall
# (Live grows them), so height isn't a hard error — but past this we warn,
# since a very tall device is awkward to work with in Live.
DEVICE_MAX_HEIGHT_PX = 169  # Live HARD-clips M4L devices at one rack unit
# Interactive controls — these must never overlap each other (the "give
# the knobs space" rule). Labels (live.comment) are exempt.
INTERACTIVE = {"live.dial", "live.button", "live.toggle", "live.text",
               "live.numbox", "live.slider", "live.menu", "textedit"}
# MIDI-effect device-type code in the `ampf` chunk.
MIDI_EFFECT_TYPE = b"mmmm"


class LintResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stats: dict[str, object] = {}

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


# ── .amxd container (L3) ─────────────────────────────────────────
def read_chunks(blob: bytes) -> list[tuple[bytes, bytes]]:
    """Parse <tag:4><len:LE32><data> until exhausted. Raises on truncation."""
    out, i = [], 0
    while i < len(blob):
        if i + 8 > len(blob):
            raise ValueError(f"truncated chunk header at offset {i}")
        tag = blob[i : i + 4]
        (length,) = struct.unpack("<I", blob[i + 4 : i + 8])
        end = i + 8 + length
        if end > len(blob):
            raise ValueError(
                f"chunk {tag!r} claims {length} bytes but only "
                f"{len(blob) - i - 8} remain")
        out.append((tag, blob[i + 8 : end]))
        i = end
    return out


def lint_amxd(path: Path, res: LintResult,
              factory: Path | None = None) -> dict | None:
    """Validate the .amxd container; return the parsed patcher dict or None."""
    blob = path.read_bytes()
    try:
        chunks = read_chunks(blob)
    except ValueError as e:
        res.err(f"container: {e}")
        return None
    by_tag = {}
    for tag, data in chunks:
        by_tag.setdefault(tag, data)
    res.stats["chunks"] = [t.decode("latin1") for t, _ in chunks]

    if b"ciph" in by_tag:
        res.err("container: device is encrypted (ciph chunk) — cannot validate")
        return None

    ampf = by_tag.get(b"ampf")
    if ampf is None:
        res.err("container: missing ampf (device-type) chunk")
    elif ampf[:4] != MIDI_EFFECT_TYPE:
        res.err(f"container: ampf type is {ampf[:4]!r}, expected "
                f"{MIDI_EFFECT_TYPE!r} (MIDI Effect)")

    if factory is not None and factory.exists():
        fmeta = {t: d for t, d in read_chunks(factory.read_bytes())}.get(b"meta")
        if fmeta is not None and by_tag.get(b"meta") != fmeta:
            res.err("container: meta chunk differs from factory template "
                    "(build_amxd should copy it verbatim)")
    elif b"meta" not in by_tag:
        res.warn("container: no meta chunk (factory unavailable to compare)")

    ptch = by_tag.get(b"ptch")
    if ptch is None:
        res.err("container: missing ptch (patcher) chunk")
        return None
    if ptch[:4] == b"mx@c":
        res.err("container: ptch is a frozen device (mx@c) — expected raw JSON")
        return None
    # Ableton's parser strips a single trailing null if present.
    raw = ptch[:-1] if ptch[-1:] == b"\x00" else ptch
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        res.err(f"container: ptch is not valid JSON — {e}")
        return None


# ── .maxpat structure (L2) ───────────────────────────────────────
def _is_whole_pixel(rect) -> bool:
    return all(isinstance(v, (int, float)) and float(v) == int(v) for v in rect)


def lint_patcher(patcher_doc: dict, base_dir: Path, res: LintResult) -> None:
    pat = patcher_doc.get("patcher")
    if not isinstance(pat, dict):
        res.err("patcher: missing top-level 'patcher' object")
        return

    if pat.get("openinpresentation") != 1:
        res.err("patcher: openinpresentation != 1 — device would open in "
                "patcher view instead of its UI")

    devicewidth = pat.get("devicewidth")
    if not isinstance(devicewidth, (int, float)):
        res.warn("patcher: no devicewidth set; using 920 for bounds check")
        devicewidth = 920.0

    boxes = [b.get("box", {}) for b in pat.get("boxes", [])]
    lines = [l.get("patchline", {}) for l in pat.get("lines", [])]
    res.stats["boxes"] = len(boxes)
    res.stats["patchlines"] = len(lines)

    # ids unique + index
    ids: dict[str, dict] = {}
    for b in boxes:
        bid = b.get("id")
        if bid is None:
            res.err("box without an id")
            continue
        if bid in ids:
            res.err(f"duplicate box id {bid!r}")
        ids[bid] = b

    # patchline referential + port-bounds integrity
    def _port_ok(box: dict, idx: int, kind: str) -> bool:
        n = box.get("numinlets" if kind == "in" else "numoutlets")
        return True if not isinstance(n, int) else 0 <= idx < n

    for ln in lines:
        src = ln.get("source") or [None, None]
        dst = ln.get("destination") or [None, None]
        for end, who in ((src, "source"), (dst, "destination")):
            if end[0] not in ids:
                res.err(f"patchline {who} references unknown box {end[0]!r}")
        if src[0] in ids and not _port_ok(ids[src[0]], src[1], "out"):
            res.err(f"patchline from {src[0]!r} uses outlet {src[1]} out of range")
        if dst[0] in ids and not _port_ok(ids[dst[0]], dst[1], "in"):
            res.err(f"patchline to {dst[0]!r} uses inlet {dst[1]} out of range")

    # object presence: MIDI pass-through + our IO objects
    def _texts(prefix: str) -> list[dict]:
        return [b for b in boxes if b.get("maxclass") == "newobj"
                and (b.get("text") or "").split()[:1] == [prefix]]

    if not _texts("midiin"):
        res.err("no `midiin` — incoming MIDI never reaches the device")
    if not _texts("midiout"):
        res.err("no `midiout` — MIDI would NOT pass through to the instrument "
                "downstream (the device would block the track)")
    if not _texts("udpsend"):
        res.warn("no `udpsend` — nothing emits OSC to the Pi")

    # live.text buttons: texton defaults to "B", so a button that sets
    # `text` but not `texton` flips to "B" when pressed (a real footgun).
    bad_texton = [b.get("id") for b in boxes
                  if b.get("maxclass") == "live.text"
                  and b.get("text") and not b.get("texton")]
    if bad_texton:
        res.warn(f"{len(bad_texton)} live.text button(s) set text but not "
                 "texton — they show the default 'B' when pressed")

    # newobj boxes whose text starts with one of our v8 message selectors
    # are almost certainly meant to be MESSAGE boxes — as objects Max says
    # "<verb>: No such object" and the send silently dies.
    MSG_VERBS = {"note", "noteoff", "palette", "reset", "tap", "bpm"}
    bad_obj = [b.get("id") for b in boxes if b.get("maxclass") == "newobj"
               and (b.get("text") or "").split()[:1]
               and (b.get("text") or "").split()[0] in MSG_VERBS]
    if bad_obj:
        res.err(f"{len(bad_obj)} newobj box(es) start with a message verb "
                "(note/noteoff/palette/reset/…) — these must be message boxes, "
                "not objects (Max: 'No such object')")

    # v8 logic box + its .js exists
    v8 = _texts("v8")
    if not v8:
        res.err("no `v8` object — the JS logic isn't loaded")
    for b in v8:
        for tok in (b.get("text") or "").split()[1:]:
            if tok.endswith(".js"):
                if not (base_dir / tok).exists():
                    res.err(f"v8 references {tok!r} but it's missing next to "
                            f"the device ({base_dir / tok})")

    # parameters: present + unique long/short names (Live requires uniqueness)
    longs: dict[str, int] = {}
    shorts: dict[str, int] = {}
    nparams = 0
    for b in boxes:
        if b.get("parameter_enable") != 1:
            continue
        nparams += 1
        valueof = (b.get("saved_attribute_attributes") or {}).get("valueof") or {}
        ln_ = valueof.get("parameter_longname")
        sn_ = valueof.get("parameter_shortname")
        if not ln_:
            res.err(f"box {b.get('id')!r} is parameter-enabled but has no "
                    "parameter_longname")
        else:
            longs[ln_] = longs.get(ln_, 0) + 1
        if sn_:
            shorts[sn_] = shorts.get(sn_, 0) + 1
    for name, n in longs.items():
        if n > 1:
            res.err(f"duplicate parameter long name {name!r} (x{n}) — Live "
                    "requires unique names")
    for name, n in shorts.items():
        if n > 1:
            res.warn(f"duplicate parameter short name {name!r} (x{n})")
    res.stats["parameters"] = nparams

    # presentation layout: in-bounds + whole-pixel + device height
    over_w = neg = subpixel = 0
    pres_n = 0
    max_bottom = 0.0
    pres_boxes = []  # (box, rect) for the overlap pass
    for b in boxes:
        if b.get("presentation") != 1:
            continue
        rect = b.get("presentation_rect")
        if not (isinstance(rect, list) and len(rect) == 4):
            continue
        pres_n += 1
        pres_boxes.append((b, rect))
        x, y, w, h = rect
        if x < 0 or y < 0:
            neg += 1
        if x + w > devicewidth + 1:
            over_w += 1
        max_bottom = max(max_bottom, y + h)
        if not _is_whole_pixel(rect):
            subpixel += 1
    res.stats["presentation_boxes"] = pres_n
    res.stats["device_height"] = round(max_bottom)
    if neg:
        res.err(f"{neg} presentation box(es) have negative x/y (off-canvas)")
    if over_w:
        res.err(f"{over_w} presentation box(es) extend past devicewidth "
                f"({devicewidth:g}px)")
    if max_bottom > DEVICE_MAX_HEIGHT_PX + 1:
        res.err(f"content is {max_bottom:.0f}px tall — Live clips M4L devices "
                f"at {DEVICE_MAX_HEIGHT_PX}px, so anything below is cut off")
    if subpixel:
        res.warn(f"{subpixel} presentation rect(s) use sub-pixel coords "
                 "(Ableton guideline: whole pixels only)")

    # interactive controls must not overlap each other — this is the
    # "give the knobs space" gate. (Labels/comments are allowed to sit
    # close; only real controls are checked.)
    def _overlaps(r1, r2) -> bool:
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return not (x1 + w1 <= x2 or x2 + w2 <= x1
                    or y1 + h1 <= y2 or y2 + h2 <= y1)

    # Controls on different tab pages legitimately share coordinates (only
    # one page is visible at a time). We scope the overlap check per page,
    # using the scripting-name prefix `<page>__…` the generator assigns.
    def _page_of(b) -> str:
        vn = b.get("varname") or ""
        return vn.split("__", 1)[0] if "__" in vn else ""

    ctrls = [(b, r) for b, r in pres_boxes
             if b.get("maxclass") in INTERACTIVE or b.get("parameter_enable") == 1]
    by_page: dict[str, list] = {}
    for b, r in ctrls:
        by_page.setdefault(_page_of(b), []).append((b, r))

    clashes = 0
    seen_pairs = set()
    for group in by_page.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _overlaps(group[i][1], group[j][1]):
                    clashes += 1
                    if len(seen_pairs) < 3:
                        seen_pairs.add(
                            f"{group[i][0].get('id')}↔{group[j][0].get('id')}")
    if clashes:
        res.err(f"{clashes} pair(s) of controls overlap within a page "
                f"(cramped UI) e.g. {', '.join(sorted(seen_pairs))}")


# ── Entry points ─────────────────────────────────────────────────
def lint(path: Path, factory: Path | None = None) -> LintResult:
    res = LintResult()
    if not path.exists():
        res.err(f"file not found: {path}")
        return res
    base_dir = path.parent
    if path.suffix == ".amxd":
        doc = lint_amxd(path, res, factory=factory)
    else:  # .maxpat / raw patcher JSON
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            res.err(f"patcher: invalid JSON — {e}")
            doc = None
    if doc is not None:
        lint_patcher(doc, base_dir, res)
    return res


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Lint a HERE M4L device.")
    ap.add_argument("path", nargs="?", default=str(here / "HERE.amxd"),
                    help="HERE.amxd or HERE.maxpat (default: HERE.amxd)")
    ap.add_argument("--factory", default=None,
                    help="factory blank .amxd to verify the meta chunk against")
    args = ap.parse_args()

    factory = Path(args.factory) if args.factory else None
    res = lint(Path(args.path), factory=factory)

    print(f"lint {args.path}")
    if res.stats:
        bits = ", ".join(f"{k}={v}" for k, v in res.stats.items()
                         if k != "chunks")
        print(f"  {bits}")
    for w in res.warnings:
        print(f"  ⚠ {w}")
    for e in res.errors:
        print(f"  ✗ {e}")
    print("  ✓ clean" if res.ok else f"  ✗ {len(res.errors)} error(s)")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
