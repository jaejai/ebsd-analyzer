"""MTEX-style ODF estimation from EBSD orientations — de la Vallee Poussin
kernel density, computed as a Wigner-D (generalized spherical harmonic) series
with arbitrary crystal and specimen symmetry.

This reproduces MTEX's `calcDensity(ori, 'halfwidth', hw)`:
  f(g) = (1/M) * sum_i  psi_hw( g * g_i^-1 )
represented in the harmonic (Fourier on SO(3)) domain so it is fast to evaluate
on a dense Euler grid and yields the texture index J directly.

Why not `gsh_core`?  That vendored PyMKS basis is not correctly crystal-
symmetrized (a single crystal expressed in different symmetry-equivalent Euler
angles gave different ODFs).  This module instead takes trustworthy Wigner-D
functions from the `spherical` library and imposes symmetry explicitly by
projecting the harmonic coefficients onto the crystal- and specimen-symmetric
subspace — verified invariant to machine precision.

Convention: the EBSD .ang Euler angles are Bunge (phi1, Phi, phi2) in radians.
To match MTEX's `convertEuler2SpatialReferenceFrame` + internal ZYZ handling we
map  Bunge(phi1,Phi,phi2) -> ZYZ(phi1-pi/2, Phi, phi2+pi/2)  and take the
inverse rotation.  (Verified against MTEX on DP590: peak positions + max mrd.)

Dependencies: numpy, scipy, orix, spherical, quaternionic.
"""
from __future__ import annotations
import numpy as np
from scipy.special import beta as _beta
import quaternionic
import spherical
from orix.quaternion import Orientation, Rotation
from orix.quaternion.symmetry import Symmetry


# ----------------------------------------------------------------------- kernel
def dlvp_kappa(halfwidth_deg: float) -> float:
    """de la Vallee Poussin concentration kappa from the halfwidth (MTEX)."""
    hw = np.radians(halfwidth_deg)
    return 0.5 * np.log(0.5) / np.log(np.cos(hw / 2.0))


def dlvp_peak(kappa: float) -> float:
    """Kernel value at zero misorientation (mrd), C = B(3/2,1/2)/B(3/2,kappa+1/2)."""
    return _beta(1.5, 0.5) / _beta(1.5, kappa + 0.5)


def _dlvp_Ahat(kappa: float, L: int) -> np.ndarray:
    """Chebyshev/Legendre coefficients A_hat_l of the dLVP kernel (A_hat_0 = 1).
    These multiply each Wigner degree-l block (MTEX SO3DeLaValleePoussinKernel)."""
    A = np.zeros(L + 1)
    A[0] = 1.0
    if L >= 1:
        A[1] = kappa / (kappa + 2.0)
    for l in range(1, L):
        A[l + 1] = ((kappa - l + 1.0) * A[l - 1] - (2 * l + 1.0) * A[l]) / (kappa + l + 2.0)
    return A


# --------------------------------------------------------- Euler <-> quaternion
def _matched_quats(eulers_bunge: np.ndarray) -> np.ndarray:
    """Bunge (phi1,Phi,phi2) radians -> quaternion (w,x,y,z).

    The frame map only relabels the ODF in Euler space (it cancels in the
    self-consistent build/eval), so it does not affect J, symmetry invariance,
    or single-crystal recovery. It DOES set where peaks land relative to MTEX's
    phi2-section axes. Verified against MTEX on DP590 (cubic+orthorhombic): the
    identity map reproduces MTEX's peak positions and max intensity (~5.5 mrd);
    the inverse map does not. So we use orix's orientation directly (Bunge)."""
    e = np.atleast_2d(np.asarray(eulers_bunge, float))
    return Orientation.from_euler(e).data


def _proper_group_quats(sym: Symmetry) -> np.ndarray:
    """Quaternions (w,x,y,z) of the PROPER rotations of a point group.
    ODF symmetrization uses proper rotations only (orientations, not directions)."""
    try:
        pg = sym.proper_subgroup
    except Exception:
        pg = sym
    q = pg.data
    return q.reshape(-1, 4)


