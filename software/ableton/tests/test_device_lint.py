"""Static validation of the built M4L device — the "does it load / is the
UI sane" gate that means we don't have to open Ableton on every change.

Two halves:
  * The device is clean — lint HERE.amxd and HERE.maxpat, expect zero errors.
  * The linter still bites — inject known breakage and assert it's caught,
    so the linter can't silently rot into an always-passing no-op.

If the clean-device test fails after a rebuild, the device would likely
not load (or render broken) in Live; read the printed errors.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABLETON_DIR = HERE.parent

if str(ABLETON_DIR) not in sys.path:
    sys.path.insert(0, str(ABLETON_DIR))

import lint_device as L  # noqa: E402

AMXD = ABLETON_DIR / "HERE.amxd"
MAXPAT = ABLETON_DIR / "HERE.maxpat"


def _load_patcher_doc() -> dict:
    """Pull the patcher JSON straight out of the .amxd ptch chunk."""
    blob = AMXD.read_bytes()
    ptch = {t: d for t, d in L.read_chunks(blob)}[b"ptch"]
    raw = ptch[:-1] if ptch[-1:] == b"\x00" else ptch
    return json.loads(raw)


class TestDeviceIsClean(unittest.TestCase):
    def test_amxd_lints_clean(self):
        res = L.lint(AMXD)
        self.assertTrue(res.ok, "HERE.amxd has lint errors:\n  " +
                        "\n  ".join(res.errors))

    def test_maxpat_lints_clean(self):
        if not MAXPAT.exists():
            self.skipTest("HERE.maxpat not present")
        res = L.lint(MAXPAT)
        self.assertTrue(res.ok, "HERE.maxpat has lint errors:\n  " +
                        "\n  ".join(res.errors))

    def test_is_midi_effect_container(self):
        # ampf type code must be the MIDI-effect marker.
        chunks = dict(L.read_chunks(AMXD.read_bytes()))
        self.assertEqual(chunks[b"ampf"][:4], L.MIDI_EFFECT_TYPE)


class TestLinterCatchesBreakage(unittest.TestCase):
    """Each mutation must produce at least one error — guards the guard."""

    def setUp(self):
        self.doc = _load_patcher_doc()
        self.base = ABLETON_DIR

    def _errors_after(self, mutate) -> list[str]:
        d = copy.deepcopy(self.doc)
        mutate(d["patcher"])
        res = L.LintResult()
        L.lint_patcher(d, self.base, res)
        return res.errors

    def test_catches_dangling_patchline(self):
        def m(p):
            p["lines"][0]["patchline"]["destination"][0] = "no-such-box"
        self.assertTrue(self._errors_after(m))

    def test_catches_missing_midiout(self):
        def m(p):
            p["boxes"] = [b for b in p["boxes"]
                          if not (b["box"].get("text", "").startswith("midiout"))]
            p["lines"] = []  # drop lines so only the missing-midiout error remains
        errs = self._errors_after(m)
        self.assertTrue(any("midiout" in e for e in errs), errs)

    def test_catches_overlapping_controls(self):
        # Stack a second dial exactly on top of the first one on the same
        # page → the "give the knobs space" gate must fire.
        def m(p):
            dials = [b for b in p["boxes"]
                     if b["box"].get("maxclass") == "live.dial"
                     and b["box"].get("presentation")]
            a, b2 = dials[0]["box"], dials[1]["box"]
            # same page + identical rect = guaranteed overlap
            b2["varname"] = a.get("varname", "midi__x") .rsplit("__", 1)[0] + "__clash"
            b2["presentation_rect"] = list(a["presentation_rect"])
        errs = self._errors_after(m)
        self.assertTrue(any("overlap" in e for e in errs), errs)

    def test_catches_too_tall(self):
        # push a control below Live's 169px clip line
        def m(p):
            for b in p["boxes"]:
                if b["box"].get("presentation_rect"):
                    b["box"]["presentation_rect"][1] = L.DEVICE_MAX_HEIGHT_PX + 40
                    break
        errs = self._errors_after(m)
        self.assertTrue(any("clip" in e or "px tall" in e for e in errs), errs)

    def test_catches_off_canvas(self):
        def m(p):
            for b in p["boxes"]:
                if b["box"].get("presentation_rect"):
                    b["box"]["presentation_rect"][0] = -50
                    break
        errs = self._errors_after(m)
        self.assertTrue(any("negative" in e for e in errs), errs)

    def test_catches_duplicate_parameter_name(self):
        def m(p):
            params = [b for b in p["boxes"] if b["box"].get("parameter_enable") == 1]
            a = params[0]["box"]["saved_attribute_attributes"]["valueof"]
            b = params[1]["box"]["saved_attribute_attributes"]["valueof"]
            b["parameter_longname"] = a["parameter_longname"]
        errs = self._errors_after(m)
        self.assertTrue(any("duplicate parameter long name" in e for e in errs), errs)

    def test_catches_not_in_presentation(self):
        def m(p):
            p["openinpresentation"] = 0
        self.assertTrue(self._errors_after(m))

    def test_catches_missing_js(self):
        def m(p):
            for b in p["boxes"]:
                if b["box"].get("text", "").startswith("v8"):
                    b["box"]["text"] = "v8 does_not_exist.js"
                    break
        errs = self._errors_after(m)
        self.assertTrue(any(".js" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
