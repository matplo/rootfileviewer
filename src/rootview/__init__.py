"""rootview — inspect ROOT files from the terminal via uproot."""

from rootview.core import Node, file_summary, tree_branch_info, walk_directory

__version__ = "0.3.0"

__all__ = ["Node", "file_summary", "tree_branch_info", "walk_directory", "__version__"]
