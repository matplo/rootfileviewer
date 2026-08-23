"""Command-line entry point for rootfileviewer."""

from __future__ import annotations

import argparse
import os
import sys

import uproot

from rootfileviewer.core import file_summary, walk_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a ROOT file's contents in the terminal (via uproot).",
    )
    parser.add_argument("rootfile", help="path to the .root file")
    parser.add_argument("--tui", action="store_true", help="launch interactive textual TUI instead of one-shot print")
    parser.add_argument(
        "--terse", "-t",
        action="store_true",
        help="plain, tab-separated output with no borders/colors, for scripts/grep/awk",
    )
    parser.add_argument("--depth", type=int, default=None, help="limit directory recursion depth")
    parser.add_argument("--filter", dest="name_filter", default=None, help="regex to filter key names")
    parser.add_argument("--no-branches", action="store_true", help="skip per-TTree branch tables in CLI mode")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    args = parser.parse_args(argv)

    if args.tui and args.terse:
        print("error: --tui and --terse/-t are mutually exclusive", file=sys.stderr)
        return 1

    if not os.path.isfile(args.rootfile):
        print(f"error: no such file: {args.rootfile}", file=sys.stderr)
        return 1

    try:
        with uproot.open(args.rootfile) as f:
            nodes = walk_directory(f, depth=args.depth, name_filter=args.name_filter)
            summary = file_summary(f, args.rootfile, nodes)

            if args.tui:
                from rootfileviewer.tui import run_tui

                run_tui(args.rootfile, nodes, summary)
            elif args.terse:
                from rootfileviewer.render import render_terse

                render_terse(args.rootfile, nodes, summary, show_branches=not args.no_branches)
            else:
                from rootfileviewer.render import render_cli

                render_cli(args.rootfile, nodes, summary, show_branches=not args.no_branches)
    except Exception as exc:
        print(f"error: failed to read {args.rootfile}: {exc}", file=sys.stderr)
        return 1

    return 0


def _version() -> str:
    from rootfileviewer import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
