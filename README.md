# rootfileviewer

Inspect a [ROOT](https://root.cern) or [Parquet](https://parquet.apache.org)
file's contents from the terminal — directory/object hierarchy, TTree
branches or Parquet columns, and file-level stats — using
[`uproot`](https://github.com/scikit-hep/uproot5) (bundled) and
[`pyarrow`](https://arrow.apache.org/docs/python/) (optional, for Parquet),
with no PyROOT/ROOT installation required.

- **One-shot mode** (default): prints a summary panel, an ASCII object tree,
  and per-`TTree`/per-Parquet-column tables, rendered with [`rich`](https://github.com/Textualize/rich).
- **Interactive TUI** (`--tui`): a navigable [`textual`](https://github.com/Textualize/textual)
  app — arrow keys to browse the object tree, select a node to see its
  details in a side panel. Selecting a 1D histogram (`TH1*`/`TProfile`)
  plots it as an ASCII bar chart in a panel below, via
  [`textual-plotext`](https://github.com/Textualize/textual-plotext)/[`plotext`](https://github.com/piccolomo/plotext).
  2D/3D histograms aren't plotted yet — the detail panel notes this instead.
  A `TTree`/`TNtuple` node (or a Parquet file's implicit table) expands into
  its branches/columns — selecting one plots its value distribution the same
  way (vector/jagged branches are flattened first; very large trees/columns
  are capped at 200,000 entries, noted in the detail panel).
- **Terse mode** (`--terse`/`-t`): flat, tab-separated, no-color output —
  for piping into `grep`/`awk`/other scripts.

Parquet support is an optional extra (see [Install](#install)) — a lean
`pip install rootfileviewer` covers ROOT files only, so pointing it at a
`.parquet` file without the extra prints clear install instructions instead
of failing with an import error.

## Install

```bash
pip install rootfileviewer
```

This installs `rootfileviewer` on [PyPI](https://pypi.org/project/rootfileviewer/),
along with two shorter aliases for it: `rfv` (equivalent to `rootfileviewer`)
and `rfvt` (equivalent to `rootfileviewer --tui`). So `rfv examples/sample.root`
and `rfvt examples/sample.root` work anywhere the long forms do.

The base install only pulls in `uproot` (and `rich`/`textual`/`plotext` for
rendering) — it does **not** require `pyarrow`, so it stays lean if you only
ever open `.root` files. Parquet support is an optional extra:

```bash
pip install 'rootfileviewer[parquet]'   # adds pyarrow, for .parquet/.pq files
pip install 'rootfileviewer[all]'       # every optional format's dependencies
```

If you point a lean install at a `.parquet` file, it tells you exactly what
to do instead of crashing:

```
$ rootfileviewer data.parquet
error: reading .parquet files needs: pyarrow
Install it with either:
    pip install 'rootfileviewer[parquet]'
or:
    pip install pyarrow
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

### Interactive TUI

```bash
rootfileviewer examples/sample.root --tui
# or, equivalently:
rfvt examples/sample.root
```

Arrow keys navigate the tree on the left; `Enter`/click selects a node and
updates the panel on the right. Expand `events` to see its branches; select
`pt_hist` or the `pt` branch to plot it below. `q` quits.

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

Note the detail panel shows `branch`/`type` labels for a selected column
(reused verbatim from the ROOT branch code path) rather than "column" —
harmless, cosmetic, and left as-is.

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

### Options

| Flag              | Description                                             |
|-------------------|----------------------------------------------------------|
| `--tui`           | launch the interactive textual TUI instead of printing (same as running `rfvt`) |
| `--terse`, `-t`   | flat, tab-separated output with no borders/colors        |
| `--depth N`       | limit directory recursion depth (ROOT only — no-op for Parquet, which has no subdirectories) |
| `--filter REGEX`  | only show keys whose name matches REGEX (ROOT) or column names matching REGEX (Parquet) |
| `--no-branches`   | skip per-TTree branch info / per-Parquet column info in one-shot/terse mode |

## License

MIT — see [LICENSE](LICENSE).
