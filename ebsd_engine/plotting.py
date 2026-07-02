"""Figure builders — ports the plotting from notebook sections §4–§12.

Every function returns a matplotlib Figure so it can be (a) embedded in the Qt
canvas, or (b) grabbed as PNG bytes for the PowerPoint report. No plt.show().
"""
from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch

from .config import Config
from .microstructure import MicroResult
from .odf import ODFResult


def _fig(w=5, h=9):
    """Figure with constrained layout so it stays fully visible at any canvas
    aspect ratio (no top-left cropping) and also packs tightly in the report."""
    return Figure(figsize=(w, h), layout="constrained")


# ---------------------------------------------------------------- maps (§4–7)
def fig_iq(res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    im = ax.imshow(res.iq, cmap="gray", extent=res.extent, interpolation="nearest")
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]"); ax.set_title("IQ"); ax.set_aspect("equal")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="IQ")
    return fig


def fig_ci(res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    im = ax.imshow(res.ci, cmap="RdYlGn", extent=res.extent, interpolation="nearest", vmin=0, vmax=1)
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]"); ax.set_title("CI"); ax.set_aspect("equal")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="CI")
    return fig


def fig_ipf(cfg: Config, res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    ax.imshow(res.rgb_map, extent=res.extent, interpolation="nearest")
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]")
    ax.set_title(f"IPF [{cfg.dir_str}]"); ax.set_aspect("equal")
    return fig


def fig_gb(cfg: Config, res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    ax.imshow(res.iq, cmap="gray", extent=res.extent, interpolation="nearest", alpha=0.25)
    if res.lagb_segs: ax.add_collection(LineCollection(res.lagb_segs, colors="blue", linewidths=0.3))
    if res.hagb_segs: ax.add_collection(LineCollection(res.hagb_segs, colors="black", linewidths=0.5))
    ax.set_xlim(res.extent[0], res.extent[1]); ax.set_ylim(res.extent[2], res.extent[3])
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]")
    ax.set_title(f"GB Map (LAGB>={cfg.lagb_angle}deg HAGB>={cfg.hagb_angle}deg)"); ax.set_aspect("equal")
    ax.legend(handles=[Patch(fc="black", label="HAGB"), Patch(fc="silver", label="LAGB")],
              loc="upper right", fontsize=7)
    return fig


def fig_ipf_hagb(cfg: Config, res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    ax.imshow(res.rgb_map, extent=res.extent, interpolation="nearest")
    if res.hagb_segs: ax.add_collection(LineCollection(res.hagb_segs, colors="black", linewidths=0.4))
    ax.set_xlim(res.extent[0], res.extent[1]); ax.set_ylim(res.extent[2], res.extent[3])
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]")
    ax.set_title(f"IPF [{cfg.dir_str}] + HAGB"); ax.set_aspect("equal")
    return fig


def fig_grains(cfg: Config, res: MicroResult) -> Figure:
    fig = _fig(); ax = fig.add_subplot(111)
    ax.imshow(res.colors[res.labels_clean], extent=res.extent, interpolation="nearest")
    if res.hagb_segs: ax.add_collection(LineCollection(res.hagb_segs, colors="black", linewidths=0.3))
    ax.set_xlim(res.extent[0], res.extent[1]); ax.set_ylim(res.extent[2], res.extent[3])
    ax.set_xlabel("x [um]"); ax.set_ylabel("y [um]")
    ax.set_title(f"Grain Map ({res.n_grains} grains)"); ax.set_aspect("equal")
    return fig


