"""ODF / texture analysis — de la Vallee Poussin kernel density (MTEX-style).

Two mathematically-equivalent engines (verified corr=1.0000), selected by
cfg.odf_method:
  "kernel"   = direct kernel sum over orientations (vectorized quaternions;
               needs only orix).
  "harmonic" = Wigner-D / GSH series (odf_mtex.ODF; needs spherical+quaternionic;
               this is MTEX's internal algorithm).
Both give f(g) >= 0, no ringing, and no Phi=pi NaN (the old gsh_core bug).
Crystal symmetry = cfg.crystal_sym ; specimen symmetry = cfg.sample_sym.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import Config
from .microstructure import MicroResult

BCC_COMPONENTS = {'Cube': (0, 0, 0), '{001}<110>': (0, 0, 45), '{112}<110>': (0, 35, 45),
                  '{111}<110>': (0, 55, 45), '{111}<112>': (30, 55, 45), 'Goss': (0, 45, 90)}
FCC_COMPONENTS = {'Cube': (0, 0, 0), 'Goss': (0, 45, 0), 'Brass': (35, 45, 0),
                  'Copper': (90, 35, 45), 'S': (59, 37, 63)}

_SAMPLE_GROUPS = {"triclinic": "C1", "monoclinic": "C2", "orthorhombic": "D2"}


@dataclass
class PhaseODF:
    """One phase's ODF result (MTEX-style per-phase ODF)."""
    pid: int = 0
    name: str = ""
    sym: str = ""
    kind: str = ""                     # "BCC"/"FCC"/"HCP" -> component overlay
    n: int = 0                         # orientations used
    J: float = 0.0
    eulers_odf: np.ndarray = None
    odf: np.ndarray = None             # (n_phi1, n_Phi, n_phi2)
    odf_max_loc: str = ""
    components: dict = field(default_factory=dict)
    # fibers
    Phi_line: np.ndarray = None
    f_alpha: np.ndarray = None
    phi1_line: np.ndarray = None
    f_gamma: np.ndarray = None


@dataclass
class ODFResult:
    # per-phase results (pid -> PhaseODF); primary multiphase container
    per_phase: dict = field(default_factory=dict)
    dominant_pid: int = 0
    # --- dominant-phase view under the OLD single-phase names (plotting/report
    #     compat) ------------------------------------------------------------
    eulers_odf: np.ndarray = None
    J: float = 0.0
    phi1_deg: np.ndarray = None
    Phi_deg: np.ndarray = None
    phi2_deg: np.ndarray = None
    odf: np.ndarray = None             # (n_phi1, n_Phi, n_phi2)
    odf_max_loc: str = ""
    # fibers
    Phi_line: np.ndarray = None
    f_alpha: np.ndarray = None
    phi1_line: np.ndarray = None
    f_gamma: np.ndarray = None
    components: dict = field(default_factory=dict)
    method: str = ""


# ------------------------------------------------------------------ kernel eval
def _kappa(hw_deg):
    return np.log(0.5) / (2.0 * np.log(np.cos(np.radians(hw_deg) / 2.0)))


def _qmul(a, b):
    w1, x1, y1, z1 = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    w2, x2, y2, z2 = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([w1*w2 - x1*x2 - y1*y2 - z1*z2,
                     w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2,
                     w1*z2 + x1*y2 - y1*x2 + z1*w2], -1)


def _make_kernel_eval(eulers_odf, pg, hw_deg):
    """Vectorized de la Vallee Poussin kernel-density evaluator (normalized to
    uniform=1). Disorientation cos(omega/2) = max_s |<q_g, s.q_i>| over the
    proper crystal rotations."""
    from orix.quaternion import Orientation, Rotation
    kappa = _kappa(hw_deg)
    sym = pg.proper_subgroup.data.reshape(-1, 4)
    qd = Orientation.from_euler(eulers_odf).data
    qv = _qmul(sym[None, :, :], qd[:, None, :]).reshape(len(qd), len(sym), 4)

    def kraw(euler_query, chunk=40):
        qg = Orientation.from_euler(np.atleast_2d(euler_query)).data
        out = np.empty(len(qg))
        for a in range(0, len(qg), chunk):
            b = min(a + chunk, len(qg))
            dot = np.abs(np.einsum('gk,nsk->gns', qg[a:b], qv))
            out[a:b] = np.mean(dot.max(2) ** (2 * kappa), axis=1)
        return out

    Ou = Orientation(Rotation.random(2000))
    fu = kraw(Ou.to_euler())
    C = 1.0 / fu.mean()
    J = float(np.mean((C * fu) ** 2))

    def odf_eval(euler_query):
        return C * kraw(euler_query)
    return odf_eval, J


def _build_phase_odf_eval(cfg, eulers_odf, pg, log):
    """Return (odf_eval, J) for one phase's orientations + point group, using the
    selected engine. The kernel/harmonic math is IDENTICAL to the single-phase
    code; this just wraps the specimen-symmetry expansion + engine dispatch so it
    can be called once per phase. Mirrors notebook cell 38b7d124 `_build_odf`."""
    from orix.quaternion import Orientation, Rotation
    import orix.quaternion.symmetry as _sym
    sgrp = getattr(_sym, _SAMPLE_GROUPS[cfg.sample_sym])

    if cfg.odf_method == "kernel":
        if sgrp.size > 1:
            O0 = Orientation.from_euler(eulers_odf)
            eul_use = Orientation(Rotation(
                np.concatenate([(s * O0).data for s in sgrp], 0))).to_euler()
        else:
            eul_use = eulers_odf
        odf_eval, J = _make_kernel_eval(eul_use, pg, cfg.odf_halfwidth)
    elif cfg.odf_method == "harmonic":
        from . import odf_mtex
        _o = odf_mtex.ODF(eulers_odf, crystal_symmetry=pg, specimen_symmetry=sgrp,
                          halfwidth_deg=cfg.odf_halfwidth, max_L=cfg.harmonic_lmax)
        odf_eval = lambda e: _o.eval(np.atleast_2d(e))
        J = _o.J
    else:
        raise ValueError(f"odf_method must be 'kernel' or 'harmonic', got {cfg.odf_method!r}")
    return odf_eval, J


