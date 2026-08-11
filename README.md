# rootview

Inspect a [ROOT](https://root.cern) file's contents from the terminal —
directory/object hierarchy, TTree branches, and file-level stats — using
[`uproot`](https://github.com/scikit-hep/uproot5), with no PyROOT/ROOT
installation required.

- **One-shot mode** (default): prints a summary panel, an ASCII object tree,
  and per-`TTree` branch tables, rendered with [`rich`](https://github.com/Textualize/rich).
- **Interactive TUI** (`--tui`): a navigable [`textual`](https://github.com/Textualize/textual)
  app — arrow keys to browse the object tree, select a node to see its
  details in a side panel.

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

### Options

| Flag             | Description                                             |
|-------------------|---------------------------------------------------------|
| `--tui`            | launch the interactive textual TUI instead of printing |
| `--depth N`        | limit directory recursion depth                        |
| `--filter REGEX`   | only show keys whose name matches REGEX                |
| `--no-branches`    | skip per-TTree branch tables in one-shot mode           |

## License

MIT — see [LICENSE](LICENSE).
