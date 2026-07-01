"""Tests for bench_link's power-state labelling (the UI's active/saving/low
indicator). _power_label prefers the leg's own report (fw ≥ v10) and falls
back to the occupancy flag for older firmware."""
import unittest

from bench_link import NodeState, BenchLink


class TestPowerLabel(unittest.TestCase):

    def test_reported_states(self):
        self.assertEqual(BenchLink._power_label(NodeState(power_state=0)), "active")
        self.assertEqual(BenchLink._power_label(NodeState(power_state=1)), "saving")
        self.assertEqual(BenchLink._power_label(NodeState(power_state=2)), "low-batt")

    def test_fallback_from_occupancy_when_no_report(self):
        # pre-v10 firmware: no power_state, derive from occ
        self.assertEqual(BenchLink._power_label(NodeState(occ=1)), "active")
        self.assertEqual(BenchLink._power_label(NodeState(occ=0)), "saving")

    def test_unknown_when_nothing_reported(self):
        self.assertEqual(BenchLink._power_label(NodeState()), "—")

    def test_report_wins_over_occupancy(self):
        # An idle leg whose last occ flag was stale-1 still reports saving.
        self.assertEqual(
            BenchLink._power_label(NodeState(power_state=1, occ=1)), "saving")


if __name__ == "__main__":
    unittest.main()
