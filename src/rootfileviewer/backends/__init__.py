"""Pluggable format-backend registry.

Each non-ROOT format (Parquet today; HDF5/awkward/pandas could follow) gets
its own module here, mapped to file extensions via a `BackendSpec`. ROOT
files stay the hardcoded default (uproot is a required dependency, so there's
nothing to detect/gate) — this registry only covers optional, extra-format
backends whose dependencies may or may not be installed.

A backend module exposes exactly two functions:
    walk(path, name_filter=None) -> list[Node]
    summary(path, nodes) -> dict
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSpec:
    name: str
    extensions: tuple[str, ...]
    module: str
    extra: str
    packages: tuple[str, ...]
    """Top-level import names this backend needs (also used as the pip
    package names suggested in the install-instructions error)."""


BACKENDS: tuple[BackendSpec, ...] = (
    BackendSpec(
        name="parquet",
        extensions=(".parquet", ".pq"),
        module="rootfileviewer.backends.parquet",
        extra="parquet",
        packages=("pyarrow",),
    ),
)


class MissingBackendError(RuntimeError):
    """Raised when a file needs a backend whose dependencies aren't installed."""

    def __init__(self, spec: BackendSpec, missing: list[str]):
        pkgs = " ".join(missing)
        super().__init__(
            f"reading .{spec.name} files needs: {pkgs}\n"
            f"Install it with either:\n"
            f"    pip install 'rootfileviewer[{spec.extra}]'\n"
            f"or:\n"
            f"    pip install {pkgs}\n"
            f"then re-run this command."
        )


def find_backend(path: str) -> BackendSpec | None:
    """Match path's extension to a registered backend. None => fall back to ROOT/uproot."""
    ext = os.path.splitext(path)[1].lower()
    for spec in BACKENDS:
        if ext in spec.extensions:
            return spec
    return None


def load_backend(spec: BackendSpec):
    """Import spec's module, or raise MissingBackendError with install instructions.

    Silent (no output) when the backend's dependencies are already installed.
    """
    missing = [pkg for pkg in spec.packages if importlib.util.find_spec(pkg) is None]
    if missing:
        raise MissingBackendError(spec, missing)
    return importlib.import_module(spec.module)