def run_odf(cfg: Config, res: MicroResult, log=print) -> ODFResult:
    """Per-phase ODF (MTEX-style): loop over res.phases, honour cfg.odf_phase_id,
    each phase with its own crystal point group. Keeps a dominant-phase view under
    the old single-phase attribute names so plotting.py/report.py keep working.
    Mirrors notebook cells 31a17096 + 38b7d124."""
    from orix.quaternion import Orientation, Rotation
    from orix.vector import Vector3d

    out = ODFResult()
    out.method = cfg.odf_method

    # --- common Euler section grid (shared across phases) --------------------
    phi1_deg = np.arange(0, 90 + cfg.section_step, cfg.section_step)
    Phi_deg = np.arange(0, 90 + cfg.section_step, cfg.section_step)
    phi2_deg = np.array(cfg.phi2_sections)
    p1, Ph, p2 = np.meshgrid(phi1_deg, Phi_deg, phi2_deg, indexing='ij')
    grid_flat = np.stack([p1, Ph, p2], axis=-1).reshape(-1, 3) * np.pi / 180.0
    Phi_line = np.linspace(0, 90, 181)
    phi1_line = np.linspace(0, 90, 181)
    alpha_eu = np.column_stack([np.zeros_like(Phi_line), Phi_line,
                                np.full_like(Phi_line, 45.0)]) * np.pi / 180
    gamma_eu = np.column_stack([phi1_line, np.full_like(phi1_line, 54.7),
                                np.full_like(phi1_line, 45.0)]) * np.pi / 180

    ci = res.ci.ravel(); phase_flat = res.phase.ravel(); euler = res.euler
    rng_odf = np.random.default_rng(cfg.seed)

    for p in res.phases:
        if cfg.odf_phase_id is not None and p["id"] != int(cfg.odf_phase_id):
            continue
        m = (ci >= cfg.ci_threshold) & (phase_flat == p["id"])
        good = euler[m]
        good = good[~np.isnan(good).any(1)]        # guard stray NaN euler (.ang)
        if len(good) < 100:
            log(f"  phase {p['name']} (id {p['id']}): only {len(good)} valid pts -> skipped")
            continue
        if cfg.n_sample is not None and cfg.n_sample < len(good):
            good = good[rng_odf.choice(len(good), cfg.n_sample, replace=False)]
        if cfg.rotate_axis is not None:
            av = {'RD': Vector3d([1, 0, 0]), 'TD': Vector3d([0, 1, 0]),
                  'ND': Vector3d([0, 0, 1])}[cfg.rotate_axis]
            good = (Rotation.from_axes_angles(av, np.deg2rad(cfg.rotate_angle)) *
                    Orientation.from_euler(good)).to_euler()
        log(f"  phase {p['name']} (id {p['id']}, {p['sym']}): {len(good):,} orientations for ODF")

        odf_eval, J = _build_phase_odf_eval(cfg, good, p["pg"], log)
        odf = odf_eval(grid_flat).reshape(p1.shape)
        amax = odf.argmax()
        max_loc = f"phi1={p1.flat[amax]:.0f} Phi={Ph.flat[amax]:.0f} phi2={p2.flat[amax]:.0f}"
        comps = BCC_COMPONENTS if p["kind"].upper() == "BCC" else FCC_COMPONENTS
        pr = PhaseODF(pid=p["id"], name=p["name"], sym=p["sym"], kind=p["kind"],
                      n=len(good), J=J, eulers_odf=good, odf=odf, odf_max_loc=max_loc,
                      components=comps,
                      Phi_line=Phi_line, f_alpha=odf_eval(alpha_eu),
                      phi1_line=phi1_line, f_gamma=odf_eval(gamma_eu))
        out.per_phase[p["id"]] = pr
        log(f"[{p['name']}] {cfg.odf_method} ODF: J={J:.3f}  "
            f"range[{odf.min():.2f},{odf.max():.2f}]  max@ {max_loc}")

    if not out.per_phase:
        raise ValueError("no phase had enough valid orientations for an ODF")
    log(f"ODF computed for {len(out.per_phase)} phase(s)")

    # --- expose dominant phase under the old single-phase names (compat) -----
    dom = res.dominant_pid if res.dominant_pid in out.per_phase else next(iter(out.per_phase))
    out.dominant_pid = dom
    d = out.per_phase[dom]
    out.eulers_odf = d.eulers_odf
    out.J = d.J
    out.phi1_deg, out.Phi_deg, out.phi2_deg = phi1_deg, Phi_deg, phi2_deg
    out.odf = d.odf
    out.odf_max_loc = d.odf_max_loc
    out.Phi_line, out.f_alpha = d.Phi_line, d.f_alpha
    out.phi1_line, out.f_gamma = d.phi1_line, d.f_gamma
    out.components = d.components
    return out
