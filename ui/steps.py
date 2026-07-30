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


def _bold_when_checked(cb):
    """Make a checkbox's label darker+bold while checked, plain grey when not —
    so the selected PowerPoint items stand out at a glance."""
    _ON = "color:#12324f; font-size:12.5px; font-weight:800;"
    _OFF = "color:#5c6775; font-size:12.5px; font-weight:500;"
    def apply():
        cb.setStyleSheet(_ON if cb.isChecked() else _OFF)
    cb.toggled.connect(lambda _=None: apply())
    apply()
    return cb


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
        ang = QLineEdit(); ang.setPlaceholderText("Select an EBSD scan file ...")
        browse = QPushButton("Browse"); browse.setObjectName("BrowseBtn")
        def pick():
            import os
            from app import ROOT
            sd = os.path.join(ROOT, "dp_data")
            sd = sd if os.path.isdir(sd) else ROOT
            # Every format the reader supports, with an "all EBSD files" default
            # so users are not limited to .ang.
            filt = ("EBSD scan files (*.ang *.osc *.ctf *.h5 *.oh5 *.hdf5 *.hdf *.dream3d);;"
                    "TSL/EDAX text (*.ang);;"
                    "EDAX OIM binary (*.osc);;"
                    "HKL Channel 5 (*.ctf);;"
                    "HDF5 / h5ebsd (*.h5 *.oh5 *.hdf5 *.hdf *.dream3d);;"
                    "All files (*)")
            p, _ = QFileDialog.getOpenFileName(win, "Open EBSD scan", sd, filt)
            if p:
                ang.setText(p); win.file_chip.setText(os.path.basename(p))
        browse.clicked.connect(pick)
        fr = QHBoxLayout(); fr.setSpacing(7); fr.addWidget(ang, 1); fr.addWidget(browse)
        fw = QWidget(); fw.setLayout(fr)
        lay.addWidget(_row("EBSD scan file (.ang / .osc / .ctf / h5ebsd)", fw))
        ctrls["ang"] = ang

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
        from .widgets import BoundaryEditor
        # Crystal symmetry: "(from data)" tells the engine to auto-detect from the
        # file header (falls back to m-3m with a warning if none is found).
        ctrls["crystal_sym"] = QComboBox()
        ctrls["crystal_sym"].addItems(["(from data)", "m-3m", "432", "m-3", "6/mmm", "4/mmm", "-3m", "2/m", "-1"])
        ctrls["crystal_sym"].setCurrentText("(from data)")
        lay.addWidget(_row("Crystal symmetry", ctrls["crystal_sym"]))

        # Which maps to display (default: CI + 3 IPF + IQ)
        map_defs = [("iq", "IQ"), ("ci", "CI"), ("ipf100", "IPF[100]"), ("ipf010", "IPF[010]"),
                    ("ipf001", "IPF[001]"), ("ipf_custom", "IPF[custom]"), ("gb", "Boundaries"),
                    ("ipfgb", "IPF+bnd"), ("grain", "Grains"), ("phase", "Phase")]
        mg = QGridLayout(); mg.setSpacing(4); ctrls["show_maps"] = {}
        for i, (key, lab) in enumerate(map_defs):
            cb = QCheckBox(lab); cb.setChecked(key in d.show_maps)
            cb.setStyleSheet("color:#dbe4ef; font-size:11px;")
            mg.addWidget(cb, i // 2, i % 2); ctrls["show_maps"][key] = cb
        mw = QWidget(); mw.setLayout(mg); lay.addWidget(_row("Maps to show", mw))

        # CI display mode
        ctrls["ci_display"] = SegGroup([("grey", "grey"), ("colormap", "colormap")], default=d.ci_display)
        lay.addWidget(_row("CI map style", ctrls["ci_display"]))

        # in-image overlay toggles (OIM-style)
        ov = QHBoxLayout(); ov.setSpacing(10)
        ctrls["show_colorbar"] = QCheckBox("Intensity bar"); ctrls["show_colorbar"].setChecked(d.show_colorbar)
        ctrls["show_scalebar"] = QCheckBox("Scale bar"); ctrls["show_scalebar"].setChecked(d.show_scalebar)
        ctrls["show_axes_labels"] = QCheckBox("Axis labels"); ctrls["show_axes_labels"].setChecked(d.show_axes_labels)
        for c in (ctrls["show_colorbar"], ctrls["show_scalebar"], ctrls["show_axes_labels"]):
            c.setStyleSheet("color:#dbe4ef; font-size:11px;"); ov.addWidget(c)
        ov.addStretch(1); ow = QWidget(); ow.setLayout(ov); lay.addWidget(_row("In-image overlays", ow))

        # grain-splitting angle — explicit, independent of the display classes
        ctrls["grain_angle"] = _dsb(0.5, 180, d.grain_angle, 1, 1)
        lay.addWidget(_row("Grain-splitting angle [deg]", ctrls["grain_angle"]))

        # grain-boundary editor (count + per-boundary range/color/width)
        ctrls["boundaries"] = BoundaryEditor(defaults=d.boundaries)
        lay.addWidget(_row("Grain-boundary display classes", ctrls["boundaries"]))

        ctrls["ci_threshold"] = _dsb(0, 1, d.ci_threshold, 0.05, 2)
        ctrls["min_grain_px"] = _sb(1, 1000, d.min_grain_px)
        cr = QHBoxLayout(); cr.addWidget(_row("CI threshold", ctrls["ci_threshold"])); cr.addWidget(_row("Min grain (px)", ctrls["min_grain_px"]))
        cw = QWidget(); cw.setLayout(cr); lay.addWidget(cw)

        ah, ab = _adv_header(ctrls); lay.addWidget(_divider()); lay.addWidget(ah); lay.addWidget(ab)
        av = QVBoxLayout(ab); av.setContentsMargins(0, 8, 0, 0); av.setSpacing(11)
        # custom IPF [hkl] direction (drives the IPF[custom] map)
        h1, h2, h3 = _sb(-9, 9, 1), _sb(-9, 9, 1), _sb(-9, 9, 1)
        hr = QHBoxLayout(); [hr.addWidget(x) for x in (h1, h2, h3)]
        hw = QWidget(); hw.setLayout(hr); av.addWidget(_row("Custom IPF direction [h k l]", hw))
        ctrls["hkl"] = (h1, h2, h3)
        ctrls["low_ci_fill"] = _dsb(0, 1, d.low_ci_fill, 0.05, 2)
        ctrls["seed"] = _sb(0, 999999, d.seed)
        sr = QHBoxLayout(); sr.addWidget(_row("Low-CI fill", ctrls["low_ci_fill"])); sr.addWidget(_row("Grain seed", ctrls["seed"]))
        sw = QWidget(); sw.setLayout(sr); av.addWidget(sw)
        ctrls["connectivity"] = SegGroup([("4", "4-neigh"), ("8", "8-neigh")], default=str(d.connectivity))
        av.addWidget(_row("Grain connectivity", ctrls["connectivity"]))
        # low-CI cleaning: OFF by default
        ctrls["ci_mask"] = QCheckBox("Clean low-CI pixels (neighbour-fill)")
        ctrls["ci_mask"].setChecked(d.ci_mask)   # default False now
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
        ctrls["odf_method"] = SegGroup([("kernel", "kernel"), ("harmonic", "harmonic")], default=d.odf_method)
        lay.addWidget(_row("ODF method (MTEX-style kernel)", ctrls["odf_method"]))
        ctrls["sample_sym"] = SegGroup([("triclinic", "tricl."), ("monoclinic", "monocl."), ("orthorhombic", "ortho.")], default=d.sample_sym)
        lay.addWidget(_row("Specimen symmetry", ctrls["sample_sym"]))
        ctrls["odf_halfwidth"] = _dsb(2, 30, d.odf_halfwidth, 1, 1)
        lay.addWidget(_row("Kernel halfwidth [deg]", ctrls["odf_halfwidth"]))
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


# ============================================================ presets (JSON)
def _save_preset(win):
    """Write the current settings (report-item ticks + every option value) to a
    JSON preset file."""
    import json
    from dataclasses import asdict
    path, _ = QFileDialog.getSaveFileName(win, "Save preset", "ebsd_preset.json",
                                          "JSON preset (*.json)")
    if not path:
        return
    try:
        cfg = read_all_controls(win)
        data = asdict(cfg)
        data.pop("input_file", None)      # presets are file-independent
        data.pop("ang_file", None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=list)
        if hasattr(win, "_log"):
            win._log(f"Preset saved: {path}")
    except Exception as e:                 # keep the GUI alive on any failure
        if hasattr(win, "_log"):
            win._log(f"[preset save failed] {e}")


def _load_preset(win):
    """Read a JSON preset and push every value back into the sidebar widgets."""
    import json
    path, _ = QFileDialog.getOpenFileName(win, "Load preset", "",
                                          "JSON preset (*.json);;All files (*)")
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        apply_config_to_controls(win, data)
        if hasattr(win, "_log"):
            win._log(f"Preset loaded: {path}")
    except Exception as e:
        if hasattr(win, "_log"):
            win._log(f"[preset load failed] {e}")


def apply_config_to_controls(win, data: dict):
    """Push a plain settings dict (from a JSON preset) back into the widgets.
    Unknown / missing keys are ignored so old presets keep working."""
    c = win.step_ctrls
    s1, s2, s3, s4, s5 = c[0], c[1], c[2], c[3], c[4]

    def setv(w, v):
        if w is None or v is None:
            return
        if hasattr(w, "setValue"):
            w.setValue(type(w.value())(v) if not isinstance(w.value(), bool) else v)
        elif hasattr(w, "setChecked"):
            w.setChecked(bool(v))

    # step 1
    setv(s1.get("grid_ratio"), data.get("grid_ratio"))
    setv(s1.get("rotate_angle"), data.get("rotate_angle"))
    for key in ("col_phi1", "col_phi", "col_phi2", "col_x", "col_y", "col_iq",
                "col_ci", "col_phase", "col_sem", "col_fit"):
        setv(s1.get(key), data.get(key))
    if "comment_char" in s1 and data.get("comment_char"):
        s1["comment_char"].setText(str(data["comment_char"]))

    # step 2
    if "crystal_sym" in s2:
        sym = data.get("crystal_sym")
        s2["crystal_sym"].setCurrentIndex(0) if sym in (None, "") else \
            s2["crystal_sym"].setCurrentText(str(sym))
    if "show_maps" in s2 and data.get("show_maps") is not None:
        sel = set(data["show_maps"])
        for k, cb in s2["show_maps"].items():
            cb.setChecked(k in sel)
    for key in ("show_colorbar", "show_scalebar", "show_axes_labels", "ci_mask"):
        setv(s2.get(key), data.get(key))
    setv(s2.get("ci_threshold"), data.get("ci_threshold"))
    setv(s2.get("min_grain_px"), data.get("min_grain_px"))
    setv(s2.get("low_ci_fill"), data.get("low_ci_fill"))
    setv(s2.get("seed"), data.get("seed"))
    if "boundaries" in s2 and data.get("boundaries"):
        s2["boundaries"].set_value(data["boundaries"])

    # step 3
    setv(s3.get("hist_bins"), data.get("hist_bins"))
    setv(s3.get("astm_c1"), data.get("astm_c1"))
    setv(s3.get("astm_c2"), data.get("astm_c2"))
    setv(s3.get("exclude_edge"), data.get("exclude_edge_grains"))

    # step 4
    setv(s4.get("odf_halfwidth"), data.get("odf_halfwidth"))
    setv(s4.get("n_sample"), data.get("n_sample"))
    setv(s4.get("section_step"), data.get("section_step"))
    if "phi2" in s4 and data.get("phi2_sections") is not None:
        want = {int(v) for v in data["phi2_sections"]}
        for s, btn in s4["phi2"].items():
            btn.setChecked(int(s) in want)

    # step 5
    if "outfile" in s5 and data.get("report_outfile"):
        s5["outfile"].setText(str(data["report_outfile"]))
    setv(s5.get("slide_w"), data.get("slide_w_in"))
    setv(s5.get("slide_h"), data.get("slide_h_in"))
    setv(s5.get("dpi"), data.get("fig_dpi"))
    if "title" in s5 and data.get("report_title"):
        s5["title"].setText(str(data["report_title"]))

    # report-item ticks live in Step 1's RESULTS pane
    try:
        r1 = win.step_results[0]
        if "report_items" in r1 and data.get("report_items") is not None:
            sel = set(data["report_items"])
            for k, cb in r1["report_items"].items():
                cb.setChecked(k in sel)
    except (AttributeError, IndexError, KeyError):
        pass


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

        # map on the left, PowerPoint-content selection on the right
        row = QHBoxLayout(); row.setSpacing(16)
        refs["phase"] = FigurePane("Phase / IQ map", min_h=320)
        refs["phase"].setMaximumWidth(360)
        row.addWidget(refs["phase"], 0, Qt.AlignTop)

        d = Config()
        rep_defs = [("iq", "IQ map"), ("ci", "CI map"), ("ipf001", "IPF [001] map"),
                    ("ipf100", "IPF [100] map"), ("ipf010", "IPF [010] map"),
                    ("gb", "Grain-boundary map"), ("ipfgb", "IPF + boundaries"),
                    ("grain", "Grain map"), ("phase", "Phase map"),
                    ("grain_size", "Grain-size charts"), ("odf", "ODF sections"),
                    ("fibers", "Fiber profiles")]
        box = QVBoxLayout(); box.setSpacing(6)
        hdr = QLabel("INCLUDE IN POWERPOINT"); hdr.setStyleSheet(
            "color:#1a2230;font-family:Consolas;font-size:12px;font-weight:800;"
            "letter-spacing:1px;padding-bottom:3px;")
        box.addWidget(hdr)
        refs["report_items"] = {}
        for key, lab in rep_defs:
            cb = QCheckBox(lab); cb.setChecked(key in d.report_items)
            _bold_when_checked(cb)          # bold label while checked, normal when not
            box.addWidget(cb); refs["report_items"][key] = cb
        # --- preset save / load (JSON) ------------------------------------
        # Persists BOTH the ticked report items and every option value in the
        # sidebar, so a preset restores a whole analysis setup.
        btn_row = QHBoxLayout(); btn_row.setSpacing(7)
        b_save = QPushButton("Save preset…"); b_save.setObjectName("BrowseBtn")
        b_load = QPushButton("Load preset…"); b_load.setObjectName("BrowseBtn")
        for b in (b_save, b_load):
            b.setStyleSheet("QPushButton{background:#44576e;color:#f2f6fb;border:1px solid #586a80;"
                            "border-radius:6px;padding:6px 12px;font-size:11.5px;font-weight:700;}"
                            "QPushButton:hover{background:#516882;border:1px solid #3B82F6;}")
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        brw = QWidget(); brw.setLayout(btn_row)
        box.addWidget(brw)
        b_save.clicked.connect(lambda: _save_preset(win))
        b_load.clicked.connect(lambda: _load_preset(win))
        refs["preset_save"] = b_save; refs["preset_load"] = b_load

        box.addStretch(1)
        bw = QWidget(); bw.setLayout(box); row.addWidget(bw, 1, Qt.AlignTop)
        rw = QWidget(); rw.setLayout(row); lay.addWidget(rw)

    elif n == 2:
        grid = QGridLayout(); grid.setSpacing(13)
        # full superset of maps; which are visible is driven by cfg.show_maps
        # (default = IQ + CI + IPF[100]/[010]/[001]). Panes not selected are
        # hidden by app.py at render time, so the grid reflows cleanly.
        specs = [("iq", "Image Quality (IQ)"), ("ci", "Confidence Index (CI)"),
                 ("ipf100", "IPF [100] (RD)"), ("ipf010", "IPF [010] (TD)"),
                 ("ipf001", "IPF [001] (ND)"), ("ipf_custom", "IPF [custom]"),
                 ("gb", "Grain Boundaries"), ("ipfgb", "IPF + boundaries"),
                 ("grain", "Grain Map"), ("phase", "Phase Map")]
        from PySide6.QtWidgets import QSizePolicy as _SP
        refs["_map_grid"] = grid
        refs["_map_order"] = [k for k, _ in specs]
        for key, title in specs:
            fp = FigurePane(title, min_h=420); refs[key] = fp
            fp.setSizePolicy(_SP.Ignored, _SP.Preferred)
            # placed dynamically in app.py based on which maps are shown
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
    cfg.input_file = s1["ang"].text().strip(); cfg.ang_file = cfg.input_file
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
    sym = s2["crystal_sym"].currentText()
    cfg.crystal_sym = None if sym.startswith("(") else sym   # "(from data)" -> auto
    # custom IPF direction (used by the IPF[custom] map)
    if "hkl" in s2 and any(w.value() for w in s2["hkl"]):
        cfg.ipf_dir = tuple(w.value() for w in s2["hkl"])
    # which maps to show
    if "show_maps" in s2:
        sel = tuple(k for k, cb in s2["show_maps"].items() if cb.isChecked())
        cfg.show_maps = sel or ("iq", "ci", "ipf001")
    if "ci_display" in s2:
        cfg.ci_display = s2["ci_display"].value() or "grey"
    for key in ("show_colorbar", "show_scalebar", "show_axes_labels"):
        if key in s2:
            setattr(cfg, key, s2[key].isChecked())
    # boundary display classes + the explicit grain-splitting angle
    if "grain_angle" in s2:
        cfg.grain_angle = s2["grain_angle"].value()
    if "boundaries" in s2:
        cfg.boundaries = s2["boundaries"].value()
    cfg.sync_boundaries()
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
    cfg.odf_method = s4["odf_method"].value()
    cfg.sample_sym = s4["sample_sym"].value()
    cfg.odf_halfwidth = s4["odf_halfwidth"].value()
    cfg.n_sample = s4["n_sample"].value()
    cfg.section_step = s4["section_step"].value()
    cfg.phi2_sections = tuple(s for s, btn in s4["phi2"].items() if btn.isChecked()) or (45,)
    if "odf_cmap" in s4:
        cfg.odf_cmap = s4["odf_cmap"].value()
    if "vmax_auto" in s4:
        cfg.odf_vmax = None if s4["vmax_auto"].isChecked() else s4["odf_vmax"].value()

    # PowerPoint content selection lives in Step 1's RESULTS pane
    try:
        r1 = win.step_results[0]
        if "report_items" in r1:
            sel = tuple(k for k, cb in r1["report_items"].items() if cb.isChecked())
            if sel:
                cfg.report_items = sel
    except (AttributeError, IndexError, KeyError):
        pass

    # step 5
    mode_map = {0: "all", 1: "ebsd", 2: "odf"}
    cfg.report_mode = mode_map.get(s5["report_mode"].currentIndex(), "all")
    cfg.report_outfile = s5["outfile"].text().strip() or "EBSD_report.pptx"
    if "slide_w" in s5:
        cfg.slide_w_in = s5["slide_w"].value(); cfg.slide_h_in = s5["slide_h"].value()
        cfg.fig_dpi = s5["dpi"].value(); cfg.report_title = s5["title"].text()

    return cfg
