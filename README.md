# rootfileviewer

Inspect a [ROOT](https://root.cern), [Parquet](https://parquet.apache.org),
[HDF5](https://www.hdfgroup.org/solutions/hdf5/), [numpy](https://numpy.org)
(`.npy`/`.npz`), or pandas-readable (`.csv`/`.pkl`/`.feather`/`.jsonl`) file's
contents from the terminal — object hierarchy, branches/columns/datasets/
arrays, and file-level stats — using
[`uproot`](https://github.com/scikit-hep/uproot5) (bundled),
[`pyarrow`](https://arrow.apache.org/docs/python/) (optional, for Parquet),
[`h5py`](https://www.h5py.org/) (optional, for HDF5), and
[`pandas`](https://pandas.pydata.org/) (optional) — numpy support needs no
extra install at all, since `numpy` is already a dependency of `uproot`
itself — with no PyROOT/ROOT installation required.

- **One-shot mode** (default): prints a summary panel, an ASCII object tree,
  and per-`TTree`/per-Parquet-column tables, rendered with [`rich`](https://github.com/Textualize/rich).
- **Interactive TUI** (`--tui`): a navigable [`textual`](https://github.com/Textualize/textual)
  app — arrow keys to browse the object tree, select a node to see its
  details in a side panel. Selecting a 1D histogram (`TH1*`/`TProfile`)
  plots it as an ASCII bar chart in a panel below, via
  [`textual-plotext`](https://github.com/Textualize/textual-plotext)/[`plotext`](https://github.com/piccolomo/plotext).
  2D/3D histograms aren't plotted yet — the detail panel notes this instead.
  A `TTree`/`TNtuple` node (or a Parquet/DataFrame file's implicit table)
  expands into its branches/columns — selecting one, or an HDF5 dataset or
  numpy array directly, plots its value distribution the same way
  (vector/jagged branches, Parquet `list<...>` columns, HDF5 variable-length
  datasets, and numpy/pandas' own ragged object-dtype arrays/columns are all
  flattened first; very large trees/columns/datasets/arrays are capped at
  200,000 entries, noted in the detail panel).
- **Terse mode** (`--terse`/`-t`): flat, tab-separated, no-color output —
  for piping into `grep`/`awk`/other scripts.

Parquet, HDF5, and pandas support are optional extras (see
[Install](#install)) — a lean `pip install rootfileviewer` covers ROOT files
only, so pointing it at a file needing one of these without the matching
extra prints clear install instructions instead of failing with an import
error.

**Security note**: `.npy`/`.npz` files containing ragged (variable-length)
arrays, and pandas' `.pkl`/`.pickle` files, are loaded via Python's `pickle`
mechanism under the hood — the same way `numpy.load`/`pandas.read_pickle`
always have — which can execute arbitrary code embedded in the file. Only
open files like these from sources you trust.

## Install

```bash
pip install rootfileviewer
```

This installs `rootfileviewer` on [PyPI](https://pypi.org/project/rootfileviewer/),
along with two shorter aliases for it: `rfv` (equivalent to `rootfileviewer`)
and `rfvt` (equivalent to `rootfileviewer --tui`). So `rfv examples/sample.root`
and `rfvt examples/sample.root` work anywhere the long forms do.

The base install only pulls in `uproot` (and `rich`/`textual`/`plotext` for
rendering) — it does **not** require `pyarrow`, `h5py`, or `pandas`, so it
stays lean if you only ever open `.root` files. `.npy`/`.npz` files work out
of the box too, no extra needed (`numpy` is already `uproot`'s own
dependency). Parquet, HDF5, and pandas-readable formats are optional extras
— and so is `matplotlib`, needed only for the TUI's PNG export (`p`, see
[Exporting a plot as a PNG](#exporting-a-plot-as-a-png)):

```bash
pip install 'rootfileviewer[parquet]'     # adds pyarrow, for .parquet/.pq files
pip install 'rootfileviewer[hdf5]'        # adds h5py, for .h5/.hdf5 files
pip install 'rootfileviewer[pandas]'      # adds pandas+pyarrow, for .csv/.pkl/.feather/.jsonl files
pip install 'rootfileviewer[matplotlib]'  # adds matplotlib, for the TUI's PNG export
pip install 'rootfileviewer[all]'         # every optional format's dependencies, plus matplotlib
```

If you point a lean install at a file needing an extra you don't have, it
tells you exactly what to do instead of crashing — naming the file's actual
extension even for a backend covering several of them at once (`.csv`,
`.pkl`, `.feather`, `.jsonl` all route through the same `pandas` extra):

```
$ rootfileviewer data.parquet
error: reading .parquet files needs: pyarrow
Install it with either:
    pip install 'rootfileviewer[parquet]'
or:
    pip install pyarrow
then re-run this command.

$ rootfileviewer data.csv
error: reading .csv files needs: pandas
Install it with either:
    pip install 'rootfileviewer[pandas]'
or:
    pip install pandas
then re-run this command.
```

You can also install straight from GitHub:

```bash
pip install git+https://github.com/matplo/rootfileviewer.git
```

Or clone and install locally:

```bash
git clone https://github.com/matplo/rootfileviewer.git
cd rootfileviewer
pip install -e .
```

## Examples

The ROOT examples below use [`examples/sample.root`](examples/sample.root),
committed in this repo (regenerate it with `python examples/make_sample.py`),
containing:
- a `TTree` `events` with branches `pt`, `eta` (`double`), `n_jets` (`int32_t`), 2,000 entries
- a `TH1D` histogram `pt_hist` of the `pt` values, 25 bins
- a subdirectory `aux` holding a second `TTree`, `meta`, with one branch `run_number`, 5 entries

The Parquet examples use [`examples/sample.parquet`](examples/sample.parquet)
(regenerate it with `python examples/make_sample_parquet.py`) — the same
`pt`/`eta`/`n_jets` columns and 2,000 rows as the `events` TTree above, so
the two are directly comparable; Parquet has no histogram or subdirectory
equivalent.

The HDF5 examples use [`examples/sample.h5`](examples/sample.h5) (regenerate
it with `python examples/make_sample_hdf5.py`) — the same `pt`/`eta`/`n_jets`
datasets and 2,000 entries, a `tracks_energy` variable-length ("jagged")
dataset (a per-event list of track energies — HDF5's analogue of a jagged
ROOT branch or a Parquet `list<double>` column), a subgroup `aux` holding a
`run_number` dataset (so it maps onto `sample.root`'s shape almost exactly —
HDF5 Groups are real directories, just like ROOT's), and a `jet` dataset
(500 entries) with a `jet_features` attribute naming its 3 columns
`pt`/`eta`/`phi` — see [Named-feature datasets](#named-feature-datasets).

The numpy examples use [`examples/sample.npz`](examples/sample.npz) and
[`examples/sample.npy`](examples/sample.npy) (regenerate both with
`python examples/make_sample_npz.py`) — `sample.npz` holds the same
`pt`/`eta`/`n_jets` arrays plus a ragged `tracks_energy` array (numpy's own
object-dtype representation of per-event variable-length data — no HDF5/
Parquet needed to see the "flatten a jagged array" feature in action) and a
`hits` array (2,000 entries, 3 columns) with no name for any of its 3
columns — `.npz`/`.npy` have no attribute mechanism the way HDF5 does — see
[Named-feature datasets](#named-feature-datasets)'s generic-column-splitting
note; `sample.npy` is just the `pt` array on its own, to show the
single-array case.

The pandas examples use [`examples/sample.csv`](examples/sample.csv),
[`sample.feather`](examples/sample.feather), [`sample.pkl`](examples/sample.pkl),
and [`sample.jsonl`](examples/sample.jsonl) (regenerate all four with
`python examples/make_sample_pandas.py`) — the same `pt`/`eta`/`n_jets`
columns; the pickle/JSONL versions also carry a ragged `tracks_energy`
column (CSV can't round-trip a list-valued cell — it serializes to a literal
string like `"[1.0, 2.0]"` — so only the binary/structured formats include it).

Clone the repo and run these directly:

```bash
git clone https://github.com/matplo/rootfileviewer.git
cd rootfileviewer
rootfileviewer examples/sample.root
```

### One-shot mode

```bash
rootfileviewer examples/sample.root
```

```
╭───────── ROOT file summary ──────────╮
│ File: examples/sample.root           │
│ Size: 80.5 KB   Compression: ZLIB(1) │
│ uproot: 5.7.6                        │
│ Keys: 3   TTrees: 2   Histograms: 1  │
╰──────────────────────────────────────╯
sample.root
├── events (TTree) - 2,000 entries, 3 branches
├── pt_hist (TH1D) - 25 bins
└── aux (TDirectory)
    └── meta (TTree) - 5 entries, 1 branches
   TTree: events    
  (2,000 entries)   
┏━━━━━━━━┳━━━━━━━━━┓
┃ Branch ┃ Type    ┃
┡━━━━━━━━╇━━━━━━━━━┩
│ pt     │ double  │
│ eta    │ double  │
│ n_jets │ int32_t │
└────────┴─────────┘
  TTree: aux/meta  (5   
        entries)        
┏━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Branch     ┃ Type    ┃
┡━━━━━━━━━━━━╇━━━━━━━━━┩
│ run_number │ int32_t │
└────────────┴─────────┘
```

The same mode works for Parquet files, once the `[parquet]` extra is
installed — the summary panel and per-column table use Parquet-appropriate
wording instead of ROOT's:

```bash
rootfileviewer examples/sample.parquet
```

```
╭────────── Parquet file summary ──────────╮
│ File: examples/sample.parquet            │
│ Size: 38.4 KB                            │
│ pyarrow: 25.0.1                          │
│ Rows: 2,000   Columns: 3   Row groups: 1 │
╰──────────────────────────────────────────╯
sample.parquet
└── table (ParquetTable) - 2,000 entries, 3 columns
      Table:       
  sample.parquet   
  (2,000 entries)  
┏━━━━━━━━┳━━━━━━━━┓
┃ Column ┃ Type   ┃
┡━━━━━━━━╇━━━━━━━━┩
│ pt     │ double │
│ eta    │ double │
│ n_jets │ int32  │
└────────┴────────┘
```

HDF5 files, once the `[hdf5]` extra is installed, look the closest to ROOT's
own output — real Groups nest like TDirectories, and each Dataset shows its
dtype and shape directly (no separate per-tree table is needed, since
there's nothing hidden the way ROOT branches are inside a TTree):

```bash
rootfileviewer examples/sample.h5
```

```
╭──────── HDF5 file summary ────────╮
│ File: examples/sample.h5          │
│ Size: 148.2 KB                    │
│ h5py: 3.16.0   HDF5: 2.0.0        │
│ Keys: 7   Groups: 1   Datasets: 6 │
╰───────────────────────────────────╯
sample.h5
├── aux (HDF5Group)
│   └── run_number (int32[5])
├── eta (float64[2000])
├── jet (HDF5FeatureSet) - 500 entries, 3 columns
├── n_jets (int32[2000])
├── pt (float64[2000])
└── tracks_energy (vlen<float64>[2000])
```

#### Named-feature datasets

There's no single universal HDF5 convention for naming the individual
entries along a dataset's last axis, but a `<dataset-name>_features`
attribute (either at the file root, or directly on the dataset — both are
recognized) is one used in the wild — for example, a `(9764, 7)` dataset
`jet` holding 7 physically distinct quantities per event (energy, angles,
...), named via a root-level `jet_features` attribute. Without reading that
attribute, selecting `jet` would only ever flatten all 7 into one
meaningless combined histogram; with it, `jet` becomes a small table of 7
individually named, selectable, plottable columns — exactly like a
`ParquetTable`'s columns, reusing the same machinery. `sample.h5`'s own
`jet` dataset (3 columns: `pt`/`eta`/`phi`) demonstrates this:

```bash
rootfileviewer examples/sample.h5
```

```
  Table: jet  (500  
      entries)      
┏━━━━━━━━┳━━━━━━━━━┓
┃ Column ┃ Type    ┃
┡━━━━━━━━╇━━━━━━━━━┩
│ pt     │ float32 │
│ eta    │ float32 │
│ phi    │ float32 │
└────────┴─────────┘
```

A 1D dataset — like `pt`/`eta`/`n_jets` above — is never affected by any of
this (there's no "last axis of features" to split); it keeps the original
flatten-everything behavior. A 3D `(events, particles, features)` shape
(not shown here) works the same way as the 2D case, with each named column
still 2D and flattened across the middle axis when plotted, same as an
unsplit multi-dim dataset.

**Generic columns, when there's no name to use.** A multi-dim dataset with
no matching (or a wrong-length) features/columns/labels attribute still
gets split, using generic `column_0`/`column_1`/... labels instead of real
names — *unless* its last axis is wider than 20 entries, which is presumed
to be genuinely homogeneous data (e.g. a 128-dim embedding) where flattening
is still the more sensible default. `.npz`/`.npy` files have no attribute
mechanism at all, so this generic fallback is the *only* splitting numpy
ever gets — demonstrated by `sample.npz`'s own `hits` array (3 unnamed
columns):

```bash
rootfileviewer examples/sample.npz
```

```
└── hits (NpyColumnSet) - 2,000 entries, 3 columns
 Table: hits  (2,000  
       entries)       
┏━━━━━━━━━━┳━━━━━━━━━┓
┃ Column   ┃ Type    ┃
┡━━━━━━━━━━╇━━━━━━━━━┩
│ column_0 │ float32 │
│ column_1 │ float32 │
│ column_2 │ float32 │
└──────────┴─────────┘
```

numpy files need no extra install at all — arrays are top-level leaves
directly (`.npz`'s several independent arrays have no shared row count to
group under a wrapper, unlike Parquet/HDF5), with the ragged array's dtype
shown as `ragged<float64>` rather than the less useful raw `object`:

```bash
rootfileviewer examples/sample.npz
```

```
╭─── numpy file summary ────╮
│ File: examples/sample.npz │
│ Size: 160.9 KB            │
│ numpy: 2.5.2              │
│ Arrays: 5                 │
╰───────────────────────────╯
sample.npz
├── pt (float64[2000])
├── eta (float64[2000])
├── n_jets (int32[2000])
├── tracks_energy (ragged<float64>[2000])
└── hits (NpyColumnSet) - 2,000 entries, 3 columns
```

(`hits`'s own column table is shown further above, in
[Named-feature datasets](#named-feature-datasets).)

pandas-readable files (CSV, pickle, Feather, JSON Lines) share the same
`DataFrameTable` wrapper node as Parquet — once the `[pandas]` extra is
installed:

```bash
rootfileviewer examples/sample.pkl
```

```
╭─ DataFrame file summary ──╮
│ File: examples/sample.pkl │
│ Size: 138.9 KB            │
│ pandas: 3.0.5             │
│ Rows: 2,000   Columns: 4  │
╰───────────────────────────╯
sample.pkl
└── table (DataFrameTable) - 2,000 entries, 4 columns
Table: sample.pkl  (2,000 entries)
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Column        ┃ Type            ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ pt            │ float64         │
│ eta           │ float64         │
│ n_jets        │ int32           │
│ tracks_energy │ ragged<float64> │
└───────────────┴─────────────────┘
```

Other one-shot flags:

```bash
rootfileviewer examples/sample.root --depth 0            # don't recurse into subdirectories
rootfileviewer examples/sample.root --filter 'events'    # only show keys matching a regex
rootfileviewer examples/sample.root --no-branches        # skip the per-TTree branch tables
```

For Parquet files, `--filter` matches **column** names instead (there's only
one flat table, so there's nothing else to filter), `--depth` is a no-op
(nothing to recurse into), and `--no-branches` skips the column table the
same way:

```bash
rootfileviewer examples/sample.parquet --filter 'pt|eta'    # only pt/eta columns
rootfileviewer examples/sample.parquet --no-branches        # skip the column table
```

HDF5 is the one non-ROOT format where `--depth` does something real, since
Groups genuinely nest — `--filter` matches group/dataset names at every
level, same as ROOT; `--no-branches` is a no-op for a plain dataset (there's
no separate table to skip — its dtype/shape is already shown directly in
the tree above), but does skip the column table for a
[named-feature dataset](#named-feature-datasets) like `jet`, same as a
TTree's branch table:

```bash
rootfileviewer examples/sample.h5 --depth 0          # don't recurse into aux/
rootfileviewer examples/sample.h5 --filter 'pt|eta'  # only pt/eta datasets
```

For numpy files, `--filter` matches array names (meaningful for a `.npz`'s
several arrays; for a single `.npy` there's only its own name to match),
`--depth` is a no-op (flat, no nesting), and `--no-branches` is a no-op for
a plain array but does skip a column-split one's table (like `hits`), same
reasoning as HDF5:

```bash
rootfileviewer examples/sample.npz --filter 'pt|eta'  # only pt/eta arrays
```

pandas-readable files behave exactly like Parquet: `--filter` matches column
names, `--depth` is a no-op, `--no-branches` skips the column table:

```bash
rootfileviewer examples/sample.pkl --filter 'pt|eta'  # only pt/eta columns
```

### Interactive TUI

```bash
rootfileviewer examples/sample.root --tui
# or, equivalently:
rfvt examples/sample.root
```

Arrow keys navigate the tree on the left; `Enter`/click selects a node and
updates the panel on the right. Expand `events` to see its branches; select
`pt_hist` or the `pt` branch to plot it below. `q` quits, `x`/`y` toggle a
logarithmic x-/y-axis on the current plot (see
[Logarithmic axes](#logarithmic-axes) below).

```
┌─ rootfileviewer: sample.root ──────────────────────────────────────────────────┐
│ ┌─ tree ───────────────────┐ ┌─ detail ─────────────────────────────┐   │
│ │ ▼ sample.root             │ │ Field     Value                     │   │
│ │   ▼ events (TTree) - ...  │ │ branch    pt                        │   │
│ │   │  ▶ pt (double)      ◀ │ │ type      double                    │   │
│ │   │    eta (double)       │ │ sampled   2,000 entries             │   │
│ │   │    n_jets (int32_t)   │ │                                     │   │
│ │     pt_hist (TH1D) - ...  │ │                                     │   │
│ │   ▼ aux (TDirectory)      │ │                                     │   │
│ │       meta (TTree) - ...  │ │                                     │   │
│ └────────────────────────  ┘ └───────────────────────────────────  ┘   │
│ ┌─ histplot ────────────────────────────────────────────────────────┐   │
│ │                                     pt                             │   │
│ │ 208.0┤         ███████                                             │   │
│ │      │    ████████████████                                        │   │
│ │      │  █████████████████████████                                 │   │
│ │  0.0 ┤█████████████████████████████████████████████████████████  │   │
│ │      └────────────┬──────────────────┬─────────────────────────  │   │
│ │            18.5                65.7                               │   │
│ └─────────────────────────────────────────────────────────────────  ┘   │
│                                                                q Quit    │
└───────────────────────────────────────────────────────────────────────  ┘
```

The plot panel is the same [`plotext`](https://github.com/piccolomo/plotext)
render whether you selected the `pt_hist` histogram or the `pt` branch
directly (they happen to look similar here since `pt_hist` was built from
`pt`) — actual captures below:

<details>
<summary>Selecting <code>pt_hist</code> (TH1D) — exact terminal capture</summary>

```
                                   pt_hist                              
     ┌─────────────────────────────────────────────────────────────────┐
248.0┤          ████                                                   │
     │        ███████████                                              │
206.7┤     ██████████████                                              │
     │     ██████████████                                              │
165.3┤     ██████████████                                              │
     │     ████████████████                                            │
124.0┤   █████████████████████                                         │
     │   █████████████████████                                         │
     │   ████████████████████████                                      │
 82.7┤   ████████████████████████                                      │
     │████████████████████████████████                                 │
 41.3┤██████████████████████████████████                               │
     │██████████████████████████████████████████                       │
  0.0┤█████████████████████████████████████████████████████████████████│
     └──────────────────────┬──────────────┬─────────────────────────┬─┘
               33.27650853248193   55.95309492725528 93.74740558521088  
```

(`plotext`'s axis tick count/labels can shift slightly with terminal width —
the bars themselves are what matters here.)

</details>

<details>
<summary>Selecting the <code>pt</code> branch under <code>events</code> — exact terminal capture</summary>

```
                                     pt                                 
     ┌─────────────────────────────────────────────────────────────────┐
208.0┤         ███████                                                 │
     │         █████████                                               │
173.3┤      ████████████                                               │
     │    ████████████████                                             │
138.7┤    ████████████████                                             │
     │    ████████████████                                             │
104.0┤    ████████████████████                                         │
     │  ██████████████████████                                         │
     │  █████████████████████████                                      │
 69.3┤  ███████████████████████████                                    │
     │█████████████████████████████████                                │
 34.7┤█████████████████████████████████                                │
     │██████████████████████████████████████████   ███                 │
  0.0┤█████████████████████████████████████████████████████████████████│
     └─────┬─────────────────────────┬──────────────────┬──────────────┘
     9.025159193627086       46.81946985158268    75.1652028450494      
```

Detail panel for this selection: `branch: pt`, `type: double`,
`sampled: 2,000 entries`. On a tree with more than 200,000 entries the
`sampled` row would instead read e.g. `200,000/5,000,000 entries` — the
plot is always built from a capped, uniformly-sampled prefix for
responsiveness, and vector/jagged branches are flattened first (noted as
`..., N values (flattened)`).

</details>

For a Parquet file, the tree root expands directly into a single `table`
node (the file's implicit flat table), which itself expands into its
columns — same navigation, same plotting:

```bash
rootfileviewer examples/sample.parquet --tui
```

<details>
<summary>Selecting the <code>pt</code> column — exact terminal capture</summary>

```
                                      pt                                 
     ┌──────────────────────────────────────────────────────────────────┐
208.0┤         ███████                                                  │
     │       ███████████                                                │
173.3┤       ███████████                                                │
     │    █████████████████                                             │
138.7┤    █████████████████                                             │
104.0┤    █████████████████████                                         │
     │  ███████████████████████                                         │
 69.3┤  █████████████████████████                                       │
     │  ███████████████████████████                                     │
 34.7┤██████████████████████████████████                                │
     │██████████████████████████████████████████                        │
  0.0┤██████████████████████████████████████████████████████████████████│
     └─────────────────────┬──────────────┬──────────────┬──────────────┘
             31.071840410767848   53.11852162790862  75.1652028450494    
```

</details>

<details>
<summary>Selecting the <code>n_jets</code> column — exact terminal capture</summary>

```
                                    n_jets                               
     ┌──────────────────────────────────────────────────────────────────┐
351.0┤███                       ███          ███                        │
     │███          ███          ███          ███          ███        ███│
292.5┤███          ███          ███          ███          ███        ███│
     │███          ███          ███          ███          ███        ███│
234.0┤███          ███          ███          ███          ███        ███│
175.5┤███          ███          ███          ███          ███        ███│
     │███          ███          ███          ███          ███        ███│
117.0┤███          ███          ███          ███          ███        ███│
     │███          ███          ███          ███          ███        ███│
 58.5┤███          ███          ███          ███          ███        ███│
     │███          ███          ███          ███          ███        ███│
  0.0┤██           ██           ██           ██           ██         ███│
     └───┬──────┬─────┬──────┬─────┬──────┬──────────────┬──────────────┘
       0.25   0.75  1.25   1.75  2.25   2.75     3.9166666666666665
```

`n_jets` is a low-cardinality integer column, so each bar lands on its own
narrow bucket — a good illustration that this is the exact same
`numpy.histogram`-based binning used for ROOT branches, not a
special-cased "categorical" plot.

</details>

For an HDF5 file, Groups expand like real directories and Datasets are
directly selectable and plottable — including a variable-length ("jagged")
dataset, flattened across all its rows the same way a jagged ROOT branch or
a Parquet `list<double>` column is:

```bash
rootfileviewer examples/sample.h5 --tui
```

<details>
<summary>Selecting the <code>tracks_energy</code> dataset (variable-length, per-event track energies) — exact terminal capture</summary>

```
                                 tracks_energy                           
     ┌──────────────────────────────────────────────────────────────────┐
884.0┤    ████                                                          │
     │  ████████                                                        │
736.7┤  ████████                                                        │
     │  ████████                                                        │
589.3┤  ██████████                                                      │
442.0┤████████████                                                      │
     │██████████████                                                    │
294.7┤████████████████                                                  │
     │██████████████████                                                │
147.3┤█████████████████████                                             │
     │███████████████████████████                                       │
  0.0┤██████████████████████████████████████████████████████████████████│
     └────────────────┬──────────────┬──────────┬───────────────────────┘
          37.1623311832877   71.71512472646408 96.39569154301864
```

Detail panel: `sampled: 2,000 entries, 4,953 values (flattened)` — 2,000
events' worth of `tracks_energy` reads to a ragged array of ~2.5 tracks per
event on average, flattened into one distribution.

</details>

Note the detail panel shows `branch`/`type` labels for a selected column or
dataset (reused verbatim from the ROOT branch code path) rather than
"column"/"dataset" — harmless, cosmetic, and left as-is.

`jet` (a [named-feature dataset](#named-feature-datasets)) expands into its
3 named columns just like a TTree expands into branches — selecting one
plots only that column, not all 3 flattened together:

<details>
<summary>Selecting the <code>eta</code> column under <code>jet</code> — exact terminal capture</summary>

```
                                     eta                                 
    ┌───────────────────────────────────────────────────────────────────┐
45.0┤                                 ███    ███                        │
    │                               █████    ███                        │
37.5┤                             ███████    ███                        │
    │                      ███    ██████████████                        │
30.0┤                      █████████████████████                        │
22.5┤                    █████████████████████████                      │
    │                  ███████████████████████████                      │
15.0┤                  ███████████████████████████                      │
    │             ███████████████████████████████████████               │
 7.5┤           █████████████████████████████████████████████           │
    │         █████████████████████████████████████████████████         │
 0.0┤██████████████████████████████████████████████████████████████  ███│
    └───────────────────────┬───────────────┬───────────────────────┬───┘
           -1.6425214290618897 1.0974516073862706     5.40312352180481
```

Detail panel: `sampled: 500 entries` — no other `jet` column's values are
mixed in.

</details>

numpy arrays are directly selectable at the top level too, including a
ragged one — the same flattening as above, this time from numpy's own
object-dtype representation of jagged data rather than HDF5's variable-length
datasets:

```bash
rootfileviewer examples/sample.npz --tui
```

<details>
<summary>Selecting the <code>tracks_energy</code> array (ragged, per-event track energies) — exact terminal capture</summary>

```
                                 tracks_energy                           
     ┌──────────────────────────────────────────────────────────────────┐
884.0┤    ████                                                          │
     │  ████████                                                        │
736.7┤  ████████                                                        │
     │  ████████                                                        │
589.3┤  ██████████                                                      │
442.0┤████████████                                                      │
     │██████████████                                                    │
294.7┤████████████████                                                  │
     │██████████████████                                                │
147.3┤█████████████████████                                             │
     │███████████████████████████                                       │
  0.0┤██████████████████████████████████████████████                 ███│
     └──────────────┬───────────────────────────┬───────────────────────┘
            32.22621781997678           96.39569154301864
```

</details>

`hits` (a column-split array with no real names — see
[Named-feature datasets](#named-feature-datasets)) expands into `column_0`/
`column_1`/`column_2`, same as `jet`'s named columns did for HDF5:

<details>
<summary>Selecting <code>column_0</code> under <code>hits</code> — exact terminal capture</summary>

```
                                   column_0                              
     ┌──────────────────────────────────────────────────────────────────┐
194.0┤                              ██████                              │
     │                            ████████████                          │
161.7┤                          ██████████████                          │
     │                          ████████████████                        │
129.3┤                        ██████████████████                        │
 97.0┤                        ████████████████████                      │
     │                      █████████████████████████                   │
 64.7┤                    █████████████████████████████                 │
     │                 ██████████████████████████████████               │
 32.3┤               ██████████████████████████████████████             │
     │           ██████████████████████████████████████████████         │
  0.0┤██     ███████████████████████████████████████████████████████████│
     └───┬────────────────────────────────────┬─────────────────────────┘
    -16.686344146728516              3.8736101786295567
```

</details>

For a pandas-readable file, the tree root expands into a `table` node the
same way Parquet's does — a ragged/list-valued column flattens exactly like
the numpy/HDF5 cases above:

```bash
rootfileviewer examples/sample.pkl --tui
```

<details>
<summary>Selecting the <code>tracks_energy</code> column (a per-row list of track energies) — exact terminal capture</summary>

```
                                 tracks_energy                           
     ┌──────────────────────────────────────────────────────────────────┐
884.0┤    ████                                                          │
     │  ████████                                                        │
736.7┤  ████████                                                        │
     │  ████████                                                        │
589.3┤  ██████████                                                      │
442.0┤████████████                                                      │
     │██████████████                                                    │
294.7┤████████████████                                                  │
     │██████████████████                                                │
147.3┤█████████████████████                                             │
     │███████████████████████████                                       │
  0.0┤██████████████████████████████████████████████                 ███│
     └──────────────────┬────────────────────────────┬──────────────────┘
                42.09844454659861           106.26791826964046
```

</details>

#### Logarithmic axes

Press `x` while a plot is showing to toggle a logarithmic x-axis; `y` does
the same for the y-axis. Both apply to whatever's currently plotted and
stay on as you select other nodes, across every format. `plotext` has no
native log-axis support, so this is faked by plotting `log10(x)` and
relabeling the ticks with the real values — the plot title gets a
`[log x]`/`[log y]` suffix as a reminder which is active.

For a branch/column/dataset/array (not a pre-binned `TH1` histogram), `x`
does a **real rebin** with logarithmically-spaced bin edges (equal width in
log space) — not just a compressed x-axis on the same linear bins — so the
shape is actually meaningful for data spanning multiple decades, e.g. a
`pt` spectrum:

<details>
<summary>The <code>pt</code> branch, linear vs. logarithmic x-axis — exact terminal captures</summary>

```
                                      pt                                 
     ┌──────────────────────────────────────────────────────────────────┐
208.0┤         ███████                                                  │
     │       ███████████                                                │
173.3┤       ███████████                                                │
     │    █████████████████                                             │
138.7┤    █████████████████                                             │
104.0┤    █████████████████████                                         │
     │  ███████████████████████                                         │
 69.3┤  █████████████████████████                                       │
     │  ███████████████████████████                                     │
 34.7┤██████████████████████████████████                                │
     │██████████████████████████████████████████                        │
  0.0┤██████████████████████████████████████████████████████████████████│
     └─┬──────────────┬────────────────────────────────────┬────────────┘
   2.726107417301151 24.772788634441916          78.31472873321235       
```

```
                                  pt [log x]                             
     ┌──────────────────────────────────────────────────────────────────┐
225.0┤                                           ████                   │
     │                                           ██████                 │
187.5┤                                       ████████████               │
     │                                       ████████████               │
150.0┤                                     ████████████████             │
112.5┤                                   ██████████████████             │
     │                                 ██████████████████████           │
 75.0┤                              █████████████████████████           │
     │                            █████████████████████████████         │
 37.5┤                          ██████████████████████████████████      │
     │                 █████████████████████████████████████████████    │
  0.0┤██████████████████████████████████████████████████████████████████│
     └─┬───────────────┬───────────────┬──────────────┬───────────────┬─┘
     1.24            3.61            10.5           30.5           88.8
```

</details>

A `TH1`/`TProfile` histogram's bins are already fixed by ROOT — there's no
raw data left to rebin — so `x` there just re-renders the *existing* bins on
a log-looking axis rather than truly rebinning them.

`y` never rebins anything (it's the count axis) — an empty bin (0 count)
simply shows no bar rather than `log10(0)`. `x` needs every plotted value to
be strictly positive (a log axis can't represent zero or negative numbers);
if the current data has any zero or negative value, pressing `x` reports a
`plot error` in the detail panel instead of a broken plot, and `y` isn't
affected by this restriction at all since counts are never negative.

#### Exporting a plot as a PNG

Press `p` while a plot is showing to save it as a real PNG via
[`matplotlib`](https://matplotlib.org/) — an optional extra (see
[Install](#install)); without it, `p` shows a toast telling you to
`pip install 'rootfileviewer[matplotlib]'` rather than crashing. The file is
named `<source-file-stem>_<node-name>.png` (e.g. `sample_pt.png`) in the
current directory — pressing `p` again on the same node overwrites it
rather than piling up new files. It's self-documenting: the node name is
the title, and a footer names the source file and the same sampling note
shown in the detail panel (e.g. `2,000 entries`, or `200,000/5,000,000
entries, ..., N non-finite excluded` on a huge or messy branch):

```
$ rootfileviewer examples/sample.root --tui
# select the pt branch, press p
Saved sample_pt.png
```

The resulting `sample_pt.png` is a normal `matplotlib` bar chart: a
right-skewed histogram titled `pt`, x-axis labeled `value`, y-axis labeled
`count`, with `sample.root — 2,000 entries` printed as a small caption below
the axes — everything needed to know what the image is without also having
the terminal session in front of you.

If `x`/`y` are toggled when you press `p`, the PNG reflects that too — but
using `matplotlib`'s own real `ax.set_xscale("log")`/`set_yscale("log")`
rather than the tick-relabeling trick the ASCII plot needs, since
`matplotlib` (unlike `plotext`) has native log-axis support. `p` exports
whatever's actually currently visible: selecting a non-plottable node (or
one that fails to plot) clears the export target, so it never re-saves a
stale previous plot by mistake.

### Terse mode

`--terse`/`-t` prints flat, tab-separated lines instead of panels/trees/tables —
each line starts with a record-type tag (`summary`/`object`/`branch`) so a
consumer can pick out what it needs:

```bash
rootfileviewer examples/sample.root -t
```

```
summary	path	examples/sample.root
summary	format	root
summary	size_bytes	82443
summary	uproot_version	5.7.6
summary	compression	ZLIB(1)
summary	num_trees	2
summary	num_histograms	1
summary	total_keys	3
object	events	TTree	entries=2000	branches=3
object	pt_hist	TH1D	bins=25
object	aux	TDirectory
object	aux/meta	TTree	entries=5	branches=1
branch	events	pt	double
branch	events	eta	double
branch	events	n_jets	int32_t
branch	aux/meta	run_number	int32_t
```

```bash
rootfileviewer examples/sample.root -t | grep '^branch'
rootfileviewer examples/sample.root -t | awk -F'\t' '$1 == "branch" && $2 == "events" {print $3, $4}'
rootfileviewer examples/sample.root -t | awk -F'\t' '$1 == "object" && $3 == "TTree" {print $2}'
```

The same tags cover Parquet output — a script can tell the two apart via
`summary format` or an `object` row's classname (`ParquetTable` vs `TTree`);
the `branch` tag itself is reused for columns rather than introducing a
separate `column` tag:

```bash
rootfileviewer examples/sample.parquet -t
```

```
summary	path	examples/sample.parquet
summary	format	parquet
summary	size_bytes	39340
summary	pyarrow_version	25.0.1
summary	num_rows	2000
summary	num_columns	3
summary	num_row_groups	1
summary	total_keys	1
object	table	ParquetTable	entries=2000	branches=3
branch	table	pt	double
branch	table	eta	double
branch	table	n_jets	int32
```

A plain HDF5 dataset needs no `branch`-tag row at all: unlike a TTree's
branches or a Parquet table's columns (which live *inside* one enumerable
object and need a separate listing mechanism), each dataset is already its
own distinct `object` row, wherever it sits in the group hierarchy. A
[named-feature dataset](#named-feature-datasets) like `jet` is the
exception — it's `object`-tagged as an `HDF5FeatureSet`, and its columns get
`branch` rows the same way a TTree's or DataFrameTable's do:

```bash
rootfileviewer examples/sample.h5 -t
```

```
summary	path	examples/sample.h5
summary	format	hdf5
summary	size_bytes	151748
summary	h5py_version	3.16.0
summary	hdf5_version	2.0.0
summary	num_groups	1
summary	num_datasets	6
summary	total_keys	7
object	aux	HDF5Group
object	aux/run_number	int32[5]	entries=5
object	eta	float64[2000]	entries=2000
object	jet	HDF5FeatureSet	entries=500	branches=3
object	n_jets	int32[2000]	entries=2000
object	pt	float64[2000]	entries=2000
object	tracks_energy	vlen<float64>[2000]	entries=2000
branch	jet	pt	float32
branch	jet	eta	float32
branch	jet	phi	float32
```

numpy output is mostly the same story as HDF5 — a plain array is already
its own `object` row, no `branch`-tag rows needed — except for a
column-split array like `hits`, which gets `branch` rows the same way an
`HDF5FeatureSet` does:

```bash
rootfileviewer examples/sample.npz -t
```

```
summary	path	examples/sample.npz
summary	format	numpy
summary	size_bytes	164715
summary	numpy_version	2.5.2
summary	num_arrays	5
summary	total_keys	5
object	pt	float64[2000]	entries=2000
object	eta	float64[2000]	entries=2000
object	n_jets	int32[2000]	entries=2000
object	tracks_energy	ragged<float64>[2000]	entries=2000
object	hits	NpyColumnSet	entries=2000	branches=3
branch	hits	column_0	float32
branch	hits	column_1	float32
branch	hits	column_2	float32
```

pandas-readable files share the `branch`-tag output with Parquet (both use
the same synthetic-table wrapper):

```bash
rootfileviewer examples/sample.pkl -t
```

```
summary	path	examples/sample.pkl
summary	format	pandas
summary	size_bytes	142209
summary	pandas_version	3.0.5
summary	num_rows	2000
summary	num_columns	4
summary	total_keys	1
object	table	DataFrameTable	entries=2000	branches=4
branch	table	pt	float64
branch	table	eta	float64
branch	table	n_jets	int32
branch	table	tracks_energy	ragged<float64>
```

### Options

| Flag              | Description                                             |
|-------------------|----------------------------------------------------------|
| `--tui`           | launch the interactive textual TUI instead of printing (same as running `rfvt`) |
| `--terse`, `-t`   | flat, tab-separated output with no borders/colors        |
| `--depth N`       | limit directory recursion depth (ROOT, HDF5 — no-op for Parquet/numpy/pandas, which are flat) |
| `--filter REGEX`  | only show keys/group/dataset names matching REGEX (ROOT, HDF5), or column/array names (Parquet, numpy, pandas) |
| `--no-branches`   | skip per-TTree/per-table branch or column tables in one-shot/terse mode (no-op for a plain HDF5/numpy array — nothing separate to skip; still applies to a column-split array, e.g. an HDF5 [named-feature dataset](#named-feature-datasets) or a numpy one like `hits`) |

## License

MIT — see [LICENSE](LICENSE).
