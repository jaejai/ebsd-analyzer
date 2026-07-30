# PyInstaller spec for EBSD Analyzer (one-folder build).
#
# Build:  pyinstaller ebsd_analyzer.spec --noconfirm --distpath ../standalone_exe --workpath build
#
# Notes:
# - orix pulls in diffpy.structure / pooch / h5py / tqdm — collect them fully so
#   PyInstaller doesn't miss data files or lazy imports.
# - gsh_core is a local pure-python package (copied into this folder); bundled as
#   a hidden import + its two coefficient .py modules.
# - matplotlib forced to the Qt backend; unused backends excluded to trim size.

import os, glob
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

datas, binaries, hiddenimports = [], [], []

# --- conda/miniforge native DLLs that PyInstaller's hooks miss ---------------
# With conda Python, several stdlib extension modules depend on DLLs that live
# in <env>/Library/bin under conda-specific names that PyInstaller does not
# scan, e.g. _ctypes -> ffi-8.dll, pyexpat -> libexpat.dll. Missing any of
# these makes the frozen exe fail at startup ("DLL load failed importing ...").
# Bundle every DLL in Library/bin to cover them all robustly.
_env_root = os.path.dirname(os.path.dirname(os.__file__))   # <env>
_lib_bin = os.path.join(_env_root, "Library", "bin")
if os.path.isdir(_lib_bin):
    for _p in glob.glob(os.path.join(_lib_bin, "*.dll")):
        binaries.append((_p, "."))

# heavy scientific deps that PyInstaller commonly under-collects.
# spherical + quaternionic + spinsfast power the "harmonic" ODF method
# (MTEX Wigner-D algorithm); they use numba, so collect fully.
for pkg in ("orix", "diffpy", "matplotlib", "scipy", "pptx", "numba", "llvmlite",
            "pooch", "spherical", "quaternionic", "spinsfast"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# ODF harmonic engine (local module bundled with the app). spinsfast is an
# optional spherical backend (not present/needed on Windows) — not forced here.
hiddenimports += ["ebsd_engine.odf_mtex", "spherical", "quaternionic"]
hiddenimports += collect_submodules("orix")
hiddenimports += [
    "scipy.special._cdflib",
    "scipy._lib.array_api_compat.numpy.fft",
]

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "PyQt5", "PyQt6", "PySide2",
        "IPython", "jupyter", "notebook", "pytest", "sphinx",
        "matplotlib.backends.backend_tk", "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_wx", "matplotlib.backends.backend_gtk3",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EBSD_Analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX off for first build (reliability over size)
    console=False,        # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EBSD_Analyzer",
)
