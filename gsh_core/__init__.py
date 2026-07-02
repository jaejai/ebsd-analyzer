"""gsh_core — standalone generalized spherical harmonics for ODF analysis.

Vendored from PyMKS (Kalidindi group, Georgia Tech) — BSD-licensed.
This module provides ONLY the core GSH math needed to compute and
reconstruct orientation distribution functions (ODFs). No sklearn,
no fftw, no versioneer — just numpy.

Basis
-----
For cubic crystal symmetry, 283 symmetrized GSH modes up to L=16.
For hexagonal, 185 symmetrized modes up to L=16.
Mode indices (l, m, n) accessible via `basis_indices(domain)`.

Bunge convention throughout. Euler angles in RADIANS.

API
---
evaluate(eulers, domain, n_states)
    Evaluate GSH basis functions T_l^{mn}(g) at given orientations.
coefficients(eulers, domain, n_states, weights=None)
    Compute GSH expansion coefficients c_s of an ODF from a set of
    discrete orientations. c_s = (1/N) * Σ w_i T_s(g_i).
reconstruct(eulers, c, domain, n_states)
    Evaluate f(g) = Re(Σ_s c_s T_s(g)) at query orientations.
basis_indices(domain, n_states=None)
    (l, m, n) triplets for the selected basis modes.

Normalization
-------------
For uniform texture, c_0 = 1 and f(g) ≡ 1 mrd everywhere.
For sharper textures, c_s grows for s>0.
"""
import numpy as np

from . import gsh_cub_tri_L0_16 as _cub
from . import gsh_hex_tri_L0_16 as _hex

_N_MODES = {"cubic": 283, "hexagonal": 185}
_EVAL   = {"cubic": _cub.gsh_eval,       "hexagonal": _hex.gsh_eval}
_INFO   = {"cubic": _cub.gsh_basis_info, "hexagonal": _hex.gsh_basis_info}


def _resolve_states(n_states, domain):
    if n_states is None:
        return np.arange(_N_MODES[domain])
    if isinstance(n_states, int):
        return np.arange(n_states)
    return np.asarray(n_states)


def basis_indices(domain="cubic", n_states=None):
    """Return (l, m, n) rows for the chosen basis modes."""
    full = _INFO[domain]()
    s = _resolve_states(n_states, domain)
    return full[s, :]


def evaluate(eulers, domain="cubic", n_states=None):
    """Evaluate GSH basis at Bunge Euler angles (radians).

    Parameters
    ----------
    eulers : array_like, shape (..., 3)
        Last axis is (phi1, Phi, phi2) in radians.
    domain : {"cubic", "hexagonal"}
    n_states : int, slice, or 1-D array of mode indices.
        If int N: uses modes 0..N-1. If None: all available modes.

    Returns
    -------
    complex array, shape (..., n_modes)
    """
    s = _resolve_states(n_states, domain)
    return _EVAL[domain](np.asarray(eulers, dtype=float), s)


def coefficients(eulers, domain="cubic", n_states=None, weights=None):
    """GSH expansion coefficients of an ODF from discrete orientations.

    c_s = Σ w_i * T_s(g_i)  with Σ w_i = 1  (default: equal weights).

    For uniform random orientations, c_0 → 1 and c_{s>0} → 0.
    """
    T = evaluate(eulers, domain=domain, n_states=n_states)
    if weights is None:
        return T.mean(axis=0)
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    # broadcast weights along the last (mode) axis
    return (T * w.reshape(w.shape + (1,) * (T.ndim - w.ndim))).sum(axis=0)


def reconstruct(eulers, c, domain="cubic", n_states=None):
    """Evaluate f(g) = Re(Σ_s c_s T_s(g)) in multiples of random distribution (mrd)."""
    T = evaluate(eulers, domain=domain, n_states=n_states)
    return (T * c).sum(axis=-1).real


def truncate_to_Lmax(L_max, domain="cubic"):
    """Return n_states (indices) for all modes with l <= L_max."""
    lvec = _INFO[domain]()[:, 0]
    return np.where(lvec <= L_max)[0]


def texture_index(c, domain="cubic", n_states=None):
    """Bunge's texture index J = Σ |c_s|² / (2l_s + 1).

    J = 1 for uniform texture, larger for sharper textures.
    """
    idx = basis_indices(domain, n_states)
    l = idx[:, 0]
    return float((np.abs(c) ** 2 / (2 * l + 1)).sum())