# ---------------------------------------------------------------- grain size (§9)
def _gs_count(fig, res: MicroResult, bins=40):
    axes = fig.subplots(1, 3)
    ax = axes[0]; ax.hist(res.g_diam_um, bins=bins, color="steelblue", edgecolor="white", lw=0.4)
    ax.axvline(res.g_diam_um.mean(), color="red", ls="--", lw=1.5, label=f"mean={res.g_diam_um.mean():.1f} um")
    ax.set_xlabel("Equiv. Diameter [um]"); ax.set_ylabel("Count"); ax.set_title("(a) Diameter - count"); ax.legend(fontsize=9)
    ax.text(0.95, 0.85, f"ASTM G = {res.G_e2627:.1f}", transform=ax.transAxes, ha="right", fontsize=11,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8))
    ax = axes[1]; ax.hist(res.g_area_um2, bins=bins, color="darkorange", edgecolor="white", lw=0.4)
    ax.axvline(res.g_area_um2.mean(), color="red", ls="--", lw=1.5, label=f"mean={res.g_area_um2.mean():.0f} um2")
    ax.set_xlabel("Grain Area [um2]"); ax.set_ylabel("Count"); ax.set_title("(b) Area - count"); ax.legend(fontsize=9)
    ax = axes[2]; ax.plot(res.d_s, res.cum, "k-", lw=1.5); ax.axhline(0.5, color="gray", ls=":", lw=0.8)
    if res.d50i < len(res.d_s): ax.axvline(res.d_s[res.d50i], color="red", ls="--", lw=1.5, label=f"d50={res.d_s[res.d50i]:.1f} um")
    ax.set_xlabel("Equiv. Diameter [um]"); ax.set_ylabel("Cum. Area Fraction"); ax.set_title("(c) Cumulative (Area-Weighted)")
    ax.legend(fontsize=9); ax.set_ylim(0, 1.05)


def _gs_frac(fig, res: MicroResult, nbins=40):
    axes = fig.subplots(1, 3)
    ax = axes[0]
    bins = np.linspace(res.g_diam_um.min(), res.g_diam_um.max(), nbins + 1); bi = np.digitize(res.g_diam_um, bins) - 1
    ba = np.array([res.g_area_um2[bi == k].sum() for k in range(len(bins) - 1)]); baf = ba / ba.sum()
    ax.bar(bins[:-1], baf, width=np.diff(bins), align="edge", color="steelblue", edgecolor="white", lw=0.4)
    ax.axvline(res.d_num, color="red", ls="--", lw=1.5, label=f"number avg={res.d_num:.1f} um")
    ax.axvline(res.d_w, color="blue", ls=":", lw=1.5, label=f"area-wt avg={res.d_w:.1f} um")
    ax.set_xlabel("Grain Size (Diameter) [um]"); ax.set_ylabel("Area Fraction"); ax.set_title("(a) Diameter - area fraction"); ax.legend(fontsize=8)
    ax.text(0.95, 0.8, f"ASTM G = {res.G_e2627:.1f}", transform=ax.transAxes, ha="right", fontsize=11,
            bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8))
    ax = axes[1]
    bins_a = np.linspace(res.g_area_um2.min(), res.g_area_um2.max(), nbins + 1); bi2 = np.digitize(res.g_area_um2, bins_a) - 1
    af = np.array([res.g_area_um2[bi2 == k].sum() for k in range(len(bins_a) - 1)]); af = af / af.sum()
    ax.bar(bins_a[:-1], af, width=np.diff(bins_a), align="edge", color="darkorange", edgecolor="white", lw=0.4)
    ax.axvline(res.g_area_um2.mean(), color="red", ls="--", lw=1.5, label=f"number avg={res.g_area_um2.mean():.0f} um2")
    ax.axvline(res.A_bar_w, color="blue", ls=":", lw=1.5, label=f"area-wt avg={res.A_bar_w:.0f} um2")
    ax.set_xlabel("Grain Area [um2]"); ax.set_ylabel("Area Fraction"); ax.set_title("(b) Area - area fraction"); ax.legend(fontsize=8)
    ax = axes[2]; ax.plot(res.d_s, res.cum, "k-", lw=1.5); ax.axhline(0.5, color="gray", ls=":", lw=0.8)
    if res.d50i < len(res.d_s): ax.axvline(res.d_s[res.d50i], color="red", ls="--", lw=1.5, label=f"d50={res.d_s[res.d50i]:.1f} um")
    ax.set_xlabel("Equiv. Diameter [um]"); ax.set_ylabel("Cum. Area Fraction"); ax.set_title("(c) Cumulative (Area-Weighted)")
    ax.legend(fontsize=9); ax.set_ylim(0, 1.05)


def fig_grain_size_count(res: MicroResult, bins: int = 40) -> Figure:
    fig = _fig(15, 4.2); _gs_count(fig, res, bins); return fig


def fig_grain_size_frac(res: MicroResult, bins: int = 40) -> Figure:
    fig = _fig(15, 4.2); _gs_frac(fig, res, bins); return fig


