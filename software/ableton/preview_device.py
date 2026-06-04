#!/usr/bin/env python3
"""Render the device's presentation layout to HTML — a headless "what does
it look like in Live" preview, so layout can be eyeballed without Ableton.

Draws one panel per tab page (chrome that's always visible + that page's
controls), approximating Live's dark device skin. Pair with Chrome
`--headless --screenshot` to get a PNG.

Usage:
    preview_device.py [HERE.amxd|HERE.maxpat] > preview.html
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

DEV_W, DEV_H = 600, 168
PAGES = [("midi1", "MIDI 1"), ("midi2", "MIDI 2"), ("master", "Master"),
         ("rings", "Rings"), ("physics", "Physics"), ("conn", "Conn")]


def load_patcher(path: Path) -> dict:
    if path.suffix == ".amxd":
        blob = path.read_bytes()
        i = 0
        while i < len(blob):
            tag = blob[i:i + 4]
            (ln,) = struct.unpack("<I", blob[i + 4:i + 8])
            data = blob[i + 8:i + 8 + ln]
            if tag == b"ptch":
                raw = data[:-1] if data[-1:] == b"\x00" else data
                return json.loads(raw)["patcher"]
            i += 8 + ln
        raise SystemExit("no ptch chunk")
    return json.loads(path.read_text())["patcher"]


def page_of(b) -> str:
    vn = b.get("varname") or ""
    return vn.split("__", 1)[0] if "__" in vn else ""


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def render_box(b, active_tab: int) -> str:
    r = b.get("presentation_rect")
    if not r:
        return ""
    x, y, w, h = r
    mc = b.get("maxclass")
    style = f"left:{x}px;top:{y}px;width:{w}px;height:{h}px;"
    if mc == "live.dial":
        return f'<div class="dial" style="{style}"></div>'
    if mc in ("live.text", "live.button"):
        return f'<div class="btn" style="{style}">{esc(b.get("text",""))}</div>'
    if mc == "live.toggle":
        return f'<div class="tog" style="{style}"></div>'
    if mc == "live.tab":
        items = (b.get("saved_attribute_attributes", {}).get("valueof", {})
                 .get("parameter_enum", []))
        cells = "".join(
            f'<span class="tabcell{" on" if i == active_tab else ""}">'
            f'{esc(t)}</span>' for i, t in enumerate(items))
        return f'<div class="tab" style="{style}">{cells}</div>'
    if mc == "textedit":
        return f'<div class="te" style="{style}">{esc(b.get("text",""))}</div>'
    if mc == "live.comment":
        fs = b.get("fontsize", 9)
        return (f'<div class="cmt" style="{style}font-size:{fs}px;">'
                f'{esc(b.get("text",""))}</div>')
    return ""


def render_panel(title: str, boxes: list, page: str, active_tab: int) -> str:
    parts = []
    for wrap in boxes:
        b = wrap["box"]
        if b.get("presentation") != 1:
            continue
        if page_of(b) not in ("", page):
            continue  # other page's controls are hidden on this tab
        parts.append(render_box(b, active_tab))
    body = "\n".join(p for p in parts if p)
    return (f'<figure><figcaption>{esc(title)}</figcaption>'
            f'<div class="device" style="width:{DEV_W}px;height:{DEV_H}px;">'
            f'{body}</div></figure>')


HEAD = """<!doctype html><meta charset=utf-8><style>
body{background:#3a3a44;margin:0;padding:18px;font-family:Arial,Helvetica,sans-serif;display:flex;flex-wrap:wrap;gap:20px;width:1264px}
figure{margin:0}
figcaption{color:#ddd;font-size:13px;margin:0 0 6px 2px}
.device{position:relative;background:#5a5a66;border:1px solid #222;border-radius:3px;overflow:hidden;color:#1c1c22}
.device>div{position:absolute;box-sizing:border-box}
.dial{border:2px solid #2a2a30;border-radius:50%;background:
  radial-gradient(circle at 50% 35%,#8a8a96,#6a6a76);
  box-shadow:inset 0 0 0 3px #c9a23a55}
.btn{background:#23232a;color:#d8d846;border:1px solid #111;border-radius:2px;
  font-size:9px;display:flex;align-items:center;justify-content:center}
.tog{background:#23232a;border:1px solid #111;border-radius:2px}
.te{background:#23232a;color:#e0a020;border:1px solid #111;border-radius:2px;
  font-size:10px;display:flex;align-items:center;padding-left:4px}
.cmt{color:#e8e8ee;line-height:1.05;overflow:hidden;white-space:nowrap}
.tab{display:flex;border:1px solid #111;border-radius:3px;overflow:hidden}
.tabcell{flex:1;display:flex;align-items:center;justify-content:center;
  font-size:11px;color:#bbb;background:#2a2a30;border-right:1px solid #111}
.tabcell.on{background:#cdd23a;color:#1c1c22;font-weight:bold}
</style>
"""


def main() -> int:
    here = Path(__file__).resolve().parent
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "HERE.amxd"
    pat = load_patcher(src)
    boxes = pat.get("boxes", [])
    out = [HEAD]
    for idx, (page, label) in enumerate(PAGES):
        out.append(render_panel(f"{label} tab", boxes, page, idx))
    sys.stdout.write("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
