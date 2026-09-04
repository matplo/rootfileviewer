#!/usr/bin/env python3
"""Regenerates examples/sample.h5 -- the HDF5 fixture used in the README.

Same pt/eta/n_jets columns and RNG seed as make_sample.py's `events` TTree,
plus a jagged (variable-length) tracks_energy dataset and a subgroup, to
mirror sample.root's shape (a tree, a jagged-analogue, a subdirectory) as
closely as HDF5's own model allows. Also includes a `jet` dataset with a
`jet_features` attribute naming its columns, demonstrating the named-feature
column-splitting behavior (there's no single universal HDF5 convention for
this, but a `<dataset-name>_features` attribute is one used in the wild).
Run from the repo root:
    python examples/make_sample_hdf5.py
"""

import os

import h5py
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sample.h5")


def main() -> None:
    rng = np.random.default_rng(42)
    pt = rng.gamma(shape=3.0, scale=8.0, size=2000)
    eta = rng.normal(0, 1.2, 2000)
    n_jets = rng.integers(0, 6, 2000).astype("int32")

    with h5py.File(OUT, "w") as f:
        f.create_dataset("pt", data=pt)
        f.create_dataset("eta", data=eta)
        f.create_dataset("n_jets", data=n_jets)

        # A per-event list of track energies -- HDF5's jagged/variable-length
        # analogue of a jagged ROOT branch or a Parquet list<double> column.
        vlen_dt = h5py.vlen_dtype(np.dtype("float64"))
        tracks = f.create_dataset("tracks_energy", (2000,), dtype=vlen_dt)
        for i, n in enumerate(n_jets):
            tracks[i] = rng.gamma(shape=2.0, scale=10.0, size=int(n))

        aux = f.create_group("aux")
        aux.create_dataset("run_number", data=np.full(5, 367123, dtype="int32"))

        # A (events, features) dataset with named columns via an attribute --
        # gets split into individually selectable/plottable columns instead
        # of one flattened blob (see backends/hdf5.py's _find_feature_names).
        jet_pt = rng.gamma(shape=3.0, scale=5.0, size=500)
        jet_eta = rng.normal(0, 2.0, 500)
        jet_phi = rng.uniform(-np.pi, np.pi, 500)
        jet = np.stack([jet_pt, jet_eta, jet_phi], axis=1).astype("float32")
        f.create_dataset("jet", data=jet)
        f.attrs["jet_features"] = ["pt", "eta", "phi"]

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
