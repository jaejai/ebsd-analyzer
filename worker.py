"""Background worker — runs pipeline stages off the GUI thread.

The 5 mockup stages map onto the engine like this:
  1 Load        -> load_ang (hex->square)
  2 Microstructure -> misorientation, IPF, boundaries, grain segmentation
  3 Grain Size  -> ASTM E2627 stats
  4 Texture ODF -> GSH ODF + fibers
  5 Report      -> (export handled separately, on demand)

The worker runs every stage from `start_stage`..`stop_stage` so a single-step
"Run" re-runs just what's needed, and "Run All" runs 1..4. Results accumulate
on the shared MicroResult / ODFResult the GUI holds onto.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ebsd_engine import Config
from ebsd_engine import microstructure as M
from ebsd_engine import odf as O


# stage indices (1-based, matching the mockup)
STAGE_LOAD = 1
STAGE_MICRO = 2
STAGE_GRAINSIZE = 3
STAGE_ODF = 4
STAGE_REPORT = 5


class PipelineWorker(QObject):
    log = Signal(str)
    progress = Signal(int)               # 0..100 within the requested range
    stage_done = Signal(int, object, object)   # (stage, MicroResult, ODFResult)
    finished = Signal(object, object)    # (MicroResult, ODFResult) at the end
    failed = Signal(str)

    def __init__(self, cfg: Config, start_stage: int, stop_stage: int,
                 micro=None, odf=None):
        super().__init__()
        self.cfg = cfg
        self.start = start_stage
        self.stop = stop_stage
        self.micro = micro
        self.odf = odf

    def run(self):
        try:
            emit = lambda m="": self.log.emit(str(m))
            cfg = self.cfg
            stages = list(range(self.start, self.stop + 1))
            n = len(stages)

            for k, stage in enumerate(stages):
                base = int(100 * k / n)
                self.progress.emit(base + 1)

                if stage == STAGE_LOAD:
                    emit("[1/5] Load & resample .ang ...")
                    self.micro = M.load_ang(cfg, log=emit)

                elif stage == STAGE_MICRO:
                    emit("")
                    emit("[2/5] Microstructure: misorientation, IPF, boundaries, grains ...")
                    if self.micro is None:
                        self.micro = M.load_ang(cfg, log=emit)
                    if cfg.ci_mask:
                        # restore pristine euler (ci_raw) so re-runs don't double-fill
                        if self.micro.ci_raw is not None and self.micro.n_filled:
                            self.micro = M.load_ang(cfg, log=lambda *a: None)
                        M.neighbor_fill_low_ci(cfg, self.micro, log=emit)
                    M.compute_misorientation(cfg, self.micro, log=emit)
                    M.compute_ipf(cfg, self.micro, log=emit)
                    M.compute_boundaries(cfg, self.micro, log=emit)
                    M.segment_grains(cfg, self.micro, log=emit)

                elif stage == STAGE_GRAINSIZE:
                    emit("")
                    emit("[3/5] Grain size (ASTM E2627) ...")
                    M.grain_size(cfg, self.micro, log=emit)

                elif stage == STAGE_ODF:
                    emit("")
                    emit("[4/5] Texture: GSH ODF + fibers ...")
                    self.odf = O.run_odf(cfg, self.micro, log=emit)

                self.stage_done.emit(stage, self.micro, self.odf)

            self.progress.emit(100)
            emit(""); emit("Done.")
            self.finished.emit(self.micro, self.odf)
        except Exception:
            import traceback
            self.failed.emit(traceback.format_exc())
