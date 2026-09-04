"""Shared helpers for backends that don't have a pyarrow-native shortcut
(Parquet's backend converts via `ak.from_arrow()` instead and doesn't need
this module)."""

from __future__ import annotations

MAX_SPLIT_COLUMNS = 20
"""A multi-dim array's last axis, if no wider than this, is treated as a
handful of distinct quantities and split into individually plottable
columns instead of being flattened together (see backends/numpy_arrays.py's
NpyColumnSet and backends/hdf5.py's generic-fallback use of HDF5FeatureSet).
Wider than this (e.g. a 128-dim embedding) is presumed to be genuinely
homogeneous data where flattening is the right default -- there's no way to
know for certain without real names, so this is a judgment call, not a
detection."""


def to_awkward(arr):
    """numpy array -> awkward Array via a Python-list round trip.

    Robust across dtypes: a plain numeric/string/bool array converts
    directly; an object-dtype array of ragged numpy sub-arrays (numpy's own
    natural representation of jagged data, e.g. read from an HDF5
    variable-length dataset or a pandas cell holding a list) round-trips
    through `.tolist()` without flattening those sub-arrays away -- verified
    that `ak.Array` then reconstructs a proper ragged type from them, the
    same way it does for a plain Python list of strings.

    Only ever called on the non-numeric-dtype fallback path (see
    core.branch_histogram_data), so the extra `.tolist()` cost never hits
    large numeric data.
    """
    import awkward as ak

    return ak.Array(arr.tolist())


def is_structured(arr_or_dtype) -> bool:
    """True for a numpy structured/compound dtype -- the numpy analogue of a
    Parquet struct column. Rejected the same way (see backends/parquet.py's
    _rejects_nesting): flattening one would mix unrelated fields into a
    single meaningless distribution rather than raising.
    """
    dtype = getattr(arr_or_dtype, "dtype", arr_or_dtype)
    return dtype.names is not None