# ------------------------------------------------------------------------- ODF
class ODF:
    """MTEX-style de la Vallee Poussin kernel ODF with crystal + specimen symmetry.

    Parameters
    ----------
    eulers_bunge : (N,3) array
        Measured orientations, Bunge (phi1,Phi,phi2) in RADIANS.
    crystal_symmetry, specimen_symmetry : orix Symmetry
        e.g. from orix.quaternion.symmetry (Oh for m-3m cubic, D6h for 6/mmm
        hexagonal, C1 for triclinic specimen, D2 for orthorhombic specimen...).
        Only the PROPER rotations are used.
    halfwidth_deg : float
        Kernel halfwidth (MTEX default 10).
    bandwidth : int or None
        Harmonic degree L. None -> auto (round(kappa), capped at max_L).
    max_L : int
        Cap on auto bandwidth (evaluation cost ~ L^3). 32 reproduces hw>=10 well.
    """
    def __init__(self, eulers_bunge, crystal_symmetry, specimen_symmetry=None,
                 halfwidth_deg=10.0, bandwidth=None, max_L=32, subsample=None,
                 random_state=0):
        self.hw = float(halfwidth_deg)
        self.kappa = dlvp_kappa(self.hw)
        self.C = dlvp_peak(self.kappa)
        if bandwidth is None:
            bandwidth = min(int(round(self.kappa)), max_L)
        self.L = int(bandwidth)
        self.A = _dlvp_Ahat(self.kappa, self.L)
        self.w = spherical.Wigner(self.L)
        self.NL = self.w.Dsize
        self._blocks = [(l, self.w.Dindex(l, -l, -l), self.w.Dindex(l, l, l) + 1)
                        for l in range(self.L + 1)]
        # per-index L2 factor (2l+1)
        self._scale = np.empty(self.NL)
        for (l, i0, i1) in self._blocks:
            self._scale[i0:i1] = 2 * l + 1

        eul = np.atleast_2d(np.asarray(eulers_bunge, float))
        if subsample is not None and len(eul) > subsample:
            rng = np.random.default_rng(random_state)
            eul = eul[rng.choice(len(eul), subsample, replace=False)]
        self.n_orientations = len(eul)

        # raw harmonic coefficients  a = < conj(D(g_i)) >   (chunked)
        q = _matched_quats(eul)
        a = np.zeros(self.NL, complex)
        for s in range(0, len(q), 4000):
            e = min(s + 4000, len(q))
            a += np.conj(self.w.D(quaternionic.array(q[s:e]))).sum(0)
        a /= len(q)

        # symmetrize + apply kernel per l-block:  fhat_l = A_l * Sg_l @ a_l @ Cg_l
        Cg = self._group_block_avg(crystal_symmetry)
        Sg = (self._group_block_avg(specimen_symmetry)
              if specimen_symmetry is not None else None)
        # Both crystal and specimen symmetry act on the LEFT of each Wigner block.
        # (Locked by NUMERICALLY matching the direct kernel-density sum — the
        # ground-truth ODF via orix disorientations — to correlation 1.0000.
        # Note: invariance alone is NOT sufficient to pick the placement; a
        # different placement can be self-consistently invariant yet compute the
        # WRONG ODF. The direct-sum match is the decisive test.)
        fhat = np.zeros(self.NL, complex)
        for (l, i0, i1) in self._blocks:
            d = 2 * l + 1
            al = Cg[l] @ a[i0:i1].reshape(d, d)   # crystal symmetry (left)
            if Sg is not None:
                al = Sg[l] @ al                   # specimen symmetry (left)
            fhat[i0:i1] = self.A[l] * al.ravel()
        self.fhat = fhat
        self._coef = fhat * self._scale
        self.J = float(np.sum(self._scale * np.abs(fhat) ** 2))  # texture index

    # -- helpers ------------------------------------------------------------
    def _group_block_avg(self, sym):
        q = _proper_group_quats(sym)
        D = self.w.D(quaternionic.array(q))       # (G, NL)
        return [D[:, i0:i1].reshape(len(q), 2 * l + 1, 2 * l + 1).mean(0)
                for (l, i0, i1) in self._blocks]

    # -- evaluation ---------------------------------------------------------
    def eval(self, eulers_bunge, chunk=6000):
        """ODF value f(g) [mrd] at Bunge Euler angles (radians)."""
        q = _matched_quats(eulers_bunge)
        out = np.empty(q.shape[0])
        for s in range(0, len(q), chunk):
            e = min(s + chunk, len(q))
            D = self.w.D(quaternionic.array(q[s:e]))
            out[s:e] = (D * self._coef).sum(1).real
        return out

    def sections(self, phi2_deg, step_deg=2.5):
        """Return (phi1_deg, Phi_deg, {phi2: 2D f-array}) for phi2 sections."""
        g = np.arange(0, 90 + step_deg, step_deg)
        P1, P2 = np.meshgrid(g, g, indexing="ij")
        out = {}
        for s in np.atleast_1d(phi2_deg):
            grid = np.stack([P1, P2, np.full_like(P1, s)], -1).reshape(-1, 3) * np.pi / 180
            out[float(s)] = self.eval(grid).reshape(P1.shape)
        return g, g, out
