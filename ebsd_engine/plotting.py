"""Figure builders.

Every function returns a matplotlib Figure so it can be (a) embedded in the Qt
canvas, or (b) grabbed as PNG bytes for the PowerPoint report. No plt.show().

Microstructure maps follow the OIM presentation convention: only the map name,
the IPF colour-key triangle and the micron marker are painted onto the image
(`_overlay`), while the intensity legend is drawn in a strip BELOW the map
(`_external_cbar`) so it never covers the data. All three are optional.
"""
from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch, Rectangle
from matplotlib import cm
from matplotlib import patheffects as pe
from matplotlib.colors import Normalize

from .config import Config
from .microstructure import MicroResult
from .odf import ODFResult


def _fig(w=5, h=9):
    """Figure with constrained layout so it stays fully visible at any canvas
    aspect ratio (no top-left cropping) and also packs tightly in the report."""
    return Figure(figsize=(w, h), layout="constrained")


#: height (inches) of the legend strip added beneath a micrograph
_CBAR_STRIP_IN = 1.05


def _map_fig(cbar=False):
    """Figure for a micrograph.

    The image axes are ALWAYS the same size (5 x 9 in). When a legend strip is
    requested the FIGURE grows taller to accommodate it, rather than the image
    axes shrinking — otherwise toggling the intensity bar would rescale the
    micrograph and change the on-screen length of the scale bar.

    Returns (fig, ax, cax) — cax is None when no legend strip was requested.
    """
    img_w, img_h = 5.0, 9.0
    if cbar:
        total_h = img_h + _CBAR_STRIP_IN
        fig = Figure(figsize=(img_w, total_h))
        # image axes keep their full 5x9 area, pinned to the top
        ax = fig.add_axes([0.0, _CBAR_STRIP_IN / total_h, 1.0, img_h / total_h])
        cax = fig.add_axes([0.18, 0.40 * _CBAR_STRIP_IN / total_h,
                            0.64, 0.20 * _CBAR_STRIP_IN / total_h])
    else:
        fig = Figure(figsize=(img_w, img_h))
        ax = fig.add_axes([0, 0, 1, 1])
        cax = None
    ax.set_aspect("equal")
    return fig, ax, cax


# --------------------------------------------------------------- OIM overlays
def _nice_bar_len(extent_um):
    """Pick a 'nice' scale-bar length (1, 2 or 5 x 10^n) close to a quarter of
    the image width — the proportion OIM's micron marker typically occupies."""
    span = abs(extent_um[1] - extent_um[0])
    raw = span / 4.0
    if raw <= 0:
        return 1.0
    p = 10 ** np.floor(np.log10(raw))
    for m in (5, 2, 1):
        if m * p <= raw:
            return m * p
    return p


# cache of rasterised IPF colour-key triangles, keyed by (point-group name, dir)
_IPFKEY_CACHE = {}


