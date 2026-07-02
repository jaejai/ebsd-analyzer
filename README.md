# EBSD Analyzer — standalone app

A desktop GUI for EBSD (Electron Backscatter Diffraction) analysis. Load a TSL
`.ang` scan, compute microstructure (IQ/CI/IPF maps, grain boundaries,
union-find grain segmentation, ASTM E2627 grain size) and crystallographic
texture (GSH-based ODF, φ₂ sections, α/γ fibers), then export a PowerPoint
report.

It wraps the `EBSD_ODF_combined.ipynb` pipeline in a 5-stage PySide6 GUI:
**1** Load & Resample → **2** Microstructure → **3** Grain Size →
**4** Texture (ODF) → **5** Report.

## Install & run

The app uses [pixi](https://prefix.dev) to build a private, self-contained
environment from conda-forge — no manual Python or conda setup required.

**Windows (one-click, for non-technical users)**

1. Run **`install.bat`** once — downloads pixi and builds the environment
   (needs an internet connection; a few hundred MB the first time).
2. Launch anytime with **`launch.bat`**.

**Any platform (with pixi already installed)**

```
pixi install     # build the locked conda-forge environment
pixi run app     # launch the GUI
```

## Layout

```
├── app.py                 # PySide6 GUI entry point (5-stage pipeline)
├── worker.py              # background pipeline thread (QThread)
├── verify_phase0.py       # headless check: engine numbers vs. notebook
├── ebsd_engine/           # pure-compute layer (no GUI)
│   ├── config.py          # Config dataclass (replaces notebook globals)
│   ├── microstructure.py  # §2–§9 load, misorientation, grains, grain size
│   ├── odf.py             # §10–§12 GSH ODF + fibers
│   ├── plotting.py        # §4–§12 matplotlib figure builders
│   └── report.py          # §13 PowerPoint builder
├── gsh_core/              # vendored BSD GSH module (cubic + hex harmonics)
├── ui/                    # GUI layer: step panels, theme, widgets
│   ├── steps.py
│   ├── theme.py
│   └── widgets.py
├── packaging/             # Windows installer (Inno Setup) + distribution notes
├── install.bat            # Windows first-time setup (downloads pixi + env)
├── launch.bat             # Windows launcher
├── get_pixi.ps1           # helper: fetches the pixi binary
├── ebsd_analyzer.spec     # PyInstaller spec (alternative frozen build)
└── pixi.toml / pixi.lock  # locked conda-forge environment definition
```

`gsh_core/` (the vendored BSD GSH module) is bundled here so the app is
self-contained for freezing.

## Low-CI clean-up (`ci_mask`)

Noisy scans (e.g. DP980) contain many low-CI pixels whose orientations are
unindexed noise; drawn raw, they speckle the IPF/GB maps. With `ci_mask=True`
(GUI default; Step 2 → Advanced → "Clean low-CI pixels"), each low-CI pixel
(CI < `ci_threshold`) is neighbour-filled with its best-indexed neighbour
("grain dilation") before misorientation/segmentation/grain-size, giving clean
maps and accurate grain counts. `ci_mask=False` reproduces the raw notebook.
The notebook has the same option via the `CI_MASK` flag (cell §2b).

## Dependencies

Python 3.12 with numpy, scipy, matplotlib, orix, python-pptx, Pillow, and
PySide6. Exact versions are pinned in `pixi.toml` and locked in `pixi.lock`,
resolved from conda-forge only (no Anaconda `defaults` channel, so no Anaconda
commercial licence / ToS is ever required).

## License

GPL v3. The app depends on **orix** (GPL v3), so the combined work is GPL v3
(free to distribute as open source). Bundled `gsh_core` is BSD; PySide6 is
LGPL v3; numpy/scipy/matplotlib/python-pptx are permissive — all compatible
under a GPL v3 umbrella. See the `LICENSE` file for the full text.
