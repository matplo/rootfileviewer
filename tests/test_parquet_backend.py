from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from rootfileviewer.core import branch_histogram_data, branch_nodes

HAVE_PYARROW = importlib.util.find_spec("pyarrow") is not None


@unittest.skipUnless(HAVE_PYARROW, "pyarrow not installed (pip install rootfileviewer[parquet])")
class ParquetBackendTests(unittest.TestCase):
    def _write(self, table_dict) -> str:
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = str(Path(tempfile.mkdtemp()) / "test.parquet")
        pq.write_table(pa.table(table_dict), path)
        return path

    def _branch(self, path: str, name: str):
        from rootfileviewer.backends.parquet import walk

        table = walk(path)[0].obj
        return {b.name: b for b in branch_nodes(table)}[name].obj

    def test_jagged_list_column_is_flattened_for_plotting(self) -> None:
        # A per-row variable-length list<double> column -- e.g. a per-event
        # list of track energies -- is the physics-data-shaped analogue of a
        # jagged ROOT branch, and should flatten the same way rather than
        # being rejected as "nested".
        path = self._write({"tracks": [[1.0, 2.0, 3.0], [4.0], [], [5.0, 6.0]]})
        branch = self._branch(path, "tracks")
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertIn("4 entries", note)
        self.assertIn("6 values (flattened)", note)

    def test_struct_column_is_rejected_with_a_clear_message(self) -> None:
        import pyarrow as pa

        path = self._write(
            {"s": pa.array([{"a": 1, "b": 2.0}, {"a": 3, "b": 4.0}], type=pa.struct([("a", pa.int64()), ("b", pa.float64())]))}
        )
        branch = self._branch(path, "s")
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(branch)
        self.assertIn("struct", str(ctx.exception))

    def test_string_column_reports_not_numeric(self) -> None:
        path = self._write({"labels": ["a", "b", "c", "d", "e"]})
        branch = self._branch(path, "labels")
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(branch)
        self.assertIn("not numeric", str(ctx.exception))

    def test_flat_numeric_column_plots_directly(self) -> None:
        path = self._write({"nums": [1.0, 2.0, 3.0, 4.0, 5.0]})
        branch = self._branch(path, "nums")
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "5 entries")


if __name__ == "__main__":
    unittest.main()
