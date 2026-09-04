"""HDF5-file adapter.

Unlike Parquet/pandas (one flat table needing a synthetic wrapper Node),
HDF5's own Group/Dataset hierarchy already matches ROOT's own
TDirectory/TTree model closely enough to need no wrapper at all: a Group
becomes a real is_dir Node (recognized via the "HDF5Group" classname), and
each Dataset becomes a real is_branch=True leaf Node directly -- so the
whole rendering/TUI pipeline (tree population, selection, plotting) needs no
further changes beyond that one classname/is_dir extension in core.py.
"""

from __future__ import annotations

import os
import re

import h5py

from rootfileviewer.backends._common import is_structured, to_awkward
from rootfileviewer.core import Node


class HDF5Dataset:
    """Duck-types a TBranch: name, typename, num_entries, array()."""

    def __init__(self, dataset: h5py.Dataset):
        self._ds = dataset
        self.name = dataset.name.rsplit("/", 1)[-1]
        shape = "x".join(str(d) for d in dataset.shape) if dataset.shape else "scalar"
        # A variable-length (jagged) dataset's own dtype is just "object";
        # check_vlen_dtype() recovers the actual per-element type so the
        # displayed typename reads as e.g. "vlen<float64>[2000]" rather than
        # the uninformative "object[2000]".
        vlen_base = h5py.check_vlen_dtype(dataset.dtype)
        if vlen_base is not None:
            # check_vlen_dtype() returns a numpy dtype for e.g. vlen<float64>,
            # but the bare Python `str` type for a vlen string column --
            # getattr(..., "__name__", ...) turns that into "str" rather than
            # the class's own repr ("<class 'str'>").
            dtype_str = f"vlen<{getattr(vlen_base, '__name__', vlen_base)}>"
        else:
            dtype_str = str(dataset.dtype)
        self.typename = f"{dtype_str}[{shape}]"
        self.num_entries = dataset.shape[0] if dataset.ndim >= 1 else 1

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for dataset '{self.name}'")
        if is_structured(self._ds.dtype):
            raise ValueError(
                f"dataset '{self.name}' has a compound dtype {self._ds.dtype} and is not supported"
            )

        n = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        sliced = self._ds[:n] if self._ds.ndim >= 1 else self._ds[()]
        # h5py slices lazily from disk. Flattening extra dims is a no-op for
        # a variable-length (jagged) dataset, which reads back as a 1-D
        # object array of numpy sub-arrays -- exactly the shape a jagged
        # ROOT branch or a Parquet list<double> column takes.
        import numpy as np

        flat = np.asarray(sliced).reshape(-1)

        if library == "ak":
            return to_awkward(flat)
        return flat


def _count(nodes: list[Node]) -> tuple[int, int]:
    groups = datasets = 0
    for node in nodes:
        if node.is_dir:
            groups += 1
            g, d = _count(node.children)
            groups += g
            datasets += d
        else:
            datasets += 1
    return groups, datasets


def walk(path: str, depth: int | None = None, name_filter: str | None = None) -> list[Node]:
    pattern = re.compile(name_filter) if name_filter else None

    def _walk_group(group, depth: int | None) -> list[Node]:
        nodes = []
        for key, obj in group.items():
            if pattern and not pattern.search(key):
                continue
            if isinstance(obj, h5py.Group):
                node = Node(name=key, classname="HDF5Group", obj=obj)
                if depth is None or depth > 0:
                    next_depth = None if depth is None else depth - 1
                    node.children = _walk_group(obj, next_depth)
                nodes.append(node)
            elif isinstance(obj, h5py.Dataset):
                wrapper = HDF5Dataset(obj)
                nodes.append(Node(name=key, classname=wrapper.typename, obj=wrapper, is_branch=True))
        return nodes

    # Kept open for the lifetime of the process (mirrors uproot.open being
    # held open for the whole TUI session elsewhere) -- there's no
    # context-manager plumbing in the backend registry's walk()/summary()
    # contract to close it explicitly, and this is a short-lived CLI tool.
    f = h5py.File(path, "r")
    return _walk_group(f, depth)


def summary(path: str, nodes: list[Node]) -> dict:
    groups, datasets = _count(nodes)
    return {
        "path": path,
        "format": "hdf5",
        "size_bytes": os.path.getsize(path),
        "h5py_version": h5py.__version__,
        "hdf5_version": h5py.version.hdf5_version,
        "num_groups": groups,
        "num_datasets": datasets,
        "total_keys": groups + datasets,
    }