def _ipf_key_image(pg, direction):
    """Rasterise the EDAX/TSL stereographic-triangle IPF colour key (via orix,
    the authoritative TSL key) to an RGBA array we can inset onto a map."""
    key = (pg.name, tuple(int(v) for v in direction))
    if key in _IPFKEY_CACHE:
        return _IPFKEY_CACHE[key]
    from orix.plot import IPFColorKeyTSL
    from orix.vector import Vector3d
    import matplotlib.pyplot as _plt
    k = IPFColorKeyTSL(pg, direction=Vector3d(list(direction)))
    kfig = k.plot(return_figure=True)
    kfig.set_dpi(120)
    kfig.canvas.draw()
    buf = np.asarray(kfig.canvas.buffer_rgba()).copy()
    _plt.close(kfig)
    # crop away surrounding white so the inset is tight
    rgb = buf[..., :3]
    nonwhite = np.any(rgb < 250, axis=2)
    ys, xs = np.where(nonwhite)
    if ys.size:
        buf = buf[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    _IPFKEY_CACHE[key] = buf
    return buf


def _scalebar(cfg, res, ax):
    """Micron marker drawn the way OIM does it: a plain SOLID BLACK bar sitting
    on an opaque WHITE background box, with the length and unit printed in black
    directly UNDER the bar. No end caps, no outline tricks — the white box is
    what makes it readable over any map."""
    if not cfg.show_scalebar:
        return
    ext = res.extent
    L = cfg.scalebar_um or _nice_bar_len(ext)
    xspan = ext[1] - ext[0]
    fL = (L / xspan) if xspan else 0.2                 # bar length, axes fraction

    pad_x, pad_top = 0.022, 0.012                      # padding inside the box
    bar_h = 0.008                                      # black bar thickness
    text_h = 0.026                                     # room for the label
    box_w = fL + 2 * pad_x
    box_h = pad_top + bar_h + text_h
    bx, by = 0.040, 0.035                              # lower-left corner of box

    # white background box
    ax.add_patch(Rectangle((bx, by), box_w, box_h, transform=ax.transAxes,
                           fc="white", ec="none", zorder=6))
    # solid black bar, sitting near the top of the box
    bar_y = by + box_h - pad_top - bar_h
    ax.add_patch(Rectangle((bx + pad_x, bar_y), fL, bar_h,
                           transform=ax.transAxes, fc="black", ec="none", zorder=7))
    # length + unit, black text, centred UNDER the bar
    ax.text(bx + box_w / 2, bar_y - 0.004, f"{L:g} µm", transform=ax.transAxes,
            ha="center", va="top", fontsize=8.5, color="black", zorder=8)


def _external_cbar(cfg, fig, cax, mappable, label=""):
    """Intensity legend drawn OUTSIDE the micrograph, in the strip beneath it."""
    if cax is None or mappable is None or not cfg.show_colorbar:
        if cax is not None:
            cax.axis("off")
        return
    cb = fig.colorbar(mappable, cax=cax, orientation="horizontal")
    vmin, vmax = mappable.get_clim()
    cb.set_ticks([vmin, vmax])
    cb.ax.set_xticklabels([f"{vmin:g}", f"{vmax:g}"], fontsize=9, color="#1a2230")
    cb.ax.tick_params(length=2, pad=2, colors="#1a2230")
    cb.outline.set_edgecolor("#1a2230"); cb.outline.set_linewidth(0.7)
    if label:
        cax.set_title(label, fontsize=9.5, color="#1a2230", pad=4, weight="bold")


def _overlay(cfg: Config, res: MicroResult, ax, *, title=None, ipf_key=None):
    """Draw the in-image decorations on a micrograph axes (all optional).

    Only things OIM actually paints onto the map live here: the map name, the
    IPF colour-key triangle, and the micron marker. The intensity legend is NOT
    drawn on the image — it goes in the strip below (see `_external_cbar`).
    """
    ext = res.extent
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])

    if cfg.show_axes_labels:
        ax.set_xlabel("x [µm]"); ax.set_ylabel("y [µm]"); ax.tick_params(labelsize=8)
    else:
        ax.set_xticks([]); ax.set_yticks([])

    if title:
        # black on an opaque white chip — same treatment as the micron marker, so
        # it stays readable over both bright and dark maps.
        ax.text(0.022, 0.978, title, transform=ax.transAxes, va="top", ha="left",
                fontsize=10, weight="bold", color="black", zorder=7,
                bbox=dict(boxstyle="square,pad=0.32", fc="white", ec="none"))

    # IPF colour-key triangle (top-right) — the authentic TSL legend
    if ipf_key is not None and cfg.show_colorbar:
        pg, direction = ipf_key
        try:
            img = _ipf_key_image(pg, direction)
            kax = ax.inset_axes([0.70, 0.72, 0.28, 0.26])
            kax.imshow(img); kax.axis("off")
            kax.patch.set_alpha(0)
        except Exception:
            pass

    _scalebar(cfg, res, ax)


