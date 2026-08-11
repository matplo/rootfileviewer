"""One-shot terminal renderer using `rich`."""

from __future__ import annotations

import os

from rootview.core import Node, flatten_trees, human_size, node_hint, tree_branch_info


def render_cli(path: str, nodes: list[Node], summary: dict, show_branches: bool = True) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree

    console = Console()

    summary_lines = (
        f"[bold]File:[/bold] {summary['path']}\n"
        f"[bold]Size:[/bold] {human_size(summary['size_bytes'])}   "
        f"[bold]Compression:[/bold] {summary['compression']}\n"
        f"[bold]uproot:[/bold] {summary['uproot_version']}\n"
        f"[bold]Keys:[/bold] {summary['total_keys']}   "
        f"[bold]TTrees:[/bold] {summary['num_trees']}   "
        f"[bold]Histograms:[/bold] {summary['num_histograms']}"
    )
    console.print(Panel(summary_lines, title="ROOT file summary", expand=False))

    root_label = f"[bold]{os.path.basename(path)}[/bold]"
    rich_tree = Tree(root_label)
    _fill_rich_tree(rich_tree, nodes)
    console.print(rich_tree)

    if show_branches:
        for tree_path, node in flatten_trees(nodes):
            rows = tree_branch_info(node.obj)
            table = Table(title=f"TTree: {tree_path}  ({node.obj.num_entries:,} entries)")
            table.add_column("Branch")
            table.add_column("Type")
            for row in rows:
                table.add_row(row["name"], row["typename"])
            console.print(table)


def _class_style(node: Node) -> str:
    if node.is_dir:
        return "cyan"
    if node.is_tree:
        return "green"
    if node.is_hist:
        return "magenta"
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
