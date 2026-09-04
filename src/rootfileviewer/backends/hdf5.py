"""HDF5-file adapter.

Unlike Parquet/pandas (one flat table needing a synthetic wrapper Node),
HDF5's own Group/Dataset hierarchy already matches ROOT's own
TDirectory/TTree model closely enough to need no wrapper at all: a Group
becomes a real is_dir Node (recognized via the "HDF5Group" classname), and
each Dataset becomes a real is_branch=True leaf Node directly -- so the
whole rendering/TUI pipeline (tree population, selection, plotting) needs no
further changes beyond that one classname/is_dir extension in core.py.

The one exception: a dataset whose last axis has *named* features (via an
attribute -- there's no single universal HDF5 convention for this, so a
short, conservative list of common attribute names/locations is tried, see
_find_feature_names()) behaves like a small table instead: it becomes an
is_tree=True "HDF5FeatureSet" Node whose children are the individual named
features, reusing the exact same branch-expansion/plotting machinery a TTree
or ParquetTable already gets. Without this, e.g. a (9764, 7) dataset holding
7 physically distinct quantities (energy, angles, ...) would only ever be
selectable as one blob, flattening all 7 into a single meaningless combined
histogram.
"""

from __future__ import annotations

import os
import re

import h5py
import numpy as np

from rootfileviewer.backends._common import is_structured, to_awkward
from rootfileviewer.core import Node

# Attribute names tried, in order, to find per-feature names for a dataset's
# last axis. Not a formal HDF5 standard -- just the common spellings seen in
# the wild -- so this is deliberately conservative: a candidate is only
# accepted if its length matches the dataset's last-axis size exactly.
_FEATURE_ATTR_NAMES = ("features", "feature_names", "columns", "column_names", "labels")
_FEATURE_ATTR_SUFFIXES = ("_features", "_labels", "_columns")


def _find_feature_names(dataset: h5py.Dataset) -> list[str] | None:
    """Best-effort: names for each entry along dataset's last axis, from
    either an attribute on the dataset itself, or a `<name>_features`-style
    one on its immediate parent group (the convention used by at least one
    real-world file this was built against, which stores them at the file
    root rather than per-dataset). None if nothing matches."""
    if dataset.ndim < 2:
        return None
    last_axis_len = dataset.shape[-1]

    for key in _FEATURE_ATTR_NAMES:
        if key in dataset.attrs:
            names = list(dataset.attrs[key])
            if len(names) == last_axis_len:
                return [str(n) for n in names]

    basename = dataset.name.rsplit("/", 1)[-1]
    parent_attrs = dataset.parent.attrs
    for suffix in _FEATURE_ATTR_SUFFIXES:
        key = f"{basename}{suffix}"
        if key in parent_attrs:
            names = list(parent_attrs[key])
            if len(names) == last_axis_len:
                return [str(n) for n in names]

    return None


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
        flat = np.asarray(sliced).reshape(-1)

        if library == "ak":
            return to_awkward(flat)
        return flat


class HDF5FeatureColumn:
    """Duck-types a TBranch: one named feature sliced out of a dataset's
    last axis (e.g. jet[:, 3] for a feature named "eta_jet")."""

    def __init__(self, dataset: h5py.Dataset, index: int, name: str):
        self._ds = dataset
        self._index = index
        self.name = name
        self.typename = str(dataset.dtype)
        self.num_entries = dataset.shape[0]

    def array(self, library: str = "np", entry_stop: int | None = None):
        if library not in ("np", "ak"):
            raise ValueError(f"unsupported library {library!r} for column '{self.name}'")
        if is_structured(self._ds.dtype):
            raise ValueError(
                f"column '{self.name}' has a compound dtype {self._ds.dtype} and is not supported"
            )

        n = self.num_entries if entry_stop is None else min(entry_stop, self.num_entries)
        # Ellipsis covers any middle axes (e.g. particle's (events, particles,
        # features) shape); the trailing integer index picks this one named
        # feature out of the last axis and drops it, same as plain numpy.
        sliced = self._ds[:n, ..., self._index]
        flat = np.asarray(sliced).reshape(-1)

        if library == "ak":
            return to_awkward(flat)
        return flat


class HDF5FeatureSet:
    """Duck-types a TTree: a dataset whose last axis has named features (see
    _find_feature_names), so it behaves like a small table of columns
    instead of one big flatten-everything blob."""

    def __init__(self, dataset: h5py.Dataset, feature_names: list[str]):
        self._ds = dataset
        self._feature_names = feature_names
        self.num_entries = dataset.shape[0]

    @property
    def branches(self) -> list[HDF5FeatureColumn]:
        return [HDF5FeatureColumn(self._ds, i, name) for i, name in enumerate(self._feature_names)]


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
                feature_names = _find_feature_names(obj)
                if feature_names:
                    feature_set = HDF5FeatureSet(obj, feature_names)
                    nodes.append(Node(name=key, classname="HDF5FeatureSet", obj=feature_set))
                else:
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