# ---------------------------------------------------------------- ODF (§12)
def fig_odf_sections(cfg: Config, odf: ODFResult) -> Figure:
    odf_disp = np.clip(odf.odf, 0, None)
    phi2_deg = odf.phi2_deg; phi1_deg = odf.phi1_deg; Phi_deg = odf.Phi_deg
    n_sec = len(phi2_deg); ncol = min(4, n_sec); nrow = int(np.ceil(n_sec / ncol))
    fig = _fig(3.2 * ncol, 3.4 * nrow)
    axes = fig.subplots(nrow, ncol, squeeze=False)
    vmax = cfg.odf_vmax if cfg.odf_vmax else np.percentile(odf_disp, 99.5)
    levels = np.linspace(0, max(vmax, 2.0), 15)
    cmap = cfg.odf_cmap
    cs = None
    for k, phi2 in enumerate(phi2_deg):
        ax = axes[k // ncol, k % ncol]; sec = odf_disp[:, :, k]
        cs = ax.contourf(phi1_deg, Phi_deg, sec.T, levels=levels, cmap=cmap, extend='max')
        ax.contour(phi1_deg, Phi_deg, sec.T, levels=levels, colors='k', linewidths=0.3)
        ax.set_title(f"phi2 = {phi2:.0f}deg"); ax.set_xlabel("phi1 [deg]"); ax.set_ylabel("Phi [deg]")
        ax.invert_yaxis(); ax.set_aspect('equal'); ax.set_xticks([0, 30, 60, 90]); ax.set_yticks([0, 30, 60, 90])
        for name, (p1c, Phc, p2c) in odf.components.items():
            if abs(phi2 - p2c) <= cfg.section_step / 2:
                ax.plot(p1c, Phc, 'wo', ms=7, mec='k', mew=1)
                ax.text(p1c + 2, Phc - 3, name, color='w', fontsize=7, weight='bold')
        if cfg.lattice.upper() == "BCC" and abs(phi2 - 45) < 1e-6:
            ax.axhline(54.7, color='w', lw=1.2, ls='--', alpha=0.7); ax.text(62, 51, 'gamma-fiber', color='w', fontsize=7, weight='bold')
            ax.axvline(0, color='w', lw=1.2, ls='--', alpha=0.7); ax.text(2, 82, 'alpha-fiber', color='w', fontsize=7, weight='bold')
    unused = [(k // ncol, k % ncol) for k in range(n_sec, nrow * ncol)]
    for r, c in unused: axes[r, c].axis('off')
    if unused:
        r, c = unused[0]; cax = axes[r, c].inset_axes([0.15, 0.40, 0.75, 0.10])
        fig.colorbar(cs, cax=cax, orientation='horizontal').set_label("f(g)  [mrd]")
    else:
        fig.colorbar(cs, ax=axes, orientation='vertical', shrink=0.8).set_label("f(g)  [mrd]")
    fig.suptitle(f"ODF ({cfg.lattice}) - L_max={cfg.l_max}, J={odf.J:.2f}, N={len(odf.eulers_odf):,}", fontsize=12)
    return fig


def fig_fibers(odf: ODFResult) -> Figure:
    fig = _fig(10, 3.5); ax1, ax2 = fig.subplots(1, 2)
    ax1.plot(odf.Phi_line, odf.f_alpha, 'b-', lw=2); ax1.axhline(1, color='k', ls=':', lw=0.8, label='random')
    ax1.set_xlabel("Phi [deg]"); ax1.set_ylabel("f(g) [mrd]"); ax1.set_title("alpha-fiber  (<110>||RD, phi1=0, phi2=45)")
    ax1.set_xlim(0, 90); ax1.grid(alpha=0.3); ax1.legend(fontsize=8)
    ax2.plot(odf.phi1_line, odf.f_gamma, 'r-', lw=2); ax2.axhline(1, color='k', ls=':', lw=0.8, label='random')
    ax2.set_xlabel("phi1 [deg]"); ax2.set_ylabel("f(g) [mrd]"); ax2.set_title("gamma-fiber  (<111>||ND, Phi=54.7, phi2=45)")
    ax2.set_xlim(0, 90); ax2.grid(alpha=0.3); ax2.legend(fontsize=8)
    return fig
