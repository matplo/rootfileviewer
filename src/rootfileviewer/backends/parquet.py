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

import pyarrow as pa
import pyarrow.parquet as pq

from rootfileviewer.core import Node


def _rejects_nesting(dtype: pa.DataType) -> bool:
    """True for types that can't be sensibly flattened to a numeric leaf for
    plotting, at any depth of list nesting.

    A `list<double>` (or `list<list<double>>`, etc.) column -- the common
    case for physics data, e.g. a per-event list of track energies -- is
    fine: it's read via awkward and flattened, exactly like a jagged ROOT
    branch. `struct`/`map`/`union` columns are rejected because flattening
    them mixes unrelated fields into one meaningless distribution (verified:
    `ak.flatten({"a": ..., "b": ...}, axis=None)` interleaves `a` and `b`
    values rather than raising).
    """
    while pa.types.is_list(dtype) or pa.types.is_large_list(dtype) or pa.types.is_fixed_size_list(dtype):
        dtype = dtype.value_type
    return pa.types.is_struct(dtype) or pa.types.is_map(dtype) or pa.types.is_union(dtype)


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
        if _rejects_nesting(self._field.type):
            raise ValueError(
                f"column '{self.name}' has unsupported type {self._field.type} "
                "(struct/map columns can't be flattened to a single distribution)"
            )

        n_needed = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        chunks: list[pa.Array] = []
        if n_needed > 0:
            total = 0
            for batch in self._pf.iter_batches(batch_size=n_needed, columns=[self.name]):
                col = batch.column(0)
                chunks.append(col)
                total += len(col)
                if total >= n_needed:
                    break
        if not chunks:
            combined = pa.array([], type=self._field.type)
        elif len(chunks) == 1:
            combined = chunks[0]
        else:
            combined = pa.concat_arrays(chunks)
        combined = combined.slice(0, n_needed)

        if library == "ak":
            import awkward as ak

            # ak.from_arrow (rather than wrapping an already-materialized
            # numpy array) is what correctly reconstructs list-typed/string
            # columns -- including genuinely jagged ones like
            # list<element: double> -- so core.py's `ak.flatten(..., axis=None)`
            # fallback for non-numeric dtypes works the same as it does for a
            # jagged ROOT branch.
            return ak.from_arrow(combined)
        return combined.to_numpy(zero_copy_only=False)


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


def walk(path: str, depth: int | None = None, name_filter: str | None = None) -> list[Node]:
    # depth is accepted for interface uniformity with other backends
    # (cli.py's single call site passes it unconditionally) but is a no-op
    # here -- a Parquet file is one flat table, nothing to recurse into.
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
