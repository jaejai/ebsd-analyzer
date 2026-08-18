"""Generate the EBSD ODF Analyzer user manual as a PDF.

Uses only matplotlib (already an app dependency), so the manual can be rebuilt
anywhere the app itself runs — no extra packages to install.

    python packaging/make_manual.py [-o OUTPUT.pdf] [--figdir DIR]

`--figdir` points at a folder of example figures (ex_ci.png, ex_ipf.png,
ex_gb.png, ex_odf.png, ex_phase.png). If a figure is missing that panel is
simply skipped, so the manual always builds.
"""
from __future__ import annotations

import argparse
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

# ---------------------------------------------------------------- palette
INK = "#12324f"
BODY = "#25303c"
MUTE = "#5c6775"
ACCENT = "#2f6fe0"
RULE = "#c7d0da"
CODE_BG = "#f2f5f9"

PAGE = (8.27, 11.69)          # A4 portrait, inches
LEFT, RIGHT = 0.085, 0.915
TOP = 0.945


class Manual:
    """Simple flowing-text page builder on top of matplotlib PdfPages."""

    def __init__(self, pdf, title_running="EBSD ODF Analyzer — User Manual"):
        self.pdf = pdf
        self.title_running = title_running
        self.page_no = 0
        self.fig = None
        self.y = 0.0

    # -- page lifecycle ---------------------------------------------------
    def new_page(self, first=False):
        self.close_page()
        self.fig = Figure(figsize=PAGE)
        self.fig.patch.set_facecolor("white")
        self.page_no += 1
        if not first:
            ax = self.fig.add_axes([0, 0, 1, 1]); ax.axis("off")
            ax.text(LEFT, 0.972, self.title_running, fontsize=7.5, color=MUTE)
            ax.plot([LEFT, RIGHT], [0.965, 0.965], color=RULE, lw=0.6)
            ax.text(RIGHT, 0.972, f"{self.page_no}", fontsize=7.5,
                    color=MUTE, ha="right")
            ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        self.y = TOP - 0.03

    def close_page(self):
        if self.fig is not None:
            self.pdf.savefig(self.fig)
            self.fig = None

    def _ax(self):
        ax = self.fig.add_axes([0, 0, 1, 1]); ax.axis("off")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        return ax

    def _room(self, need):
        if self.y - need < 0.06:
            self.new_page()

    # -- content blocks ---------------------------------------------------
    def h1(self, text):
        self._room(0.075)
        ax = self._ax()
        ax.text(LEFT, self.y, text, fontsize=19, weight="bold", color=INK,
                va="top")
        self.y -= 0.030
        ax.plot([LEFT, RIGHT], [self.y, self.y], color=ACCENT, lw=1.6)
        self.y -= 0.022

    def h2(self, text):
        self._room(0.055)
        ax = self._ax()
        ax.text(LEFT, self.y, text, fontsize=13, weight="bold", color=INK,
                va="top")
        self.y -= 0.030

    def para(self, text, size=9.6, color=BODY, indent=0.0, wrap=104):
        for line in textwrap.wrap(" ".join(text.split()), wrap) or [""]:
            self._room(0.020)
            ax = self._ax()
            ax.text(LEFT + indent, self.y, line, fontsize=size, color=color,
                    va="top")
            self.y -= 0.0165
        self.y -= 0.008

    def bullet(self, text, size=9.4, wrap=96):
        lines = textwrap.wrap(" ".join(text.split()), wrap) or [""]
        for i, line in enumerate(lines):
            self._room(0.020)
            ax = self._ax()
            if i == 0:
                ax.text(LEFT + 0.012, self.y, "•", fontsize=size, color=ACCENT,
                        va="top", weight="bold")
            ax.text(LEFT + 0.032, self.y, line, fontsize=size, color=BODY,
                    va="top")
            self.y -= 0.0162
        self.y -= 0.004

    def kv(self, key, val, size=9.2, wrap=74):
        """A labelled setting: bold key on the left, description on the right."""
        lines = textwrap.wrap(" ".join(val.split()), wrap) or [""]
        for i, line in enumerate(lines):
            self._room(0.020)
            ax = self._ax()
            if i == 0:
                ax.text(LEFT + 0.012, self.y, key, fontsize=size, color=INK,
                        va="top", weight="bold")
            ax.text(LEFT + 0.30, self.y, line, fontsize=size, color=BODY, va="top")
            self.y -= 0.0160
        self.y -= 0.004

    def code(self, lines, size=8.6):
        if isinstance(lines, str):
            lines = lines.strip("\n").split("\n")
        h = 0.0168 * len(lines) + 0.016
        self._room(h + 0.01)
        ax = self._ax()
        ax.add_patch(matplotlib.patches.Rectangle(
            (LEFT, self.y - h + 0.004), RIGHT - LEFT, h,
            facecolor=CODE_BG, edgecolor=RULE, lw=0.6))
        yy = self.y - 0.014
        for ln in lines:
            ax.text(LEFT + 0.012, yy, ln, fontsize=size, color="#1c3a5e",
                    va="top", family="monospace")
            yy -= 0.0168
        self.y -= h + 0.010

    def note(self, text, size=9.0, kind="note"):
        colors = {"note": ("#eaf2ff", ACCENT), "warn": ("#fff4e5", "#c77700")}
        bg, edge = colors.get(kind, colors["note"])
        lines = textwrap.wrap(" ".join(text.split()), 96) or [""]
        h = 0.0165 * len(lines) + 0.018
        self._room(h + 0.01)
        ax = self._ax()
        ax.add_patch(matplotlib.patches.Rectangle(
            (LEFT, self.y - h + 0.004), RIGHT - LEFT, h,
            facecolor=bg, edgecolor=edge, lw=0.8))
        yy = self.y - 0.015
        for ln in lines:
            ax.text(LEFT + 0.014, yy, ln, fontsize=size, color=BODY, va="top")
            yy -= 0.0165
        self.y -= h + 0.010

    def image(self, path, height=0.30, caption=None):
        if not os.path.isfile(path):
            return
        need = height + (0.022 if caption else 0.010)
        self._room(need)
        try:
            img = mpimg.imread(path)
        except Exception:
            return
        ih, iw = img.shape[0], img.shape[1]
        page_ar = PAGE[0] / PAGE[1]
        # width (fig fraction) that preserves aspect at the requested height
        w = height * (iw / ih) * (PAGE[1] / PAGE[0]) * page_ar / page_ar
        w = height * (iw / ih) / (PAGE[0] / PAGE[1])
        w = min(w, RIGHT - LEFT)
        h = w * (ih / iw) * (PAGE[0] / PAGE[1])
        x = LEFT + (RIGHT - LEFT - w) / 2
        ax = self.fig.add_axes([x, self.y - h, w, h])
        ax.imshow(img); ax.axis("off")
        self.y -= h + 0.006
        if caption:
            cax = self._ax()
            cax.text(0.5, self.y, caption, fontsize=8.2, color=MUTE,
                     ha="center", va="top", style="italic")
            self.y -= 0.020


