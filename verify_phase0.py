"""Phase 0 verification — run the extracted engine headless and compare against
the notebook's known outputs for DP590_Initial_x2000(1).ang.

Expected (from EBSD_ODF_combined.ipynb cell outputs):
    Loaded 342,453 pts ; grid 317x937 ; step 0.1200 um
    HAGB: H 12.4%  V 11.0%
    Grains >=5px: 437 ; ASTM G = 13.8 ; number-avg diam 3.39 um ; area-wt 6.72 um
    (NOTE: the 1284 / 11.8 / 2.74 figures in 'EBSD ODF Analyzer.dc.html' are
     hardcoded mockup placeholders, NOT the notebook's real output.)
    Good orientations: 264,392 / 297,029 ; 20,000 sampled
    GSH modes 40 ; c_0 = 1.0000 ; J = 2.043
    ODF range [-23.89, 55.86] ; max at phi1=45 Phi=5 phi2=0
"""
import os
import sys

# make ebsd_engine importable, and gsh_core (one dir up)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import numpy as np
from ebsd_engine import Config, run_microstructure, run_odf

ANG = os.path.join(ROOT, "dp_data", "DP590_Initial_x2000(1).ang")


def main():
    # ci_mask=False reproduces the raw notebook (no low-CI clean-up), which is
    # what these reference numbers come from. The app defaults ci_mask=True.
    cfg = Config(ang_file=ANG, ci_mask=False)
    print("=" * 60)
    print("MICROSTRUCTURE")
    print("=" * 60)
    micro = run_microstructure(cfg)
    print("=" * 60)
    print("ODF / TEXTURE")
    print("=" * 60)
    odf = run_odf(cfg, micro)

    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    checks = [
        ("grid nx",        micro.nx,                317),
        ("grid ny",        micro.ny,                937),
        ("step um",        round(micro.step, 4),    0.12),
        ("n_grains",       micro.n_grains,          437),
        ("ASTM G",         round(micro.G_e2627, 1), 13.8),
        ("d_num um",       round(micro.d_num, 2),   3.39),
        ("d_w um",         round(micro.d_w, 2),     6.72),
        ("GSH modes",      len(odf.n_states),       40),
        ("c_0 real",       round(float(odf.c[0].real), 4), 1.0),
        ("texture J",      round(odf.J, 3),         2.043),
        ("odf max mrd",    round(float(odf.odf.max()), 2), 55.86),
        ("odf min mrd",    round(float(odf.odf.min()), 2), -23.89),
    ]
    ok = True
    for name, got, exp in checks:
        if exp is None:
            print(f"  {name:18s} = {got!s:>10}   (info)")
        else:
            match = (got == exp) or (isinstance(exp, float) and abs(got - exp) < 0.05)
            flag = "OK " if match else "XX "
            if not match:
                ok = False
            print(f"  {flag}{name:18s} = {got!s:>10}   expected {exp}")
    print("=" * 60)
    print("ALL MATCH" if ok else "MISMATCH - investigate")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
