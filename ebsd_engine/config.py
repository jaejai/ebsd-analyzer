"""Configuration for the EBSD + ODF analysis pipeline.

A dataclass so the GUI / CLI can drive the pipeline instead of editing module
globals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # --- Data ----------------------------------------------------------------
    input_file: str = ""               # general multi-format path (.ang/.osc/...)
    ang_file: str = ""                 # backward-compat alias for input_file;
                                       # kept so old callers Config(ang_file=...)
                                       # keep working. Reconciled in __post_init__.
    col_phi1: int = 0
    col_phi: int = 1
    col_phi2: int = 2
    col_x: int = 3
    col_y: int = 4
    col_iq: int = 5
    col_ci: int = 6
    col_phase: int = 7
    col_sem: int = 8
    col_fit: int = 9

    # --- Load (advanced) -----------------------------------------------------
    euler_unit: str = "rad"            # 'rad' (TSL .ang) or 'deg'
    comment_char: str = "#"            # header/comment line prefix in .ang

    # --- Microstructure params ----------------------------------------------
    grid_ratio: float = 1.0
    crystal_sym: Optional[str] = None  # None = auto-detect from file; else manual
                                       # override (e.g. "m-3m" for cubic ferrite)
    ipf_dir: tuple = (0, 0, 1)         # custom IPF direction (advanced); the three
                                       # standard IPF maps [100]/[010]/[001] are
                                       # always available regardless of this.
    ci_threshold: float = 0.1
    min_grain_px: int = 5
    low_ci_fill: float = 0.15          # grey level for sub-threshold CI pixels (IPF)
    connectivity: int = 4              # grain neighbour connectivity: 4 or 8
    ci_mask: bool = False              # neighbour-fill low-CI pixels (CI<ci_threshold)
                                       # before misorientation/segmentation/grain size.
                                       # Default OFF (raw): only turn on to clean
                                       # noisy scans. True = clean; False = raw.

    # --- Grain-boundary definitions -----------------------------------------
    # A list of boundary classes, each drawn on the boundary/IPF maps. Each entry:
    #   {"name","lo","hi","color","width"}  angle range lo<=theta<hi [deg].
    # These are DISPLAY classes only — adding one must never change the grain
    # segmentation. The grain-splitting angle is `grain_angle` below.
    boundaries: list = field(default_factory=lambda: [
        {"name": "LAGB", "lo": 2.0, "hi": 15.0, "color": "blue", "width": 0.4},
        {"name": "HAGB", "lo": 15.0, "hi": 180.0, "color": "black", "width": 0.6},
    ])
    # Misorientation above which neighbouring pixels belong to DIFFERENT grains.
    # Explicit and independent of `boundaries`: defining an extra high-angle
    # display class (e.g. 62-180 deg) previously raised this implicitly and
    # collapsed the whole map into one grain.
    grain_angle: float = 15.0
    # Back-compat scalars; kept in sync in __post_init__ so old code / plots that
    # read lagb_angle / hagb_angle still work.
    lagb_angle: float = 2.0
    hagb_angle: float = 15.0

    # --- Microstructure display options (OIM-style, all optional) -----------
    ci_display: str = "grey"           # CI map: "grey" (default) or "colormap"
    show_colorbar: bool = True         # in-image intensity bar (sunk into corner)
    show_scalebar: bool = True         # in-image micron scale bar
    show_axes_labels: bool = False     # x/y axis ticks+labels (off = clean OIM look)
    scalebar_um: Optional[float] = None  # fixed length [um]; None = auto "nice" value
    # Which maps to display in Step 2 (keys: iq, ci, ipf100, ipf010, ipf001,
    # ipf_custom, gb, ipfgb, grain, phase). Default = CI + 3 IPF + IQ.
    show_maps: tuple = ("iq", "ci", "ipf100", "ipf010", "ipf001")

    # --- PowerPoint content selection (Step 1) ------------------------------
    # Which items go into the report; default = the standard set.
    report_items: tuple = ("iq", "ci", "ipf001", "gb", "grain",
                           "grain_size", "odf", "fibers")

    # --- Grain size (advanced) ----------------------------------------------
    hist_bins: int = 40
    astm_c1: float = -3.321928         # ASTM E2627 G = C1*log10(A_mm2) + C2
    astm_c2: float = -2.954
    exclude_edge_grains: bool = False

    # --- ODF / texture params ------------------------------------------------
    lattice: str = "BCC"               # "FCC" or "BCC" — reference components
    odf_method: str = "kernel"         # de la Vallee Poussin kernel-density ODF.
                                       # Two equivalent engines:
                                       #  "kernel"   = direct sum (orix only).
                                       #  "harmonic" = Wigner-D/GSH series (needs
                                       #               spherical+quaternionic).
                                       # Both f(g)>=0, no ringing, no Phi=pi NaN.
    odf_halfwidth: float = 10.0        # kernel halfwidth [deg], default 10
    sample_sym: str = "triclinic"      # "triclinic"|"monoclinic"|"orthorhombic"
    harmonic_lmax: int = 28            # bandwidth for odf_method="harmonic"
    odf_phase_id: Optional[int] = None # None = all phases; int = restrict ODF to
                                       # that phase id (per-phase ODF).
    n_sample: Optional[int] = 20000    # subsample for ODF speed; None = all
    section_step: float = 5.0          # Euler grid step [deg] for ODF plotting
    phi2_sections: tuple = (0, 15, 30, 45, 60, 75, 90)
    odf_cmap: str = "jet"              # 'jet' or 'viridis'
    odf_vmax: Optional[float] = None   # None = auto (99.5th pct); else fixed mrd

    # Optional sample-frame rotation before ODF (None to skip)
    rotate_axis: Optional[str] = None  # None, 'ND', 'RD', or 'TD'
    rotate_angle: float = 90.0         # degrees

    # --- Report (advanced) ---------------------------------------------------
    report_mode: str = "all"           # 'all' | 'ebsd' | 'odf'
    report_outfile: str = "EBSD_report.pptx"
    slide_w_in: float = 13.333
    slide_h_in: float = 7.5
    fig_dpi: int = 150
    report_title: str = "EBSD Analysis"

    # --- Reproducibility -----------------------------------------------------
    seed: int = 42

    def __post_init__(self):
        # Reconcile the ang_file backward-compat alias with input_file: whichever
        # was supplied wins, and both end up pointing at the same path.
        if not self.input_file and self.ang_file:
            self.input_file = self.ang_file
        elif self.input_file and not self.ang_file:
            self.ang_file = self.input_file
        self.sync_boundaries()

    def sync_boundaries(self):
        """Keep the back-compat scalars consistent with the boundary list.

        `hagb_angle` follows `grain_angle` (the explicit grain-splitting angle),
        NOT the highest display class — deriving it from the classes meant that
        adding, say, a 62-180 deg class silently merged the whole map into one
        grain. `lagb_angle` is just the lowest class bound, used for display.
        """
        if self.boundaries:
            self.lagb_angle = min(b["lo"] for b in self.boundaries)
        self.hagb_angle = self.grain_angle

    @property
    def dir_str(self) -> str:
        return "".join(str(int(v)) for v in self.ipf_dir)
