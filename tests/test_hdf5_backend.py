from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from rootfileviewer.core import branch_histogram_data, node_facts

HAVE_H5PY = importlib.util.find_spec("h5py") is not None


@unittest.skipUnless(HAVE_H5PY, "h5py not installed (pip install rootfileviewer[hdf5])")
class HDF5BackendTests(unittest.TestCase):
    def _write(self, datasets: dict, groups: dict | None = None) -> str:
        import h5py

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            for name, data in datasets.items():
                f.create_dataset(name, data=data)
            for group_name, group_datasets in (groups or {}).items():
                grp = f.create_group(group_name)
                for name, data in group_datasets.items():
                    grp.create_dataset(name, data=data)
        return path

    def _dataset(self, path: str, name: str):
        from rootfileviewer.backends.hdf5 import walk

        return {n.name: n for n in walk(path)}[name].obj

    def test_groups_nest_like_root_directories(self) -> None:
        from rootfileviewer.backends.hdf5 import walk

        path = self._write({"top": [1.0, 2.0]}, groups={"aux": {"run_number": [123]}})
        nodes = walk(path)
        by_name = {n.name: n for n in nodes}
        self.assertTrue(by_name["aux"].is_dir)
        self.assertFalse(by_name["top"].is_dir)
        self.assertEqual(by_name["aux"].children[0].name, "run_number")
        self.assertTrue(by_name["aux"].children[0].is_branch)

    def test_depth_limits_recursion(self) -> None:
        from rootfileviewer.backends.hdf5 import walk

        path = self._write({}, groups={"aux": {"run_number": [123]}})
        nodes = walk(path, depth=0)
        self.assertEqual(nodes[0].children, [])

    def test_jagged_vlen_dataset_is_flattened_for_plotting(self) -> None:
        import h5py
        import numpy as np

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            vlen_dt = h5py.vlen_dtype(np.dtype("float64"))
            ds = f.create_dataset("tracks", (4,), dtype=vlen_dt)
            ds[0] = np.array([1.0, 2.0, 3.0])
            ds[1] = np.array([4.0])
            ds[2] = np.array([])
            ds[3] = np.array([5.0, 6.0])

        dataset = self._dataset(path, "tracks")
        self.assertIn("vlen<float64>", dataset.typename)
        centers, values, note = branch_histogram_data(dataset)
        self.assertEqual(len(centers), 30)
        self.assertIn("4 entries", note)
        self.assertIn("6 values (flattened)", note)

    def test_compound_dtype_is_rejected_with_a_clear_message(self) -> None:
        import numpy as np

        compound_dt = np.dtype([("a", "i8"), ("b", "f8")])
        path = self._write({"s": np.array([(1, 2.0), (3, 4.0)], dtype=compound_dt)})
        dataset = self._dataset(path, "s")
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(dataset)
        self.assertIn("compound", str(ctx.exception))

    def test_string_dataset_reports_not_numeric(self) -> None:
        import h5py
        import numpy as np

        path = self._write({"labels": np.array(["a", "b", "c"], dtype=h5py.string_dtype())})
        dataset = self._dataset(path, "labels")
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(dataset)
        self.assertIn("not numeric", str(ctx.exception))

    def test_flat_numeric_dataset_plots_directly(self) -> None:
        path = self._write({"nums": [1.0, 2.0, 3.0, 4.0, 5.0]})
        dataset = self._dataset(path, "nums")
        centers, values, note = branch_histogram_data(dataset)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "5 entries")

    def test_multidim_dataset_is_flattened_across_extra_axes(self) -> None:
        path = self._write({"grid": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]})
        dataset = self._dataset(path, "grid")
        self.assertEqual(dataset.num_entries, 3)
        centers, values, note = branch_histogram_data(dataset)
        self.assertEqual(note, "3 entries, 6 values (flattened)")

    def test_node_facts_reports_entries_for_a_leaf_dataset(self) -> None:
        from rootfileviewer.backends.hdf5 import walk

        path = self._write({"nums": [1.0, 2.0, 3.0]})
        node = walk(path)[0]
        self.assertEqual(node_facts(node), {"entries": 3})


if __name__ == "__main__":
    unittest.main()
