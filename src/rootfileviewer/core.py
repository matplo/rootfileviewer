"""Shared core: uproot-only data extraction, no rendering dependencies."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import numpy as np
import uproot

_HIST_CLASS_PREFIXES = ("TH1", "TH2", "TH3", "TProfile")

#: Default cap on how many entries to read when plotting a branch's value
#: distribution, so selecting a branch on a huge tree stays responsive.
DEFAULT_BRANCH_PLOT_MAX_ENTRIES = 200_000
DEFAULT_BRANCH_PLOT_BINS = 30


@dataclass
class Node:
    name: str
    classname: str
    obj: object
    children: list["Node"] = field(default_factory=list)
    is_branch: bool = False
    """True if this node is a synthetic TBranch child of a TTree/TNtuple node
    (as opposed to a real file object from walk_directory)."""

    @property
    def is_dir(self) -> bool:
        # HDF5Group is a real (not synthetic) classname for an h5py Group --
        # see backends/hdf5.py -- reusing this same directory-recursion
        # machinery, unlike ParquetTable/DataFrameTable's single-node wrapper.
        return self.classname.startswith("TDirectory") or self.classname == "HDF5Group"

    @property
    def is_tree(self) -> bool:
        # ParquetTable/DataFrameTable are synthetic classnames (see
        # backends/parquet.py, backends/pandas_tables.py) standing in for a
        # whole file's implicit flat table, so they can reuse this same
        # branch-expansion/plotting machinery.
        return self.classname in ("TTree", "TNtuple", "ParquetTable", "DataFrameTable")

    @property
    def is_hist(self) -> bool:
        return self.classname.startswith(_HIST_CLASS_PREFIXES)


def walk_directory(directory, depth: int | None = None, name_filter: str | None = None) -> list[Node]:
    """Recursively list keys under a TDirectory/file into a Node tree."""
    pattern = re.compile(name_filter) if name_filter else None
    nodes: list[Node] = []
    for key, classname in directory.classnames(recursive=False).items():
        short_name = key.split(";")[0]
        if pattern and not pattern.search(short_name):
            continue
        try:
            obj = directory[key]
        except Exception:
            obj = None
        node = Node(name=short_name, classname=classname, obj=obj)
        if classname.startswith("TDirectory") and obj is not None:
            if depth is None or depth > 0:
                next_depth = None if depth is None else depth - 1
                node.children = walk_directory(obj, depth=next_depth, name_filter=name_filter)
        nodes.append(node)
    return nodes


def tree_branch_info(ttree) -> list[dict]:
    """Per-branch details for a TTree: name, type, entry count."""
    n_entries = ttree.num_entries
    rows = []
    for branch in ttree.branches:
        try:
            typename = branch.typename
        except Exception:
            typename = "?"
        rows.append({"name": branch.name, "typename": typename, "num_entries": n_entries})
    return rows


def _count_classes(nodes: list[Node]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        if node.is_dir:
            sub = _count_classes(node.children)
            for k, v in sub.items():
                counts[k] = counts.get(k, 0) + v
            continue
        key = "TTree" if node.is_tree else "Histogram" if node.is_hist else node.classname
        counts[key] = counts.get(key, 0) + 1
    return counts


def file_summary(uproot_file, path: str, nodes: list[Node]) -> dict:
    counts = _count_classes(nodes)
    total_keys = sum(counts.values())
    return {
        "path": path,
        "format": "root",
        "size_bytes": os.path.getsize(path),
        "uproot_version": uproot.__version__,
        "compression": str(uproot_file.file.compression),
        "num_trees": counts.get("TTree", 0),
        "num_histograms": counts.get("Histogram", 0),
        "total_keys": total_keys,
    }


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def node_facts(node: Node) -> dict[str, int]:
    """Raw numeric facts about a node (entries/branches/bins), for machine consumption.

    See `node_hint` for the human-readable, formatted equivalent.
    """
    if node.is_tree and node.obj is not None:
        try:
            return {"entries": node.obj.num_entries, "branches": len(node.obj.branches)}
        except Exception:
            return {}
    if node.is_hist and node.obj is not None:
        try:
            return {"bins": len(node.obj.axis())}
        except Exception:
            return {}
    if node.is_branch and node.obj is not None:
        # Dead code for ROOT/Parquet: their branch/column children are only
        # ever synthesized dynamically inside the TUI (branch_nodes()), never
        # part of the static walk() tree that flatten_nodes()/node_facts()
        # here operate on. First live for a backend whose leaves genuinely
        # are top-level/nested tree members -- HDF5 datasets, numpy arrays.
        try:
            return {"entries": node.obj.num_entries}
        except Exception:
            return {}
    return {}


def node_hint(node: Node) -> str:
    """Short, human-readable annotation shown next to a node's name."""
    facts = node_facts(node)
    if node.is_tree:
        if "entries" not in facts:
            return ""
        # Inverted to a ROOT-specific allowlist rather than an ever-growing
        # list of non-ROOT classnames, so new table-shaped backends don't
        # need another edit here.
        unit = "branches" if node.classname in ("TTree", "TNtuple") else "columns"
        return f"{facts['entries']:,} entries, {facts['branches']} {unit}"
    if node.is_hist:
        if "bins" not in facts:
            return ""
        return f"{facts['bins']} bins"
    return ""