def _draw_boundaries(res: MicroResult, ax, cfg: Config):
    """Draw every configured boundary class with its own colour + thickness."""
    if res.boundary_segs:
        for b in res.boundary_segs:
            if b["segs"]:
                ax.add_collection(LineCollection(b["segs"], colors=b["color"],
                                                 linewidths=b["width"]))
    else:   # fallback to classic two-class
        if res.lagb_segs:
            ax.add_collection(LineCollection(res.lagb_segs, colors="blue", linewidths=0.3))
        if res.hagb_segs:
            ax.add_collection(LineCollection(res.hagb_segs, colors="black", linewidths=0.5))


# ---------------------------------------------------------------- maps (§4–7)
def fig_iq(cfg: Config, res: MicroResult) -> Figure:
    fig, ax, cax = _map_fig(cbar=cfg.show_colorbar)
    im = ax.imshow(res.iq, cmap="gray", extent=res.extent, interpolation="nearest")
    _overlay(cfg, res, ax, title="IQ")
    _external_cbar(cfg, fig, cax, im, label="Image Quality")
    return fig


def fig_ci(cfg: Config, res: MicroResult) -> Figure:
    fig, ax, cax = _map_fig(cbar=cfg.show_colorbar)
    cmap = "gray" if cfg.ci_display == "grey" else "RdYlGn"
    im = ax.imshow(res.ci, cmap=cmap, extent=res.extent, interpolation="nearest",
                   vmin=0, vmax=1)
    _overlay(cfg, res, ax, title="CI")
    _external_cbar(cfg, fig, cax, im, label="Confidence Index")
    return fig


def _ipf_rgb(cfg: Config, res: MicroResult, direction):
    """Per-phase IPF colouring for an arbitrary sample direction [h k l]."""
    from orix.quaternion import Orientation
    from orix.plot import IPFColorKeyTSL
    from orix.vector import Vector3d
    ny, nx = res.ny, res.nx
    rgb = np.zeros((ny * nx, 3))
    phase_flat = res.phase.ravel()
    vec = Vector3d(list(direction))
    for p in res.phases:
        sel = phase_flat == p["id"]
        if not sel.any():
            continue
        ori_p = Orientation.from_euler(res.euler[sel], symmetry=p["pg"])
        key = IPFColorKeyTSL(p["pg"], direction=vec)
        rgb[sel] = key.orientation2color(ori_p)
    rgb = rgb.reshape(ny, nx, 3).copy()
    if not cfg.ci_mask:
        rgb[res.ci < cfg.ci_threshold] = cfg.low_ci_fill
    return rgb


def fig_ipf(cfg: Config, res: MicroResult, direction=None) -> Figure:
    """IPF map for a given sample direction (default = cfg.ipf_dir)."""
    direction = tuple(direction) if direction is not None else tuple(cfg.ipf_dir)
    fig, ax, _ = _map_fig()
    rgb = _ipf_rgb(cfg, res, direction)
    ax.imshow(rgb, extent=res.extent, interpolation="nearest")
    dstr = "".join(str(int(v)) for v in direction)
    # colour key of the dominant phase (its symmetry defines the legend)
    dom_pg = res.pid2phase[res.dominant_pid]["pg"]
    _overlay(cfg, res, ax, title=f"IPF [{dstr}]", ipf_key=(dom_pg, direction))
    return fig


def fig_gb(cfg: Config, res: MicroResult) -> Figure:
    fig, ax, _ = _map_fig()
    ax.imshow(res.iq, cmap="gray", extent=res.extent, interpolation="nearest", alpha=0.25)
    _draw_boundaries(res, ax, cfg)
    _overlay(cfg, res, ax, title="Boundaries")
    # legend for boundary classes
    if res.boundary_segs:
        ax.legend(handles=[Patch(fc=b["color"], label=f"{b['name']} {b['lo']:.0f}-{b['hi']:.0f}deg")
                           for b in res.boundary_segs],
                  loc="upper right", fontsize=7, framealpha=0.7)
    return fig


