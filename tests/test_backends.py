from __future__ import annotations

import unittest

from rootfileviewer.backends import MissingBackendError, find_backend


class BackendRegistryTests(unittest.TestCase):
    def test_find_backend_matches_parquet_extensions(self) -> None:
        for path in ("file.parquet", "FILE.PARQUET", "file.pq", "dir/sub/file.pq"):
            with self.subTest(path=path):
                spec = find_backend(path)
                self.assertIsNotNone(spec)
                self.assertEqual(spec.name, "parquet")

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


if __name__ == "__main__":
    unittest.main()
