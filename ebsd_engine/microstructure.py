"""Loading + microstructure analysis.

Hex->square resampling, orientations & misorientations, IQ/CI/IPF maps,
grain-boundary segments, union-find grain segmentation, ASTM E2627 grain size.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .config import Config


# ============================================================================
# Results container
# ============================================================================
@dataclass
class MicroResult:
    # grid
    nx: int = 0
    ny: int = 0
    step: float = 0.0
    extent: list = field(default_factory=list)
    # maps
    iq: np.ndarray = None
    ci: np.ndarray = None
    phase: np.ndarray = None
    euler: np.ndarray = None          # (ny*nx, 3) radians, Bunge/TSL (post-fill)
    ci_raw: np.ndarray = None         # CI before any clean-up (for display masking)
    n_filled: int = 0                 # low-CI pixels replaced by neighbour-fill
    rgb_map: np.ndarray = None
    # phases (multiphase); single-phase scans -> one entry
    phases: list = field(default_factory=list)   # ordered dicts: id,name,sym,pg,lattice,kind
    dominant_pid: int = 0             # phase id with the most valid pixels
    pid2phase: dict = field(default_factory=dict)
    # misorientation
    mis_h: np.ndarray = None
    mis_v: np.ndarray = None
    # boundaries
    hagb_segs: list = field(default_factory=list)
    lagb_segs: list = field(default_factory=list)
    # per-boundary-class segments, aligned with cfg.boundaries; each entry is
    # {"name","color","width","segs":[...]}. Drives the configurable boundary maps.
    boundary_segs: list = field(default_factory=list)
    # grains
    labels_clean: np.ndarray = None
    colors: np.ndarray = None
    n_grains: int = 0
    n_grains_measured: int = 0
    # grain size
    g_area_px: np.ndarray = None
    g_area_um2: np.ndarray = None
    g_diam_um: np.ndarray = None
    d_num: float = 0.0
    d_w: float = 0.0
    A_bar_w: float = 0.0
    G_e2627: float = 0.0
    d_s: np.ndarray = None
    cum: np.ndarray = None
    d50i: int = 0


# ============================================================================
# §2 — Load scan (multi-format) & hex->square + build phases
# ============================================================================
def load_scan(cfg: Config, log=print) -> MicroResult:
    from scipy.spatial import cKDTree
    from orix.crystal_map import Phase

    from .ebsd_read import read_ebsd, lattice_kind

    raw, meta = read_ebsd(cfg.input_file)
    log(f"[{meta['format']}] Loaded {raw.shape[0]:,} pts x {raw.shape[1]} cols")

    # Crystal symmetry: auto-detect from the file unless set manually in cfg.
    # If auto is requested but the file carries none, fall back to m-3m + warn.
    _sym_file = meta.get("crystal_sym")
    if cfg.crystal_sym is None:
        if _sym_file is None:
            cfg.crystal_sym = "m-3m"
            log("WARNING: no crystal symmetry found in the file; defaulting to "
                "m-3m (cubic). Set it manually in Step 2 if this is wrong.")
        else:
            cfg.crystal_sym = _sym_file
            log(f"crystal_sym auto-detected from file: {cfg.crystal_sym}")
    elif _sym_file is not None and _sym_file != cfg.crystal_sym:
        log(f"NOTE: manual crystal_sym={cfg.crystal_sym} overrides file value {_sym_file}")
    else:
        log(f"crystal_sym = {cfg.crystal_sym} (manual)")

    x_hex, y_hex = raw[:, cfg.col_x], raw[:, cfg.col_y]
    y_uniq = np.unique(np.round(y_hex, 6))
    row0 = np.sort(x_hex[np.abs(y_hex - y_uniq[0]) < 0.05 * np.median(np.diff(y_uniq))])
    hex_step = np.median(np.diff(row0))
    step = hex_step * cfg.grid_ratio

    x1d = np.arange(x_hex.min(), x_hex.max() + step * 0.5, step)
    y1d = np.arange(y_hex.min(), y_hex.max() + step * 0.5, step)
    nx, ny = len(x1d), len(y1d)
    gx, gy = np.meshgrid(x1d, y1d)
    tree = cKDTree(np.column_stack([x_hex, y_hex]))
    _, nn_idx = tree.query(np.column_stack([gx.ravel(), gy.ravel()]))

    res = MicroResult()
    res.nx, res.ny, res.step = nx, ny, step
    res.iq = raw[nn_idx, cfg.col_iq].reshape(ny, nx)
    res.ci = raw[nn_idx, cfg.col_ci].reshape(ny, nx)
    res.phase = raw[nn_idx, cfg.col_phase].reshape(ny, nx).astype(int)
    res.euler = np.column_stack(
        [raw[nn_idx, cfg.col_phi1], raw[nn_idx, cfg.col_phi], raw[nn_idx, cfg.col_phi2]])
    if cfg.euler_unit == "deg":   # engine works in radians (TSL .ang already radians)
        res.euler = np.deg2rad(res.euler)
        log("Converted Euler angles deg -> rad")

    half = step / 2
    res.extent = [-half, (nx - 1) * step + half, (ny - 1) * step + half, -half]
    log(f"Square grid: {nx}x{ny} = {nx*ny:,}   step = {step:.4f} um")

    # keep the raw (pre-fill) CI for display masking decisions
    res.ci_raw = res.ci.copy()

    # --- Phases present in this scan (multiphase) ----------------------------
    # Ordered list of the phases actually present in the data, each with its own
    # crystal point group. Single-phase scans -> one entry.
    def _pg_for(pg_str):
        return Phase(name="x", point_group=pg_str).point_group

    meta_phases = meta.get("phases") or []
    present = [int(v) for v in np.unique(res.phase.ravel())]   # ids in the data
    phases = []
    for ph in meta_phases:
        if ph["id"] not in present:
            continue
        sym = ph["point_group"]
        if sym is None:                    # this phase had no symmetry in header
            sym = cfg.crystal_sym or _sym_file or "m-3m"
            log(f"WARNING: phase {ph['id']} ({ph.get('name') or '?'}) has no "
                f"symmetry in the file; using {sym} for it.")
        phases.append({
            "id": ph["id"],
            "name": ph["name"] or f"phase{ph['id']}",
            "sym": sym,
            "pg": _pg_for(sym),
            "lattice": ph.get("lattice"),
            "kind": lattice_kind(ph.get("lattice"), ph["name"] or ""),
        })
    # fallback if the header carried no phase blocks: one phase per present id
    if not phases:
        sym = cfg.crystal_sym or _sym_file or "m-3m"
        for pid in present:
            phases.append({"id": int(pid), "name": f"phase{pid}", "sym": sym,
                           "pg": _pg_for(sym), "lattice": None,
                           "kind": cfg.lattice.upper()})

    counts = {p["id"]: int((res.phase.ravel() == p["id"]).sum()) for p in phases}
    res.phases = phases
    res.dominant_pid = max(counts, key=counts.get)
    res.pid2phase = {p["id"]: p for p in phases}

    log("Phases present: " + ", ".join(
        f"{p['name']}(id={p['id']},{p['sym']},{p['kind']})" for p in phases))
    log(f"Dominant phase id = {res.dominant_pid}")
    if len(phases) > 1:
        log(f"MULTIPHASE scan: {len(phases)} phases -> per-phase misorientation, "
            f"IPF, grains (phase boundaries split grains) and a separate ODF each.")
    return res


# backward-compat alias for the old single-format name
def load_ang(cfg: Config, log=print) -> MicroResult:
    return load_scan(cfg, log)


# ============================================================================
# Low-CI clean-up (grain dilation / neighbor-fill)
# ============================================================================
def neighbor_fill_low_ci(cfg: Config, res: MicroResult, log=print, max_iter=50):
    """Replace orientations of low-CI (unindexed) pixels with their best-indexed
    neighbour, iteratively, so downstream misorientation / segmentation / grain
    size see clean data instead of random noise. This is the standard EBSD
    "grain dilation" clean-up. Operates on the (ny, nx, 3) euler grid in place.

    A pixel is "bad" if CI < cfg.ci_threshold. Each pass, every bad pixel that
    touches a good pixel adopts the orientation of its highest-CI 8-neighbour and
    becomes good. Repeats until no bad pixels remain or max_iter is hit.
    """
    ny, nx = res.ny, res.nx
    ci = res.ci.copy()
    eul = res.euler.reshape(ny, nx, 3).copy()
    good = ci >= cfg.ci_threshold
    n_bad0 = int((~good).sum())
    if n_bad0 == 0:
        log("Neighbor-fill: no low-CI pixels")
        res.n_filled = 0
        return
    # work CI used to pick the "best" neighbour; bad pixels start at -inf
    work_ci = np.where(good, ci, -np.inf)
    neigh = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    filled_total = 0
    for it in range(max_iter):
        bad = ~good
        if not bad.any():
            break
        # for each bad pixel, find the neighbour with the highest work_ci
        best_ci = np.full((ny, nx), -np.inf)
        best_src = np.full((ny, nx, 2), -1, dtype=np.int64)
        for dy, dx in neigh:
            y0s, y0e = max(0, -dy), ny - max(0, dy)
            x0s, x0e = max(0, -dx), nx - max(0, dx)
            # neighbour value placed at the bad-pixel location
            shifted = np.full((ny, nx), -np.inf)
            shifted[y0s:y0e, x0s:x0e] = work_ci[y0s + dy:y0e + dy, x0s + dx:x0e + dx]
            take = shifted > best_ci
            best_ci = np.where(take, shifted, best_ci)
            ys, xs = np.nonzero(take)
            best_src[ys, xs, 0] = ys + dy
            best_src[ys, xs, 1] = xs + dx
        fillable = bad & np.isfinite(best_ci)
        ys, xs = np.nonzero(fillable)
        if ys.size == 0:
            break
        sy = best_src[ys, xs, 0]; sx = best_src[ys, xs, 1]
        eul[ys, xs, :] = eul[sy, sx, :]
        work_ci[ys, xs] = ci[ys, xs]   # now treated as indexed for later passes
        good[ys, xs] = True
        filled_total += ys.size
    res.euler = eul.reshape(-1, 3)
    res.n_filled = filled_total
    log(f"Neighbor-fill: filled {filled_total:,} / {n_bad0:,} low-CI pixels "
        f"(CI<{cfg.ci_threshold}) in {it+1} passes")
    return res


# ============================================================================
# §3 — Orientations & misorientations
# ============================================================================
def compute_misorientation(cfg: Config, res: MicroResult, log=print):
    from orix.quaternion import Orientation
    from orix.crystal_map import Phase

    # Per-phase orientations + misorientation. Neighbour pairs are only meaningful
    # within the SAME phase (you cannot compare a BCC orientation to an FCC one),
    # so cross-phase neighbours get misorientation = +inf and thus act as
    # boundaries (they never link grains and draw as boundaries).
    ny, nx = res.ny, res.nx
    dom_pg = res.pid2phase[res.dominant_pid]["pg"]
    ori = Orientation.from_euler(res.euler, symmetry=dom_pg).reshape(ny, nx)
    qdata = ori.data                    # raw quaternions (symmetry only tags frame)
    phase_grid = res.phase.reshape(ny, nx)

    t0 = time.time()
    mis_h = np.full((ny, nx - 1), np.inf)
    mis_v = np.full((ny - 1, nx), np.inf)

    same_h = (phase_grid[:, :-1] == phase_grid[:, 1:])
    same_v = (phase_grid[:-1, :] == phase_grid[1:, :])

    for p in res.phases:
        pg = p["pg"]; pid = p["id"]
        hmask = same_h & (phase_grid[:, :-1] == pid)
        if hmask.any():
            qL = qdata[:, :-1, :][hmask]; qR = qdata[:, 1:, :][hmask]
            mis_h[hmask] = Orientation(qL, symmetry=pg).angle_with(
                Orientation(qR, symmetry=pg), degrees=True)
        vmask = same_v & (phase_grid[:-1, :] == pid)
        if vmask.any():
            qT = qdata[:-1, :, :][vmask]; qB = qdata[1:, :, :][vmask]
            mis_v[vmask] = Orientation(qT, symmetry=pg).angle_with(
                Orientation(qB, symmetry=pg), degrees=True)

    res.mis_h, res.mis_v = mis_h, mis_v
    log(f"Per-phase misorientation done in {time.time()-t0:.1f}s")
    finite_h = np.isfinite(mis_h); finite_v = np.isfinite(mis_v)
    log(f"HAGB (valid same-phase pairs only): "
        f"H {np.mean(mis_h[finite_h]>=cfg.hagb_angle):.1%}  "
        f"V {np.mean(mis_v[finite_v]>=cfg.hagb_angle):.1%}")
    if len(res.phases) > 1:
        xh = int((~same_h).sum()); xv = int((~same_v).sum())
        log(f"Phase-boundary links treated as grain boundaries: H {xh:,}  V {xv:,}")


# ============================================================================
# §5 — IPF map
# ============================================================================
def compute_ipf(cfg: Config, res: MicroResult, log=print):
    from orix.quaternion import Orientation
    from orix.plot import IPFColorKeyTSL
    from orix.vector import Vector3d

    # IPF colouring is symmetry-dependent, so colour each phase with ITS OWN
    # point group and composite into one map (multiphase IPF).
    ny, nx = res.ny, res.nx
    rgb = np.zeros((ny * nx, 3))
    phase_flat = res.phase.ravel()
    for p in res.phases:
        sel = phase_flat == p["id"]
        if not sel.any():
            continue
        ori_p = Orientation.from_euler(res.euler[sel], symmetry=p["pg"])
        key = IPFColorKeyTSL(p["pg"], direction=Vector3d(list(cfg.ipf_dir)))
        rgb[sel] = key.orientation2color(ori_p)
    rgb = rgb.reshape(ny, nx, 3).copy()
    if not cfg.ci_mask:
        # grey out sub-threshold CI pixels.
        rgb[res.ci < cfg.ci_threshold] = cfg.low_ci_fill
    # when ci_mask is on, low-CI pixels were neighbour-filled with valid
    # orientations, so the IPF map shows them coloured (clean) rather than grey.
    res.rgb_map = rgb


# ============================================================================
# §6 — Grain-boundary segments
# ============================================================================
def make_segments(mis_h, mis_v, step, ny, nx, lagb, hagb):
    half = step / 2
    hagb_s, lagb_s = [], []
    for mask, sl in [(mis_h >= hagb, hagb_s), ((mis_h >= lagb) & (mis_h < hagb), lagb_s)]:
        jj, ii = np.nonzero(mask)
        xe = (ii + 1) * step - half; yc = jj * step
        sl.extend([[(x, y - half), (x, y + half)] for x, y in zip(xe, yc)])
    for mask, sl in [(mis_v >= hagb, hagb_s), ((mis_v >= lagb) & (mis_v < hagb), lagb_s)]:
        jj, ii = np.nonzero(mask)
        ye = (jj + 1) * step - half; xc = ii * step
        sl.extend([[(x - half, y), (x + half, y)] for x, y in zip(xc, ye)])
    return hagb_s, lagb_s


def _range_segments(mis_h, mis_v, step, lo, hi):
    """Boundary segments for pairs whose misorientation is in [lo, hi) degrees."""
    half = step / 2
    segs = []
    mh = (mis_h >= lo) & (mis_h < hi)
    jj, ii = np.nonzero(mh)
    xe = (ii + 1) * step - half; yc = jj * step
    segs.extend([[(x, y - half), (x, y + half)] for x, y in zip(xe, yc)])
    mv = (mis_v >= lo) & (mis_v < hi)
    jj, ii = np.nonzero(mv)
    ye = (jj + 1) * step - half; xc = ii * step
    segs.extend([[(x - half, y), (x + half, y)] for x, y in zip(xc, ye)])
    return segs


def compute_boundaries(cfg: Config, res: MicroResult, log=print):
    # per-boundary-class segments (configurable count / range / color / width)
    res.boundary_segs = []
    for b in cfg.boundaries:
        segs = _range_segments(res.mis_h, res.mis_v, res.step, b["lo"], b["hi"])
        res.boundary_segs.append({"name": b.get("name", ""),
                                  "color": b.get("color", "black"),
                                  "width": float(b.get("width", 0.5)),
                                  "lo": b["lo"], "hi": b["hi"], "segs": segs})
        log(f"{b.get('name','bnd')} [{b['lo']:.0f},{b['hi']:.0f}) segs: {len(segs):,}")
    # back-compat: keep hagb_segs/lagb_segs populated from the classic thresholds
    res.hagb_segs, res.lagb_segs = make_segments(
        res.mis_h, res.mis_v, res.step, res.ny, res.nx, cfg.lagb_angle, cfg.hagb_angle)


# ============================================================================
# §8 — Grain segmentation (union-find)
# ============================================================================
class UnionFind:
    def __init__(self, n):
        self.p = np.arange(n, dtype=np.int64); self.r = np.zeros(n, dtype=np.int32)

    def find(self, x):
        root = x
        while self.p[root] != root: root = self.p[root]
        while self.p[x] != root: self.p[x], x = root, self.p[x]
        return root

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b: return
        if self.r[a] < self.r[b]: a, b = b, a
        self.p[b] = a
        if self.r[a] == self.r[b]: self.r[a] += 1


def _diag_misorientation(cfg, res):
    """Misorientation to the down-right and down-left diagonal neighbours,
    computed lazily only when 8-connectivity is requested. Per-phase with
    cross-phase pairs = +inf (phase boundaries), same pattern as
    compute_misorientation."""
    from orix.quaternion import Orientation
    ny, nx = res.ny, res.nx
    dom_pg = res.pid2phase[res.dominant_pid]["pg"]
    q = Orientation.from_euler(res.euler, symmetry=dom_pg).reshape(ny, nx).data
    ph = res.phase.reshape(ny, nx)

    mis_dr = np.full((ny - 1, nx - 1), np.inf)   # (j,i) vs (j+1,i+1)
    mis_dl = np.full((ny - 1, nx - 1), np.inf)   # (j,i) vs (j+1,i-1)
    same_dr = (ph[:-1, :-1] == ph[1:, 1:])
    same_dl = (ph[:-1, 1:] == ph[1:, :-1])
    for p in res.phases:
        pg = p["pg"]; pid = p["id"]
        m = same_dr & (ph[:-1, :-1] == pid)
        if m.any():
            a = q[:-1, :-1, :][m]; b = q[1:, 1:, :][m]
            mis_dr[m] = Orientation(a, symmetry=pg).angle_with(
                Orientation(b, symmetry=pg), degrees=True)
        m = same_dl & (ph[:-1, 1:] == pid)
        if m.any():
            a = q[:-1, 1:, :][m]; b = q[1:, :-1, :][m]
            mis_dl[m] = Orientation(a, symmetry=pg).angle_with(
                Orientation(b, symmetry=pg), degrees=True)
    return mis_dr, mis_dl


def segment_grains(cfg: Config, res: MicroResult, log=print):
    ny, nx = res.ny, res.nx
    uf = UnionFind(ny * nx)
    for j in range(ny):
        for i in range(nx - 1):
            if res.mis_h[j, i] < cfg.hagb_angle: uf.union(j * nx + i, j * nx + i + 1)
    for j in range(ny - 1):
        for i in range(nx):
            if res.mis_v[j, i] < cfg.hagb_angle: uf.union(j * nx + i, (j + 1) * nx + i)
    if cfg.connectivity == 8:
        mis_dr, mis_dl = _diag_misorientation(cfg, res)
        for j in range(ny - 1):
            for i in range(nx - 1):
                if mis_dr[j, i] < cfg.hagb_angle: uf.union(j * nx + i, (j + 1) * nx + i + 1)
            for i in range(1, nx):
                if mis_dl[j, i - 1] < cfg.hagb_angle: uf.union(j * nx + i, (j + 1) * nx + i - 1)

    labels = np.empty(ny * nx, dtype=np.int64)
    root2id = {}; gid = 0
    for k in range(ny * nx):
        r = uf.find(k)
        if r not in root2id: root2id[r] = gid; gid += 1
        labels[k] = root2id[r]
    labels = labels.reshape(ny, nx)

    sizes = np.bincount(labels.ravel())
    remap = np.zeros(gid, dtype=np.int64); nid = 1
    for g in range(gid):
        if sizes[g] >= cfg.min_grain_px: remap[g] = nid; nid += 1
    res.labels_clean = remap[labels]
    res.n_grains = nid - 1
    log(f"Grains >= {cfg.min_grain_px}px: {res.n_grains}")

    rng = np.random.default_rng(cfg.seed)
    colors = np.zeros((res.n_grains + 1, 3)); colors[1:] = rng.random((res.n_grains, 3)); colors[0] = 0.3
    res.colors = colors


# ============================================================================
# §9 — Grain size (ASTM E2627)
# ============================================================================
def grain_size(cfg: Config, res: MicroResult, log=print):
    labels = res.labels_clean
    counts = np.bincount(labels.ravel())          # index 0 = background
    keep = np.ones(len(counts), dtype=bool); keep[0] = False
    if cfg.exclude_edge_grains:
        edge_ids = set(np.unique(labels[0, :])) | set(np.unique(labels[-1, :])) \
            | set(np.unique(labels[:, 0])) | set(np.unique(labels[:, -1]))
        for gid in edge_ids:
            if gid != 0:
                keep[gid] = False
        log(f"Excluded {len(edge_ids - {0})} edge-touching grains")
    g_area_px = counts[keep]
    g_area_um2 = g_area_px * res.step**2
    g_diam_um = np.sqrt(4 * g_area_um2 / np.pi)

    A_bar_mm2 = g_area_um2.mean() * 1e-6
    d_num = np.sqrt(4 * g_area_um2.mean() / np.pi)
    G_e2627 = cfg.astm_c1 * np.log10(A_bar_mm2) + cfg.astm_c2
    A_bar_w = np.sum(g_area_um2**2) / np.sum(g_area_um2)
    d_w = np.sqrt(4 * A_bar_w / np.pi)

    idx_s = np.argsort(g_diam_um); d_s, a_s = g_diam_um[idx_s], g_area_um2[idx_s]
    cum = np.cumsum(a_s) / a_s.sum(); d50i = int(np.searchsorted(cum, 0.5))

    res.g_area_px = g_area_px
    res.g_area_um2 = g_area_um2
    res.g_diam_um = g_diam_um
    res.d_num = d_num
    res.d_w = d_w
    res.A_bar_w = A_bar_w
    res.G_e2627 = G_e2627
    res.d_s = d_s
    res.cum = cum
    res.d50i = d50i
    res.n_grains_measured = int(g_area_px.size)

    log(f"Grains: {res.n_grains_measured}   ASTM E2627 G: {G_e2627:.1f}")
    log(f"Number avg diam: {d_num:.2f} um   Area-weighted diam: {d_w:.2f} um")


# ============================================================================
# Orchestration
# ============================================================================
def run_microstructure(cfg: Config, log=print) -> MicroResult:
    res = load_scan(cfg, log)
    if cfg.ci_mask:
        neighbor_fill_low_ci(cfg, res, log)   # clean low-CI noise before analysis
    compute_misorientation(cfg, res, log)
    compute_ipf(cfg, res, log)
    compute_boundaries(cfg, res, log)
    segment_grains(cfg, res, log)
    grain_size(cfg, res, log)
    return res