def fig_ipf_hagb(cfg: Config, res: MicroResult, direction=None) -> Figure:
    """IPF + boundaries overlay (all configured boundary classes)."""
    direction = tuple(direction) if direction is not None else tuple(cfg.ipf_dir)
    fig, ax, _ = _map_fig()
    rgb = _ipf_rgb(cfg, res, direction)
    ax.imshow(rgb, extent=res.extent, interpolation="nearest")
    _draw_boundaries(res, ax, cfg)
    dstr = "".join(str(int(v)) for v in direction)
    dom_pg = res.pid2phase[res.dominant_pid]["pg"]
    _overlay(cfg, res, ax, title=f"IPF [{dstr}] + boundaries", ipf_key=(dom_pg, direction))
    return fig


def fig_grains(cfg: Config, res: MicroResult) -> Figure:
    fig, ax, _ = _map_fig()
    ax.imshow(res.colors[res.labels_clean], extent=res.extent, interpolation="nearest")
    # grains outlined by the highest boundary class only (grain-defining)
    if res.boundary_segs:
        top = res.boundary_segs[-1]
        if top["segs"]:
            ax.add_collection(LineCollection(top["segs"], colors="black", linewidths=0.3))
    elif res.hagb_segs:
        ax.add_collection(LineCollection(res.hagb_segs, colors="black", linewidths=0.3))
    _overlay(cfg, res, ax, title=f"Grains ({res.n_grains})")
    return fig


def fig_phase(cfg: Config, res: MicroResult) -> Figure:
    """Phase map (only meaningful for multiphase scans)."""
    from matplotlib import pyplot as _plt
    fig, ax, _ = _map_fig()
    ny, nx = res.ny, res.nx
    pal = _plt.cm.tab10(np.linspace(0, 1, max(len(res.phases), 2)))
    disp = np.zeros((ny, nx, 3))
    pgrid = res.phase.reshape(ny, nx)
    for i, p in enumerate(res.phases):
        disp[pgrid == p["id"]] = pal[i, :3]
    ax.imshow(disp, extent=res.extent, interpolation="nearest")
    _overlay(cfg, res, ax, title="Phase")
    ax.legend(handles=[Patch(fc=pal[i, :3], label=p["name"])
                       for i, p in enumerate(res.phases)],
              loc="upper right", fontsize=7, framealpha=0.7)
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
    # extra width on the right for a dedicated, readable colorbar
    fig = _fig(3.4 * ncol + 1.2, 3.4 * nrow)
    axes = fig.subplots(nrow, ncol, squeeze=False)
    vmax = cfg.odf_vmax if cfg.odf_vmax else np.percentile(odf_disp, 99.9)
    levels = np.linspace(0, max(vmax, 2.0), 16)
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
    for k in range(n_sec, nrow * ncol):
        axes[k // ncol, k % ncol].axis('off')
    # one clean, readable colorbar spanning all panels (constrained-layout aware,
    # so no subplots_adjust / manual add_axes that would fight the layout engine)
    cb = fig.colorbar(cs, ax=axes, shrink=0.85, pad=0.02, aspect=30)
    cb.set_label("f(g)  [mrd]", fontsize=12); cb.ax.tick_params(labelsize=11)
    _tag = "kernel" if cfg.odf_method == "kernel" else f"harmonic L={cfg.harmonic_lmax}"
    fig.suptitle(f"ODF ({cfg.lattice}) - {_tag}, hw={cfg.odf_halfwidth:g}deg, "
                 f"sample={cfg.sample_sym}, J={odf.J:.2f}, N={len(odf.eulers_odf):,}", fontsize=12)
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
