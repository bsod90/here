"""Transport gamma-correction tests.

The DDP path gamma-corrects outgoing bytes (WLED's realtime gamma is off)
so full-field effects keep their contrast on the near-linear LEDs and don't
blow the ABL power budget. The simulator frame stays raw.
"""
from transport import UDPTransport


def _make(gamma):
    return UDPTransport([], {"transport": {"gamma": gamma}})


def test_gamma_identity_when_disabled():
    t = _make(1.0)
    try:
        fr = bytearray([0, 64, 122, 128, 255])
        assert bytes(t._apply_gamma(fr, 1.0)) == bytes(fr)
    finally:
        t.stop()


def test_gamma_deepens_midtones_preserves_endpoints():
    t = _make(2.2)
    try:
        out = t._apply_gamma(bytearray([0, 122, 255]), 2.2)
        assert out[0] == 0          # black stays black
        assert out[2] == 255        # peak stays peak
        assert out[1] < 122         # muddy midtone pulled down → contrast
    finally:
        t.stop()


def test_gamma_lut_is_cached_and_rebuilds_on_change():
    t = _make(2.2)
    try:
        t._apply_gamma(bytearray([128]), 2.2)
        lut1 = t._gamma_lut
        t._apply_gamma(bytearray([128]), 2.2)
        assert t._gamma_lut is lut1          # unchanged exponent → same LUT
        t._apply_gamma(bytearray([128]), 2.8)
        assert t._gamma_lut is not lut1      # new exponent → rebuilt
        assert t._gamma_exp == 2.8
    finally:
        t.stop()


def test_gamma_handles_bad_value():
    t = _make(1.0)
    try:
        fr = bytearray([10, 20, 30])
        assert bytes(t._apply_gamma(fr, None)) == bytes(fr)
        assert bytes(t._apply_gamma(fr, "x")) == bytes(fr)
    finally:
        t.stop()


def test_gamma_dither_stays_within_one_level_of_exact():
    t = _make(2.2)
    try:
        fr = bytearray(range(256))
        out = t._apply_gamma(fr, 2.2)
        for i, v in enumerate(out):
            exact = (i / 255.0) ** 2.2 * 255.0
            assert exact - 1.0 < v <= exact + 1.0, (i, v, exact)
    finally:
        t.stop()


def test_gamma_static_frame_is_temporally_stable():
    # The dither offsets are fixed per pixel — resending the same frame
    # must produce byte-identical output (no flicker on static content).
    t = _make(2.2)
    try:
        fr = bytearray([7, 30, 63, 120] * 100)
        first = bytes(t._apply_gamma(fr, 2.2))
        for _ in range(10):
            assert bytes(t._apply_gamma(fr, 2.2)) == first
    finally:
        t.stop()


def test_gamma_dither_varies_across_equal_pixels():
    # Pixels with the SAME input value land on adjacent output levels —
    # that spatial spread is what breaks fade banding into a fine ripple.
    t = _make(2.2)
    try:
        out = t._apply_gamma(bytearray([73] * 500), 2.2)
        vals = set(out)
        assert len(vals) == 2 and max(vals) - min(vals) == 1, vals
    finally:
        t.stop()


def test_gamma_dither_preserves_channel_order():
    # The dither offset is shared across a pixel's three channels, so the
    # rounding can never flip hue — a dim warm pixel (r==g>b) must come
    # out with r==g>=b, never as a lone red LED.
    t = _make(2.2)
    try:
        out = t._apply_gamma(bytearray([4, 4, 3] * 400), 2.2)
        for i in range(0, len(out), 3):
            assert out[i] == out[i + 1] >= out[i + 2], (i, out[i:i+3])
    finally:
        t.stop()


# ── Power limiter (ABL) ─────────────────────────────────────────────

def _make_pl(max_watts, gamma=1.0, release_s=0.7, enabled=True):
    return UDPTransport([], {"transport": {
        "gamma": gamma,
        "power_limit": {"enabled": enabled, "max_watts": max_watts,
                        "release_s": release_s},
    }})


def _watts(frame_bytes):
    return sum(frame_bytes) / (255 * 3) * 0.1


