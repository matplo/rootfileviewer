#!/usr/bin/env python3
"""Regenerates examples/sample.parquet — the Parquet fixture used in the README.

Same RNG seed/columns as make_sample.py's `events` TTree, so the two sample
files are directly comparable. Run from the repo root:
    python examples/make_sample_parquet.py
"""

import os

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sample.parquet")


def main() -> None:
    rng = np.random.default_rng(42)
    pt = rng.gamma(shape=3.0, scale=8.0, size=2000)
    eta = rng.normal(0, 1.2, 2000)
    n_jets = rng.integers(0, 6, 2000).astype("int32")

    table = pa.table({"pt": pt, "eta": eta, "n_jets": n_jets})
    pq.write_table(table, OUT)

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
