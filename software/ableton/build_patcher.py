#!/usr/bin/env python3
"""Generate the HERE M4L MIDI Effect patcher JSON.

The HERE device accepts MIDI, routes notes through `v8 here.js` for
choke + OSC formatting, emits OSC over UDP to `here.local:9000`, and
exposes ~39 automatable `live.dial` parameters plus a 4×10 pad grid.

HARD CONSTRAINT: a Max for Live device is fixed at **169 px tall** —
taller content is clipped by Live's device view (it is NOT resizable).
So the UI is paged with a `live.tab`, each page sized to fit one unit:

    MIDI     — the pad grid (number + note name, with the event below)
    Master   — 11 global dials
    Rings     — 3 rings × 6 dials (Outer/Middle/Inner)
    Physics  — 10 physics dials

Pages are stacked in the same area and shown/hidden via
`thispatcher script show/hide <scriptingname>`. A Connection strip
(host/port/test/debug) stays visible on every page. Each control gets a
page-prefixed scripting name so `lint_device.py` checks no-overlap
*within* a page while allowing the pages to share coordinates — and it
hard-fails if anything exceeds the 169px height.

Run from `software/ableton/`:
    python3 build_patcher.py > HERE.maxpat
Prereq: `here_events.json` and `here_knobs.json` (run `gen_metadata.py`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

EVENTS = json.loads((HERE / "here_events.json").read_text())
KNOBS = json.loads((HERE / "here_knobs.json").read_text())

# ── Device size ── height is the hard 169px Live cap; width is ours.
DEV_W = 600.0
DEV_H = 168.0

# Off-presentation patching column anchors.
PATCH_COL_MIDI = 20.0
PATCH_COL_PADS = 220.0
PATCH_COL_KNOBS = 420.0
PATCH_COL_OSC = 760.0
PATCH_COL_SWITCH = 1000.0

# Tab pages (order = tab index).
PAGES = ["midi1", "midi2", "master", "rings", "physics", "conn"]
PAGE_LABELS = ["MIDI 1", "MIDI 2", "Master", "Rings", "Physics", "Conn"]

# ── Note naming (Ableton convention: middle C = C3 = MIDI 60) ─────
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(pitch: int) -> str:
    return f"{_NOTE_NAMES[pitch % 12]}{pitch // 12 - 2}"


_obj_counter = 0


def next_id(prefix: str = "obj") -> str:
    global _obj_counter
    _obj_counter += 1
    return f"{prefix}-{_obj_counter}"


# ── Page tracking ────────────────────────────────────────────────
_current_page: str | None = None
_page_members: dict[str, list[str]] = {p: [] for p in PAGES}

boxes: list = []
lines: list = []


def box(obj_id, maxclass, rect, *, text=None, presentation_rect=None, **kwargs):
    b = {"id": obj_id, "maxclass": maxclass,
         "patching_rect": [float(v) for v in rect]}
    if text is not None:
        b["text"] = text
    if presentation_rect is not None:
        b["presentation"] = 1
        b["presentation_rect"] = [float(round(v)) for v in presentation_rect]
        if _current_page is not None and "varname" not in kwargs:
            vn = f"{_current_page}__{obj_id.replace('-', '_')}"
            b["varname"] = vn
            _page_members[_current_page].append(vn)
    b.update(kwargs)
    boxes.append({"box": b})
    return obj_id


def patchline(src_id, src_outlet, dst_id, dst_inlet):
    lines.append({"patchline": {"destination": [dst_id, dst_inlet],
                                "source": [src_id, src_outlet]}})


def newobj(rect, text, *, presentation_rect=None, **kw):
    return box(next_id("n"), "newobj", rect, text=text,
               presentation_rect=presentation_rect, **kw)


def message(rect, text, **kw):
    return box(next_id("m"), "message", rect, text=text,
               numinlets=2, numoutlets=1, **kw)


def live_comment(rect, text, *, presentation_rect=None, fontsize=9.0, **kw):
    return box(next_id("lc"), "live.comment", rect, text=text,
               presentation_rect=presentation_rect,
               fontsize=fontsize, numinlets=1, numoutlets=0, **kw)


def live_dial(rect, *, presentation_rect, longname, shortname, initial,
              mmin, mmax, unitstyle=1, ptype=0, exponent=1.0, **kw):
    # Continuous, smoothly-modulatable dial — modeled on Ableton's own
    # factory float dials so an LFO/automation mapped to it sweeps smoothly:
    #   parameter_type=0      float (not int → no "1 2 3" stepping)
    #   parameter_unitstyle=1 Float display (shows decimals)
    #   parameter_modmode=2   modulation enabled (the missing piece that
    #                         made LFO output coarse/stepped)
    #   parameter_steps=0     no step quantization
    #   parameter_speedlim=0  no output rate-limit
    # showname/shownumber=0 → knob-only (the layout labels it separately),
    # so dense tabs (Rings) don't overlap with on-dial name/value text.
    return box(
        next_id("d"), "live.dial", rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=2, outlettype=["", "float"], parameter_enable=1,
        showname=0, shownumber=0,
        saved_attribute_attributes={"valueof": {
            "parameter_initial": [float(initial)], "parameter_initial_enable": 1,
            "parameter_longname": longname, "parameter_shortname": shortname,
            "parameter_mmax": float(mmax), "parameter_mmin": float(mmin),
            "parameter_type": int(ptype), "parameter_unitstyle": int(unitstyle),
            "parameter_exponent": float(exponent),
            "parameter_modmode": 2, "parameter_steps": 0,
            "parameter_speedlim": 0.0, "parameter_linknames": 1}}, **kw)


def live_tab(rect, *, presentation_rect, longname, shortname, items, initial=0,
             varname=None, **kw):
    return box(
        next_id("tab"), "live.tab", rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=3, outlettype=["", "", "float"],
        parameter_enable=1, num_lines_patching=len(items),
        num_lines_presentation=0, varname=varname,
        saved_attribute_attributes={"valueof": {
            "parameter_enum": list(items), "parameter_initial": [int(initial)],
            "parameter_initial_enable": 1, "parameter_longname": longname,
            "parameter_shortname": shortname, "parameter_mmax": len(items) - 1,
            "parameter_type": 2, "parameter_unitstyle": 9}}, **kw)


def live_button(rect, *, presentation_rect, longname, shortname, **kw):
    return box(
        next_id("b"), "live.button", rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=1, parameter_enable=1,
        saved_attribute_attributes={"valueof": {
            "parameter_longname": longname, "parameter_shortname": shortname,
            "parameter_type": 2}}, **kw)


def live_text(rect, *, presentation_rect, longname, shortname, text, mode=0, **kw):
    # `text` = off-state label, `texton` = on-state label. If texton is
    # left unset it shows the factory default "B" when pressed — so we
    # pin both to the same label. mode 0 = momentary Button (not 2).
    return box(
        next_id("t"), "live.text", rect, presentation_rect=presentation_rect,
        text=text, texton=text, numinlets=1, numoutlets=1,
        parameter_enable=1, mode=mode,
        saved_attribute_attributes={"valueof": {
            "parameter_longname": longname, "parameter_shortname": shortname,
            "parameter_type": 2}}, **kw)


def live_toggle(rect, *, presentation_rect, longname, shortname, initial=0, **kw):
    return box(
        next_id("tog"), "live.toggle", rect, presentation_rect=presentation_rect,
        numinlets=1, numoutlets=1, parameter_enable=1,
        saved_attribute_attributes={"valueof": {
            "parameter_initial": [int(initial)], "parameter_initial_enable": 1,
            "parameter_longname": longname, "parameter_shortname": shortname,
            "parameter_type": 2}}, **kw)


def textedit_string(rect, *, presentation_rect, longname, initial):
    return box(
        next_id("te"), "textedit", rect, presentation_rect=presentation_rect,
        keymode=1, numinlets=1, numoutlets=4, outlettype=["", "int", "", ""],
        parameter_enable=1, text=str(initial),
        saved_attribute_attributes={"valueof": {
            "parameter_initial": [initial], "parameter_initial_enable": 1,
            "parameter_invisible": 1, "parameter_longname": longname,
            "parameter_shortname": longname, "parameter_type": 3}})


# ── Always-visible chrome: the tab selector. The device is already
# named "HERE" in its title bar, so we drop the redundant title and give
# the tab bar the full width.
view_tab = live_tab(
    [PATCH_COL_SWITCH, 40, 150, 22],
    presentation_rect=[8, 6, 584, 19],
    longname="here_view", shortname="View",
    items=PAGE_LABELS, initial=0, varname="here_view_tab")

# ── MIDI input chain + v8 + OSC sender (off-presentation) ────────
midi_in = newobj([PATCH_COL_MIDI, 40, 60, 22], "midiin")
midi_parse = newobj([PATCH_COL_MIDI, 70, 80, 22], "midiparse")
patchline(midi_in, 0, midi_parse, 0)
midi_out = newobj([PATCH_COL_MIDI, 130, 60, 22], "midiout")
patchline(midi_in, 0, midi_out, 0)

v8 = newobj([PATCH_COL_MIDI + 100, 100, 100, 22], "v8 here.js")
note_pack = newobj([PATCH_COL_MIDI, 100, 60, 22], "pack i i")
note_prepend = newobj([PATCH_COL_MIDI, 130, 80, 22], "prepend note")
patchline(midi_parse, 0, note_pack, 0)
patchline(midi_parse, 1, note_pack, 1)
patchline(note_pack, 0, note_prepend, 0)
patchline(note_prepend, 0, v8, 0)

udpsend = newobj([PATCH_COL_OSC, 540, 200, 22], "udpsend here.local 9000")
patchline(v8, 0, udpsend, 0)

# Pad → REAL MIDI. A shared makenote→midiformat emits a genuine note
# on/off out the device's MIDI output (downstream + recordable) when a
# pad is pressed — so clicking a pad plays that note for real, in
# addition to the OSC animation trigger wired in the pad loop below.
pad_makenote = newobj([PATCH_COL_MIDI + 220, 160, 110, 22], "makenote 110 250")
pad_midiformat = newobj([PATCH_COL_MIDI + 220, 190, 80, 22], "midiformat")
patchline(pad_makenote, 0, pad_midiformat, 0)   # pitch
patchline(pad_makenote, 1, pad_midiformat, 1)   # velocity
patchline(pad_midiformat, 0, midi_out, 0)        # → MIDI output

# Shared content band: y in [PAGE_TOP, PAGE_BOTTOM]; Connection below.
PAGE_TOP = 26.0
PAGE_BOTTOM = 146.0

# ── PAGES: MIDI 1 / MIDI 2 — pads grouped by function ────────────
# Each pad keeps its FIXED pitch (shown on the button); its on-screen
# position is purely visual, so we can group related events together.
# Inert "—" (noop) lanes get no pad. Pitches never move (see the
# append-only NOTE_LANES rule).
by_label = {ev["label"]: ev for ev in EVENTS["events"]}
MIDI_ROWS = {
    "midi1": [   # Performance: shape · lifecycle · states/palettes
        ["Expand", "Contract", "Pulse", "Blow Out", "Shimmer"],
        ["Regrow", "Dissolve", "Respawn", "Reset", "Fade Out"],
        ["Border", "Dissolve Border", "Particles",
         "Palette 1", "Palette 2", "Palette 3", "Palette 4"],
    ],
    "midi2": [   # Control: rotation · stops/show-hide · sfx/motion
        ["Rotate CW", "Rotate CCW", "Outer CW", "Outer CCW",
         "Middle CW", "Middle CCW", "Inner CW", "Inner CCW"],
        ["Stop Rot All", "Stop Outer", "Stop Middle", "Stop Inner",
         "Show Outer", "Hide Outer", "Show Middle", "Hide Middle"],
        ["Show Inner", "Hide Inner", "Meteors", "Dust",
         "Flash", "Wipe", "Pull Center", "Push Random"],
    ],
}
_pad_n = 0
for _page, _rows in MIDI_ROWS.items():
    _current_page = _page
    for r, labels in enumerate(_rows):
        n = len(labels)
        cell_w = (DEV_W - 12.0) / n
        cy = PAGE_TOP + 2.0 + r * 46.0
        for c, lbl in enumerate(labels):
            ev = by_label.get(lbl)
            if ev is None:
                continue
            pitch = ev["pitch"]
            cx = 6.0 + c * cell_w
            # Off-presentation patch positions (layout irrelevant; just keep
            # them from overlapping so the patcher view is followable).
            px = PATCH_COL_PADS + (_pad_n % 12) * 26
            py = 200.0 + (_pad_n // 12) * 120
            _pad_n += 1
            pad_id = live_text(
                [px, py, 24, 14],
                presentation_rect=[cx + 2, cy, cell_w - 6, 15],
                longname=f"pad_{pitch:03d}", shortname=str(pitch),
                text=f"{pitch} {note_name(pitch)}", mode=0)
            live_comment(
                [px, py + 15, 50, 12], lbl,
                presentation_rect=[cx + 2, cy + 15, cell_w - 4, 11],
                fontsize=7.5, hint=lbl)
            pad_route = newobj([px, py + 30, 60, 22], "route 1 0")
            patchline(pad_id, 0, pad_route, 0)
            # Message boxes (NOT newobj) → v8 for the OSC animation trigger.
            note_msg = message([px, py + 60, 100, 22], f"note {pitch} 1")
            patchline(pad_route, 0, note_msg, 0)
            patchline(note_msg, 0, v8, 0)
            off_msg = message([px + 50, py + 60, 100, 22], f"noteoff {pitch}")
            patchline(pad_route, 1, off_msg, 0)
            patchline(off_msg, 0, v8, 0)
            # Also emit a REAL MIDI note: pad press → pitch → shared makenote.
            mk_msg = message([px, py + 90, 40, 18], str(pitch))
            patchline(pad_route, 0, mk_msg, 0)
            patchline(mk_msg, 0, pad_makenote, 0)
_current_page = None


def dial_chain(dial_id, prepend_text, px, py):
    chg = newobj([px, py, 60, 22], "change")
    patchline(dial_id, 0, chg, 0)
    msg = newobj([px, py + 26, 200, 22], prepend_text)
    patchline(chg, 0, msg, 0)
    patchline(msg, 0, v8, 0)


def big_dial_row(items, *, key_fn, longname_fn, short_fn, init_fn,
                 prepend_fn, x0=8.0, cw=52.0, knob=42.0, top=36.0,
                 patch_y0=700.0):
    dx = (cw - knob) / 2.0
    for i, k in enumerate(items):
        cx = x0 + i * cw
        d = live_dial(
            [PATCH_COL_KNOBS + i * 36, patch_y0, 24, 36],
            presentation_rect=[cx + dx, top, knob, knob],
            longname=longname_fn(k), shortname=short_fn(k),
            initial=init_fn(k), mmin=k["min"], mmax=k["max"])
        live_comment([PATCH_COL_KNOBS + i * 36, patch_y0 - 14, cw + 8, 12],
                     k["label"],
                     presentation_rect=[cx, top + knob + 2, cw, 12],
                     fontsize=7.5, hint=k["label"])
        dial_chain(d, prepend_fn(k), PATCH_COL_KNOBS + i * 36, patch_y0 + 40)


# ── PAGE: Master (11 dials) ──────────────────────────────────────
_current_page = "master"
big_dial_row(
    KNOBS["master"], key_fn=lambda k: k["key"],
    longname_fn=lambda k: f"here_{k['key']}",
    short_fn=lambda k: k["label"][:11],
    init_fn=lambda k: k.get("default", k["min"]),
    prepend_fn=lambda k: f"prepend knob master {k['key']}",
    x0=8.0, cw=52.0, knob=42.0, top=40.0, patch_y0=700.0)

# ── PAGE: Physics (10 dials) ─────────────────────────────────────
_current_page = "physics"
big_dial_row(
    KNOBS["physics"], key_fn=lambda k: k["key"],
    longname_fn=lambda k: f"here_phys_{k['key']}",
    short_fn=lambda k: k["label"][:11],
    init_fn=lambda k: k["default"],
    prepend_fn=lambda k: f"prepend knob physics {k['key']}",
    x0=6.0, cw=59.0, knob=44.0, top=40.0, patch_y0=1080.0)

# ── PAGE: Rings (3 rows × 6 dials) ───────────────────────────────
_current_page = "rings"
ring_labels = ["Outer", "Middle", "Inner"]
RING_X0, RING_CW = 64.0, 84.0
RING_COLHDR_Y, RING_Y0, RING_ROW_H, RING_SZ = 28.0, 44.0, 33.0, 32.0
RING_DX = (RING_CW - RING_SZ) / 2.0
patch_y_ring = 800.0
for ki, k in enumerate(KNOBS["oval"]):
    cx = RING_X0 + ki * RING_CW
    live_comment([PATCH_COL_KNOBS + ki * 36, patch_y_ring - 18, 60, 12], k["label"],
                 presentation_rect=[cx, RING_COLHDR_Y, RING_CW, 11], fontsize=7.5)
for ri in range(3):
    rowY = RING_Y0 + ri * RING_ROW_H
    live_comment([PATCH_COL_KNOBS - 60, patch_y_ring + ri * 80, 56, 14],
                 ring_labels[ri],
                 presentation_rect=[6, rowY + (RING_SZ - 12) / 2, 56, 12],
                 fontsize=8.0, hint=f"{ring_labels[ri]} ring")
    for ki, k in enumerate(KNOBS["oval"]):
        cx = RING_X0 + ki * RING_CW
        d = live_dial(
            [PATCH_COL_KNOBS + ki * 36, patch_y_ring + ri * 80, 22, 18],
            presentation_rect=[cx + RING_DX, rowY, RING_SZ, RING_SZ],
            longname=f"here_oval_{k['key']}_{ri}",
            shortname=f"{ring_labels[ri][0]} {k['label']}"[:11],
            initial=k["defaults"][ri], mmin=k["min"], mmax=k["max"])
        dial_chain(d, f"prepend knob oval {ri} {k['key']}",
                   PATCH_COL_KNOBS + ki * 36, patch_y_ring + 22 + ri * 80)

_current_page = None

# ── PAGE: Conn (connection settings + link test) ─────────────────
_current_page = "conn"
live_comment([PATCH_COL_OSC, 40, 60, 14], "host",
             presentation_rect=[8, 36, 32, 14], fontsize=9.0)
host_te = textedit_string([PATCH_COL_OSC, 70, 120, 22],
                          presentation_rect=[46, 34, 220, 18],
                          longname="here_host", initial="here.local")
host_route = newobj([PATCH_COL_OSC, 100, 100, 22], "route text")
patchline(host_te, 0, host_route, 0)
host_prep = newobj([PATCH_COL_OSC, 130, 100, 22], "prepend host")
patchline(host_route, 0, host_prep, 0)
patchline(host_prep, 0, udpsend, 0)

live_comment([PATCH_COL_OSC, 160, 60, 14], "port",
             presentation_rect=[8, 64, 32, 14], fontsize=9.0)
port_te = textedit_string([PATCH_COL_OSC, 190, 120, 22],
                          presentation_rect=[46, 62, 90, 18],
                          longname="here_port", initial=9000)
port_route = newobj([PATCH_COL_OSC, 220, 100, 22], "route text")
patchline(port_te, 0, port_route, 0)
port_prep = newobj([PATCH_COL_OSC, 250, 100, 22], "prepend port")
patchline(port_route, 0, port_prep, 0)
patchline(port_prep, 0, udpsend, 0)

test_btn = live_button([PATCH_COL_OSC, 290, 24, 24],
                       presentation_rect=[8, 92, 22, 18],
                       longname="here_test", shortname="test")
# Message box (outputs "palette 0" when clicked) → v8 → OSC /here/scene/palette 0.
test_msg = message([PATCH_COL_OSC, 320, 100, 22], "palette 0")
patchline(test_btn, 0, test_msg, 0)
patchline(test_msg, 0, v8, 0)
live_comment([PATCH_COL_OSC + 30, 290, 60, 14],
             "ping  ·  sends a palette swap so you can confirm the bench is listening",
             presentation_rect=[36, 94, 440, 14], fontsize=8.0)

dbg_tog = live_toggle([PATCH_COL_OSC, 350, 24, 24],
                      presentation_rect=[8, 120, 18, 18],
                      longname="here_debug", shortname="debug", initial=0)
gate = newobj([PATCH_COL_OSC, 380, 80, 22], "gate 1 0")
patchline(dbg_tog, 0, gate, 0)
patchline(v8, 0, gate, 1)
dbg_print = newobj([PATCH_COL_OSC, 410, 80, 22], "print HERE")
patchline(gate, 0, dbg_print, 0)
live_comment([PATCH_COL_OSC + 30, 350, 60, 14],
             "debug  ·  print every outgoing OSC message to the Max console",
             presentation_rect=[36, 122, 440, 14], fontsize=8.0)

live_comment([PATCH_COL_OSC, 450, 200, 14], "MIDI notes 36–75 → events  ·  knobs → live params",
             presentation_rect=[8, 150, 470, 12], fontsize=7.5)
_current_page = None

# ── Tab switching: index → show one page, hide the rest ──────────
thispatcher = newobj([PATCH_COL_SWITCH, 240, 90, 22], "thispatcher")
tab_sel = newobj([PATCH_COL_SWITCH, 80, 120, 22],
                 "sel " + " ".join(str(i) for i in range(len(PAGES))))
patchline(view_tab, 0, tab_sel, 0)

first_msg = None
for idx, pg in enumerate(PAGES):
    parts = [f"script show {v}" for v in _page_members[pg]]
    for other in PAGES:
        if other != pg:
            parts += [f"script hide {v}" for v in _page_members[other]]
    msg = message([PATCH_COL_SWITCH + idx * 210, 130, 200, 22], ", ".join(parts))
    patchline(tab_sel, idx, msg, 0)
    patchline(msg, 0, thispatcher, 0)
    if idx == 0:
        first_msg = msg

# ── thisdevice: reset v8 + force the initial (MIDI) page on load ──
thisdevice = newobj([PATCH_COL_MIDI, 4, 80, 22], "live.thisdevice",
                    numinlets=1, numoutlets=3)
reset_msg = message([PATCH_COL_MIDI + 90, 4, 60, 22], "reset")
patchline(thisdevice, 0, reset_msg, 0)
patchline(reset_msg, 0, v8, 0)
patchline(thisdevice, 0, first_msg, 0)


# ── Patcher envelope ─────────────────────────────────────────────
patcher = {
    "fileversion": 1,
    "appversion": {"major": 8, "minor": 1, "revision": 2,
                   "architecture": "x64", "modernui": 1},
    "classnamespace": "box",
    "rect": [60.0, 100.0, 1400.0, 900.0],
    "openrect": [0.0, 0.0, DEV_W, DEV_H],
    "bglocked": 0,
    "openinpresentation": 1,
    "default_fontsize": 10.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 1,
    "gridsize": [8.0, 8.0],
    "gridsnaponopen": 1,
    "objectsnaponopen": 1,
    "statusbarvisible": 2,
    "toolbarvisible": 1,
    "lefttoolbarpinned": 0,
    "toptoolbarpinned": 0,
    "righttoolbarpinned": 0,
    "bottomtoolbarpinned": 0,
    "toolbars_unpinned_last_save": 0,
    "tallnewobj": 0,
    "boxanimatetime": 500,
    "enablehscroll": 1,
    "enablevscroll": 1,
    "devicewidth": DEV_W,
    "description": "HERE — MIDI → OSC controller for the HERE LED installation.",
    "digest": "HERE",
    "tags": "HERE OSC MIDI",
    "style": "",
    "subpatcher_template": "",
    "boxes": boxes,
    "lines": lines,
}

json.dump({"patcher": patcher}, sys.stdout, indent=2)
sys.stdout.write("\n")
