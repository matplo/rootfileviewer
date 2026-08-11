# rootview

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
pip install git+https://github.com/matplo/rootview.git
```

Or clone and install locally:

```bash
git clone https://github.com/matplo/rootview.git
cd rootview
pip install -e .
```

## Usage

```bash
rootview file.root
rootview file.root --tui
rootview file.root --depth 2 --filter 'jet.*'
rootview file.root --no-branches
```

```
$ rootview file.root
╭───────────────────────── ROOT file summary ─────────────────────────╮
│ File: file.root                                                     │
│ Size: 64.5 KB   Compression: ZLIB(1)                                │
│ uproot: 5.7.4                                                       │
│ Keys: 3   TTrees: 2   Histograms: 1                                 │
╰───────────────────────────────────────────────────────────────────────╯
file.root
├── tree1 (TTree) - 1,000 entries, 3 branches
├── hist1 (TH1D) - 20 bins
└── subdir (TDirectory)
    └── tree2 (TTree) - 10 entries, 1 branches
```

### Terse mode

`--terse`/`-t` prints flat, tab-separated lines instead of panels/trees/tables —
each line starts with a record-type tag (`summary`/`object`/`branch`) so a
consumer can pick out what it needs:

```
$ rootview file.root -t
summary	path	file.root
summary	size_bytes	65536
summary	uproot_version	5.7.5
summary	compression	ZLIB(1)
summary	num_trees	2
summary	num_histograms	1
summary	total_keys	3
object	tree1	TTree	entries=1000	branches=3
object	hist1	TH1D	bins=20
object	subdir	TDirectory
object	subdir/tree2	TTree	entries=10	branches=1
branch	tree1	px	double
branch	tree1	py	double
branch	tree1	n	int32_t
branch	subdir/tree2	x	int64_t
```

```bash
rootview file.root -t | grep '^branch'
rootview file.root -t | awk -F'\t' '$1 == "branch" && $2 == "tree1" {print $3, $4}'
```

### Options

| Flag              | Description                                             |
|-------------------|----------------------------------------------------------|
| `--tui`           | launch the interactive textual TUI instead of printing   |
| `--terse`, `-t`   | flat, tab-separated output with no borders/colors        |
| `--depth N`       | limit directory recursion depth                          |
| `--filter REGEX`  | only show keys whose name matches REGEX                  |
| `--no-branches`   | skip per-TTree branch info in one-shot/terse mode         |

## License

MIT — see [LICENSE](LICENSE).
