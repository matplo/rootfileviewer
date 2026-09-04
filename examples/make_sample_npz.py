#!/usr/bin/env python3
"""Regenerates examples/sample.npz and examples/sample.npy -- the numpy
fixtures used in the README.

Same pt/eta/n_jets arrays and RNG seed as the other sample fixtures, plus:
- a ragged tracks_energy array (numpy's own object-dtype representation of
  per-event variable-length data) to demonstrate flattening ragged numpy
  arrays -- the "awkward arrays functionality" this backend was built for.
- a `hits` array (2000, 3) -- .npz has no attribute mechanism to name its
  3 columns the way HDF5 can, so this demonstrates the generic column_N
  split instead (see backends/numpy_arrays.py's NpyColumnSet).
sample.npy is just the `pt` array on its own, to show the single-array case.

Run from the repo root:
    python examples/make_sample_npz.py
"""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_NPZ = os.path.join(HERE, "sample.npz")
OUT_NPY = os.path.join(HERE, "sample.npy")


def main() -> None:
    rng = np.random.default_rng(42)
    pt = rng.gamma(shape=3.0, scale=8.0, size=2000)
    eta = rng.normal(0, 1.2, 2000)
    n_jets = rng.integers(0, 6, 2000).astype("int32")

    tracks_energy = np.empty(2000, dtype=object)
    for i, n in enumerate(n_jets):
        tracks_energy[i] = rng.gamma(shape=2.0, scale=10.0, size=int(n))

    hits = rng.normal(0, 5.0, size=(2000, 3)).astype("float32")

    np.savez(OUT_NPZ, pt=pt, eta=eta, n_jets=n_jets, tracks_energy=tracks_energy, hits=hits)
    np.save(OUT_NPY, pt)

    print(f"wrote {OUT_NPZ}")
    print(f"wrote {OUT_NPY}")


if __name__ == "__main__":
    main()
