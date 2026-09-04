from __future__ import annotations

import unittest

from rootfileviewer.backends import MissingBackendError, find_backend, load_backend


class BackendRegistryTests(unittest.TestCase):
    def test_find_backend_matches_parquet_extensions(self) -> None:
        for path in ("file.parquet", "FILE.PARQUET", "file.pq", "dir/sub/file.pq"):
            with self.subTest(path=path):
                spec = find_backend(path)
                self.assertIsNotNone(spec)
                self.assertEqual(spec.name, "parquet")

    def test_find_backend_matches_hdf5_extensions(self) -> None:
        for path in ("file.h5", "FILE.H5", "file.hdf5", "dir/sub/file.hdf5"):
            with self.subTest(path=path):
                spec = find_backend(path)
                self.assertIsNotNone(spec)
                self.assertEqual(spec.name, "hdf5")

    def test_find_backend_matches_numpy_extensions(self) -> None:
        for path in ("file.npy", "FILE.NPY", "file.npz", "dir/sub/file.npz"):
            with self.subTest(path=path):
                spec = find_backend(path)
                self.assertIsNotNone(spec)
                self.assertEqual(spec.name, "numpy")

    def test_find_backend_returns_none_for_root_and_unknown(self) -> None:
        for path in ("file.root", "file.txt", "file", "file.parquet.bak"):
            with self.subTest(path=path):
                self.assertIsNone(find_backend(path))

    def test_missing_backend_error_names_both_install_alternatives(self) -> None:
        spec = find_backend("file.parquet")
        exc = MissingBackendError(spec, ["pyarrow"])
        message = str(exc)
        self.assertIn("pip install 'rootfileviewer[parquet]'", message)
        self.assertIn("pip install pyarrow", message)

    def test_missing_backend_error_for_hdf5(self) -> None:
        spec = find_backend("file.h5")
        exc = MissingBackendError(spec, ["h5py"])
        message = str(exc)
        self.assertIn("pip install 'rootfileviewer[hdf5]'", message)
        self.assertIn("pip install h5py", message)

    def test_load_backend_never_raises_for_numpy(self) -> None:
        # numpy is uproot's own dependency, so it's always present -- the
        # numpy backend spec declares no packages to probe, and this should
        # load without ever hitting MissingBackendError.
        spec = find_backend("file.npy")
        module = load_backend(spec)
        self.assertTrue(hasattr(module, "walk"))
        self.assertTrue(hasattr(module, "summary"))


if __name__ == "__main__":
    unittest.main()
