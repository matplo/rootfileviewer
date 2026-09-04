from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from rootfileviewer.backends.numpy_arrays import walk
from rootfileviewer.core import branch_histogram_data, branch_nodes, node_facts


class NumpyBackendTests(unittest.TestCase):
    def _tmp_path(self, filename: str) -> str:
        return str(Path(tempfile.mkdtemp()) / filename)

    def test_single_npy_is_one_top_level_leaf_node(self) -> None:
        path = self._tmp_path("test.npy")
        np.save(path, np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        nodes = walk(path)
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.name, "test")
        self.assertTrue(node.is_branch)
        self.assertFalse(node.is_dir)
        centers, values, note = branch_histogram_data(node.obj)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "5 entries")

    def test_npz_produces_one_leaf_node_per_array(self) -> None:
        path = self._tmp_path("test.npz")
        np.savez(path, a=np.array([1.0, 2.0]), b=np.array([3, 4, 5], dtype="int32"))
        nodes = {n.name: n for n in walk(path)}
        self.assertEqual(set(nodes), {"a", "b"})
        self.assertTrue(all(n.is_branch for n in nodes.values()))
        self.assertEqual(nodes["a"].obj.num_entries, 2)
        self.assertEqual(nodes["b"].obj.num_entries, 3)

    def test_name_filter_matches_array_names_in_npz(self) -> None:
        path = self._tmp_path("test.npz")
        np.savez(path, keep=np.array([1.0]), drop=np.array([2.0]))
        nodes = walk(path, name_filter="keep")
        self.assertEqual([n.name for n in nodes], ["keep"])

    def test_ragged_object_array_is_flattened_for_plotting(self) -> None:
        # numpy's own representation of jagged/variable-length data: an
        # object-dtype array whose elements are numpy sub-arrays of
        # differing length -- the concrete "awkward arrays functionality"
        # case this backend was built for.
        path = self._tmp_path("test.npz")
        ragged = np.empty(4, dtype=object)
        ragged[0] = np.array([1.0, 2.0, 3.0])
        ragged[1] = np.array([4.0])
        ragged[2] = np.array([])
        ragged[3] = np.array([5.0, 6.0])
        np.savez(path, tracks=ragged)

        node = walk(path)[0]
        self.assertIn("ragged<float64>", node.classname)
        centers, values, note = branch_histogram_data(node.obj)
        self.assertEqual(len(centers), 30)
        self.assertIn("4 entries", note)
        self.assertIn("6 values (flattened)", note)

    def test_structured_dtype_is_rejected_with_a_clear_message(self) -> None:
        path = self._tmp_path("test.npy")
        structured = np.array([(1, 2.0), (3, 4.0)], dtype=[("a", "i8"), ("b", "f8")])
        np.save(path, structured)
        node = walk(path)[0]
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(node.obj)
        self.assertIn("structured dtype", str(ctx.exception))

    def test_string_array_reports_not_numeric(self) -> None:
        path = self._tmp_path("test.npy")
        np.save(path, np.array(["a", "b", "c"]))
        node = walk(path)[0]
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(node.obj)
        self.assertIn("not numeric", str(ctx.exception))

    def test_narrow_multidim_array_splits_into_generic_columns(self) -> None:
        # No attribute mechanism exists for numpy files (unlike HDF5), so
        # there's no real name -- but a (3, 2) array's 2 last-axis entries
        # are still probably distinct quantities, not one homogeneous blob,
        # so this should split rather than flatten everything together.
        path = self._tmp_path("test.npy")
        np.save(path, np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]))
        node = walk(path)[0]
        self.assertEqual(node.classname, "NpyColumnSet")
        self.assertTrue(node.is_tree)
        columns = {b.name: b for b in branch_nodes(node.obj)}
        self.assertEqual(set(columns), {"column_0", "column_1"})
        centers, values, note = branch_histogram_data(columns["column_0"].obj)
        self.assertEqual(note, "3 entries")
        self.assertEqual(list(columns["column_0"].obj.array()), [1.0, 3.0, 5.0])
        self.assertEqual(list(columns["column_1"].obj.array()), [2.0, 4.0, 6.0])

    def test_wide_multidim_array_still_flattens(self) -> None:
        # A last axis wider than MAX_SPLIT_COLUMNS (e.g. an embedding-style
        # vector) is presumed genuinely homogeneous -- flattening stays the
        # right default there, unlike the narrow case above.
        path = self._tmp_path("test.npy")
        wide = np.arange(3 * 25, dtype="float64").reshape(3, 25)
        np.save(path, wide)
        node = walk(path)[0]
        self.assertTrue(node.is_branch)
        self.assertNotEqual(node.classname, "NpyColumnSet")
        centers, values, note = branch_histogram_data(node.obj)
        self.assertEqual(note, "3 entries, 75 values (flattened)")

    def test_structured_dtype_2d_array_is_not_split(self) -> None:
        path = self._tmp_path("test.npy")
        structured = np.array([[(1, 2.0), (3, 4.0)]] * 3, dtype=[("a", "i8"), ("b", "f8")])
        np.save(path, structured)
        node = walk(path)[0]
        self.assertNotEqual(node.classname, "NpyColumnSet")
        self.assertTrue(node.is_branch)

    def test_node_facts_reports_entries(self) -> None:
        path = self._tmp_path("test.npy")
        np.save(path, np.array([1.0, 2.0, 3.0]))
        node = walk(path)[0]
        self.assertEqual(node_facts(node), {"entries": 3})


if __name__ == "__main__":
    unittest.main()