def build(out_path, figdir):
    import matplotlib.patches  # noqa: F401  (used via matplotlib.patches)

    with PdfPages(out_path) as pdf:
        m = Manual(pdf)

        # ---------------------------------------------------------- cover
        m.new_page(first=True)
        ax = m._ax()
        ax.add_patch(matplotlib.patches.Rectangle((0, 0.80), 1, 0.20,
                                                  facecolor="#12324f"))
        ax.text(0.5, 0.90, "EBSD ODF Analyzer", fontsize=32, weight="bold",
                color="white", ha="center", va="center")
        ax.text(0.5, 0.855, "Microstructure and crystallographic texture from EBSD scans",
                fontsize=11.5, color="#b9cbe0", ha="center", va="center")
        ax.text(0.5, 0.72, "User Manual", fontsize=20, color=INK, ha="center",
                weight="bold")
        ax.text(0.5, 0.685, "Version 1.0", fontsize=11, color=MUTE, ha="center")
        for i, (t, s) in enumerate([
            ("Multi-format input", ".ang (TSL text), .osc (EDAX binary), .ctf / h5ebsd"),
            ("Microstructure", "IQ / CI / IPF maps, configurable boundaries,\nASTM E2627 grain size"),
            ("Texture", "ODF (kernel or harmonic),\nphi2 sections, alpha / gamma fibers"),
            ("Multiphase", "per-phase symmetry, per-phase ODF, phase boundaries"),
            ("Export", "PowerPoint report with selectable content"),
        ]):
            y = 0.60 - i * 0.046
            ax.text(0.14, y, t, fontsize=10.5, weight="bold", color=INK, va="center")
            ax.text(0.36, y, s, fontsize=9.4, color=BODY, va="center",
                    linespacing=1.5)

        # ------------------------------------------------------ 1 overview
        m.new_page()
        m.h1("1  Overview")
        m.para("EBSD ODF Analyzer turns an indexed EBSD scan into a complete "
               "microstructure and texture analysis, then exports the result as a "
               "PowerPoint report. It is a desktop application: you move through "
               "five steps in order, adjusting parameters in the left sidebar and "
               "inspecting results on the right.")
        m.h2("The five steps")
        m.kv("1  Load & Resample", "Read the scan file and resample the hexagonal "
             "measurement grid onto a square pixel grid.")
        m.kv("2  Microstructure", "Orientations, misorientations, IQ / CI / IPF maps, "
             "grain-boundary classes and grain segmentation.")
        m.kv("3  Grain Size", "Grain-size distributions and the ASTM E2627 grain-size "
             "number G.")
        m.kv("4  Texture (ODF)", "Orientation distribution function, phi2 sections and "
             "alpha / gamma fiber profiles.")
        m.kv("5  Report", "Export the selected results to a PowerPoint file.")
        m.h2("Supported input formats")
        m.kv(".ang", "TSL / EDAX text export. Euler angles in radians (Bunge).")
        m.kv(".osc", "EDAX OIM binary. Read natively — no external converter needed.")
        m.kv(".ctf, .h5, .oh5", "Read through orix (HKL / h5ebsd family).")
        m.note("Crystal symmetry and the phase list are read from the file header "
               "automatically. If a file carries no symmetry, the app falls back to "
               "m-3m (cubic) and writes a warning to the log.")

        # ------------------------------------------------- 2 installation
        m.h1("2  Installation and launch")
        m.h2("Option A — standalone executable (no install)")
        m.para("Copy the EBSD_Analyzer folder anywhere and run EBSD_Analyzer.exe. "
               "Everything needed is bundled; Python does not have to be installed.")
        m.code(["standalone_exe_new/",
                "  EBSD_Analyzer/",
                "    EBSD_Analyzer.exe      <- double-click this",
                "    _internal/ ...         <- bundled libraries (do not delete)"])
        m.h2("Option B — reproducible environment with pixi")
        m.para("pixi builds the exact, locked dependency set from conda-forge only, so "
               "no Anaconda licence is required.")
        m.code(["cd standalone_ebsd",
                "pixi install        # create the locked environment",
                "pixi run app        # launch the GUI"])
        m.h2("Verifying an installation")
        m.para("Both forms accept a headless self-test that runs the whole pipeline "
               "(both ODF engines, grain segmentation, a multiphase check and a "
               "PowerPoint export) and prints a pass or fail line.")
        m.code(["EBSD_Analyzer.exe --selftest        # frozen build",
                "pixi run python app.py --selftest   # pixi environment"])

        # -------------------------------------------------- 3 step 1
        m.new_page()
        m.h1("3  Step 1 — Load & Resample")
        m.para("Choose the scan file, then press Run. The scan's hexagonal grid is "
               "resampled onto a square grid by nearest-neighbour lookup so that all "
               "later image operations work on regular pixels.")
        m.h2("Settings")
        m.kv("Scan file", "Path to the scan. The Browse dialog lists every "
             "supported format by default (.ang, .osc, .ctf, .h5 / .oh5 / "
             ".hdf5 / .dream3d), with per-format filters available.")
        m.kv("Grid ratio", "Square pixel size as a multiple of the hex step. 1.0 keeps "
             "the native resolution; larger values downsample.")
        m.kv("Sample-frame rotation", "Optional rotation about ND, RD or TD applied "
             "before texture analysis.")
        m.kv("Column indices (advanced)", "Override the column order if a file "
             "deviates from the standard TSL layout.")
        m.h2("Choosing what goes into the report")
        m.para("The right-hand panel lists every item that can be placed in the "
               "PowerPoint export. Ticked items are shown in bold. The selection and "
               "all option values can be stored as a preset:")
        m.kv("Save preset…", "Write the current selection and every parameter value to "
             "a JSON file.")
        m.kv("Load preset…", "Restore a saved setup. Presets deliberately do not store "
             "the scan path, so one preset can be reused across datasets.")
        m.note("Preset files are plain JSON and can be edited by hand — useful for "
               "sharing a standard analysis recipe across a group.")

        # -------------------------------------------------- 4 step 2
        m.new_page()
        m.h1("4  Step 2 — Microstructure")
        m.para("This step computes orientations, neighbour misorientations, the "
               "orientation and quality maps, grain-boundary classes, and the grain "
               "segmentation used later for grain size.")
        m.image(os.path.join(figdir, "ex_ipf.png"), height=0.20,
                caption="IPF [001] map — TSL colour key and OIM micron marker")
        m.h2("Key settings")
        m.kv("Crystal symmetry", "'(from data)' reads the point group from the file "
             "header. Choose a value explicitly to override it.")
        m.kv("Maps to show", "Any combination of IQ, CI, IPF [100] / [010] / [001], a "
             "custom IPF direction, boundary map, IPF+boundaries, grain map and phase "
             "map. Defaults: IQ, CI and the three IPF maps.")
        m.kv("CI map style", "Greyscale (default) or a colour map.")
        m.kv("Overlays", "Independently toggle the intensity legend, the scale bar "
             "and the axis labels. Turning the legend on or off never resizes or "
             "rescales the micrograph — the figure grows instead, so the image "
             "itself is pixel-identical either way.")
        m.kv("CI threshold", "Points with CI below this value are treated as "
             "unindexed and dropped from every downstream calculation.")
        m.kv("Grain-splitting angle", "Misorientation above which neighbouring "
             "pixels belong to different grains. Default 15°. This is set on its "
             "own — it is NOT derived from the boundary classes below.")
        m.kv("Clean low-CI pixels", "Off by default. When on, low-CI pixels adopt "
             "their best-indexed neighbour's orientation (grain dilation).")

        m.h2("How maps are annotated")
        m.para("Micrographs follow the OIM presentation convention. Painted on the "
               "image: the map name, the TSL stereographic-triangle colour key on "
               "IPF maps, and a micron marker — a solid black bar on a white box "
               "with the length and unit printed beneath it. The intensity legend "
               "for scalar maps (IQ, CI) is drawn in a strip BELOW the image, never "
               "over the data.")

        # ------------------------------------------- boundaries page
        m.new_page()
        m.h2("Grain-boundary display classes")
        m.para("Boundaries are not fixed to a single low/high pair. You choose how "
               "many classes to define, and each class has its own angular range, "
               "colour and line thickness. These control DISPLAY only.")
        m.kv("Count", "Number of boundary classes (1 to 6).")
        m.kv("name", "Label used in map legends, e.g. LAGB or HAGB.")
        m.kv("from lo°  /  to hi°", "A boundary is drawn where "
             "lo° <= misorientation < hi°. The range is closed at the low end and "
             "open at the high end, so adjacent classes never double-count a segment.")
        m.kv("colour / width", "Line colour and thickness for that class on every map "
             "that draws boundaries.")
        m.note("Adding or editing a display class never changes the grain count. "
               "Grains are split by the separate 'Grain-splitting angle' setting "
               "(default 15°). Defaults here are LAGB 2–15° and HAGB 15–180°.")
        m.image(os.path.join(figdir, "ex_gb.png"), height=0.19,
                caption="Boundary map — each configured class drawn in its own colour and thickness")

        # -------------------------------------------------- multiphase
        m.h1("5  Multiphase scans")
        m.para("When the file header declares more than one phase, every stage becomes "
               "phase-aware:")
        m.bullet("Each phase keeps its own crystal symmetry; IPF colouring uses the "
                 "symmetry of the phase that each pixel belongs to.")
        m.bullet("Misorientation is only computed between neighbours of the same "
                 "phase. A boundary between two different phases is treated as a "
                 "grain boundary, so grains never span a phase change.")
        m.bullet("A separate ODF is computed for each phase, each with its own "
                 "texture index J, phi2 sections and fiber profiles.")
        m.bullet("A phase map is added to the results automatically.")
        m.note("Two phases can share a point group and still be different phases — "
               "FCC and BCC are both cubic m-3m and are distinguished by their "
               "lattice parameters, which the reader also extracts.")
        m.image(os.path.join(figdir, "ex_phase.png"), height=0.17,
                caption="Phase map of a two-phase scan (ferrite + silver)")

        # -------------------------------------------------- step 3 & 4
        m.new_page()
        m.h1("6  Step 3 — Grain Size")
        m.para("Grains come from a union-find segmentation: neighbouring valid pixels "
               "are merged while their misorientation stays below the grain-splitting "
               "angle set in Step 2 (default 15 deg). Grains smaller than the minimum "
               "pixel count are discarded.")
        m.kv("Histogram bins", "Bin count for the distribution charts.")
        m.kv("Min grain (px)", "Grains below this area are ignored (Step 2 setting).")
        m.kv("Exclude edge grains", "Ignore grains touching the scan border, which are "
             "only partly measured.")
        m.para("Reported quantities include the number-average and area-weighted "
               "equivalent-circle diameters, the mean grain area, the cumulative "
               "area-weighted distribution, and the ASTM E2627 grain-size number G.")

        m.h1("7  Step 4 — Texture (ODF)")
        m.para("The orientation distribution function is estimated with a de la Vallée "
               "Poussin kernel. Two mathematically equivalent engines are available "
               "and agree to within numerical noise.")
        m.kv("kernel", "Direct kernel summation over orientations. Needs only orix.")
        m.kv("harmonic", "Wigner-D / generalised spherical harmonic series. Uses the "
             "spherical and quaternionic packages.")
        m.kv("Kernel halfwidth", "Kernel width in degrees. 10° is the default; "
             "smaller values give sharper, noisier textures.")
        m.kv("Specimen symmetry", "triclinic (none), monoclinic, or orthorhombic — "
             "orthorhombic folds the ODF about RD, TD and ND.")
        m.kv("N sample", "Number of orientations sampled for speed. Increase for a "
             "smoother ODF at the cost of runtime.")
        m.kv("phi2 sections", "Which constant-phi2 slices to plot.")
        m.para("Results include the texture index J (J = 1 for a random texture), the "
               "phi2 section maps in multiples of a random distribution, and the "
               "alpha and gamma fiber intensity profiles.")
        m.image(os.path.join(figdir, "ex_odf.png"), height=0.22,
                caption="ODF phi2 sections with ideal component markers and fiber traces")

        # -------------------------------------------------- step 5 + ref
        m.new_page()
        m.h1("8  Step 5 — Report")
        m.para("Exports the analysis to a PowerPoint file. Content follows the "
               "selection made in Step 1.")
        m.kv("Report contents", "All results, microstructure only, or texture only.")
        m.kv("Output file", "Destination .pptx path.")
        m.kv("Slide size / DPI", "Slide geometry in inches and the raster resolution "
             "of embedded figures.")

        m.h1("9  Troubleshooting")
        m.kv("Wrong or odd IPF colours", "Check the crystal symmetry in Step 2. If the "
             "header was missing, the app defaults to m-3m and logs a warning.")
        m.kv("Too few or too many grains", "Adjust the Grain-splitting angle in "
             "Step 2, the CI threshold and the minimum grain size. Adding boundary "
             "display classes does not affect the grain count.")
        m.kv("Speckled maps", "Raise the CI threshold, or enable 'Clean low-CI pixels' "
             "to fill unindexed points from their neighbours.")
        m.kv("ODF looks noisy", "Increase N sample or the kernel halfwidth.")
        m.kv("Texture index J near 1", "The material is nearly randomly oriented; this "
             "is a result, not an error.")
        m.kv("Application will not start", "Run the self-test from a terminal "
             "(--selftest) to see which component fails.")

        m.h1("10  Reference — file layout")
        m.code(["standalone_ebsd/",
                "  app.py               GUI entry point",
                "  worker.py            background pipeline thread",
                "  pixi.toml            locked dependency definition",
                "  ebsd_engine/",
                "    ebsd_read.py       multi-format reader (.ang/.osc/orix)",
                "    config.py          all settings (Config dataclass)",
                "    microstructure.py  load, misorientation, grains, grain size",
                "    odf.py             ODF engines (kernel / harmonic)",
                "    plotting.py        figure builders",
                "    report.py          PowerPoint builder",
                "  ui/                  GUI widgets, steps and theme",
                "  packaging/           build helpers and this manual generator"])

        m.close_page()

    return out_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(os.path.dirname(here), "EBSD_Analyzer_Manual.pdf")
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default=default_out)
    ap.add_argument("--figdir", default=os.path.join(os.path.dirname(here),
                                                     "..", "scratch_manual"))
    a = ap.parse_args()
    p = build(a.output, os.path.abspath(a.figdir))
    print(f"manual written: {p}  ({os.path.getsize(p):,} bytes)")
