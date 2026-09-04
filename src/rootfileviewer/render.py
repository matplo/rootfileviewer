"""One-shot terminal renderer using `rich`."""

from __future__ import annotations

import os

from rootfileviewer.core import Node, flatten_nodes, flatten_trees, human_size, node_facts, node_hint, tree_branch_info


def render_cli(path: str, nodes: list[Node], summary: dict, show_branches: bool = True) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree

    console = Console()

    fmt = summary.get("format")
    if fmt == "parquet":
        summary_lines = (
            f"[bold]File:[/bold] {summary['path']}\n"
            f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}\n"
            f"[bold]pyarrow:[/bold] {summary['pyarrow_version']}\n"
            f"[bold]Rows:[/bold] {summary['num_rows']:,}   "
            f"[bold]Columns:[/bold] {summary['num_columns']}   "
            f"[bold]Row groups:[/bold] {summary['num_row_groups']}"
        )
        panel_title = "Parquet file summary"
    elif fmt == "hdf5":
        summary_lines = (
            f"[bold]File:[/bold] {summary['path']}\n"
            f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}\n"
            f"[bold]h5py:[/bold] {summary['h5py_version']}   "
            f"[bold]HDF5:[/bold] {summary['hdf5_version']}\n"
            f"[bold]Keys:[/bold] {summary['total_keys']}   "
            f"[bold]Groups:[/bold] {summary['num_groups']}   "
            f"[bold]Datasets:[/bold] {summary['num_datasets']}"
        )
        panel_title = "HDF5 file summary"
    elif fmt == "numpy":
        summary_lines = (
            f"[bold]File:[/bold] {summary['path']}\n"
            f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}\n"
            f"[bold]numpy:[/bold] {summary['numpy_version']}\n"
            f"[bold]Arrays:[/bold] {summary['num_arrays']}"
        )
        panel_title = "numpy file summary"
    elif fmt == "pandas":
        summary_lines = (
            f"[bold]File:[/bold] {summary['path']}\n"
            f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}\n"
            f"[bold]pandas:[/bold] {summary['pandas_version']}\n"
            f"[bold]Rows:[/bold] {summary['num_rows']:,}   "
            f"[bold]Columns:[/bold] {summary['num_columns']}"
        )
        panel_title = "DataFrame file summary"
    else:
        summary_lines = (
            f"[bold]File:[/bold] {summary['path']}\n"
            f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}   "
            f"[bold]Compression:[/bold] {summary['compression']}\n"
            f"[bold]uproot:[/bold] {summary['uproot_version']}\n"
            f"[bold]Keys:[/bold] {summary['total_keys']}   "
            f"[bold]TTrees:[/bold] {summary['num_trees']}   "
            f"[bold]Histograms:[/bold] {summary['num_histograms']}"
        )
        panel_title = "ROOT file summary"
    console.print(Panel(summary_lines, title=panel_title, expand=False))

    root_label = f"[bold]{os.path.basename(path)}[/bold]"
    rich_tree = Tree(root_label)
    _fill_rich_tree(rich_tree, nodes)
    console.print(rich_tree)

    if show_branches:
        for tree_path, node in flatten_trees(nodes):
            rows = tree_branch_info(node.obj)
            # Inverted to a ROOT-specific check rather than enumerating every
            # non-ROOT wrapper classname, so new table-shaped backends (a
            # single synthetic Node standing in for a whole file's implicit
            # flat table -- see Node.is_tree) get "Table"/"Column" labeling
            # without another edit here.
            is_wrapper_table = node.classname not in ("TTree", "TNtuple")
            if is_wrapper_table:
                # There's only ever one (synthetic) table per file for these
                # backends, so identify it by the file itself rather than the
                # internal node name ("table"), which would read redundantly.
                label = f"Table: {os.path.basename(path)}"
            else:
                label = f"TTree: {tree_path}"
            table = Table(title=f"{label}  ({node.obj.num_entries:,} entries)")
            table.add_column("Column" if is_wrapper_table else "Branch")
            table.add_column("Type")
            for row in rows:
                table.add_row(row["name"], row["typename"])
            console.print(table)


def render_terse(path: str, nodes: list[Node], summary: dict, show_branches: bool = True) -> None:
    """Flat, tab-separated, no-color output for scripts/grep/awk.

    Every line starts with a record-type tag (summary/object/branch) so a
    consumer can select what it wants, e.g.:
        rootfileviewer file.root -t | awk -F'\\t' '$1 == "branch" && $2 == "tree1"'
        rootfileviewer file.root -t | grep '^object.*TTree'
    """
    for key, value in summary.items():
        print(f"summary\t{key}\t{value}")

    for obj_path, node in flatten_nodes(nodes):
        fields = [f"{k}={v}" for k, v in node_facts(node).items()]
        print("\t".join(["object", obj_path, node.classname, *fields]))

    if show_branches:
        for tree_path, node in flatten_trees(nodes):
            for row in tree_branch_info(node.obj):
                print(f"branch\t{tree_path}\t{row['name']}\t{row['typename']}")


def _class_style(node: Node) -> str:
    if node.is_dir:
        return "cyan"
    if node.is_tree:
        return "green"
    if node.is_hist:
        return "magenta"
    if node.is_branch:
        # First relevant for a backend whose leaves are real top-level/nested
        # tree members (HDF5 datasets, numpy arrays) rather than only ever
        # synthesized dynamically inside the TUI.
        return "yellow"
    return "white"


def _fill_rich_tree(rich_parent, nodes: list[Node]) -> None:
    for node in nodes:
        style = _class_style(node)
        hint = node_hint(node)
        label = f"[{style}]{node.name}[/{style}] [dim]({node.classname})[/dim]"
        if hint:
            label += f" [dim]- {hint}[/dim]"
        branch = rich_parent.add(label)
        if node.children:
            _fill_rich_tree(branch, node.children)
