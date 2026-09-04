"""Command-line entry point for rootfileviewer."""

from __future__ import annotations

import argparse
import os
import sys

import uproot

from rootfileviewer.backends import MissingBackendError, find_backend, load_backend
from rootfileviewer.core import file_summary, walk_directory


def _dispatch(args, path: str, nodes, summary: dict) -> None:
    """Run the requested output mode (TUI/terse/one-shot) against nodes/summary."""
    if args.tui:
        from rootfileviewer.tui import run_tui

        run_tui(path, nodes, summary)
    elif args.terse:
        from rootfileviewer.render import render_terse

        render_terse(path, nodes, summary, show_branches=not args.no_branches)
    else:
        from rootfileviewer.render import render_cli

        render_cli(path, nodes, summary, show_branches=not args.no_branches)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a ROOT or Parquet file's contents in the terminal (via uproot/pyarrow).",
    )
    parser.add_argument("rootfile", help="path to the .root or .parquet file")
    parser.add_argument("--tui", action="store_true", help="launch interactive textual TUI instead of one-shot print")
    parser.add_argument(
        "--terse", "-t",
        action="store_true",
        help="plain, tab-separated output with no borders/colors, for scripts/grep/awk",
    )
    parser.add_argument(
        "--depth", type=int, default=None,
        help="limit directory recursion depth (ROOT, HDF5; no-op for flat formats)",
    )
    parser.add_argument(
        "--filter", dest="name_filter", default=None,
        help="regex to filter key/group/dataset names (ROOT, HDF5) or column names (Parquet, pandas)",
    )
    parser.add_argument(
        "--no-branches", action="store_true",
        help="skip per-TTree/per-table branch or column tables in CLI mode (no-op for HDF5/numpy)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    args = parser.parse_args(argv)

    if args.tui and args.terse:
        print("error: --tui and --terse/-t are mutually exclusive", file=sys.stderr)
        return 1

    if not os.path.isfile(args.rootfile):
        print(f"error: no such file: {args.rootfile}", file=sys.stderr)
        return 1

    spec = find_backend(args.rootfile)
    try:
        if spec is not None:
            backend = load_backend(spec)
            nodes = backend.walk(args.rootfile, depth=args.depth, name_filter=args.name_filter)
            summary = backend.summary(args.rootfile, nodes)
            _dispatch(args, args.rootfile, nodes, summary)
        else:
            with uproot.open(args.rootfile) as f:
                nodes = walk_directory(f, depth=args.depth, name_filter=args.name_filter)
                summary = file_summary(f, args.rootfile, nodes)
                _dispatch(args, args.rootfile, nodes, summary)
    except MissingBackendError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: failed to read {args.rootfile}: {exc}", file=sys.stderr)
        return 1

    return 0


def main_tui(argv: list[str] | None = None) -> int:
    """Entry point for `rfvt`: same as `rootfileviewer --tui`."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--tui" not in args:
        args = ["--tui", *args]
    return main(args)


def _version() -> str:
    from rootfileviewer import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
