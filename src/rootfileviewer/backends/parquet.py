"""Parquet-file adapter.

Duck-types the parts of an uproot TTree/TBranch that core.py's generic
functions (tree_branch_info, branch_nodes, branch_histogram_data,
flatten_trees, node_facts) and all of tui.py's tree population/selection/
plotting already know how to use: a "tree-like" object exposing
`.num_entries`/`.branches`, and "branch-like" objects exposing
`.name`/`.typename`/`.num_entries`/`.array(library=..., entry_stop=...)`.

Because of that, the whole file is modeled as a single Node
(classname="ParquetTable", already recognized by Node.is_tree) whose
children are its columns -- mirroring how a TTree node expands into branch
leaves -- so the rest of the pipeline needs no format-specific code at all.
"""

from __future__ import annotations

import os
import re

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from rootfileviewer.core import Node


class ParquetColumn:
    """Duck-types a TBranch: name, typename, num_entries, array()."""

    def __init__(self, parquet_file: pq.ParquetFile, field: pa.Field, num_entries: int):
        self._pf = parquet_file
        self._field = field
        self.name = field.name
        self.typename = str(field.type)
        self.num_entries = num_entries

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for parquet column '{self.name}'")
        if pa.types.is_nested(self._field.type):
            raise ValueError(
                f"column '{self.name}' has nested type {self._field.type} and is not supported"
            )

        n_needed = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        if n_needed <= 0:
            arr = np.array([])
        else:
            chunks: list[np.ndarray] = []
            total = 0
            for batch in self._pf.iter_batches(batch_size=n_needed, columns=[self.name]):
                col = batch.column(0)
                chunks.append(col.to_numpy(zero_copy_only=False))
                total += len(col)
                if total >= n_needed:
                    break
            arr = np.concatenate(chunks)[:n_needed] if chunks else np.array([])

        if library == "ak":
            import awkward as ak

            # awkward's Array() constructor rejects numpy object-dtype arrays
            # outright (e.g. a Parquet string column comes back from to_numpy()
            # as dtype=object); going through a plain list lets it infer a
            # proper (string) awkward type instead of raising here. This
            # column is already flat, so no jagged/nested structure is lost.
            if arr.dtype == object:
                return ak.Array(arr.tolist())
            return ak.Array(arr)
        return arr


class ParquetTable:
    """Duck-types a TTree: num_entries, branches (list of ParquetColumn)."""

    def __init__(self, path: str, name_filter: str | None = None):
        self._pf = pq.ParquetFile(path)
        self.num_entries = self._pf.metadata.num_rows
        self.num_row_groups = self._pf.metadata.num_row_groups
        self._all_fields = list(self._pf.schema_arrow)
        pattern = re.compile(name_filter) if name_filter else None
        self._fields = [f for f in self._all_fields if not pattern or pattern.search(f.name)]

    @property
    def branches(self) -> list[ParquetColumn]:
        return [ParquetColumn(self._pf, f, self.num_entries) for f in self._fields]

    @property
    def num_columns_total(self) -> int:
        """Unfiltered top-level column count, for the file summary panel."""
        return len(self._all_fields)


def walk(path: str, name_filter: str | None = None) -> list[Node]:
    table = ParquetTable(path, name_filter=name_filter)
    return [Node(name="table", classname="ParquetTable", obj=table)]


def summary(path: str, nodes: list[Node]) -> dict:
    table: ParquetTable = nodes[0].obj
    return {
        "path": path,
        "format": "parquet",
        "size_bytes": os.path.getsize(path),
        "pyarrow_version": pa.__version__,
        "num_rows": table.num_entries,
        "num_columns": table.num_columns_total,
        "num_row_groups": table.num_row_groups,
        "total_keys": 1,
    }
