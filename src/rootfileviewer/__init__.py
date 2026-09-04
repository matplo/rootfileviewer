"""rootfileviewer — inspect ROOT files from the terminal via uproot.

Renamed to datafileviewer (https://github.com/matplo/datafileviewer,
https://pypi.org/project/datafileviewer/) now that it also reads Parquet,
HDF5, numpy, and pandas-readable files. This package is frozen as of this
release."""

from rootfileviewer.core import Node, file_summary, tree_branch_info, walk_directory

__version__ = "0.13.1"

__all__ = ["Node", "file_summary", "tree_branch_info", "walk_directory", "__version__"]
