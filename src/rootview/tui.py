"""Interactive terminal UI using `textual`."""

from __future__ import annotations

import os

from rootview.core import Node, node_hint, tree_branch_info


def run_tui(path: str, nodes: list[Node], summary: dict) -> None:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal
    from textual.widgets import DataTable, Footer, Header
    from textual.widgets import Tree as TextualTree

    class RootViewApp(App):
        CSS = """
        Horizontal { height: 1fr; }
        #tree { width: 45%; border: solid $accent; }
        #detail { width: 55%; border: solid $accent; }
        """
        BINDINGS = [("q", "quit", "Quit")]
        TITLE = f"rootview: {os.path.basename(path)}"

        def compose(self) -> ComposeResult:
            yield Header()
            with Horizontal():
                yield TextualTree(os.path.basename(path), id="tree")
                yield DataTable(id="detail")
            yield Footer()

        def on_mount(self) -> None:
            tree_widget = self.query_one("#tree", TextualTree)
            tree_widget.root.expand()
            self._populate(tree_widget.root, nodes)
            table = self.query_one("#detail", DataTable)
            table.add_columns("Field", "Value")
            for k, v in summary.items():
                table.add_row(k, str(v))

        def _populate(self, parent, node_list: list[Node]) -> None:
            for node in node_list:
                hint = node_hint(node)
                label = f"{node.name} ({node.classname})"
                if hint:
                    label += f" - {hint}"
                child = parent.add(label, data=node)
                if node.children:
                    self._populate(child, node.children)
                elif node.is_dir:
                    child.allow_expand = False

        def on_tree_node_selected(self, event) -> None:
            node: Node | None = event.node.data
            table = self.query_one("#detail", DataTable)
            table.clear(columns=True)
            if node is None:
                return
            if node.is_tree and node.obj is not None:
                table.add_columns("Branch", "Type")
                for row in tree_branch_info(node.obj):
                    table.add_row(row["name"], row["typename"])
            else:
                table.add_columns("Field", "Value")
                table.add_row("name", node.name)
                table.add_row("classname", node.classname)
                hint = node_hint(node)
                if hint:
                    table.add_row("info", hint)

    RootViewApp().run()
