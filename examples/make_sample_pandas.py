#!/usr/bin/env python3
"""Regenerates the pandas-readable sample fixtures used in the README:
examples/sample.csv, sample.pkl, sample.feather, sample.jsonl.

Same pt/eta/n_jets columns and RNG seed as the other sample fixtures. CSV
can't round-trip a list-valued cell (it serializes to a literal string like
"[1.0, 2.0]"), so only the pickle/JSONL fixtures also carry a ragged
tracks_energy column, demonstrating the "flatten ragged DataFrame columns"
feature -- the pandas/numpy equivalent of a jagged ROOT branch.

Run from the repo root:
    python examples/make_sample_pandas.py
"""

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    rng = np.random.default_rng(42)
    pt = rng.gamma(shape=3.0, scale=8.0, size=2000)
    eta = rng.normal(0, 1.2, 2000)
    n_jets = rng.integers(0, 6, 2000).astype("int32")

    flat_df = pd.DataFrame({"pt": pt, "eta": eta, "n_jets": n_jets})
    flat_df.to_csv(os.path.join(HERE, "sample.csv"), index=False)
    flat_df.to_feather(os.path.join(HERE, "sample.feather"))

    tracks_energy = [
        list(rng.gamma(shape=2.0, scale=10.0, size=int(n))) for n in n_jets
    ]
    ragged_df = flat_df.assign(tracks_energy=tracks_energy)
    ragged_df.to_pickle(os.path.join(HERE, "sample.pkl"))
    ragged_df.to_json(os.path.join(HERE, "sample.jsonl"), orient="records", lines=True)

    for name in ("sample.csv", "sample.feather", "sample.pkl", "sample.jsonl"):
        print(f"wrote {os.path.join(HERE, name)}")


if __name__ == "__main__":
    main()