def test_limiter_dims_white_flood_to_budget():
    # 1936-LED full white ≈ 193.6 W → a 150 W budget must scale ~0.77.
    t = _make_pl(150.0)
    try:
        white = bytearray([255] * 1936 * 3)
        tcfg = t._config["transport"]
        out = t._shape_output(white, tcfg)
        w = _watts(out)
        assert w <= 150.0 * 1.01, w
        st = t.limiter_state()
        assert st["enabled"] and 0.74 <= st["scale"] <= 0.79, st
        assert abs(st["watts"] - 193.6) < 1.0
    finally:
        t.stop()


def test_limiter_leaves_dim_frames_untouched():
    t = _make_pl(150.0)
    try:
        dim = bytearray([40] * 1936 * 3)      # ~30 W — well under budget
        tcfg = t._config["transport"]
        out = t._shape_output(dim, tcfg)
        assert bytes(out) == bytes(dim)
        assert t.limiter_state()["scale"] == 1.0
    finally:
        t.stop()


def test_limiter_disabled_passes_everything():
    t = _make_pl(150.0, enabled=False)
    try:
        white = bytearray([255] * 1936 * 3)
        out = t._shape_output(white, t._config["transport"])
        assert bytes(out) == bytes(white)
        assert t.limiter_state()["enabled"] is False
    finally:
        t.stop()


def test_limiter_measures_post_gamma_power():
    # With gamma 2.2 a mid-gray frame's REAL draw is far below its raw
    # byte sum — the limiter must not dim what the LEDs won't pull.
    t = _make_pl(150.0, gamma=2.2)
    try:
        mid = bytearray([180] * 1936 * 3)     # raw sum would say ~137 W…
        t._shape_output(mid, t._config["transport"])
        st = t.limiter_state()
        assert st["watts"] < 100.0, st        # …post-gamma it's ~63 W
        assert st["scale"] == 1.0
    finally:
        t.stop()


def test_limiter_attack_instant_release_gradual():
    t = _make_pl(150.0, release_s=10.0)
    try:
        tcfg = t._config["transport"]
        white = bytearray([255] * 1936 * 3)
        dim = bytearray([40] * 1936 * 3)
        t._shape_output(white, tcfg)
        clamped = t.limiter_state()["scale"]
        assert clamped < 0.8                  # attack: clamped immediately
        t._shape_output(dim, tcfg)
        after_one = t.limiter_state()["scale"]
        assert after_one < 1.0                # release: still climbing…
        assert after_one >= clamped
    finally:
        t.stop()


def test_limiter_applies_with_gamma_disabled():
    t = _make_pl(100.0, gamma=1.0)
    try:
        white = bytearray([255] * 1936 * 3)
        out = t._shape_output(white, t._config["transport"])
        assert _watts(out) <= 100.0 * 1.02
    finally:
        t.stop()


def test_limiter_catches_one_panel_hotspot():
    # A bright top half concentrates its whole draw on panel 1: total is
    # under budget but the panel is over ITS half — must still dim. This
    # is the "bright scenes that aren't even white still glitch" case.
    t = _make_pl(150.0)
    try:
        half = 1936 * 3 // 2
        frame = bytearray([255] * half + [0] * half)   # ~97 W total
        out = t._shape_output(frame, t._config["transport"])
        st = t.limiter_state()
        assert st["watts"] < 100.0                     # total looks "safe"
        assert st["zone_watts"][0] > 90.0 and st["zone_watts"][1] == 0.0
        # panel 1 clamped to 75 W (150/2): scale ≈ 75/96.8
        assert 0.75 <= st["scale"] <= 0.80, st
        assert _watts(out[:half]) <= 75.0 * 1.01
    finally:
        t.stop()


def test_limiter_symmetric_white_unchanged_by_zoning():
    # Symmetric content: per-panel budgeting must behave exactly like the
    # old total-watts budgeting (each panel sees half the total).
    t = _make_pl(150.0)
    try:
        white = bytearray([255] * 1936 * 3)
        t._shape_output(white, t._config["transport"])
        st = t.limiter_state()
        assert 0.74 <= st["scale"] <= 0.79
        assert abs(st["zone_watts"][0] - st["zone_watts"][1]) < 0.5
    finally:
        t.stop()
