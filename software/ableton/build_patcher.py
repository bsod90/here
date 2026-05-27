#!/usr/bin/env python3
"""Generate the HERE M4L MIDI Effect patcher JSON.

The HERE device:
- accepts MIDI from its track (via `midiin`),
- routes notes through `v8 here.js` for choke + OSC formatting,
- emits OSC over UDP to `here.local:9000` (Pi orchestrator),
- exposes ~44 automatable `live.dial` parameters (master + rings + physics),
- shows a 4×10 pad grid labeled from `here_events.json`.

The patcher is intentionally a flat one-page layout (no `live.tab`
view-switching) — auto-generating the show/hide scripting needed for
real tabs is fragile, and Live's 169px height cap is workable if the
controls are dense enough. Users can rearrange in Max if they want
tabs (saving in Max breaks the symlink — see setup.sh).

Run from `software/ableton/`:
    python3 build_patcher.py > HERE.maxpat

Prereq: `here_events.json` and `here_knobs.json` must exist (run
`gen_metadata.py` first).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

EVENTS = json.loads((HERE / "here_events.json").read_text())
KNOBS = json.loads((HERE / "here_knobs.json").read_text())

# Live's M4L device strip is hard-capped at ~169 px tall. Width is free.
DEV_W = 920.0
DEV_H = 169.0

# Off-presentation patching column anchors (where wiring objects live —
# users can edit-mode them, but they're not part of the device UI).
PATCH_COL_MIDI = 20.0
PATCH_COL_PADS = 220.0
PATCH_COL_KNOBS = 420.0
PATCH_COL_OSC = 760.0

# Counter for unique object ids.
_obj_counter = 0


def next_id(prefix: str = "obj") -> str:
    global _obj_counter
    _obj_counter += 1
    return f"{prefix}-{_obj_counter}"


# ── Patcher JSON helpers ─────────────────────────────────────────
boxes: list = []
lines: list = []


def box(obj_id, maxclass, rect, *, text=None, presentation_rect=None, **kwargs):
    b = {
        "id": obj_id,
        "maxclass": maxclass,
        "patching_rect": [float(v) for v in rect],
    }
    if text is not None:
        b["text"] = text
    if presentation_rect is not None:
        b["presentation"] = 1
        b["presentation_rect"] = [float(v) for v in presentation_rect]
    b.update(kwargs)
    boxes.append({"box": b})
    return obj_id


def patchline(src_id, src_outlet, dst_id, dst_inlet):
    lines.append({
        "patchline": {
            "destination": [dst_id, dst_inlet],
            "source": [src_id, src_outlet],
        }
    })


def newobj(rect, text, *, presentation_rect=None, **kw):
    """A `newobj` (text-creation) box."""
    return box(next_id("n"), "newobj", rect, text=text,
               presentation_rect=presentation_rect, **kw)


def comment(rect, text, *, presentation_rect=None, fontsize=9.0, **kw):
    return box(next_id("c"), "comment", rect, text=text,
               presentation_rect=presentation_rect,
               fontsize=fontsize, numinlets=1, numoutlets=0, **kw)


def live_comment(rect, text, *, presentation_rect=None, fontsize=9.0, **kw):
    return box(next_id("lc"), "live.comment", rect, text=text,
               presentation_rect=presentation_rect,
               fontsize=fontsize, numinlets=1, numoutlets=0, **kw)


def live_dial(rect, *, presentation_rect, longname, shortname, initial,
              mmin, mmax, unitstyle=0, ptype=0, exponent=1.0, **kw):
    """An automatable `live.dial` parameter. Visibility=Automated and
    Stored (`parameter_visibility=0` is the Max constant for that)."""
    return box(
        next_id("d"), "live.dial", rect,
        presentation_rect=presentation_rect,
        numinlets=1, numoutlets=2,
        outlettype=["", "float"],
        parameter_enable=1,
        saved_attribute_attributes={
            "valueof": {
                "parameter_initial": [float(initial)],
                "parameter_initial_enable": 1,
                "parameter_longname": longname,
                "parameter_shortname": shortname,
                "parameter_mmax": float(mmax),
                "parameter_mmin": float(mmin),
                "parameter_type": int(ptype),  # 0=float
                "parameter_unitstyle": int(unitstyle),
                "parameter_exponent": float(exponent),
            }
        },
        **kw,
    )


def live_button(rect, *, presentation_rect, longname, shortname, **kw):
    return box(
        next_id("b"), "live.button", rect,
        presentation_rect=presentation_rect,
        numinlets=1, numoutlets=1,
        parameter_enable=1,
        saved_attribute_attributes={
            "valueof": {
                "parameter_longname": longname,
                "parameter_shortname": shortname,
                "parameter_type": 2,
            }
        },
        **kw,
    )


def live_text(rect, *, presentation_rect, longname, shortname, text,
              mode=2, **kw):
    """`live.text` as a button (mode=2 = momentary). Used for the
    on-device pad buttons + the OSC test pulse."""
    return box(
        next_id("t"), "live.text", rect,
        presentation_rect=presentation_rect,
        text=text,
        numinlets=1, numoutlets=1,
        parameter_enable=1,
        mode=mode,
        saved_attribute_attributes={
            "valueof": {
                "parameter_longname": longname,
                "parameter_shortname": shortname,
                "parameter_type": 2,
            }
        },
        **kw,
    )


def live_toggle(rect, *, presentation_rect, longname, shortname, initial=0, **kw):
    return box(
        next_id("tog"), "live.toggle", rect,
        presentation_rect=presentation_rect,
        numinlets=1, numoutlets=1,
        parameter_enable=1,
        saved_attribute_attributes={
            "valueof": {
                "parameter_initial": [int(initial)],
                "parameter_initial_enable": 1,
                "parameter_longname": longname,
                "parameter_shortname": shortname,
                "parameter_type": 2,
            }
        },
        **kw,
    )


def textedit_string(rect, *, presentation_rect, longname, initial):
    """A persisted text-editing field. Live can't store strings on
    `live.*` numeric widgets, so we use a `textedit` whose first outlet
    emits its value on edit. Wired through `[route text]` to strip the
    leading `text` symbol Max emits."""
    return box(
        next_id("te"), "textedit", rect,
        presentation_rect=presentation_rect,
        keymode=1,
        numinlets=1,
        numoutlets=4,
        outlettype=["", "int", "", ""],
        parameter_enable=1,
        text=str(initial),
        saved_attribute_attributes={
            "valueof": {
                "parameter_initial": [initial],
                "parameter_initial_enable": 1,
                "parameter_invisible": 1,
                "parameter_longname": longname,
                "parameter_shortname": longname,
                "parameter_type": 3,
            }
        },
    )


# ── Header (presentation row 0) ──────────────────────────────────
HEADER_Y = 2.0
HEADER_H = 14.0

live_comment([20, 4, 200, 16], "HERE — MIDI → OSC",
             presentation_rect=[6, HEADER_Y, 130, HEADER_H], fontsize=10.5)

# ── MIDI input chain (off-presentation) ──────────────────────────
midi_in = newobj([PATCH_COL_MIDI, 40, 60, 22], "midiin")
# `midiparse` outlets: 0=note-on/off (pitch vel), 1=poly aftertouch,
# 2=control change, 3=program change, 4=channel aftertouch, 5=pitch
# bend. We only consume outlet 0.
midi_parse = newobj([PATCH_COL_MIDI, 70, 80, 22], "midiparse")
patchline(midi_in, 0, midi_parse, 0)

# Pass MIDI through to downstream devices so HERE doesn't sink the
# track's MIDI signal.
midi_out = newobj([PATCH_COL_MIDI, 130, 60, 22], "midiout")
patchline(midi_in, 0, midi_out, 0)

# v8 here.js — central logic. The patcher feeds it Max messages
# (`note <p> <v>`, `noteoff <p>`, `knob ...`, `bpm`, `tap`, `palette`)
# and receives OSC-shaped lists on outlet 0.
v8 = newobj([PATCH_COL_MIDI + 100, 100, 100, 22], "v8 here.js")
# Wire the note pairs: midiparse → [pack pitch vel] → [prepend note] → v8
note_pack = newobj([PATCH_COL_MIDI, 100, 60, 22], "pack i i")
note_prepend = newobj([PATCH_COL_MIDI, 130, 80, 22], "prepend note")
patchline(midi_parse, 0, note_pack, 0)   # pitch
patchline(midi_parse, 1, note_pack, 1)   # velocity  (midiparse outlets it on outlet 1 for note-off pairs in Max 8)
patchline(note_pack, 0, note_prepend, 0)
patchline(note_prepend, 0, v8, 0)

# ── OSC sender (off-presentation, fed by v8 and by knob chains) ──
host_te_x = PATCH_COL_OSC
udpsend = newobj([host_te_x, 540, 200, 22], "udpsend here.local 9000")
patchline(v8, 0, udpsend, 0)

# ── Pad section: 4×10 grid of clickable buttons + labels ─────────
# Each pad fires `note <pitch> 1` then `noteoff <pitch>` via v8. The
# pad's `live.text` widget is momentary (mode=2), so 1=press, 0=release.

PAD_X0 = 6.0
PAD_Y0 = 20.0
PAD_W = 26.0
PAD_H = 16.0
PAD_GAP_X = 1.0
PAD_GAP_Y = 1.0
PAD_LABEL_H = 10.0

# Patching positions for pad-related objects so wiring is followable.
patch_y = 200.0

events = EVENTS["events"]
# Lay out in row-major order: 4 rows × 10 cols = 40 cells.
for i, ev in enumerate(events):
    row = i // 10
    col = i % 10
    px = PAD_X0 + col * (PAD_W + PAD_GAP_X)
    py = PAD_Y0 + row * (PAD_H + PAD_LABEL_H + PAD_GAP_Y)
    pitch = ev["pitch"]
    label = ev["label"]
    pad_long = f"pad_{pitch:03d}"
    # Pad button (compact, no built-in label — drawn under via live.comment).
    pad_id = live_text(
        [PATCH_COL_PADS + col * 28, patch_y + row * 30, 24, 14],
        presentation_rect=[px, py, PAD_W, PAD_H],
        longname=pad_long, shortname=str(pitch),
        text=str(pitch),
        mode=2,  # momentary: press → 1, release → 0
    )
    # Label below the pad showing the event's short name. Truncated to
    # ~4 chars by the cell width; users can hover for full label.
    live_comment(
        [PATCH_COL_PADS + col * 28, patch_y + row * 30 + 16, 50, 14],
        label,
        presentation_rect=[px, py + PAD_H, PAD_W, PAD_LABEL_H],
        fontsize=7.5,
        hint=label,
    )
    # Wiring: pad → [t b b] (so we send note-on AND a delayed note-off)
    # The pad's 1/0 outlet drives: 1 → `note <pitch> 1`, 0 → `noteoff <pitch>`.
    pad_route = newobj([PATCH_COL_PADS + col * 28, patch_y + 30 + row * 30, 60, 22],
                       "route 1 0")
    patchline(pad_id, 0, pad_route, 0)
    note_msg = newobj(
        [PATCH_COL_PADS + col * 28, patch_y + 60 + row * 30, 100, 22],
        f"note {pitch} 1")
    patchline(pad_route, 0, note_msg, 0)
    patchline(note_msg, 0, v8, 0)
    off_msg = newobj(
        [PATCH_COL_PADS + col * 28 + 50, patch_y + 60 + row * 30, 100, 22],
        f"noteoff {pitch}")
    patchline(pad_route, 1, off_msg, 0)
    patchline(off_msg, 0, v8, 0)


# ── Knob section ────────────────────────────────────────────────
# Layout (left-to-right, top-to-bottom within the knob area):
#   Master row  : 11 dials at y=20  (top of knob block)
#   Ring rows   : 18 dials at y=64  (3 rows × 6 cols, rows = O/M/I)
#   Physics row : 10 dials at y=132 (bottom)
# Knob block starts at presentation x=290 and runs to ~ x=910.

KNOB_X0 = 290.0
KNOB_W = 28.0
KNOB_H = 28.0
KNOB_GAP_X = 2.0
KNOB_LABEL_H = 9.0


def _osc_step_for_knob(category, key, val_message):
    """Wire a `live.dial` outlet through `change` (dedup) then
    `prepend knob <category> [<i>] <key>` then into the v8 box."""
    pass  # implemented inline below


# Master row (top) — 11 dials.
master_y = 20.0
patch_y_master = 700.0
for i, k in enumerate(KNOBS["master"]):
    x = KNOB_X0 + i * (KNOB_W + KNOB_GAP_X)
    long_name = f"here_{k['key']}"
    short_name = k["label"][:11]
    dial_id = live_dial(
        [PATCH_COL_KNOBS + i * 36, patch_y_master, 24, 36],
        presentation_rect=[x, master_y, KNOB_W, KNOB_H],
        longname=long_name, shortname=short_name,
        initial=k.get("default", k["min"]),
        mmin=k["min"], mmax=k["max"],
    )
    # Label under dial.
    live_comment(
        [PATCH_COL_KNOBS + i * 36, patch_y_master + 38, 40, 12],
        k["label"],
        presentation_rect=[x, master_y + KNOB_H + 1, KNOB_W + 4, KNOB_LABEL_H],
        fontsize=7.0,
        hint=k["label"],
    )
    # change → prepend knob master <key> → v8
    chg = newobj([PATCH_COL_KNOBS + i * 36, patch_y_master + 60, 60, 22], "change")
    patchline(dial_id, 0, chg, 0)
    msg = newobj([PATCH_COL_KNOBS + i * 36, patch_y_master + 90, 180, 22],
                 f"prepend knob master {k['key']}")
    patchline(chg, 0, msg, 0)
    patchline(msg, 0, v8, 0)

# Ring rows (middle) — 3 rows × 6 cols. Each row = one ring (outer/mid/inner).
ring_labels = ["Outer", "Middle", "Inner"]
ring_y0 = 64.0
ring_row_h = 22.0  # dial + tiny label
ring_knob_h = 18.0
patch_y_ring = 800.0

for ri in range(3):
    # Ring tag on the left edge.
    live_comment(
        [PATCH_COL_KNOBS - 60, patch_y_ring + ri * 30, 50, 14],
        ring_labels[ri],
        presentation_rect=[KNOB_X0 - 32, ring_y0 + ri * ring_row_h, 30, ring_knob_h],
        fontsize=7.5,
        hint=f"{ring_labels[ri]} ring",
    )
    for ki, k in enumerate(KNOBS["oval"]):
        x = KNOB_X0 + ki * (KNOB_W + KNOB_GAP_X)
        y = ring_y0 + ri * ring_row_h
        long_name = f"here_oval_{k['key']}_{ri}"
        short_name = f"{ring_labels[ri][0]} {k['label']}"[:11]
        default = k["defaults"][ri]
        dial_id = live_dial(
            [PATCH_COL_KNOBS + ki * 36, patch_y_ring + ri * 80, 22, 18],
            presentation_rect=[x, y, KNOB_W, ring_knob_h],
            longname=long_name, shortname=short_name,
            initial=default,
            mmin=k["min"], mmax=k["max"],
        )
        chg = newobj([PATCH_COL_KNOBS + ki * 36, patch_y_ring + 22 + ri * 80, 60, 22],
                     "change")
        patchline(dial_id, 0, chg, 0)
        msg = newobj(
            [PATCH_COL_KNOBS + ki * 36, patch_y_ring + 44 + ri * 80, 180, 22],
            f"prepend knob oval {ri} {k['key']}")
        patchline(chg, 0, msg, 0)
        patchline(msg, 0, v8, 0)
# Column headers for the ring grid — one label above each column.
for ki, k in enumerate(KNOBS["oval"]):
    x = KNOB_X0 + ki * (KNOB_W + KNOB_GAP_X)
    live_comment(
        [PATCH_COL_KNOBS + ki * 36, patch_y_ring - 18, 40, 12],
        k["label"],
        presentation_rect=[x, ring_y0 - 9, KNOB_W + 4, 9],
        fontsize=7.0,
    )

# Physics row (bottom) — 10 dials.
phys_y = 132.0
patch_y_phys = 1080.0
for i, k in enumerate(KNOBS["physics"]):
    x = KNOB_X0 + i * (KNOB_W + KNOB_GAP_X)
    long_name = f"here_phys_{k['key']}"
    short_name = k["label"][:11]
    dial_id = live_dial(
        [PATCH_COL_KNOBS + i * 36, patch_y_phys, 24, 28],
        presentation_rect=[x, phys_y, KNOB_W, 22],
        longname=long_name, shortname=short_name,
        initial=k["default"],
        mmin=k["min"], mmax=k["max"],
    )
    live_comment(
        [PATCH_COL_KNOBS + i * 36, patch_y_phys + 30, 40, 12],
        k["label"],
        presentation_rect=[x, phys_y + 22, KNOB_W + 4, KNOB_LABEL_H],
        fontsize=7.0,
        hint=k["label"],
    )
    chg = newobj([PATCH_COL_KNOBS + i * 36, patch_y_phys + 60, 60, 22], "change")
    patchline(dial_id, 0, chg, 0)
    msg = newobj([PATCH_COL_KNOBS + i * 36, patch_y_phys + 90, 180, 22],
                 f"prepend knob physics {k['key']}")
    patchline(chg, 0, msg, 0)
    patchline(msg, 0, v8, 0)


# ── OSC settings section (right edge of presentation) ────────────
OSC_X = 780.0
OSC_Y0 = 24.0

# host (editable text)
live_comment([PATCH_COL_OSC, 40, 60, 14], "host",
             presentation_rect=[OSC_X, OSC_Y0, 36, 12], fontsize=8.0)
host_te = textedit_string(
    [PATCH_COL_OSC, 70, 120, 22],
    presentation_rect=[OSC_X + 30, OSC_Y0, 100, 14],
    longname="here_host", initial="here.local",
)
host_route = newobj([PATCH_COL_OSC, 100, 100, 22], "route text")
patchline(host_te, 0, host_route, 0)
# `prepend host` lets the value retarget `udpsend`'s host at runtime.
host_prep = newobj([PATCH_COL_OSC, 130, 100, 22], "prepend host")
patchline(host_route, 0, host_prep, 0)
patchline(host_prep, 0, udpsend, 0)

# port (editable text-as-int)
live_comment([PATCH_COL_OSC, 160, 60, 14], "port",
             presentation_rect=[OSC_X, OSC_Y0 + 18, 36, 12], fontsize=8.0)
port_te = textedit_string(
    [PATCH_COL_OSC, 190, 120, 22],
    presentation_rect=[OSC_X + 30, OSC_Y0 + 18, 60, 14],
    longname="here_port", initial=9000,
)
port_route = newobj([PATCH_COL_OSC, 220, 100, 22], "route text")
patchline(port_te, 0, port_route, 0)
port_prep = newobj([PATCH_COL_OSC, 250, 100, 22], "prepend port")
patchline(port_route, 0, port_prep, 0)
patchline(port_prep, 0, udpsend, 0)

# Test pulse — sends `palette 0` (a harmless one-shot) to verify the link.
test_btn = live_button(
    [PATCH_COL_OSC, 290, 24, 24],
    presentation_rect=[OSC_X, OSC_Y0 + 40, 22, 14],
    longname="here_test", shortname="test",
)
test_msg = newobj([PATCH_COL_OSC, 320, 100, 22], "palette 0")
patchline(test_btn, 0, test_msg, 0)
patchline(test_msg, 0, v8, 0)
live_comment([PATCH_COL_OSC + 30, 290, 60, 14], "test ping",
             presentation_rect=[OSC_X + 26, OSC_Y0 + 40, 60, 12], fontsize=8.0)

# Debug toggle — gates a print of every outgoing OSC msg into the Max console.
dbg_tog = live_toggle(
    [PATCH_COL_OSC, 350, 24, 24],
    presentation_rect=[OSC_X, OSC_Y0 + 58, 16, 16],
    longname="here_debug", shortname="debug", initial=0,
)
gate = newobj([PATCH_COL_OSC, 380, 80, 22], "gate 1 0")
patchline(dbg_tog, 0, gate, 0)
patchline(v8, 0, gate, 1)
dbg_print = newobj([PATCH_COL_OSC, 410, 80, 22], "print HERE")
patchline(gate, 0, dbg_print, 0)
live_comment([PATCH_COL_OSC + 30, 350, 60, 14], "debug",
             presentation_rect=[OSC_X + 20, OSC_Y0 + 58, 60, 12], fontsize=8.0)

# Footer hint line — what this device does.
live_comment(
    [PATCH_COL_OSC, 450, 200, 14],
    "Plays MIDI clips → OSC → here.local",
    presentation_rect=[OSC_X, OSC_Y0 + 78, 130, 12], fontsize=7.5,
)

# ── thisdevice lifecycle: reset v8 state on (re)load ─────────────
# `live.thisdevice` left outlet bangs when the device is fully
# initialized — send the v8 a `reset` so the activeNotes set is clean.
thisdevice = newobj([PATCH_COL_MIDI, 4, 80, 22], "live.thisdevice",
                    numinlets=1, numoutlets=3)
reset_msg = newobj([PATCH_COL_MIDI + 90, 4, 60, 22], "reset")
patchline(thisdevice, 0, reset_msg, 0)
patchline(reset_msg, 0, v8, 0)


# ── Patcher envelope ─────────────────────────────────────────────
patcher = {
    "fileversion": 1,
    "appversion": {
        "major": 8,
        "minor": 1,
        "revision": 2,
        "architecture": "x64",
        "modernui": 1,
    },
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
