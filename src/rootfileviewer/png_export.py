"""Static PNG export of a plotted histogram, via matplotlib (optional
dependency -- lazily imported here, only when actually called, so importing
this module itself never requires matplotlib to be installed)."""

from __future__ import annotations


def _bin_widths(centers: list[float]) -> list[float]:
    """Approximate each bar's width from its neighbors' midpoints -- works
    for both evenly-spaced (linear) and geometrically-spaced (log_x) centers,
    without needing the original bin edges (not part of the existing
    core.py return contract)."""
    if len(centers) < 2:
        return [1.0] * len(centers)
    edges = [(centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1)]
    first_edge = centers[0] - (edges[0] - centers[0])
    last_edge = centers[-1] + (centers[-1] - edges[-1])
    all_edges = [first_edge, *edges, last_edge]
    return [all_edges[i + 1] - all_edges[i] for i in range(len(centers))]


def export_png(
    output_path: str,
    title: str,
    subtitle: str,
    centers: list[float],
    values: list[float],
    log_x: bool = False,
    log_y: bool = False,
) -> None:
    """Render centers/values as a static bar-chart PNG. Raises ImportError
    if matplotlib isn't installed -- the caller (tui.py) is responsible for
    turning that into a friendly install-instructions message, the same
    pattern as backends/__init__.py's MissingBackendError elsewhere.

    Uses Figure/FigureCanvasAgg directly rather than pyplot, so there's no
    global backend/GUI state to worry about running inside a TUI process.
    Unlike plotext's fake log axis (core.py/tui.py's own centers are
    plotted at log10(x) with relabeled ticks, since plotext has no native
    log-scale support), matplotlib gets a real ax.set_xscale("log")/
    set_yscale("log") -- no transform or relabeling needed here.
    """
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(8, 5), dpi=120)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    widths = [w * 0.9 for w in _bin_widths(centers)]
    ax.bar(centers, values, width=widths, align="center")
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")

    ax.set_title(title)
    ax.set_xlabel("value" + (" (log)" if log_x else ""))
    ax.set_ylabel("count" + (" (log)" if log_y else ""))
    fig.text(0.5, 0.01, subtitle, ha="center", va="bottom", fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output_path)
