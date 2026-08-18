"""EBSD + ODF analysis engine.

Pure-compute layer (no GUI). Pipeline:
  load .ang -> microstructure (maps, grains, ASTM E2627) -> ODF (GSH texture).
"""
from .config import Config
from .microstructure import MicroResult, run_microstructure
from .odf import ODFResult, run_odf
from . import plotting
from .report import build_report

__all__ = ["Config", "MicroResult", "run_microstructure", "ODFResult", "run_odf",
           "plotting", "build_report"]
