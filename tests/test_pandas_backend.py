from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from rootfileviewer.core import branch_histogram_data, branch_nodes

HAVE_PANDAS = importlib.util.find_spec("pandas") is not None


@unittest.skipUnless(HAVE_PANDAS, "pandas not installed (pip install rootfileviewer[pandas])")
class PandasBackendTests(unittest.TestCase):
    def _write_csv(self, df) -> str:
        path = str(Path(tempfile.mkdtemp()) / "test.csv")
        df.to_csv(path, index=False)
        return path

    def _write_pickle(self, df) -> str:
        path = str(Path(tempfile.mkdtemp()) / "test.pkl")
        df.to_pickle(path)
        return path

    def _branch(self, path: str, name: str):
        from rootfileviewer.backends.pandas_tables import walk

        table = walk(path)[0].obj
        return {b.name: b for b in branch_nodes(table)}[name].obj

    def test_flat_numeric_column_plots_directly(self) -> None:
        import pandas as pd

        path = self._write_csv(pd.DataFrame({"nums": [1.0, 2.0, 3.0, 4.0, 5.0]}))
        branch = self._branch(path, "nums")
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertEqual(note, "5 entries")

    def test_string_column_reports_not_numeric(self) -> None:
        import pandas as pd

        path = self._write_csv(pd.DataFrame({"labels": ["a", "b", "c", "d", "e"]}))
        branch = self._branch(path, "labels")
        with self.assertRaises(ValueError) as ctx:
            branch_histogram_data(branch)
        self.assertIn("not numeric", str(ctx.exception))

    def test_ragged_list_column_is_flattened_for_plotting(self) -> None:
        # A cell holding a Python list -- pandas' own representation of
        # per-row variable-length data, and the concrete "awkward arrays
        # functionality" case this backend was built for. CSV can't
        # round-trip this (it serializes to a literal string), so pickle is
        # used here, same as the README's own sample fixture.
        import pandas as pd

        path = self._write_pickle(pd.DataFrame({"tracks": [[1.0, 2.0, 3.0], [4.0], [], [5.0, 6.0]]}))
        branch = self._branch(path, "tracks")
        self.assertIn("ragged<float64>", branch.typename)
        centers, values, note = branch_histogram_data(branch)
        self.assertEqual(len(centers), 30)
        self.assertIn("4 entries", note)
        self.assertIn("6 values (flattened)", note)

    def test_filter_matches_column_names(self) -> None:
        import pandas as pd

        from rootfileviewer.backends.pandas_tables import walk

        path = self._write_csv(pd.DataFrame({"pt": [1.0], "eta": [2.0], "n_jets": [3]}))
        table = walk(path, name_filter="pt|eta")[0].obj
        self.assertEqual({b.name for b in table.branches}, {"pt", "eta"})
        self.assertEqual(table.num_columns_total, 3)

    def test_csv_extension_dispatches_to_read_csv(self) -> None:
        import pandas as pd

        path = self._write_csv(pd.DataFrame({"a": [1, 2, 3]}))
        branch = self._branch(path, "a")
        self.assertEqual(branch.num_entries, 3)


if __name__ == "__main__":
    unittest.main()
