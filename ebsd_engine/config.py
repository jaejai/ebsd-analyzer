"""Configuration for the EBSD + ODF analysis pipeline.

Mirrors the `## 1 — Configuration` cell of EBSD_ODF_combined.ipynb, but as a
dataclass so the GUI / CLI can drive it instead of editing module globals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # --- Data ----------------------------------------------------------------
    ang_file: str = ""
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
    crystal_sym: str = "m-3m"          # DP590 ferrite, cubic
    ipf_dir: tuple = (0, 0, 1)
    lagb_angle: float = 2.0
    hagb_angle: float = 15.0
    ci_threshold: float = 0.1
    min_grain_px: int = 5
    low_ci_fill: float = 0.15          # grey level for sub-threshold CI pixels (IPF)
    connectivity: int = 4              # grain neighbour connectivity: 4 (notebook) or 8
    ci_mask: bool = True               # neighbour-fill low-CI pixels (CI<ci_threshold)
                                       # before misorientation/segmentation/grain size.
                                       # True = clean noisy scans; False = raw notebook.

    # --- Grain size (advanced) ----------------------------------------------
    hist_bins: int = 40
    astm_c1: float = -3.321928         # ASTM E2627 G = C1*log10(A_mm2) + C2
    astm_c2: float = -2.954
    exclude_edge_grains: bool = False

    # --- ODF / texture params ------------------------------------------------
    lattice: str = "BCC"               # "FCC" or "BCC" — reference components
    l_max: int = 8                     # GSH bandwidth
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
    report_title: str = "DP590_Initial"

    # --- Reproducibility -----------------------------------------------------
    seed: int = 42

    @property
    def dir_str(self) -> str:
        return "".join(str(int(v)) for v in self.ipf_dir)
