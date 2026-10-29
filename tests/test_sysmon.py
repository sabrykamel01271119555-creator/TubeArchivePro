import tempfile, unittest
from types import SimpleNamespace as NS
from app import sysmon


class Mon(unittest.TestCase):
    def test_sample_rates_and_scale(self):
        t = [0.0]
        m = sysmon.SysMonitor(clock=lambda: t[0])
        d = tempfile.gettempdir()
        a = m.sample(d)
        self.assertEqual((a["net"], a["disk"]), (0.0, 0.0))                    # first sample has no rate
        self.assertGreater(a["total"], a["free"] - 1)
        t[0] = 2.0
        m._counters = lambda: (10_000_000, 6_000_000)                           # 10 MB in 2 s from 0
        m._last = (0.0, 0, 0)
        b = m.sample(d + "/does/not/exist")                                     # a folder that is not there yet
        self.assertAlmostEqual(b["net"], 5.0)
        self.assertAlmostEqual(b["disk"], 3.0)
        self.assertGreater(b["total"], 0)                                       # the partition of its parent
        self.assertEqual(sysmon.auto_max(4, sysmon.NET_STEPS), 5)
        self.assertEqual(sysmon.auto_max(4.6, sysmon.NET_STEPS), 10)
        self.assertEqual(sysmon.human_size(2.5e9), ("2.5", "GB"))
        self.assertEqual(sysmon.human_size(5e8), ("500", "MB"))


if __name__ == "__main__":
    unittest.main()
