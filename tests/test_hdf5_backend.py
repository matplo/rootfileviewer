from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from rootfileviewer.core import branch_histogram_data, branch_nodes, node_facts

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

    def test_narrow_multidim_dataset_without_an_attr_splits_into_generic_columns(self) -> None:
        # No matching *_features attribute exists here -- but a (3, 2)
        # dataset's 2 last-axis entries still probably aren't one
        # homogeneous blob, so this should split with generic names rather
        # than flattening everything together.
        path = self._write({"grid": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]})
        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        self.assertEqual(node.classname, "HDF5FeatureSet")
        self.assertTrue(node.is_tree)
        columns = {b.name: b for b in branch_nodes(node.obj)}
        self.assertEqual(set(columns), {"column_0", "column_1"})
        centers, values, note = branch_histogram_data(columns["column_0"].obj)
        self.assertEqual(note, "3 entries")

    def test_wide_multidim_dataset_still_flattens(self) -> None:
        # A last axis wider than MAX_SPLIT_COLUMNS is presumed genuinely
        # homogeneous -- flattening stays the right default there.
        import numpy as np

        path = self._write({"wide": np.arange(3 * 25, dtype="float64").reshape(3, 25)})
        dataset = self._dataset(path, "wide")
        self.assertEqual(dataset.num_entries, 3)
        centers, values, note = branch_histogram_data(dataset)
        self.assertEqual(note, "3 entries, 75 values (flattened)")

    def test_node_facts_reports_entries_for_a_leaf_dataset(self) -> None:
        from rootfileviewer.backends.hdf5 import walk

        path = self._write({"nums": [1.0, 2.0, 3.0]})
        node = walk(path)[0]
        self.assertEqual(node_facts(node), {"entries": 3})

    def test_root_level_features_attr_splits_dataset_into_named_columns(self) -> None:
        # The convention used by a real file this was built against: a
        # `<dataset-name>_features` attribute at the file root, naming each
        # entry along the dataset's last axis.
        import h5py
        import numpy as np

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            f.create_dataset("jet", data=np.arange(6, dtype="float32").reshape(2, 3))
            f.attrs["jet_features"] = ["pt", "eta", "phi"]

        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        self.assertEqual(node.classname, "HDF5FeatureSet")
        self.assertTrue(node.is_tree)
        columns = {b.name: b for b in node.obj.branches}
        self.assertEqual(set(columns), {"pt", "eta", "phi"})
        centers, values, note = branch_histogram_data(columns["eta"])
        self.assertEqual(note, "2 entries")

    def test_dataset_level_features_attr_also_splits_columns(self) -> None:
        import h5py
        import numpy as np

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            ds = f.create_dataset("jet", data=np.arange(6, dtype="float32").reshape(2, 3))
            ds.attrs["features"] = ["pt", "eta", "phi"]

        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        self.assertEqual({b.name for b in node.obj.branches}, {"pt", "eta", "phi"})

    def test_mismatched_length_feature_attr_falls_back_to_generic_columns(self) -> None:
        # An attr that doesn't match the last axis's length is a false
        # positive for real names -- don't guess at a name that's provably
        # wrong, but a (2, 3) shape still qualifies for the same generic
        # column split a missing attribute would get.
        import h5py
        import numpy as np

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            f.create_dataset("jet", data=np.arange(6, dtype="float32").reshape(2, 3))
            f.attrs["jet_features"] = ["only", "two"]  # length 2, but last axis is 3

        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        self.assertEqual(node.classname, "HDF5FeatureSet")
        self.assertEqual({b.name for b in branch_nodes(node.obj)}, {"column_0", "column_1", "column_2"})

    def test_1d_dataset_is_never_split_even_with_a_matching_attr(self) -> None:
        import h5py
        import numpy as np

        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            f.create_dataset("nums", data=np.array([1.0, 2.0, 3.0], dtype="float32"))
            # Coincidentally matches length 3, but ndim < 2 -- there's no
            # "last axis" of independent features to split here.
            f.attrs["nums_features"] = ["a", "b", "c"]

        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        self.assertTrue(node.is_branch)
        self.assertNotEqual(node.classname, "HDF5FeatureSet")

    def test_3d_dataset_splits_and_flattens_each_named_column(self) -> None:
        # The real-world shape this was built for: (events, particles,
        # features) -- each named feature is still 2D per column and needs
        # flattening across the middle axis, same as an unsplit dataset.
        import h5py
        import numpy as np

        rng = np.random.default_rng(0)
        data = rng.normal(size=(5, 10, 2)).astype("float32")
        path = str(Path(tempfile.mkdtemp()) / "test.h5")
        with h5py.File(path, "w") as f:
            f.create_dataset("particle", data=data)
            f.attrs["particle_features"] = ["eta", "phi"]

        from rootfileviewer.backends.hdf5 import walk

        node = walk(path)[0]
        columns = {b.name: b for b in node.obj.branches}
        centers, values, note = branch_histogram_data(columns["eta"])
        self.assertEqual(note, "5 entries, 50 values (flattened)")


if __name__ == "__main__":
    unittest.main()
