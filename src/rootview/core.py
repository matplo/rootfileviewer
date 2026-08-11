"""Shared core: uproot-only data extraction, no rendering dependencies."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import uproot

_HIST_CLASS_PREFIXES = ("TH1", "TH2", "TH3", "TProfile")


@dataclass
class Node:
    name: str
    classname: str
    obj: object
    children: list["Node"] = field(default_factory=list)

    @property
    def is_dir(self) -> bool:
        return self.classname.startswith("TDirectory")

    @property
    def is_tree(self) -> bool:
        return self.classname in ("TTree", "TNtuple")

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


def node_hint(node: Node) -> str:
    """Short type-specific annotation shown next to a node's name."""
    if node.is_tree and node.obj is not None:
        try:
            return f"{node.obj.num_entries:,} entries, {len(node.obj.branches)} branches"
        except Exception:
            return ""
    if node.is_hist and node.obj is not None:
        try:
            return f"{len(node.obj.axis())} bins"
        except Exception:
            return ""
    return ""


def is_1d_histogram(classname: str) -> bool:
    """Whether a histogram classname is 1D and thus bar-plottable (TH1*, TProfile)."""
    return classname.startswith(("TH1", "TProfile"))


def histogram_data(hist_obj) -> tuple[list[float], list[float]]:
    """Bin centers and values for a 1D histogram-like object, for bar plotting."""
    values, edges = hist_obj.to_numpy()
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(values))]
    return centers, [float(v) for v in values]


def flatten_trees(nodes: list[Node], prefix: str = "") -> list[tuple[str, Node]]:
    result = []
    for node in nodes:
        path = f"{prefix}/{node.name}" if prefix else node.name
        if node.is_tree and node.obj is not None:
            result.append((path, node))
        elif node.is_dir:
            result.extend(flatten_trees(node.children, path))
    return result
