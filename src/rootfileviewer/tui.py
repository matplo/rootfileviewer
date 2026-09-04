"""Interactive terminal UI using `textual`."""

from __future__ import annotations

import math
import os

from rootfileviewer.core import (
    Node,
    branch_histogram_data,
    branch_nodes,
    histogram_data,
    is_1d_histogram,
    node_hint,
    tree_branch_info,
)


def _log_axis_ticks(vmin: float, vmax: float, n: int = 5) -> tuple[list[float], list[str]]:
    """n evenly log-spaced tick values between vmin and vmax (both > 0),
    with reasonably compact labels -- plotext has no native log-axis
    support, so a log-scaled plot is rendered by plotting log10(x) and
    relabeling the ticks with these real (un-transformed) values."""
    log_min, log_max = math.log10(vmin), math.log10(vmax)
    if log_max == log_min:
        values = [vmin]
    else:
        values = [10 ** (log_min + i * (log_max - log_min) / (n - 1)) for i in range(n)]
    return values, [f"{v:.3g}" for v in values]


def run_tui(path: str, nodes: list[Node], summary: dict) -> None:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import DataTable, Footer, Header
    from textual.widgets import Tree as TextualTree
    from textual_plotext import PlotextPlot

    class RootFileViewerApp(App):
        CSS = """
        #top { height: 1fr; }
        #tree { width: 45%; border: solid $accent; }
        #detail { width: 55%; border: solid $accent; }
        #histplot { height: 15; border: solid $accent; }
        """
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("x", "toggle_log_x", "Log X"),
            ("y", "toggle_log_y", "Log Y"),
        ]
        TITLE = f"rootfileviewer: {os.path.basename(path)}"

        def compose(self) -> ComposeResult:
            yield Header()
            with Vertical():
                with Horizontal(id="top"):
                    yield TextualTree(os.path.basename(path), id="tree")
                    yield DataTable(id="detail")
                yield PlotextPlot(id="histplot")
            yield Footer()

        def on_mount(self) -> None:
            self._log_x = False
            self._log_y = False
            self._selected_node: Node | None = None
            tree_widget = self.query_one("#tree", TextualTree)
            tree_widget.root.expand()
            self._populate(tree_widget.root, nodes)
            table = self.query_one("#detail", DataTable)
            self._set_table(table, ("Field", "Value"), [(k, str(v)) for k, v in summary.items()])
            self.query_one("#histplot", PlotextPlot).display = False

        def action_toggle_log_x(self) -> None:
            self._log_x = not self._log_x
            self._show_node(self._selected_node)

        def action_toggle_log_y(self) -> None:
            self._log_y = not self._log_y
            self._show_node(self._selected_node)

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
                elif node.is_tree and node.obj is not None:
                    # TTree/TNtuple: expand into its branches, so a specific
                    # branch can be selected and plotted on its own.
                    for bnode in branch_nodes(node.obj):
                        child.add_leaf(f"{bnode.name} ({bnode.classname})", data=bnode)
                else:
                    # Leaf node (histogram, TList, or anything else with
                    # nothing to descend into): disable the expand arrow.
                    # Otherwise Tree's default auto_expand behavior toggles
                    # it expanded/collapsed on every Enter press with nothing
                    # to actually show, which reads as the row's formatting
                    # randomly changing each time you select it.
                    child.allow_expand = False

        def on_tree_node_selected(self, event) -> None:
            self._selected_node = event.node.data
            self._show_node(self._selected_node)

        def _show_node(self, node: Node | None) -> None:
            table = self.query_one("#detail", DataTable)
            plot_widget = self.query_one("#histplot", PlotextPlot)
            plot_widget.display = False

            if node is None:
                self._set_table(table, ("Field", "Value"), [])
                return

            if node.is_branch:
                rows = [("branch", node.name), ("type", node.classname)]
                note, error = self._plot_branch(plot_widget, node)
                if note:
                    rows.append(("sampled", note))
                if error:
                    rows.append(("plot error", error))
                self._set_table(table, ("Field", "Value"), rows)
                return

            if node.is_tree and node.obj is not None:
                rows = [(row["name"], row["typename"]) for row in tree_branch_info(node.obj)]
                self._set_table(table, ("Branch", "Type"), rows)
                return

            rows = [("name", node.name), ("classname", node.classname)]
            hint = node_hint(node)
            if hint:
                rows.append(("info", hint))

            if node.is_hist and node.obj is not None:
                if is_1d_histogram(node.classname):
                    error = self._plot_histogram(plot_widget, node)
                    if error:
                        rows.append(("plot error", error))
                else:
                    rows.append(("plot", "not supported yet (2D/3D histogram)"))

            self._set_table(table, ("Field", "Value"), rows)

        def _render_plot(
            self,
            plot_widget: "PlotextPlot",
            title: str,
            centers: list[float],
            values: list[float],
        ) -> None:
            """Bar-plot centers/values, honoring self._log_x/self._log_y.

            plotext has no native log-axis support, so a log axis is faked by
            plotting log10(x) and relabeling the ticks with the real values
            (see _log_axis_ticks). log_y treats a zero-count bin as simply
            absent (no bar) rather than log10(0); log_x requires every
            center to be positive -- raises ValueError otherwise, caught by
            the _plot_histogram/_plot_branch callers exactly like any other
            plotting error.
            """
            plt = plot_widget.plt
            plt.clear_figure()

            title_suffix = ""
            x = centers
            if self._log_x:
                if any(c <= 0 for c in centers):
                    raise ValueError("cannot use a log x-axis: bin centers are not all positive")
                title_suffix += " [log x]"
                x = [math.log10(c) for c in centers]

            y = values
            if self._log_y:
                title_suffix += " [log y]"
                y = [math.log10(v) if v > 0 else 0.0 for v in values]

            plt.title(title + title_suffix)
            plt.bar(x, y, width=1.0)

            if self._log_x:
                tick_values, tick_labels = _log_axis_ticks(min(centers), max(centers))
                plt.xticks([math.log10(v) for v in tick_values], tick_labels)
            if self._log_y:
                positive_values = [v for v in values if v > 0]
                if positive_values:
                    tick_values, tick_labels = _log_axis_ticks(min(positive_values), max(positive_values))
                    plt.yticks([math.log10(v) for v in tick_values], tick_labels)

            plot_widget.display = True
            plot_widget.refresh()

        def _plot_histogram(self, plot_widget: "PlotextPlot", node: Node) -> str | None:
            """Render node's histogram into plot_widget. Returns an error message, if any."""
            try:
                centers, values = histogram_data(node.obj)
                self._render_plot(plot_widget, node.name, centers, values)
            except Exception as exc:
                plot_widget.display = False
                return str(exc)
            return None

        def _plot_branch(self, plot_widget: "PlotextPlot", node: Node) -> tuple[str | None, str | None]:
            """Render a branch's value distribution. Returns (sampling note, error message)."""
            try:
                centers, values, note = branch_histogram_data(node.obj, log_x=self._log_x)
                self._render_plot(plot_widget, node.name, centers, values)
                return note, None
            except Exception as exc:
                plot_widget.display = False
                return None, str(exc)

    RootFileViewerApp().run()
