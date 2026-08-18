# EBSD Analyzer — standalone app

Desktop GUI for EBSD analysis: load an EBSD scan (`.ang`, `.osc`, `.ctf`, or
h5ebsd), compute microstructure (IQ/CI/IPF maps, grain boundaries, union-find
grain segmentation, ASTM E2627 grain size) and crystallographic texture
(de la Vallée Poussin kernel / GSH-harmonic ODF, φ₂ sections, α/γ fibers), then
export a PowerPoint report.

## Layout

```
standalone_ebsd/
├── app.py                 # PySide6 GUI entry point
├── worker.py              # background pipeline thread (QThread)
└── ebsd_engine/           # pure-compute layer (no GUI)
    ├── config.py          # Config dataclass (all parameters)
    ├── ebsd_read.py       # multi-format reader (.ang/.osc/.ctf/h5ebsd)
    ├── microstructure.py  # load, misorientation, grains, grain size
    ├── odf.py             # ODF (kernel / harmonic) + φ₂ sections + fibers
    ├── odf_harmonic.py    # Wigner-D / GSH harmonic ODF engine
    ├── plotting.py        # matplotlib figure builders
    └── report.py          # PowerPoint builder
```

## Install & run (end user, no Python needed)

1. Download / clone this folder.
2. Double-click **`install.bat`** (first time only) — it downloads `pixi` and
   builds a private conda-forge environment. No Python or conda required.
3. Double-click **`launch.bat`** to start the GUI.

For development, run `python app.py` inside the environment `install.bat` builds.

## Build the standalone .exe (PyInstaller, one-folder)

```
pyinstaller ebsd_analyzer.spec --noconfirm --distpath ../standalone_exe --workpath build
```

Output: `../standalone_exe/EBSD_Analyzer/EBSD_Analyzer.exe` (plus its
`_internal/` dependency folder). The whole `EBSD_Analyzer` folder is the
distributable — zip it and share it; no Python needed on the target machine.

## Low-CI clean-up (`ci_mask`)

Noisy scans contain many low-CI pixels whose orientations are unindexed noise;
drawn raw, they speckle the IPF/GB maps. With `ci_mask=True` (GUI default;
Step 2 → Advanced → "Clean low-CI pixels"), each low-CI pixel
(CI < `ci_threshold`) is neighbour-filled with its best-indexed neighbour
("grain dilation") before misorientation/segmentation/grain-size, giving clean
maps and accurate grain counts. `ci_mask=False` uses the raw pixels.

## Dependencies

Python 3.12: numpy, scipy, matplotlib, orix, python-pptx, Pillow, plus
**PySide6** (GUI). The harmonic ODF engine also uses `spherical` + `quaternionic`.
All are fetched into a private conda-forge environment by `install.bat` — nothing
to install by hand.

## License

`orix` is GPL v3, so the distributed application is **GPL v3** (see `LICENSE`).
PySide6 is LGPL v3 (dynamically linked); numpy / scipy / matplotlib /
python-pptx / Pillow are permissive (BSD / MIT / Apache). All compatible under a
GPL v3 umbrella.
