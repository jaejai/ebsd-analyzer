# EBSD ODF Analyzer — standalone app

Desktop GUI wrapping the `EBSD_ODF_combined.ipynb` pipeline: load a TSL `.ang`
scan, compute microstructure (IQ/CI/IPF maps, grain boundaries, union-find grain
segmentation, ASTM E2627 grain size) and crystallographic texture (GSH-based
ODF, φ₂ sections, α/γ fibers), then export a PowerPoint report.

## Layout

```
standalone_ebsd/
├── app.py                 # PySide6 GUI entry point
├── worker.py              # background pipeline thread (QThread)
├── verify_phase0.py       # headless check: engine vs. notebook numbers
└── ebsd_engine/           # pure-compute layer (no GUI)
    ├── config.py          # Config dataclass (replaces notebook globals)
    ├── microstructure.py  # §2–§9 load, misorientation, grains, grain size
    ├── odf.py             # §10–§12 GSH ODF + fibers
    ├── plotting.py        # §4–§12 matplotlib figure builders
    └── report.py          # §13 PowerPoint builder
```

`gsh_core/` (the vendored BSD GSH module) is bundled inside this folder so the
app is self-contained for freezing.

## Run (development)

```
conda activate EBSD_lite_standalone
cd standalone_ebsd
python app.py
```

## Build the standalone .exe (PyInstaller, one-folder)

```
conda activate EBSD_lite_standalone
cd standalone_ebsd
pyinstaller ebsd_analyzer.spec --noconfirm --distpath ../standalone_exe --workpath build
```

Output: `../standalone_exe/EBSD_Analyzer/EBSD_Analyzer.exe` (plus its
`_internal/` dependency folder). The whole `EBSD_Analyzer` folder is the
distributable — zip it and share it; no Python needed on the target machine.

## Verify the engine reproduces the notebook

```
python verify_phase0.py
```

Expected for `dp_data/DP590_Initial_x2000(1).ang` (with `ci_mask=False`, the raw
notebook behaviour): grid 317×937, 437 grains, ASTM G 13.8, texture index
J 2.043, ODF range [-23.89, 55.86] mrd.

## Low-CI clean-up (`ci_mask`)

Noisy scans (e.g. DP980) contain many low-CI pixels whose orientations are
unindexed noise; drawn raw, they speckle the IPF/GB maps. With `ci_mask=True`
(GUI default; Step 2 → Advanced → "Clean low-CI pixels"), each low-CI pixel
(CI < `ci_threshold`) is neighbour-filled with its best-indexed neighbour
("grain dilation") before misorientation/segmentation/grain-size, giving clean
maps and accurate grain counts. `ci_mask=False` reproduces the raw notebook.
The notebook has the same option via the `CI_MASK` flag (cell §2b).

## Environment

`EBSD_lite_standalone` conda env (Python 3.12): the `EBSD_lite` stack
(numpy, scipy, matplotlib, orix, python-pptx, Pillow) plus **PySide6** and
**PyInstaller** for the GUI and the eventual frozen build.

## License

orix is GPL v3 → the distributed application is **GPL v3** (open source).
gsh_core is BSD; PySide6 is LGPL v3; numpy/scipy/matplotlib/python-pptx are
permissive. All compatible under a GPL v3 umbrella.
```
