"""EBSD ODF Analyzer — standalone desktop GUI.

Faithful to 'EBSD ODF Analyzer.dc.html': a 5-stage pipeline
  1 Load & Resample  2 Microstructure  3 Grain Size  4 Texture (ODF)  5 Report
with a step-nav sidebar, per-step parameter panels (basic + Advanced expander),
a metric header bar, per-step result panes (stat cards + embedded figures),
per-step Run + Run-All, progress, and Back/Next navigation.

Run:  python app.py
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# When frozen by PyInstaller, __file__ lives inside the bundle, so data next to
# the .exe would never be found. Resolve paths against the executable instead.
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(os.path.abspath(sys.executable))
    ROOT = os.path.dirname(HERE)
for p in (HERE, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# orix pulls in numba, which caches compiled functions to disk. In a fresh,
# read-restricted install the default cache path (inside site-packages) may not
# be writable, crashing on first run. Point numba at a guaranteed-writable dir
# BEFORE anything imports orix/numba.
if "NUMBA_CACHE_DIR" not in os.environ:
    _cache = os.path.join(tempfile.gettempdir(), "ebsd_analyzer_numba_cache")
    try:
        os.makedirs(_cache, exist_ok=True)
        os.environ["NUMBA_CACHE_DIR"] = _cache
    except OSError:
        os.environ["NUMBA_CACHE_DIR"] = tempfile.gettempdir()

import matplotlib
matplotlib.use("QtAgg")

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QPushButton, QLineEdit, QLabel, QComboBox, QDoubleSpinBox,
    QSpinBox, QPlainTextEdit, QFileDialog, QProgressBar, QMessageBox, QFrame,
    QScrollArea, QStackedWidget, QSizePolicy, QCheckBox, QButtonGroup,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ebsd_engine import Config, build_report
from ebsd_engine import plotting as P
from worker import (PipelineWorker, STAGE_LOAD, STAGE_MICRO, STAGE_GRAINSIZE,
                    STAGE_ODF, STAGE_REPORT)
from ui.theme import STYLESHEET, ACCENT
from ui.widgets import (Card, MetricCard, SectionLabel, SegButton, ChipButton,
                        FigurePane, StatCard, mono)

APP_TITLE = "EBSD ODF Analyzer"

STEPS = [
    ("Load & Resample", ".ang -> square grid",
     "Read the TSL .ang scan, map columns, and resample the hexagonal grid to a square grid for downstream analysis."),
    ("Microstructure", "IQ . CI . IPF . GB",
     "Compute orientations and neighbour misorientations, then render quality, IPF, grain-boundary maps and union-find grain segmentation."),
    ("Grain Size", "ASTM E2627",
     "Equivalent-circle diameters and grain areas, with count and area-weighted distributions and the ASTM E2627 grain-size number G."),
    ("Texture (ODF)", "GSH . phi2 . fibers",
     "Subsample ferrite orientations, fit a GSH ODF, and plot phi2 sections with ideal BCC components plus alpha and gamma fiber intensities."),
    ("Report", "PowerPoint export",
     "Assemble the selected results into a 16:9 PowerPoint deck. Every figure is captured in-memory and every metric read from the computed variables."),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1480, 920)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(STYLESHEET)

        self.cfg = Config()
        self.micro = None
        self.odf = None
        self.step = 1
        self.status = {1: "idle", 2: "idle", 3: "idle", 4: "idle", 5: "idle"}
        self._thread = None
        self._worker = None
        self._run_all = False

        # ---- import the step panels lazily (kept in ui.steps) ----
        from ui.steps import build_step_controls, build_step_results
        self._build_step_controls = build_step_controls
        self._build_step_results = build_step_results

        self._build_ui()
        self.goto_step(1)

    # ===================================================================== UI
    def _build_ui(self):
        central = QWidget(); root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QWidget(); bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0); bl.setSpacing(0)
        bl.addWidget(self._build_sidebar())
        bl.addWidget(self._build_main(), 1)
        root.addWidget(body, 1)
        self.setCentralWidget(central)

    def _build_header(self):
        h = QFrame(); h.setObjectName("Header"); h.setFixedHeight(58)
        lay = QHBoxLayout(h); lay.setContentsMargins(20, 0, 18, 0); lay.setSpacing(16)

        logo = QLabel("EBSD Analyzer"); logo.setObjectName("Logo")
        sub = QLabel("Microstructure + ODF"); sub.setObjectName("LogoSub")
        lbox = QVBoxLayout(); lbox.setSpacing(0); lbox.addWidget(logo); lbox.addWidget(sub)
        lw = QWidget(); lw.setLayout(lbox); lay.addWidget(lw)

        self.file_chip = QLabel("no file loaded"); self.file_chip.setObjectName("FileChip")
        lay.addWidget(self.file_chip)
        lay.addStretch(1)

        # metric cards (live)
        self.m_grains = MetricCard("Grains", "-")
        self.m_astm = MetricCard("ASTM G", "-")
        self.m_dia = MetricCard("Mean Ø", "-")
        self.m_j = MetricCard("Texture J", "-", accent=True)
        for m in (self.m_grains, self.m_astm, self.m_dia, self.m_j):
            lay.addWidget(m)
        return h

    def _build_sidebar(self):
        # Wide enough for the Step-2 boundary editor (name/lo/hi/colour/width row)
        # to show every value without clipping.
        # Wide enough for the Step-2 boundary table (name / lo / hi / colour /
        # width) to show every value — including the longest colour name — at
        # its measured width, with room for the scrollbar.
        side = QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(560)
        lay = QVBoxLayout(side); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        # --- pipeline nav ---
        nav = QWidget(); nl = QVBoxLayout(nav); nl.setContentsMargins(12, 14, 12, 10); nl.setSpacing(2)
        nl.addWidget(SectionLabel("Pipeline"))
        self.nav_btns = []
        for i, (title, sub, _desc) in enumerate(STEPS, start=1):
            b = QPushButton(); b.setObjectName("NavBtn"); b.setCheckable(True)
            b.setText(f"  {i}   {title}\n      {sub}")
            b.clicked.connect(lambda _=False, n=i: self.goto_step(n))
            self.nav_btns.append(b); nl.addWidget(b)
        nav.setObjectName("Nav")
        lay.addWidget(nav)

        # --- parameters (scrollable, stacked per step) ---
        self.param_title = SectionLabel("Parameters . Load")
        ptw = QWidget(); ptw.setObjectName("ParamHost")
        ptl = QVBoxLayout(ptw); ptl.setContentsMargins(16, 12, 16, 6); ptl.setSpacing(0)
        ptl.addWidget(self.param_title)

        self.param_stack = QStackedWidget(); self.param_stack.setObjectName("ParamStack")
        self.step_ctrls = []   # per-step dict of widgets
        for n in range(1, 6):
            page, ctrls = self._build_step_controls(self, n)
            page.setObjectName("ParamPage")
            self.step_ctrls.append(ctrls)
            self.param_stack.addWidget(page)
        ptl.addWidget(self.param_stack)
        ptl.addStretch(1)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setObjectName("ParamScroll")
        scroll.setWidget(ptw); scroll.setFrameShape(QFrame.NoFrame)
        lay.addWidget(scroll, 1)

        # --- run footer ---
        foot = QFrame(); foot.setObjectName("RunFooter"); fl = QVBoxLayout(foot)
        fl.setContentsMargins(16, 13, 16, 16); fl.setSpacing(8)
        self.prog = QProgressBar(); self.prog.setRange(0, 100); self.prog.setValue(0)
        self.prog.setObjectName("RunProg"); self.prog.setVisible(False)
        fl.addWidget(self.prog)
        self.run_btn = QPushButton("Run . Load & Resample"); self.run_btn.setObjectName("RunBtn")
        self.run_btn.clicked.connect(self.run_current_step)
        fl.addWidget(self.run_btn)
        self.run_all_btn = QPushButton("Run All Steps"); self.run_all_btn.setObjectName("RunAllBtn")
        self.run_all_btn.clicked.connect(self.run_all_steps)
        fl.addWidget(self.run_all_btn)
        lay.addWidget(foot)
        return side

    def _build_main(self):
        main = QFrame(); main.setObjectName("Main")
        lay = QVBoxLayout(main); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        # header strip (stage title + desc)
        head = QWidget(); hl = QVBoxLayout(head); hl.setContentsMargins(26, 22, 26, 8); hl.setSpacing(2)
        self.stage_kicker = QLabel("STAGE 1 / 5"); self.stage_kicker.setObjectName("Kicker")
        self.stage_title = QLabel(STEPS[0][0]); self.stage_title.setObjectName("StageTitle")
        self.stage_desc = QLabel(STEPS[0][2]); self.stage_desc.setObjectName("StageDesc")
        self.stage_desc.setWordWrap(True)
        hl.addWidget(self.stage_kicker); hl.addWidget(self.stage_title); hl.addWidget(self.stage_desc)
        lay.addWidget(head)

        # result stack
        self.result_stack = QStackedWidget()
        self.step_results = []
        for n in range(1, 6):
            page, refs = self._build_step_results(self, n)
            self.step_results.append(refs)
            self.result_stack.addWidget(page)
        rs = QScrollArea(); rs.setWidgetResizable(True); rs.setFrameShape(QFrame.NoFrame)
        # vertical scroll only; the page already fits the width, and disabling
        # the horizontal bar stops the "v-bar appears -> content 11px too wide
        # -> h-bar appears" feedback that was clipping the right edge.
        rs.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        rs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rs.setWidget(self.result_stack); rs.setObjectName("ResultScroll")
        lay.addWidget(rs, 1)

        # footer nav
        foot = QWidget(); foot.setObjectName("MainFooter"); fl = QHBoxLayout(foot)
        fl.setContentsMargins(26, 12, 26, 16)
        self.back_btn = QPushButton("< Back"); self.back_btn.setObjectName("BackBtn")
        self.back_btn.clicked.connect(lambda: self.goto_step(max(1, self.step - 1)))
        self.stage_count = QLabel("Stage 1 of 5"); self.stage_count.setObjectName("StageCount")
        self.next_btn = QPushButton("Next >"); self.next_btn.setObjectName("NextBtn")
        self.next_btn.clicked.connect(lambda: self.goto_step(min(5, self.step + 1)))
        fl.addWidget(self.back_btn); fl.addStretch(1); fl.addWidget(self.stage_count)
        fl.addStretch(1); fl.addWidget(self.next_btn)
        lay.addWidget(foot)
        return main

    # ================================================================= nav
    def goto_step(self, n: int):
        self.step = n
        for i, b in enumerate(self.nav_btns, start=1):
            b.setChecked(i == n)
        self.param_stack.setCurrentIndex(n - 1)
        self.result_stack.setCurrentIndex(n - 1)
        self.param_title.setText(f"Parameters . {STEPS[n-1][0].split(' ')[0]}")
        self.stage_kicker.setText(f"STAGE {n} / 5")
        self.stage_title.setText(STEPS[n - 1][0])
        self.stage_desc.setText(STEPS[n - 1][2])
        self.stage_count.setText(f"Stage {n} of 5")
        self.back_btn.setEnabled(n > 1)
        if n == 5:
            self.run_btn.setText("Export PowerPoint")
            self.next_btn.setText("Done")
        else:
            self.run_btn.setText(f"Run . {STEPS[n-1][0]}")
            self.next_btn.setText("Next >")

    # ============================================================== config
    def collect_config(self) -> Config:
        """Read every control across all steps into a fresh Config."""
        from ui.steps import read_all_controls
        return read_all_controls(self)

    # ================================================================= run
    def _busy(self, on: bool):
        self.run_btn.setEnabled(not on); self.run_all_btn.setEnabled(not on)
        for b in self.nav_btns:
            b.setEnabled(not on)
        self.prog.setVisible(on)
        if not on:
            self.prog.setValue(0)

    def run_current_step(self):
        if self.step == STAGE_REPORT:
            self.export_report()
            return
        self._start(self.step, self.step, run_all=False)

    def run_all_steps(self):
        self._start(STAGE_LOAD, STAGE_ODF, run_all=True)

    def _start(self, start_stage, stop_stage, run_all):
        cfg = self.collect_config()
        if not cfg.ang_file or not os.path.isfile(cfg.ang_file):
            QMessageBox.warning(self, APP_TITLE, "Please select a valid .ang file first.")
            return
        # stages after LOAD need prior results
        if start_stage > STAGE_LOAD and self.micro is None and not run_all:
            QMessageBox.information(self, APP_TITLE,
                                    "Run earlier steps first (or use Run All).")
            return
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(self, APP_TITLE, "A run is already in progress.")
            return
        self.cfg = cfg
        self._run_all = run_all
        self._busy(True)

        thread = QThread()
        worker = PipelineWorker(cfg, start_stage, stop_stage,
                                micro=self.micro, odf=self.odf)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._log)
        worker.progress.connect(self.prog.setValue)
        worker.stage_done.connect(self.on_stage_done)
        worker.finished.connect(self.on_finished)
        worker.failed.connect(self.on_failed)
        # teardown: quit the thread, then delete both objects once it has stopped
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread_refs)
        self._thread = thread
        self._worker = worker
        if run_all:
            self.goto_step(1)
        thread.start()

    def _clear_thread_refs(self):
        self._thread = None
        self._worker = None

    def _log(self, msg: str):
        for refs in self.step_results:
            lv = refs.get("log")
            if lv is not None:
                lv.appendPlainText(msg)

    def _sync_detected_symmetry(self):
        """After a run, reflect the auto-detected crystal symmetry in the Step 2
        combo so the user can see what was actually used (without overriding a
        manual choice — only updates when the combo is on '(from data)')."""
        try:
            if self.micro is None or not self.micro.phases:
                return
            combo = self.step_ctrls[1].get("crystal_sym")
            if combo is None or not combo.currentText().startswith("("):
                return
            sym = self.micro.pid2phase[self.micro.dominant_pid]["sym"]
            i = combo.findText(sym)
            if i >= 0:
                combo.setItemText(0, f"(from data: {sym})")
        except (AttributeError, IndexError, KeyError):
            pass

    def on_stage_done(self, stage, micro, odf):
        self.micro = micro; self.odf = odf
        self._update_metrics()
        self._sync_detected_symmetry()
        self._refresh_step_figs(stage)
        if self._run_all and stage < STAGE_ODF:
            self.goto_step(stage + 1)

    def on_finished(self, micro, odf):
        self.micro = micro; self.odf = odf
        self._busy(False)
        self._update_metrics()
        # Re-render every stage that produced results. The per-stage `stage_done`
        # signal for the final stage can be dropped when the worker thread quits
        # immediately after, so refresh the full range here to be safe.
        for stage in (STAGE_LOAD, STAGE_MICRO, STAGE_GRAINSIZE, STAGE_ODF):
            if stage == STAGE_ODF and odf is None:
                continue
            if stage >= STAGE_MICRO and (micro is None or micro.labels_clean is None):
                continue
            self._refresh_step_figs(stage)
        self.status[1] = self.status[2] = self.status[3] = self.status[4] = "done"
        if self._run_all:
            self.goto_step(5)
        msg = f"{micro.n_grains} grains, ASTM G {micro.G_e2627:.1f}" if micro else ""
        if odf:
            msg += f", J {odf.J:.2f}"
        self.statusBar().showMessage("Done. " + msg)

    def on_failed(self, tb):
        self._busy(False)
        self._log("\n[ERROR]\n" + tb)
        QMessageBox.critical(self, APP_TITLE, "Pipeline failed:\n\n" + tb.strip().splitlines()[-1])

    # ============================================================ metrics
    def _update_metrics(self):
        m, o = self.micro, self.odf
        if m is not None:
            self.m_grains.set_value(f"{m.n_grains:,}" if m.n_grains else "-")
            if m.G_e2627:
                self.m_astm.set_value(f"{m.G_e2627:.1f}")
            if m.g_diam_um is not None:
                self.m_dia.set_value(f"{m.g_diam_um.mean():.2f} µm")
        if o is not None:
            self.m_j.set_value(f"{o.J:.2f}")

    def _refresh_step_figs(self, stage):
        """Re-render the figures owned by the just-completed stage.

        Each pane gets a *builder* (a zero-arg callable that rebuilds the figure)
        so it renders inline now AND can re-render large in the click-to-enlarge
        popup with the current config snapshot.
        """
        cfg, m, o = self.cfg, self.micro, self.odf
        refs1, refs2, refs3, refs4 = (self.step_results[0], self.step_results[1],
                                      self.step_results[2], self.step_results[3])

        def wire(pane, builder):
            pane.set_builder(builder)
            pane.show_figure(builder())

        try:
            if stage == STAGE_LOAD and m is not None:
                wire(refs1["phase"], lambda: P.fig_iq(cfg, m))
                refs1["pts"].set_value(f"{m.iq.size:,}")
                refs1["grid"].set_value(f"{m.nx} × {m.ny}")
                refs1["step"].set_value(f"{m.step:.3f} µm")
                refs1["extent"].set_value(f"{(m.nx-1)*m.step:.1f} × {(m.ny-1)*m.step:.1f}")
            if stage == STAGE_MICRO and m is not None:
                # builders for every possible map; only the selected ones (and
                # the phase map when multiphase) are placed + drawn.
                builders = {
                    "iq":     lambda: P.fig_iq(cfg, m),
                    "ci":     lambda: P.fig_ci(cfg, m),
                    "ipf100": lambda: P.fig_ipf(cfg, m, direction=(1, 0, 0)),
                    "ipf010": lambda: P.fig_ipf(cfg, m, direction=(0, 1, 0)),
                    "ipf001": lambda: P.fig_ipf(cfg, m, direction=(0, 0, 1)),
                    "ipf_custom": lambda: P.fig_ipf(cfg, m, direction=cfg.ipf_dir),
                    "gb":     lambda: P.fig_gb(cfg, m),
                    "ipfgb":  lambda: P.fig_ipf_hagb(cfg, m),
                    "grain":  lambda: P.fig_grains(cfg, m),
                    "phase":  lambda: P.fig_phase(cfg, m),
                }
                selected = list(cfg.show_maps)
                if len(m.phases) > 1 and "phase" not in selected:
                    selected.append("phase")   # auto-show phase map for multiphase
                grid = refs2["_map_grid"]
                # detach all panes, then place the selected ones in order
                for key in refs2["_map_order"]:
                    pane = refs2[key]
                    grid.removeWidget(pane); pane.setVisible(False)
                pos = 0
                for key in refs2["_map_order"]:
                    if key not in selected:
                        continue
                    pane = refs2[key]
                    grid.addWidget(pane, pos // 3, pos % 3)
                    pane.setVisible(True)
                    wire(pane, builders[key])
                    pos += 1
            if stage == STAGE_GRAINSIZE and m is not None:
                wire(refs3["count"], lambda: P.fig_grain_size_count(m, cfg.hist_bins))
                wire(refs3["frac"], lambda: P.fig_grain_size_frac(m, cfg.hist_bins))
                refs3["c_grains"].set_value(f"{m.n_grains_measured:,}")
                refs3["c_astm"].set_value(f"{m.G_e2627:.1f}")
                refs3["c_dnum"].set_value(f"{m.d_num:.2f} µm")
                refs3["c_dw"].set_value(f"{m.d_w:.2f} µm")
            if stage == STAGE_ODF and o is not None:
                wire(refs4["sections"], lambda: P.fig_odf_sections(cfg, o))
                wire(refs4["fibers"], lambda: P.fig_fibers(o))
                refs4["c_j"].set_value(f"{o.J:.2f}")
                refs4["c_max"].set_value(f"{o.odf.max():.2f} mrd")
                refs4["c_amax"].set_value(f"{o.f_alpha.max():.2f} mrd")
                refs4["c_gmax"].set_value(f"{o.f_gamma.max():.2f} mrd")
        except Exception as e:
            self._log(f"[plot error stage {stage}] {e}")

    # ============================================================== export
    def export_report(self):
        if self.micro is None:
            QMessageBox.information(self, APP_TITLE, "Run the analysis first.")
            return
        cfg = self.collect_config(); self.cfg = cfg
        mode = cfg.report_mode
        if mode in ("all", "odf") and self.odf is None:
            QMessageBox.information(self, APP_TITLE, "Texture (Step 4) is required for this report mode.")
            return
        default = os.path.join(ROOT, cfg.report_outfile)
        path, _ = QFileDialog.getSaveFileName(self, "Save PowerPoint", default, "PowerPoint (*.pptx)")
        if not path:
            return
        try:
            build_report(cfg, self.micro, self.odf, path, mode=mode, log=self._log)
            QMessageBox.information(self, APP_TITLE, f"Report saved:\n{path}")
            self.statusBar().showMessage(f"Saved {os.path.basename(path)}")
        except Exception as e:
            import traceback
            self._log("\n[EXPORT ERROR]\n" + traceback.format_exc())
            QMessageBox.critical(self, APP_TITLE, f"Export failed:\n{e}")


def _selftest():
    """Headless end-to-end check of the bundled compute path (orix, scipy,
    spherical+quaternionic, matplotlib, python-pptx). Tests BOTH ODF engines.
    Run with:  EBSD_Analyzer.exe --selftest
    Exits 0 on success, 1 on failure. Used to verify the frozen build."""
    import traceback
    import numpy as np
    try:
        import matplotlib
        matplotlib.use("Agg")
        from ebsd_engine import Config, run_microstructure, run_odf, build_report
        # locate a .ang: next to the exe, or the dev dp_data folder
        candidates = [
            os.path.join(ROOT, "dp_data", "DP590-InitialX1000_pre(1).ang"),
            os.path.join(ROOT, "dp_data", "DP590_Initial_x2000(1).ang"),
            os.path.join(os.path.dirname(sys.executable), "DP590_Initial_x2000(1).ang"),
        ]
        ang = next((c for c in candidates if os.path.isfile(c)), None)
        if ang is None:
            print("SELFTEST: no .ang found; import-only check")
            import orix, scipy, pptx, PIL, spherical, quaternionic  # noqa
            print("SELFTEST IMPORTS OK (incl spherical+quaternionic)")
            return 0
        cfg = Config(ang_file=ang)
        m = run_microstructure(cfg, log=lambda *a: None)
        # test BOTH ODF engines (kernel needs only orix; harmonic needs
        # spherical+quaternionic — the frozen-build risk)
        results = {}
        for method in ("kernel", "harmonic"):
            cfg.odf_method = method
            o = run_odf(cfg, m, log=lambda *a: None)
            nan = bool(np.isnan(o.odf).any())
            results[method] = (o.J, nan)
            print(f"SELFTEST ODF[{method}]: J={o.J:.3f} NaN={nan}")
        # build a report with the last (harmonic) result to exercise plotting/pptx
        out = os.path.join(os.path.dirname(sys.executable), "_selftest.pptx")
        build_report(cfg, m, o, out, mode="all", log=lambda *a: None)
        ok = (os.path.getsize(out) > 0
              and not results["kernel"][1] and not results["harmonic"][1])
        print(f"SELFTEST: grains={m.n_grains} G={m.G_e2627:.1f} pptx={os.path.getsize(out)}")
        try:
            os.remove(out)
        except OSError:
            pass

        # --- multiphase check (only if the synthetic 2-phase file is present) ---
        mp = os.path.join(ROOT, "ruan dat", "synthetic_mixed.ang")
        if os.path.isfile(mp):
            cfg2 = Config(input_file=mp, odf_method="kernel", n_sample=6000)
            m2 = run_microstructure(cfg2, log=lambda *a: None)
            o2 = run_odf(cfg2, m2, log=lambda *a: None)
            ph = m2.phase.reshape(m2.ny, m2.nx)
            cross = ph[:, :-1] != ph[:, 1:]
            cross_ok = bool(np.isfinite(m2.mis_h[cross]).sum() == 0)  # all cross = inf
            js = {pr.name: pr.J for pr in o2.per_phase.values()}
            j_ok = (len(o2.per_phase) == 2
                    and all(np.isfinite(v) for v in js.values()))
            print(f"SELFTEST MULTIPHASE: phases={len(m2.phases)} J={js} "
                  f"cross-phase-inf={cross_ok}")
            ok = ok and cross_ok and j_ok
        else:
            print("SELFTEST MULTIPHASE: skipped (synthetic_mixed.ang not bundled)")

        print("SELFTEST OK" if ok else "SELFTEST FAIL")
        return 0 if ok else 1
    except Exception:
        print("SELFTEST FAIL\n" + traceback.format_exc())
        return 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
