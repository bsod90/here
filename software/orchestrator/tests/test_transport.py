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
