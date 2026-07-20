"""Day/night scheduler tests — gates applied per period, config untouched."""
import time
import unittest

from daynight import DayNightScheduler


class FakeConfig:
    def __init__(self, schedule):
        self._d = {"schedule": schedule}

    def get(self, key):
        return self._d.get(key)


class FakeEngine:
    output_on = True


class FakeBorder:
    schedule_on = True


class FakeAudio:
    def __init__(self):
        self.enabled = True

    def set_master_enabled(self, on):
        self.enabled = on


def clock_at(hhmm):
    h, m = hhmm.split(":")
    return lambda: time.struct_time((2026, 8, 30, int(h), int(m), 0, 0, 0, -1))


def make(schedule, now="12:00"):
    e, b, a = FakeEngine(), FakeBorder(), FakeAudio()
    s = DayNightScheduler(FakeConfig(schedule), engine=e, border=b, audio=a,
                          clock=clock_at(now))
    return s, e, b, a


BASE = {"enabled": True, "day_start": "09:00", "night_start": "20:00",
        "day": {"floor": False, "border": False, "audio": True},
        "night": {"floor": True, "border": True, "audio": True}}


class TestScheduler(unittest.TestCase):

    def test_day_gates_applied(self):
        s, e, b, a = make(BASE, now="12:00")
        s.tick()
        self.assertEqual(s.state()["period"], "day")
        self.assertFalse(e.output_on)
        self.assertFalse(b.schedule_on)
        self.assertTrue(a.enabled)

    def test_night_gates_applied(self):
        s, e, b, a = make(BASE, now="22:30")
        s.tick()
        self.assertEqual(s.state()["period"], "night")
        self.assertTrue(e.output_on)
        self.assertTrue(b.schedule_on)

    def test_disabled_means_everything_on(self):
        s, e, b, a = make({**BASE, "enabled": False,
                           "day": {"floor": False, "border": False,
                                   "audio": False}}, now="12:00")
        s.tick()
        self.assertIsNone(s.state()["period"])
        self.assertTrue(e.output_on)
        self.assertTrue(b.schedule_on)
        self.assertTrue(a.enabled)

    def test_boundaries(self):
        s, e, b, a = make(BASE, now="09:00")
        s.tick()
        self.assertEqual(s.state()["period"], "day")    # day start inclusive
        s2, *_ = make(BASE, now="20:00")
        s2.tick()
        self.assertEqual(s2.state()["period"], "night")  # night start inclusive

    def test_window_wrapping_midnight(self):
        cfg = {**BASE, "day_start": "21:00", "night_start": "06:00"}
        s, *_ = make(cfg, now="23:00")
        s.tick()
        self.assertEqual(s.state()["period"], "day")
        s2, *_ = make(cfg, now="12:00")
        s2.tick()
        self.assertEqual(s2.state()["period"], "night")

    def test_bad_time_strings_fall_back(self):
        s, e, b, a = make({**BASE, "day_start": "banana",
                           "night_start": None}, now="12:00")
        s.tick()                                # defaults 09:00 / 20:00
        self.assertEqual(s.state()["period"], "day")
