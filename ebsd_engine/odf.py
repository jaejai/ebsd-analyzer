"""ODF / texture analysis — ports notebook sections §10–§12.

Filter + subsample + optional rotate, GSH coefficients & reconstruction,
phi2-section grid and alpha/gamma fiber lines.
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


@dataclass
class ODFResult:
    eulers_odf: np.ndarray = None
    n_states: np.ndarray = None
    c: np.ndarray = None
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


def run_odf(cfg: Config, res: MicroResult, log=print) -> ODFResult:
    import gsh_core as gc

    out = ODFResult()
    out.components = BCC_COMPONENTS if cfg.lattice.upper() == "BCC" else FCC_COMPONENTS

    # --- §10 filter / subsample / rotate ---
    ci = res.ci; phase = res.phase; euler = res.euler
    mask = (ci.ravel() >= cfg.ci_threshold) & (phase.ravel() == 1)
    eulers_good = euler[mask]
    log(f"Good orientations: {len(eulers_good):,} / {len(euler):,}")

    rng_odf = np.random.default_rng(cfg.seed)
    if cfg.n_sample is not None and cfg.n_sample < len(eulers_good):
        eulers_odf = eulers_good[rng_odf.choice(len(eulers_good), cfg.n_sample, replace=False)]
    else:
        eulers_odf = eulers_good
    log(f"Using {len(eulers_odf):,} orientations for ODF")

    if cfg.rotate_axis is not None:
        from orix.quaternion import Rotation, Orientation
        from orix.vector import Vector3d
        axis_vec = {'RD': Vector3d([1, 0, 0]), 'TD': Vector3d([0, 1, 0]),
                    'ND': Vector3d([0, 0, 1])}[cfg.rotate_axis]
        R = Rotation.from_axes_angles(axis_vec, np.deg2rad(cfg.rotate_angle))
        eulers_odf = (R * Orientation.from_euler(eulers_odf)).to_euler()
        log(f"Rotated {cfg.rotate_angle} deg about {cfg.rotate_axis}")
    else:
        log("No rotation applied")
    out.eulers_odf = eulers_odf

    # --- §11 GSH coefficients & reconstruction ---
    n_states = gc.truncate_to_Lmax(cfg.l_max, domain='cubic')
    c = gc.coefficients(eulers_odf, domain='cubic', n_states=n_states)
    J = gc.texture_index(c, 'cubic', n_states)
    out.n_states, out.c, out.J = n_states, c, J
    log(f"GSH modes: {len(n_states)}   c_0 = {c[0].real:.4f}   Texture index J = {J:.3f}")

    phi1_deg = np.arange(0, 90 + cfg.section_step, cfg.section_step)
    Phi_deg = np.arange(0, 90 + cfg.section_step, cfg.section_step)
    phi2_deg = np.array(cfg.phi2_sections)
    p1, Ph, p2 = np.meshgrid(phi1_deg, Phi_deg, phi2_deg, indexing='ij')
    grid_flat = np.stack([p1, Ph, p2], axis=-1).reshape(-1, 3) * np.pi / 180.0
    odf = gc.reconstruct(grid_flat, c, 'cubic', n_states).reshape(p1.shape)
    out.phi1_deg, out.Phi_deg, out.phi2_deg, out.odf = phi1_deg, Phi_deg, phi2_deg, odf
    log(f"ODF range [{odf.min():.2f}, {odf.max():.2f}] mrd   mean {odf.mean():.3f}")

    amax = odf.argmax()
    out.odf_max_loc = f"phi1={p1.flat[amax]:.0f} Phi={Ph.flat[amax]:.0f} phi2={p2.flat[amax]:.0f}"
    log(f"Max density at {out.odf_max_loc}")

    # --- §12 fibers ---
    Phi_line = np.linspace(0, 90, 181)
    alpha_eu = np.column_stack([np.zeros_like(Phi_line), Phi_line,
                                np.full_like(Phi_line, 45.0)]) * np.pi / 180
    f_alpha = gc.reconstruct(alpha_eu, c, 'cubic', n_states)
    phi1_line = np.linspace(0, 90, 181)
    gamma_eu = np.column_stack([phi1_line, np.full_like(phi1_line, 54.7),
                                np.full_like(phi1_line, 45.0)]) * np.pi / 180
    f_gamma = gc.reconstruct(gamma_eu, c, 'cubic', n_states)
    out.Phi_line, out.f_alpha = Phi_line, f_alpha
    out.phi1_line, out.f_gamma = phi1_line, f_gamma
    log(f"alpha max {f_alpha.max():.2f} mrd   gamma max {f_gamma.max():.2f} mrd")
    return out
