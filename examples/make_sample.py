#!/usr/bin/env python3
"""Regenerates examples/sample.root — the file used throughout the README.

Run from the repo root:
    python examples/make_sample.py
"""

import os

import numpy as np
import uproot

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sample.root")


def main() -> None:
    rng = np.random.default_rng(42)
    pt = rng.gamma(shape=3.0, scale=8.0, size=2000)
    eta = rng.normal(0, 1.2, 2000)
    n_jets = rng.integers(0, 6, 2000).astype("int32")

    with uproot.recreate(OUT) as f:
        f.mktree("events", {"pt": "float64", "eta": "float64", "n_jets": "int32"})
        f["events"].extend({"pt": pt, "eta": eta, "n_jets": n_jets})

        counts, edges = np.histogram(pt, bins=25)
        f["pt_hist"] = (counts, edges)

        f.mkdir("aux")
        f.mktree("aux/meta", {"run_number": "int32"})
        f["aux/meta"].extend({"run_number": np.full(5, 367123, dtype="int32")})

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