def is_1d_histogram(classname: str) -> bool:
    """Whether a histogram classname is 1D and thus bar-plottable (TH1*, TProfile)."""
    return classname.startswith(("TH1", "TProfile"))


def histogram_data(hist_obj) -> tuple[list[float], list[float]]:
    """Bin centers and values for a 1D histogram-like object, for bar plotting."""
    values, edges = hist_obj.to_numpy()
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(values))]
    return centers, [float(v) for v in values]


def branch_nodes(tree_obj) -> list[Node]:
    """Synthetic leaf Nodes for a TTree/TNtuple's branches, for TUI tree display."""
    nodes = []
    for branch in tree_obj.branches:
        try:
            typename = branch.typename
        except Exception:
            typename = "?"
        nodes.append(Node(name=branch.name, classname=typename, obj=branch, is_branch=True))
    return nodes


def branch_histogram_data(
    branch,
    max_entries: int = DEFAULT_BRANCH_PLOT_MAX_ENTRIES,
    bins: int = DEFAULT_BRANCH_PLOT_BINS,
) -> tuple[list[float], list[float], str]:
    """Bin centers/values (via numpy.histogram) for a TBranch's values, plus a note
    describing how many entries/values were actually used.

    Vector/jagged branches are flattened across all their elements first.
    Raises ValueError if the branch has no numeric values to histogram.
    """
    total = branch.num_entries
    entry_stop = min(total, max_entries)
    arr = branch.array(library="np", entry_stop=entry_stop)
    if arr.dtype.kind not in "iuf":
        import awkward as ak

        arr = ak.flatten(branch.array(library="ak", entry_stop=entry_stop), axis=None).to_numpy()
        if arr.dtype.kind not in "iuf":
            raise ValueError(f"branch '{branch.name}' is not numeric (dtype {arr.dtype})")

    if len(arr) == 0:
        raise ValueError(f"branch '{branch.name}' has no values to plot")

    flattened_len = len(arr)  # before any non-finite filtering below, for the "(flattened)" note

    # np.histogram() computes bin edges in the *input array's own dtype* --
    # for a narrow type like float16 that's a real problem even with no
    # actual inf/nan in the data: two finite-but-large float16 edges can
    # overflow float16's ~65504 max when core.py itself adds them together
    # below to get bin centers, producing inf and crashing plotext's tick
    # rendering downstream. Upcasting first keeps that arithmetic in
    # float64, where it has ample headroom.
    arr = arr.astype(np.float64, copy=False)

    # A column can also contain genuine inf/nan values (e.g. from an
    # overflowed float16 source, or an actual NaN sentinel) -- histogramming
    # those directly makes np.histogram's autodetected range non-finite.
    finite_mask = np.isfinite(arr)
    n_nonfinite = flattened_len - int(finite_mask.sum())
    if n_nonfinite:
        arr = arr[finite_mask]
    if len(arr) == 0:
        raise ValueError(f"branch '{branch.name}' has only non-finite (inf/nan) values to plot")

    values, edges = np.histogram(arr, bins=bins)
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(values))]

    note = f"{entry_stop:,}/{total:,} entries" if entry_stop < total else f"{total:,} entries"
    if flattened_len != entry_stop:
        note += f", {flattened_len:,} values (flattened)"
    if n_nonfinite:
        note += f", {n_nonfinite:,} non-finite excluded"
    return centers, [float(v) for v in values], note


def flatten_trees(nodes: list[Node], prefix: str = "") -> list[tuple[str, Node]]:
    result = []
    for node in nodes:
        path = f"{prefix}/{node.name}" if prefix else node.name
        if node.is_tree and node.obj is not None:
            result.append((path, node))
        elif node.is_dir:
            result.extend(flatten_trees(node.children, path))
    return result


def flatten_nodes(nodes: list[Node], prefix: str = "") -> list[tuple[str, Node]]:
    """Flatten the tree into (full_path, node) pairs, depth-first, directories included."""
    result = []
    for node in nodes:
        path = f"{prefix}/{node.name}" if prefix else node.name
        result.append((path, node))
        if node.is_dir and node.children:
            result.extend(flatten_nodes(node.children, path))
    return result
