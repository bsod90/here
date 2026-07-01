"""Soap — ported from WLED `mode_2Dsoap`.

A slowly-morphing palette noise field that "refracts" like soap film: each
frame a low-pass-filtered 3D noise field both colors the image and warps
it (two separable displacement passes, horizontal then vertical, with
sub-pixel blending). The framebuffer feeds back, so colors flow and smear
like liquid. The user liked it but found it too fast — defaults here are
slowed right down.

Knobs (WLED 0..255):
  speed     — flow rate (kept low for a calm drift)
  intensity — smoothness / persistence (how slowly the field morphs)
"""
from __future__ import annotations

import numpy as np

from . import _wled as w
import palettes

DEFAULTS = {
    "palette": "ocean",
    "speed": 16,         # much slower than stock
    "intensity": 200,    # high smoothness = slow morph
    "brightness": 1.0,
    "fade_in_s": 2.5,
}


def _ease(u):                                   # smoothstep ≈ ease8InOutApprox
    u = np.clip(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def _warp(buf, fallback, noise3d, amplitude, axis):
    cols, rows = w.COLS, w.ROWS
    out = np.empty_like(buf)
    if axis == 1:                               # horizontal: displace x per row
        x = np.arange(cols)
        for y in range(rows):
            amount = (float(noise3d[y, 0]) - 128.0) * 2.0 * amplitude
            delta = int(abs(amount)) >> 8
            frac = int(abs(amount)) & 255
            s = 1 if amount >= 0 else -1
            zD = x + s * delta
            zF = zD + s
            a = _ease((255 - frac) / 255.0)
            b = _ease(frac / 255.0)
            pa = np.where((zD >= 0)[:, None] & (zD < cols)[:, None],
                          buf[y, np.clip(zD, 0, cols - 1)],
                          fallback[y, np.abs(zD) % cols])
            pb = np.where((zF >= 0)[:, None] & (zF < cols)[:, None],
                          buf[y, np.clip(zF, 0, cols - 1)],
                          fallback[y, np.abs(zF) % cols])
            out[y] = pa * a + pb * b
    else:                                       # vertical: displace y per col
        y = np.arange(rows)
        for x in range(cols):
            amount = (float(noise3d[0, x]) - 128.0) * 2.0 * amplitude
            delta = int(abs(amount)) >> 8
            frac = int(abs(amount)) & 255
            s = 1 if amount >= 0 else -1
            zD = y + s * delta
            zF = zD + s
            a = _ease((255 - frac) / 255.0)
            b = _ease(frac / 255.0)
            pa = np.where((zD >= 0)[:, None] & (zD < rows)[:, None],
                          buf[np.clip(zD, 0, rows - 1), x],
                          fallback[np.abs(zD) % rows, x])
            pb = np.where((zF >= 0)[:, None] & (zF < rows)[:, None],
                          buf[np.clip(zF, 0, rows - 1), x],
                          fallback[np.abs(zF) % rows, x])
            out[:, x] = pa * a + pb * b
    return out


def render(frame: bytearray, time_ms: float, params: dict, state: dict | None = None) -> None:
    p = {**DEFAULTS, **(params or {})}
    st = state if state is not None else {}
    now = w.elapsed(st, time_ms)
    cols, rows = w.COLS, w.ROWS

    if "noise3d" not in st:
        st["noise3d"] = np.zeros((rows, cols), dtype=np.float32)
        st["nx"], st["ny"], st["nz"] = 12345.0, 22222.0, 33333.0
        st["first"] = True
    n3 = st["noise3d"]

    mov = min(cols, rows) * (float(p["speed"]) + 2.0) / 2.0
    if not st.get("first"):
        st["nx"] += mov
        st["ny"] += mov
        st["nz"] += mov
    X, Y = w.coords()
    sx = 160000.0 / cols
    sy = 160000.0 / rows
    data = w.inoise16(st["nx"] + sx * (X - cols / 2),
                      st["ny"] + sy * (Y - rows / 2), st["nz"]) / 256.0
    smooth = min(250.0, float(p["intensity"]))
    n3[:] = n3 * (smooth / 255.0) + data * ((255.0 - smooth) / 255.0)

    pal = palettes.as_array(p["palette"])
    fallback = w.from_palette(pal, ((255.0 - n3) * 3.0) % 256.0, 255.0, wrap=False)
    buf = w.get_buf(st)
    if st.get("first"):
        buf[:] = fallback
        st["first"] = False

    amp = (cols - 8) / 8.0 if cols >= 16 else 1.0
    buf = _warp(buf, fallback, n3, amp, axis=1)
    buf = _warp(buf, fallback, n3, amp, axis=0)
    st["buf"] = buf
    w.finalize(frame, buf.copy(), now / 1000.0, p)
