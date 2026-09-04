from __future__ import annotations

import unittest

import numpy as np

from rootfileviewer.core import branch_histogram_data


class _FakeBranch:
    """Minimal duck-typed branch: the exact surface branch_histogram_data
    needs (name, num_entries, array()). Used to regression-test core.py's
    shared numeric-histogramming logic without depending on any specific
    (optional) backend."""

    def __init__(self, name: str, values):
        self.name = name
        self._values = np.asarray(values)
        self.num_entries = len(self._values)

    def array(self, library: str = "np", entry_stop=None):
        arr = self._values if entry_stop is None else self._values[:entry_stop]
        if library == "ak":
            import awkward as ak

            return ak.Array(arr.tolist())
        return arr


class BranchHistogramDataTests(unittest.TestCase):
    def test_float16_precision_overflow_does_not_produce_inf_centers(self) -> None:
        # Regression: np.histogram() computes bin edges in the *input
        # array's own dtype*. For float16, two finite-but-large edges can
        # overflow float16's ~65504 max when added together to compute a
        # bin center -- even though neither the raw data nor np.histogram's
        # own output contained any inf. That inf then crashed plotext's
        # tick rendering downstream (reported against a real HDF5 file with
        # a float16 dataset).
        branch = _FakeBranch("vals", np.array([1.0, 100.0, 60000.0, 65000.0, 500.0], dtype="float16"))
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertTrue(all(np.isfinite(c) for c in centers))
        self.assertEqual(note, "5 entries")

    def test_literal_infinite_values_are_excluded_and_noted(self) -> None:
        branch = _FakeBranch("vals", np.array([1.0, 2.0, 3.0, float("inf"), 4.0]))
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertTrue(all(np.isfinite(c) for c in centers))
        self.assertEqual(note, "5 entries, 1 non-finite excluded")

    def test_nan_values_are_excluded_and_noted(self) -> None:
        branch = _FakeBranch("vals", np.array([1.0, 2.0, float("nan"), 3.0]))
        centers, values, note = branch_histogram_data(branch)
        self.assertTrue(all(np.isfinite(c) for c in centers))
        self.assertIn("1 non-finite excluded", note)

    def test_all_nonfinite_raises_a_clear_error(self) -> None:
        branch = _FakeBranch("vals", np.array([float("inf"), float("nan"), float("-inf")]))
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(branch)
        self.assertIn("only non-finite", str(ctx.exception))

    def test_flat_numeric_case_is_unaffected(self) -> None:
        branch = _FakeBranch("vals", np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "5 entries")

    def test_log_x_produces_geometrically_spaced_centers(self) -> None:
        rng = np.random.default_rng(0)
        branch = _FakeBranch("vals", rng.exponential(scale=10, size=2000) + 0.1)
        centers, values, note = branch_histogram_data(branch, log_x=True)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "2,000 entries")
        # Equal-width-in-log-space bins -> the ratio between consecutive
        # centers is constant (not true for linear bins on this data).
        ratios = [centers[i + 1] / centers[i] for i in range(len(centers) - 1)]
        self.assertTrue(all(abs(r - ratios[0]) < 1e-9 for r in ratios))

    def test_log_x_rejects_non_positive_values(self) -> None:
        branch = _FakeBranch("vals", np.array([-1.0, 2.0, 3.0]))
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(branch, log_x=True)
        self.assertIn("non-positive", str(ctx.exception))

    def test_log_x_rejects_zero(self) -> None:
        # A log axis can't represent exactly zero either, not just negatives.
        branch = _FakeBranch("vals", np.array([0.0, 2.0, 3.0]))
        with self.assertRaises(ValueError):
            branch_histogram_data(branch, log_x=True)


if __name__ == "__main__":
    unittest.main()
