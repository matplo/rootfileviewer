"""pandas-readable-file adapter (.csv, .pkl/.pickle, .feather, .jsonl/.ndjson).

Same "table" shape as Parquet -- one dict of readers by extension, then a
DataFrameTable/DataFrameColumn pair that's structurally a near-clone of
ParquetTable/ParquetColumn, so it plugs into the same is_tree-wrapper-node
reuse (see core.py's Node.is_tree, which recognizes "DataFrameTable").

Security note: .pkl/.pickle files are loaded via pandas.read_pickle, which
uses Python's pickle module under the hood and can execute arbitrary code
embedded in the file -- the same trust model as backends/numpy_arrays.py's
ragged-array support. Only open .pkl/.pickle files from trusted sources.
"""

from __future__ import annotations

import os
import re

import numpy as np
import pandas as pd

from rootfileviewer.backends._common import to_awkward
from rootfileviewer.core import Node

_READERS = {
    ".csv": pd.read_csv,
    ".pkl": pd.read_pickle,
    ".pickle": pd.read_pickle,
    ".feather": pd.read_feather,
    ".jsonl": lambda path: pd.read_json(path, lines=True),
    ".ndjson": lambda path: pd.read_json(path, lines=True),  # common alt spelling
}


def _display_dtype(series: pd.Series) -> str:
    """A human-readable dtype string -- for a plain column, just its dtype;
    for an object-dtype column holding a per-row list/array (pandas' own
    representation of ragged data), peek at the first non-empty element to
    show e.g. "ragged<float64>" instead of the uninformative "object"
    (mirrors the same treatment given to HDF5's vlen datasets and numpy's
    own ragged arrays)."""
    if series.dtype != object:
        return str(series.dtype)
    for element in series:
        # Only list/array-shaped elements count as "ragged" -- a plain
        # string also has __len__, but isn't the case this is meant to
        # detect (a per-row variable-length list/array of values).
        if isinstance(element, (list, tuple, np.ndarray)) and len(element) > 0:
            return f"ragged<{np.asarray(element).dtype}>"
    return "object"


class DataFrameColumn:
    """Duck-types a TBranch: name, typename, num_entries, array()."""

    def __init__(self, series: pd.Series):
        self._series = series
        self.name = str(series.name)
        self.typename = _display_dtype(series)
        self.num_entries = len(series)

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for column '{self.name}'")
        n = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        values = self._series.iloc[:n].to_numpy()
        if library == "ak":
            return to_awkward(values)
        return values


class DataFrameTable:
    """Duck-types a TTree: num_entries, branches (list of DataFrameColumn)."""

    def __init__(self, df: pd.DataFrame, name_filter: str | None = None):
        self._df = df
        self.num_entries = len(df)
        pattern = re.compile(name_filter) if name_filter else None
        self._columns = [c for c in df.columns if not pattern or pattern.search(str(c))]

    @property
    def branches(self) -> list[DataFrameColumn]:
        return [DataFrameColumn(self._df[c]) for c in self._columns]

    @property
    def num_columns_total(self) -> int:
        """Unfiltered column count, for the file summary panel."""
        return len(self._df.columns)


def walk(path: str, depth: int | None = None, name_filter: str | None = None) -> list[Node]:
    # depth is accepted for interface uniformity with other backends
    # (cli.py's single call site passes it unconditionally) but is a no-op
    # here -- a DataFrame is one flat table, nothing to recurse into.
    ext = os.path.splitext(path)[1].lower()
    df = _READERS[ext](path)
    table = DataFrameTable(df, name_filter=name_filter)
    return [Node(name="table", classname="DataFrameTable", obj=table)]


def summary(path: str, nodes: list[Node]) -> dict:
    table: DataFrameTable = nodes[0].obj
    return {
        "path": path,
        "format": "pandas",
        "size_bytes": os.path.getsize(path),
        "pandas_version": pd.__version__,
        "num_rows": table.num_entries,
        "num_columns": table.num_columns_total,
        "total_keys": 1,
    }
