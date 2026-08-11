"""Interactive terminal UI using `textual`."""

from __future__ import annotations

import os

from rootview.core import Node, histogram_data, is_1d_histogram, node_hint, tree_branch_info


def run_tui(path: str, nodes: list[Node], summary: dict) -> None:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import DataTable, Footer, Header
    from textual.widgets import Tree as TextualTree
    from textual_plotext import PlotextPlot

    class RootViewApp(App):
        CSS = """
        #top { height: 1fr; }
        #tree { width: 45%; border: solid $accent; }
        #detail { width: 55%; border: solid $accent; }
        #histplot { height: 15; border: solid $accent; }
        """
        BINDINGS = [("q", "quit", "Quit")]
        TITLE = f"rootview: {os.path.basename(path)}"

        def compose(self) -> ComposeResult:
            yield Header()
            with Vertical():
                with Horizontal(id="top"):
                    yield TextualTree(os.path.basename(path), id="tree")
                    yield DataTable(id="detail")
                yield PlotextPlot(id="histplot")
            yield Footer()

        def on_mount(self) -> None:
            tree_widget = self.query_one("#tree", TextualTree)
            tree_widget.root.expand()
            self._populate(tree_widget.root, nodes)
            table = self.query_one("#detail", DataTable)
            self._set_table(table, ("Field", "Value"), [(k, str(v)) for k, v in summary.items()])
            self.query_one("#histplot", PlotextPlot).display = False

        @staticmethod
        def _set_table(table: DataTable, headers: tuple[str, str], rows: list[tuple[str, str]]) -> None:
            """Replace a DataTable's columns/rows with explicit content-based widths.

            `add_columns()` leaves column width to DataTable's lazy auto-sizing,
            which can render stale/inconsistent widths across rows when the
            table's columns are repeatedly cleared and rebuilt (e.g. selecting
            different TTrees in quick succession). Computing widths ourselves
            avoids that entirely.
            """
            table.clear(columns=True)
            max_width = 60
            widths = [
                min(max(len(headers[i]), *(len(str(row[i])) for row in rows)) + 2, max_width) if rows else len(headers[i]) + 2
                for i in range(2)
            ]
            for header, width in zip(headers, widths):
                table.add_column(header, width=width)
            for row in rows:
                table.add_row(*row)

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
            plot_widget = self.query_one("#histplot", PlotextPlot)
            plot_widget.display = False

            if node is None:
                self._set_table(table, ("Field", "Value"), [])
                return

            if node.is_tree and node.obj is not None:
                rows = [(row["name"], row["typename"]) for row in tree_branch_info(node.obj)]
                self._set_table(table, ("Branch", "Type"), rows)
                return

            rows = [("name", node.name), ("classname", node.classname)]
            hint = node_hint(node)
            if hint:
                rows.append(("info", hint))
            if node.is_hist and node.obj is not None and not is_1d_histogram(node.classname):
                rows.append(("plot", "not supported yet (2D/3D histogram)"))
            self._set_table(table, ("Field", "Value"), rows)

            if node.is_hist and node.obj is not None and is_1d_histogram(node.classname):
                self._plot_histogram(plot_widget, node)

        def _plot_histogram(self, plot_widget: "PlotextPlot", node: Node) -> None:
            try:
                centers, values = histogram_data(node.obj)
            except Exception as exc:
                table = self.query_one("#detail", DataTable)
                table.add_row("plot error", str(exc))
                return
            plt = plot_widget.plt
            plt.clear_figure()
            plt.title(node.name)
            plt.bar(centers, values, width=1.0)
            plot_widget.display = True
            plot_widget.refresh()

    RootViewApp().run()
