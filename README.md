# rootfileviewer

Inspect a [ROOT](https://root.cern) file's contents from the terminal —
directory/object hierarchy, TTree branches, and file-level stats — using
[`uproot`](https://github.com/scikit-hep/uproot5), with no PyROOT/ROOT
installation required.

- **One-shot mode** (default): prints a summary panel, an ASCII object tree,
  and per-`TTree` branch tables, rendered with [`rich`](https://github.com/Textualize/rich).
- **Interactive TUI** (`--tui`): a navigable [`textual`](https://github.com/Textualize/textual)
  app — arrow keys to browse the object tree, select a node to see its
  details in a side panel. Selecting a 1D histogram (`TH1*`/`TProfile`)
  plots it as an ASCII bar chart in a panel below, via
  [`textual-plotext`](https://github.com/Textualize/textual-plotext)/[`plotext`](https://github.com/piccolomo/plotext).
  2D/3D histograms aren't plotted yet — the detail panel notes this instead.
  A `TTree`/`TNtuple` node expands into its branches — selecting a branch
  plots its value distribution the same way (vector/jagged branches are
  flattened first; very large trees are capped at 200,000 entries, noted
  in the detail panel).
- **Terse mode** (`--terse`/`-t`): flat, tab-separated, no-color output —
  for piping into `grep`/`awk`/other scripts.

## Install

```bash
pip install rootfileviewer
```

This installs `rootfileviewer` on [PyPI](https://pypi.org/project/rootfileviewer/),
along with two shorter aliases for it: `rfv` (equivalent to `rootfileviewer`)
and `rfvt` (equivalent to `rootfileviewer --tui`). So `rfv examples/sample.root`
and `rfvt examples/sample.root` work anywhere the long forms do.

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

The examples below all use [`examples/sample.root`](examples/sample.root),
committed in this repo (regenerate it with `python examples/make_sample.py`),
containing:
- a `TTree` `events` with branches `pt`, `eta` (`double`), `n_jets` (`int32_t`), 2,000 entries
- a `TH1D` histogram `pt_hist` of the `pt` values, 25 bins
- a subdirectory `aux` holding a second `TTree`, `meta`, with one branch `run_number`, 5 entries

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
│ uproot: 5.7.5                        │
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

Other one-shot flags:

```bash
rootfileviewer examples/sample.root --depth 0            # don't recurse into subdirectories
rootfileviewer examples/sample.root --filter 'events'    # only show keys matching a regex
rootfileviewer examples/sample.root --no-branches        # skip the per-TTree branch tables
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

### Terse mode

`--terse`/`-t` prints flat, tab-separated lines instead of panels/trees/tables —
each line starts with a record-type tag (`summary`/`object`/`branch`) so a
consumer can pick out what it needs:

```bash
rootfileviewer examples/sample.root -t
```

```
summary	path	examples/sample.root
summary	size_bytes	82443
summary	uproot_version	5.7.5
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

### Options

| Flag              | Description                                             |
|-------------------|----------------------------------------------------------|
| `--tui`           | launch the interactive textual TUI instead of printing (same as running `rfvt`) |
| `--terse`, `-t`   | flat, tab-separated output with no borders/colors        |
| `--depth N`       | limit directory recursion depth                          |
| `--filter REGEX`  | only show keys whose name matches REGEX                  |
| `--no-branches`   | skip per-TTree branch info in one-shot/terse mode         |

## License

MIT — see [LICENSE](LICENSE).
