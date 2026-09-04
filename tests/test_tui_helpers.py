from __future__ import annotations

import math
import unittest

from rootfileviewer.tui import _log_axis_ticks


class LogAxisTicksTests(unittest.TestCase):
    def test_ticks_are_evenly_spaced_in_log_space(self) -> None:
        values, labels = _log_axis_ticks(1.0, 100.0, n=5)
        self.assertEqual(len(values), 5)
        self.assertEqual(len(labels), 5)
        self.assertAlmostEqual(values[0], 1.0)
        self.assertAlmostEqual(values[-1], 100.0)
        log_values = [math.log10(v) for v in values]
        gaps = [log_values[i + 1] - log_values[i] for i in range(len(log_values) - 1)]
        self.assertTrue(all(abs(g - gaps[0]) < 1e-9 for g in gaps))

    def test_degenerate_range_returns_single_tick(self) -> None:
        values, labels = _log_axis_ticks(5.0, 5.0)
        self.assertEqual(values, [5.0])
        self.assertEqual(len(labels), 1)

    def test_labels_are_compact_strings(self) -> None:
        values, labels = _log_axis_ticks(1.0, 1000.0)
        for label in labels:
            self.assertLessEqual(len(label), 10)


if __name__ == "__main__":
    unittest.main()
