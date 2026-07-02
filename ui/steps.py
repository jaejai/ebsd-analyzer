"""Per-step parameter panels and result panes, faithful to the .dc.html mockup.

Each step has:
  - build_step_controls(win, n) -> (page_widget, ctrls_dict)
  - build_step_results(win, n)  -> (page_widget, refs_dict)
read_all_controls(win) -> Config  reads every control into a fresh Config.

Widget refs are stored on `win.step_ctrls[n-1]` so read_all_controls can find
them regardless of which step is visible.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox,
    QFileDialog, QFrame, QSizePolicy, QPlainTextEdit,
)

from ebsd_engine import Config
from .widgets import (SectionLabel, SegGroup, ChipButton, Card, FigurePane,
                      StatCard, ParamLabel)


# ---------------------------------------------------------------- small helpers
def _row(label, w):
    box = QVBoxLayout(); box.setSpacing(4); box.setContentsMargins(0, 0, 0, 0)
    lab = ParamLabel(label.upper()); box.addWidget(lab); box.addWidget(w)
    cont = QWidget(); cont.setObjectName("RowCont"); cont.setLayout(box)
    return cont


def _adv_header(ctrls):
    """An 'Advanced' toggle that shows/hides ctrls['adv_body']."""
    btn = QPushButton("▶  ADVANCED"); btn.setObjectName("AdvToggle"); btn.setCheckable(True)
    btn.setStyleSheet("text-align:left; border:none; background:transparent; color:#9fc3ff;"
                      "font-family:Consolas; font-size:11px; font-weight:800; letter-spacing:1px; padding:8px 2px;")
    body = QWidget(); body.setVisible(False)
    def toggle():
        body.setVisible(btn.isChecked())
        btn.setText(("▼  ADVANCED") if btn.isChecked() else ("▶  ADVANCED"))
    btn.clicked.connect(toggle)
    ctrls["adv_body"] = body
    return btn, body


def _dsb(lo, hi, val, step=1.0, dec=2):
    s = QDoubleSpinBox(); s.setRange(lo, hi); s.setValue(val); s.setSingleStep(step); s.setDecimals(dec); return s


def _sb(lo, hi, val, step=1):
    s = QSpinBox(); s.setRange(lo, hi); s.setValue(val); s.setSingleStep(step); return s


# ================================================================= CONTROLS
def build_step_controls(win, n):
    page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0, 6, 0, 0); lay.setSpacing(13)
    ctrls = {}
    d = Config()  # defaults

    if n == 1:
        # file picker
        ang = QLineEdit(); ang.setPlaceholderText("Select a .ang file ...")
        browse = QPushButton("Browse"); browse.setObjectName("BrowseBtn")
        def pick():
            import os
            start = os.path.join(win.__class__.__module__ and "", "")
            from app import ROOT
            sd = os.path.join(ROOT, "dp_data")
            sd = sd if os.path.isdir(sd) else ROOT
            p, _ = QFileDialog.getOpenFileName(win, "Open .ang", sd, "ANG files (*.ang);;All files (*)")
            if p:
                ang.setText(p); win.file_chip.setText(os.path.basename(p))
        browse.clicked.connect(pick)
        fr = QHBoxLayout(); fr.setSpacing(7); fr.addWidget(ang, 1); fr.addWidget(browse)
        fw = QWidget(); fw.setLayout(fr)
        lay.addWidget(_row(".ang file", fw)); ctrls["ang"] = ang

        ctrls["grid_ratio"] = _dsb(0.2, 4.0, d.grid_ratio, 0.1, 2)
        lay.addWidget(_row("Grid ratio (hex→square)", ctrls["grid_ratio"]))

        rot = SegGroup([("None", "None"), ("ND", "ND"), ("RD", "RD"), ("TD", "TD")], default="None")
        ctrls["rotate_axis"] = rot
        ctrls["rotate_angle"] = _dsb(-360, 360, d.rotate_angle, 5, 1)
        rr = QHBoxLayout(); rr.addWidget(rot, 2); rr.addWidget(ctrls["rotate_angle"], 1)
        rw = QWidget(); rw.setLayout(rr)
        lay.addWidget(_row("Sample-frame rotation", rw))

        # advanced
        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        # column mapping grid
        cols = [("φ₁", "col_phi1"), ("φ", "col_phi"), ("φ₂", "col_phi2"), ("X", "col_x"), ("Y", "col_y"),
                ("IQ", "col_iq"), ("CI", "col_ci"), ("Phase", "col_phase"), ("SEM", "col_sem"), ("Fit", "col_fit")]
        grid = QGridLayout(); grid.setSpacing(5)
        for i, (name, key) in enumerate(cols):
            sb = _sb(0, 50, getattr(d, key)); sb.setFixedWidth(58)
            cell = QVBoxLayout(); cell.setSpacing(2)
            lb = ParamLabel(name); lb.setAlignment(Qt.AlignCenter); cell.addWidget(lb); cell.addWidget(sb)
            cw = QWidget(); cw.setLayout(cell)
            grid.addWidget(cw, i // 5, i % 5); ctrls[key] = sb
        gw = QWidget(); gw.setLayout(grid); av.addWidget(_row("Column indices (0-based)", gw))
        ctrls["euler_unit"] = SegGroup([("rad", "rad"), ("deg", "deg")], default=d.euler_unit)
        ctrls["comment_char"] = QLineEdit(d.comment_char); ctrls["comment_char"].setFixedWidth(50)
        er = QHBoxLayout(); er.addWidget(_row("Euler unit", ctrls["euler_unit"]), 1); er.addWidget(_row("Comment char", ctrls["comment_char"]))
        ew = QWidget(); ew.setLayout(er); av.addWidget(ew)

    elif n == 2:
        ctrls["crystal_sym"] = QComboBox(); ctrls["crystal_sym"].addItems(["m-3m", "432", "m-3", "6/mmm", "4/mmm"])
        ctrls["crystal_sym"].setCurrentText(d.crystal_sym)
        lay.addWidget(_row("Crystal symmetry", ctrls["crystal_sym"]))
        ctrls["ipf_dir"] = SegGroup([("ND", "ND [001]"), ("RD", "RD [100]"), ("TD", "TD [010]")], default="ND")
        lay.addWidget(_row("IPF reference direction", ctrls["ipf_dir"]))
        ctrls["lagb_angle"] = _dsb(0.5, 30, d.lagb_angle, 0.5, 1)
        ctrls["hagb_angle"] = _dsb(1, 180, d.hagb_angle, 1, 1)
        gr = QHBoxLayout(); gr.addWidget(_row("LAGB ≥ °", ctrls["lagb_angle"])); gr.addWidget(_row("HAGB ≥ °", ctrls["hagb_angle"]))
        gw = QWidget(); gw.setLayout(gr); lay.addWidget(gw)
        ctrls["ci_threshold"] = _dsb(0, 1, d.ci_threshold, 0.05, 2)
        ctrls["min_grain_px"] = _sb(1, 1000, d.min_grain_px)
        cr = QHBoxLayout(); cr.addWidget(_row("CI threshold", ctrls["ci_threshold"])); cr.addWidget(_row("Min grain (px)", ctrls["min_grain_px"]))
        cw = QWidget(); cw.setLayout(cr); lay.addWidget(cw)
        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        # custom IPF [hkl]
        h1, h2, h3 = _sb(-9, 9, 0), _sb(-9, 9, 0), _sb(-9, 9, 1)
        hr = QHBoxLayout(); [hr.addWidget(x) for x in (h1, h2, h3)]
        hw = QWidget(); hw.setLayout(hr); av.addWidget(_row("Custom IPF direction [h k l]", hw))
        ctrls["hkl"] = (h1, h2, h3)
        ctrls["low_ci_fill"] = _dsb(0, 1, d.low_ci_fill, 0.05, 2)
        ctrls["seed"] = _sb(0, 999999, d.seed)
        sr = QHBoxLayout(); sr.addWidget(_row("Low-CI fill", ctrls["low_ci_fill"])); sr.addWidget(_row("Grain seed", ctrls["seed"]))
        sw = QWidget(); sw.setLayout(sr); av.addWidget(sw)
        ctrls["connectivity"] = SegGroup([("4", "4-neigh"), ("8", "8-neigh")], default=str(d.connectivity))
        av.addWidget(_row("Grain connectivity", ctrls["connectivity"]))
        ctrls["ci_mask"] = QCheckBox("Clean low-CI pixels (neighbour-fill)")
        ctrls["ci_mask"].setChecked(d.ci_mask)
        ctrls["ci_mask"].setStyleSheet("color:#e3eaf3; font-size:12px;")
        av.addWidget(ctrls["ci_mask"])

    elif n == 3:
        ctrls["standard"] = QComboBox(); ctrls["standard"].addItems(["ASTM E2627 · planimetric", "ASTM E112 · intercept"])
        lay.addWidget(_row("Grain-size standard", ctrls["standard"]))
        ctrls["hist_bins"] = _sb(5, 200, d.hist_bins)
        lay.addWidget(_row("Histogram bins", ctrls["hist_bins"]))
        info = QLabel("Equivalent-circle ⌀ = √(4A/π)"); info.setStyleSheet("color:#cdd8e6;font-family:Consolas;font-size:11px;background:transparent;")
        lay.addWidget(_row("Diameter measure", info))
        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        ctrls["astm_c1"] = _dsb(-10, 10, d.astm_c1, 0.001, 6)
        ctrls["astm_c2"] = _dsb(-10, 10, d.astm_c2, 0.001, 3)
        ar = QHBoxLayout(); ar.addWidget(_row("ASTM C₁", ctrls["astm_c1"])); ar.addWidget(_row("ASTM C₂", ctrls["astm_c2"]))
        aw = QWidget(); aw.setLayout(ar); av.addWidget(aw)
        ctrls["exclude_edge"] = QCheckBox("Exclude edge grains"); ctrls["exclude_edge"].setChecked(d.exclude_edge_grains)
        ctrls["exclude_edge"].setStyleSheet("color:#e3eaf3; font-size:12px;")
        av.addWidget(ctrls["exclude_edge"])

    elif n == 4:
        ctrls["lattice"] = SegGroup([("BCC", "BCC"), ("FCC", "FCC")], default=d.lattice)
        lay.addWidget(_row("Lattice / reference set", ctrls["lattice"]))
        ctrls["l_max"] = _sb(4, 16, d.l_max, 2)
        lay.addWidget(_row("GSH bandwidth L_max", ctrls["l_max"]))
        ctrls["n_sample"] = _sb(1000, 500000, d.n_sample, 1000)
        ctrls["section_step"] = _dsb(1, 15, d.section_step, 1, 1)
        nr = QHBoxLayout(); nr.addWidget(_row("N sample", ctrls["n_sample"]), 2); nr.addWidget(_row("Step °", ctrls["section_step"]), 1)
        nw = QWidget(); nw.setLayout(nr); lay.addWidget(nw)
        # phi2 chips
        chips = QHBoxLayout(); chips.setSpacing(5); ctrls["phi2"] = {}
        for s in (0, 15, 30, 45, 60, 75, 90):
            c = ChipButton(f"{s}°", checked=True); chips.addWidget(c); ctrls["phi2"][s] = c
        chips.addStretch(1); cw = QWidget(); cw.setLayout(chips); lay.addWidget(_row("φ₂ sections", cw))
        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        ctrls["odf_cmap"] = SegGroup([("jet", "jet"), ("viridis", "viridis")], default=d.odf_cmap)
        av.addWidget(_row("ODF colormap", ctrls["odf_cmap"]))
        ctrls["vmax_auto"] = QCheckBox("Auto color-scale max"); ctrls["vmax_auto"].setChecked(True)
        ctrls["vmax_auto"].setStyleSheet("color:#e3eaf3; font-size:12px;")
        ctrls["odf_vmax"] = _dsb(1, 100, 7.0, 0.5, 1)
        vr = QHBoxLayout(); vr.addWidget(ctrls["vmax_auto"]); vr.addWidget(ctrls["odf_vmax"])
        vw = QWidget(); vw.setLayout(vr); av.addWidget(_row("Color scale max (mrd)", vw))

    elif n == 5:
        ctrls["report_mode"] = QComboBox()
        ctrls["report_mode"].addItems(["All results (micro + texture)", "Microstructure only", "Texture only"])
        lay.addWidget(_row("Report contents", ctrls["report_mode"]))
        ctrls["outfile"] = QLineEdit(d.report_outfile)
        lay.addWidget(_row("Output file", ctrls["outfile"]))
        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        ctrls["slide_w"] = _dsb(5, 40, d.slide_w_in, 0.1, 2)
        ctrls["slide_h"] = _dsb(3, 30, d.slide_h_in, 0.1, 2)
        sr = QHBoxLayout(); sr.addWidget(_row("Slide W (in)", ctrls["slide_w"])); sr.addWidget(_row("Slide H (in)", ctrls["slide_h"]))
        sw = QWidget(); sw.setLayout(sr); av.addWidget(sw)
        ctrls["dpi"] = _sb(72, 600, d.fig_dpi)
        ctrls["title"] = QLineEdit(d.report_title)
        dr = QHBoxLayout(); dr.addWidget(_row("Figure DPI", ctrls["dpi"])); dr.addWidget(_row("Title", ctrls["title"]))
        dw = QWidget(); dw.setLayout(dr); av.addWidget(dw)

    lay.addStretch(1)
    return page, ctrls


def _divider():
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setStyleSheet("color:rgba(255,255,255,0.07);"); return f


# ================================================================= RESULTS
def build_step_results(win, n):
    page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(26, 8, 26, 26); lay.setSpacing(14)
    refs = {}

    if n == 1:
        cards = QHBoxLayout(); cards.setSpacing(13)
        refs["pts"] = StatCard("Points loaded"); refs["grid"] = StatCard("Square grid")
        refs["step"] = StatCard("Step size"); refs["extent"] = StatCard("Scan extent")
        for c in (refs["pts"], refs["grid"], refs["step"], refs["extent"]):
            cards.addWidget(c)
        cards.addStretch(1); cw = QWidget(); cw.setLayout(cards); lay.addWidget(cw)
        refs["phase"] = FigurePane("Phase / IQ map", min_h=320)
        refs["phase"].setMaximumWidth(360)
        lay.addWidget(refs["phase"], alignment=Qt.AlignLeft)

    elif n == 2:
        grid = QGridLayout(); grid.setSpacing(13)
        specs = [("iq", "Image Quality (IQ)"), ("ci", "Confidence Index (CI)"), ("ipf", "IPF Map [001]"),
                 ("gb", "Grain Boundaries"), ("ipfgb", "IPF + HAGB"), ("grain", "Grain Map")]
        from PySide6.QtWidgets import QSizePolicy as _SP
        for i, (key, title) in enumerate(specs):
            fp = FigurePane(title, min_h=420); refs[key] = fp
            # ignore the figure's natural width so every card fills its grid
            # column equally (colorbar maps no longer end up a different width)
            fp.setSizePolicy(_SP.Ignored, _SP.Preferred)
            grid.addWidget(fp, i // 3, i % 3)
        for col in range(3):
            grid.setColumnStretch(col, 1)
        gw = QWidget(); gw.setLayout(grid); lay.addWidget(gw)

    elif n == 3:
        cards = QHBoxLayout(); cards.setSpacing(11)
        refs["c_grains"] = StatCard("Grains ≥ min"); refs["c_astm"] = StatCard("ASTM E2627 G")
        refs["c_dnum"] = StatCard("Number-avg ⌀"); refs["c_dw"] = StatCard("Area-wt ⌀")
        for c in (refs["c_grains"], refs["c_astm"], refs["c_dnum"], refs["c_dw"]):
            cards.addWidget(c)
        cards.addStretch(1); cw = QWidget(); cw.setLayout(cards); lay.addWidget(cw)
        refs["count"] = FigurePane("Count distribution", min_h=230); lay.addWidget(refs["count"])
        refs["frac"] = FigurePane("Area-weighted distribution", min_h=230); lay.addWidget(refs["frac"])

    elif n == 4:
        cards = QHBoxLayout(); cards.setSpacing(11)
        refs["c_j"] = StatCard("Texture J", accent=True); refs["c_max"] = StatCard("ODF max")
        refs["c_amax"] = StatCard("α-fiber max"); refs["c_gmax"] = StatCard("γ-fiber max")
        for c in (refs["c_j"], refs["c_max"], refs["c_amax"], refs["c_gmax"]):
            cards.addWidget(c)
        cards.addStretch(1); cw = QWidget(); cw.setLayout(cards); lay.addWidget(cw)
        refs["sections"] = FigurePane("ODF φ₂ sections — f(g) [mrd]", min_h=300); lay.addWidget(refs["sections"])
        refs["fibers"] = FigurePane("Fiber intensity profiles", min_h=240); lay.addWidget(refs["fibers"])

    elif n == 5:
        info = QLabel("Configure the report in the sidebar, then click Export PowerPoint (or Run · Report).")
        info.setStyleSheet("color:#69737f;font-size:13px;")
        lay.addWidget(info)
        exp = QPushButton("⬇  Export PowerPoint"); exp.setObjectName("RunBtn"); exp.setMaximumWidth(240)
        exp.clicked.connect(win.export_report); lay.addWidget(exp)

    # shared log pane on every step
    log = QPlainTextEdit(); log.setReadOnly(True); log.setObjectName("LogView")
    log.setMaximumBlockCount(3000); log.setMinimumHeight(120); log.setMaximumHeight(170)
    lay.addWidget(QLabel("Log")); lay.addWidget(log)
    refs["log"] = log

    lay.addStretch(1)
    return page, refs


# ================================================================= READ CONFIG
def read_all_controls(win) -> Config:
    c = win.step_ctrls
    cfg = Config()
    s1, s2, s3, s4, s5 = c[0], c[1], c[2], c[3], c[4]

    # step 1
    cfg.ang_file = s1["ang"].text().strip()
    cfg.grid_ratio = s1["grid_ratio"].value()
    ra = s1["rotate_axis"].value(); cfg.rotate_axis = None if ra == "None" else ra
    cfg.rotate_angle = s1["rotate_angle"].value()
    for key in ("col_phi1", "col_phi", "col_phi2", "col_x", "col_y", "col_iq", "col_ci", "col_phase", "col_sem", "col_fit"):
        if key in s1:
            setattr(cfg, key, s1[key].value())
    if "euler_unit" in s1:
        cfg.euler_unit = s1["euler_unit"].value() or "rad"
    if "comment_char" in s1:
        cfg.comment_char = s1["comment_char"].text() or "#"

    # step 2
    cfg.crystal_sym = s2["crystal_sym"].currentText()
    ipf = s2["ipf_dir"].value()
    if "hkl" in s2 and any(w.value() for w in s2["hkl"]) and s2["adv_body"].isVisible():
        cfg.ipf_dir = tuple(w.value() for w in s2["hkl"])
    else:
        cfg.ipf_dir = {"ND": (0, 0, 1), "RD": (1, 0, 0), "TD": (0, 1, 0)}[ipf]
    cfg.lagb_angle = s2["lagb_angle"].value()
    cfg.hagb_angle = s2["hagb_angle"].value()
    cfg.ci_threshold = s2["ci_threshold"].value()
    cfg.min_grain_px = s2["min_grain_px"].value()
    if "low_ci_fill" in s2:
        cfg.low_ci_fill = s2["low_ci_fill"].value()
    if "seed" in s2:
        cfg.seed = s2["seed"].value()
    if "connectivity" in s2:
        cfg.connectivity = int(s2["connectivity"].value() or 4)
    if "ci_mask" in s2:
        cfg.ci_mask = s2["ci_mask"].isChecked()

    # step 3
    cfg.hist_bins = s3["hist_bins"].value()
    if "astm_c1" in s3:
        cfg.astm_c1 = s3["astm_c1"].value()
        cfg.astm_c2 = s3["astm_c2"].value()
    if "exclude_edge" in s3:
        cfg.exclude_edge_grains = s3["exclude_edge"].isChecked()

    # step 4
    cfg.lattice = s4["lattice"].value()
    cfg.l_max = s4["l_max"].value()
    cfg.n_sample = s4["n_sample"].value()
    cfg.section_step = s4["section_step"].value()
    cfg.phi2_sections = tuple(s for s, btn in s4["phi2"].items() if btn.isChecked()) or (45,)
    if "odf_cmap" in s4:
        cfg.odf_cmap = s4["odf_cmap"].value()
    if "vmax_auto" in s4:
        cfg.odf_vmax = None if s4["vmax_auto"].isChecked() else s4["odf_vmax"].value()

    # step 5
    mode_map = {0: "all", 1: "ebsd", 2: "odf"}
    cfg.report_mode = mode_map.get(s5["report_mode"].currentIndex(), "all")
    cfg.report_outfile = s5["outfile"].text().strip() or "EBSD_report.pptx"
    if "slide_w" in s5:
        cfg.slide_w_in = s5["slide_w"].value(); cfg.slide_h_in = s5["slide_h"].value()
        cfg.fig_dpi = s5["dpi"].value(); cfg.report_title = s5["title"].text()

    return cfg
