"""numpy-file adapter (.npy single array, .npz multi-array archive).

Unlike Parquet/pandas (needs a synthetic wrapper node for a table's shared
row count) or HDF5 (real hierarchy), numpy files need no wrapper at all:
`.npy` is a single top-level leaf Node; `.npz` is several *independent*
top-level leaf Nodes, since its arrays have no shared row count to hang a
wrapper's own num_entries off of. Module named numpy_arrays (not numpy) to
avoid shadowing the real numpy package.

Security note: object-dtype (ragged/jagged) arrays -- the exact case this
project added to support "flatten ragged arrays" -- can only be loaded with
allow_pickle=True (numpy itself refuses otherwise). That means loading a
.npy/.npz file can execute arbitrary code embedded via pickle, the same
trust model as backends/pandas_tables.py's .pkl support. Only open files
from trusted sources -- documented in the README.
"""

from __future__ import annotations

import os
import re

import numpy as np

from rootfileviewer.backends._common import MAX_SPLIT_COLUMNS, is_structured, to_awkward
from rootfileviewer.core import Node


def _display_dtype(get, dtype) -> str:
    """A human-readable dtype string -- for a plain array, just its dtype;
    for numpy's own object-dtype representation of ragged/jagged data (an
    array of variable-length numpy sub-arrays), peek at the first non-empty
    element to show e.g. "ragged<float64>" instead of the uninformative
    "object" (mirrors the same treatment given to HDF5's vlen datasets)."""
    if dtype != object:
        return str(dtype)
    try:
        arr = get()
        for element in arr:
            if isinstance(element, np.ndarray) and element.size > 0:
                return f"ragged<{element.dtype}>"
    except Exception:
        pass
    return "object"


class NpyArray:
    """Duck-types a TBranch. `get` is a zero-arg callable returning the
    (possibly memory-mapped) full ndarray, called lazily so walk() never
    forces a read it doesn't need."""

    def __init__(self, name: str, get, dtype, shape: tuple[int, ...]):
        self.name = name
        shape_str = "x".join(str(d) for d in shape) if shape else "scalar"
        self.typename = f"{_display_dtype(get, dtype)}[{shape_str}]"
        self.num_entries = shape[0] if shape else 1
        self._get = get

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for array '{self.name}'")
        arr = self._get()
        if is_structured(arr):
            raise ValueError(
                f"array '{self.name}' has a structured dtype {arr.dtype} and is not supported"
            )

        n = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        sliced = arr[:n] if arr.ndim >= 1 else arr[()]
        flat = np.asarray(sliced).reshape(-1)

        if library == "ak":
            return to_awkward(flat)
        return flat


class NpyColumn:
    """Duck-types a TBranch: one column sliced out of a multi-dim array's
    last axis (e.g. data[:, 1]). No real name is available -- numpy files
    carry no per-array attribute metadata the way HDF5 does -- so it's
    labeled generically ("column_<i>")."""

    def __init__(self, get, index: int, dtype, num_entries: int):
        self._get = get
        self._index = index
        self.name = f"column_{index}"
        self.typename = str(dtype)
        self.num_entries = num_entries

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for '{self.name}'")
        arr = self._get()
        if is_structured(arr):
            raise ValueError(f"array has a structured dtype {arr.dtype} and is not supported")

        n = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        flat = np.asarray(arr[:n, ..., self._index]).reshape(-1)

        if library == "ak":
            return to_awkward(flat)
        return flat


class NpyColumnSet:
    """Duck-types a TTree: a multi-dim array whose last axis is narrow
    enough (see MAX_SPLIT_COLUMNS) to split into individually selectable/
    plottable NpyColumn leaves instead of being flattened together."""

    def __init__(self, get, shape: tuple[int, ...], dtype):
        self.num_entries = shape[0]
        self._get = get
        self._n_columns = shape[-1]
        self._dtype = dtype

    @property
    def branches(self) -> list[NpyColumn]:
        return [NpyColumn(self._get, i, self._dtype, self.num_entries) for i in range(self._n_columns)]


def _make_node(name: str, get, dtype, shape: tuple[int, ...]) -> Node:
    """A plain is_branch=True leaf for a flat (or wide-last-axis) array; a
    NpyColumnSet "table" node when the last axis is narrow enough that
    splitting it into columns beats flattening everything together."""
    if len(shape) >= 2 and shape[-1] <= MAX_SPLIT_COLUMNS and not is_structured(dtype):
        return Node(name=name, classname="NpyColumnSet", obj=NpyColumnSet(get, shape, dtype))
    wrapper = NpyArray(name, get, dtype, shape)
    return Node(name=name, classname=wrapper.typename, obj=wrapper, is_branch=True)


def walk(path: str, depth: int | None = None, name_filter: str | None = None) -> list[Node]:
    # depth is accepted for interface uniformity with other backends
    # (cli.py's single call site passes it unconditionally) but is a no-op
    # here -- numpy files are flat, nothing to recurse into.
    pattern = re.compile(name_filter) if name_filter else None

    if path.lower().endswith(".npz"):
        npz = np.load(path, allow_pickle=True)
        nodes = []
        for key in npz.files:
            if pattern and not pattern.search(key):
                continue
            # npz members are zip-compressed, so unlike a single .npy file
            # they can't be memory-mapped/read lazily -- reading the member
            # once here (rather than a fresh read per array() call) means
            # walk() pays this cost once, not twice.
            arr = npz[key]
            nodes.append(_make_node(key, (lambda a=arr: a), arr.dtype, arr.shape))
        return nodes

    arr = np.load(path, mmap_mode="r", allow_pickle=True)
    name = os.path.splitext(os.path.basename(path))[0]
    if pattern and not pattern.search(name):
        return []
    return [_make_node(name, (lambda: arr), arr.dtype, arr.shape)]


def summary(path: str, nodes: list[Node]) -> dict:
    return {
        "path": path,
        "format": "numpy",
        "size_bytes": os.path.getsize(path),
        "numpy_version": np.__version__,
        "num_arrays": len(nodes),
        "total_keys": len(nodes),
    }
