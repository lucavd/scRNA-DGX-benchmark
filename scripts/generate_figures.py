#!/usr/bin/env python3
"""Generate the scRNA-seq figures of the LNBI chapter at LNCS print size.

Figures (numbering of manuscript/full_paper_LNBI.md as of step S4; files keep
their historical names until the renaming of step S7, plan entry R0735):

  Figure 1  fig1_speedup_heatmap    per-step speedup, single GPU vs CPU
  Figure 2  fig5_timing_breakdown   per-step wall time, CPU and single GPU
  Figure 5  fig3_concordance        CPU-GPU concordance at 10,000 cells
  Figure 6  fig4_memory_profile     peak RAM and aggregate VRAM

The two multi-GPU figures (old Figures 3 and 4) are no longer produced
(decision D-02 of the chapter).

Inputs: only the main benchmark files
    <results>/cpu_<N>_r<k>_results.json
    <results>/gpu_<N>_r<k>_results.json        (1 GPU)
    <results>/gpu<g>_<N>_r<k>_results.json     (g = 2, 4, 8 GPUs)
and <results>/concordance_10000_r1.json. The stress-test (maxpower_*) and
differential-expression benchmark files in the same folder are excluded by
the file-name pattern, not by a later filter.

Convention (decision D-15): every time and memory value is the mean of all
five repeats with the sample SD (ddof = 1); a speedup is the ratio of the
mean times. The first repeat is included.

Print specification (LNCS): figure width at most 12.2 cm (the text width),
all text at least 7 pt at print size, vector PDF with embedded TrueType
fonts, PNG previews at 800 dpi. Include the PDFs at their natural size.

Outputs in --output-dir: <name>.pdf and <name>.png for each figure,
summary_table.csv; with --values-dir also figure_values.csv (every value
drawn or printed in a figure), figure_styles.json (colours, markers and
line styles per series, for the greyscale check) and figure_inputs_md5.tsv.

Usage:
    python scripts/generate_figures.py --results-dir results \
        --output-dir figures --values-dir results_v2/S4
"""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

# ---------------------------------------------------------------------------
# Print geometry and style
# ---------------------------------------------------------------------------
CM = 1 / 2.54
TEXT_WIDTH_IN = 12.2 * CM          # LNCS text width (llncs.cls)
MIN_PT = 7.0                       # smallest type size used anywhere

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 7.5,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.title_fontsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.minor.width": 0.4,
    "ytick.minor.width": 0.4,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "xtick.minor.size": 1.5,
    "ytick.minor.size": 1.5,
    "lines.linewidth": 1.0,
    "lines.markersize": 3.5,
    "pdf.fonttype": 42,            # embed TrueType fonts
    "ps.fonttype": 42,
    "svg.hashsalt": "lnbi-s4",
    "savefig.dpi": 800,
    "savefig.bbox": None,          # keep the declared figure size
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# One colour per pipeline, reused by every chapter figure (plan entry R0381).
# Paul Tol "bright" palette; series are also told apart by marker and line
# style so that the figures stay readable in greyscale (plan entry R0379).
COLORS = {
    "cpu": "#4477AA",
    "gpu1": "#EE6677",
    "gpu2": "#228833",
    "gpu4": "#CCBB44",
    "gpu8": "#AA3377",
}
MARKERS = {"cpu": "o", "gpu1": "s", "gpu2": "^", "gpu4": "D", "gpu8": "v"}
LINESTYLES = {"cpu": "-", "gpu1": "--", "gpu2": ":", "gpu4": "-.",
              "gpu8": (0, (5, 1.5, 1, 1.5, 1, 1.5))}
CONFIG_LABELS = {"cpu": "CPU", "gpu1": "1 GPU", "gpu2": "2 GPUs",
                 "gpu4": "4 GPUs", "gpu8": "8 GPUs"}

# Pipeline steps in execution order; names as in Table 1 of the chapter.
STEPS = [
    "data_loading", "qc_filtering", "normalization", "hvg_selection",
    "pca", "neighbors", "leiden_0.5", "leiden_1.0", "leiden_1.5",
    "umap", "de_testing",
]
STEP_LABELS = {
    "data_loading": "Data loading",
    "qc_filtering": "QC and filtering",
    "normalization": "Normalisation",
    "hvg_selection": "HVG selection",
    "pca": "PCA",
    "neighbors": "Neighbour graph",
    "leiden_0.5": "Leiden r = 0.5",
    "leiden_1.0": "Leiden r = 1.0",
    "leiden_1.5": "Leiden r = 1.5",
    "umap": "UMAP",
    "de_testing": "DE testing",
}
SIZES_1GPU = [10_000, 50_000, 100_000]
SIZES_ALL = [10_000, 50_000, 100_000, 500_000, 1_300_000]
SIZE_LABELS = {10_000: "10k", 50_000: "50k", 100_000: "100k",
               500_000: "500k", 1_300_000: "1.3M"}

RESULT_RE = re.compile(r"^(cpu|gpu\d*)_(\d+)_r(\d+)_results\.json$")
N_REPEATS = 5

# ---------------------------------------------------------------------------
# Bookkeeping: every drawn value and every style goes to a file
# ---------------------------------------------------------------------------
VALUES: list[dict] = []
STYLES: dict = {}
INPUTS: dict[str, str] = {}


def record(figure, panel, series, x, stat, value, n=None):
    VALUES.append({"figure": figure, "panel": panel, "series": series,
                   "x": x, "stat": stat, "value": repr(float(value)),
                   "n": "" if n is None else n})


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def luminance(color) -> float:
    """Greyscale value 0-255 (ITU-R BT.601, as PIL 'L')."""
    r, g, b = matplotlib.colors.to_rgb(color)
    return 255 * (0.299 * r + 0.587 * g + 0.114 * b)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def config_key(prefix: str) -> str:
    """'cpu' -> cpu, 'gpu' -> gpu1, 'gpu8' -> gpu8."""
    return "gpu1" if prefix == "gpu" else prefix


def load_main_results(results_dir: Path) -> pd.DataFrame:
    rows = []
    for jf in sorted(results_dir.iterdir()):
        m = RESULT_RE.match(jf.name)
        if not m:
            continue
        prefix, n_cells, rep = m.group(1), int(m.group(2)), int(m.group(3))
        data = json.loads(jf.read_text())
        meta = data["metadata"]
        assert meta["n_cells_input"] == n_cells, jf
        assert meta.get("repeat_id") == rep, jf
        INPUTS[str(jf)] = md5(jf)
        row = {"config": config_key(prefix), "n_cells": n_cells, "repeat": rep,
               "n_gpus": meta.get("n_gpus", 0), "pipeline": meta["pipeline"],
               "total": data["timings"]["total"],
               "peak_ram_gb": data["memory"]["peak_ram_gb"],
               "peak_vram_gb": data["memory"]["peak_vram_gb"]}
        for s in STEPS:
            row[s] = data["timings"].get(s, np.nan)
        rows.append(row)
    df = pd.DataFrame(rows)
    counts = df.groupby(["config", "n_cells"]).size()
    bad = counts[counts != N_REPEATS]
    if len(bad):
        raise SystemExit(f"configurations without {N_REPEATS} repeats: {bad.to_dict()}")
    print(f"Loaded {len(df)} main benchmark files "
          f"({len(counts)} configurations x {N_REPEATS} repeats)")
    return df


def sub(df, config, n_cells):
    s = df[(df["config"] == config) & (df["n_cells"] == n_cells)]
    assert len(s) == N_REPEATS, (config, n_cells, len(s))
    return s


def mean_sd(x: pd.Series) -> tuple[float, float]:
    return float(x.mean()), float(x.std(ddof=1))


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save(fig, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.pdf",
                metadata={"CreationDate": None, "ModDate": None,
                          "Producer": None, "Creator": None})
    fig.savefig(output_dir / f"{name}.png", dpi=800,
                metadata={"Software": None})
    plt.close(fig)
    print(f"  {name}: pdf and png saved")


# ---------------------------------------------------------------------------
# Figure 1: speedup heatmap
# ---------------------------------------------------------------------------

def speedup_cmap(lo: float, hi: float) -> LinearSegmentedColormap:
    """Diverging map on log10(speedup) between lo and hi: orange below 1,
    white at 1, blues above 1. The white node sits at the position of 1 on a
    proportional log scale, so equal ratios take equal lengths of the
    colour bar; luminance falls monotonically from 1 towards both ends and
    the high end is much darker than the low end."""
    f = (0.0 - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    up = [(0.0, "#F7F7F7"), (0.3, "#C6DBEF"), (0.6, "#6BAED6"),
          (0.8, "#2171B5"), (1.0, "#08306B")]
    nodes = [(0.0, "#E66101")] + [(f + (1 - f) * p, c) for p, c in up]
    return LinearSegmentedColormap.from_list("speedup", nodes)


def rel_lum(rgb) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(rgb1, rgb2) -> float:
    l1, l2 = sorted((rel_lum(rgb1), rel_lum(rgb2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def fmt_speedup(v: float) -> str:
    if v >= 100:
        return f"{v:.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def fig_speedup_heatmap(df: pd.DataFrame, output_dir: Path) -> None:
    fid = "fig1_speedup_heatmap"
    mat = np.full((len(STEPS), len(SIZES_1GPU)), np.nan)
    for j, n in enumerate(SIZES_1GPU):
        cpu, gpu = sub(df, "cpu", n), sub(df, "gpu1", n)
        for i, s in enumerate(STEPS):
            mat[i, j] = cpu[s].mean() / gpu[s].mean()
            record(fid, "main", STEP_LABELS[s], n, "speedup_ratio_of_means", mat[i, j], N_REPEATS)

    lo, hi = 0.3, 400.0             # fixed colour limits, cover 0.36-329
    assert np.nanmin(mat) > lo and np.nanmax(mat) < hi
    norm = Normalize(vmin=np.log10(lo), vmax=np.log10(hi))
    cmap = speedup_cmap(lo, hi)

    fig = plt.figure(figsize=(8.4 * CM, 8.0 * CM))
    ax = fig.add_axes([0.30, 0.11, 0.42, 0.86])
    cax = fig.add_axes([0.76, 0.11, 0.035, 0.86])
    mesh = ax.pcolormesh(np.log10(mat), cmap=cmap, norm=norm,
                         edgecolors="white", linewidth=0.6)
    cells = []
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            bg = cmap(norm(np.log10(v)))
            black, white = contrast(bg, (0, 0, 0)), contrast(bg, (1, 1, 1))
            tc = "black" if black >= white else "white"
            ax.text(j + 0.5, i + 0.5, fmt_speedup(v), ha="center", va="center",
                    fontsize=7, color=tc)
            cells.append({"step": STEPS[i], "n_cells": SIZES_1GPU[j], "value": v,
                          "cell_color": to_hex(bg), "text_color": tc,
                          "contrast": max(black, white),
                          "luminance": luminance(bg)})
    ax.set_xlim(0, mat.shape[1]); ax.set_ylim(mat.shape[0], 0)
    ax.set_xticks(np.arange(mat.shape[1]) + 0.5)
    ax.set_xticklabels([SIZE_LABELS[n] for n in SIZES_1GPU])
    ax.set_yticks(np.arange(mat.shape[0]) + 0.5)
    ax.set_yticklabels([STEP_LABELS[s] for s in STEPS])
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("Dataset size (cells)")

    cb = fig.colorbar(mesh, cax=cax)
    # matplotlib rasterises colour-bar solids above 50 levels; keep vector
    cb.solids.set_rasterized(False)
    ticks = [0.5, 1, 10, 100]
    cb.set_ticks(np.log10(ticks))
    cb.set_ticklabels(["0.5", "1", "10", "100"])
    cb.minorticks_off()
    cb.outline.set_linewidth(0.6)
    cb.set_label("Speedup (CPU time / GPU time)")
    STYLES[fid] = {"heatmap_cells": cells, "colour_limits": [lo, hi],
                   "colourbar_ticks": ticks}
    save(fig, output_dir, fid)


# ---------------------------------------------------------------------------
# Figure 2: per-step wall time, CPU and single GPU on separate axes
# ---------------------------------------------------------------------------

def fig_timing_breakdown(df: pd.DataFrame, output_dir: Path) -> None:
    fid = "fig5_timing_breakdown"
    # Sequential palette (viridis), dark at the bottom of the stack and light
    # at the top: luminance grows with the step order, so the stack order can
    # be read in greyscale against the legend.
    cols = [plt.cm.viridis(x) for x in np.linspace(0.0, 0.97, len(STEPS))]
    fig = plt.figure(figsize=(TEXT_WIDTH_IN, 6.0 * CM))
    axes = [fig.add_axes([0.11, 0.16, 0.24, 0.74]),
            fig.add_axes([0.44, 0.16, 0.24, 0.74])]
    for ax, cfg, title in zip(axes, ["cpu", "gpu1"],
                              ["CPU (Scanpy)", "1 GPU (rapids-singlecell)"]):
        tops = []
        for k, n in enumerate(SIZES_1GPU):
            s = sub(df, cfg, n)
            bottom = 0.0
            for i, st in enumerate(STEPS):
                h = float(s[st].mean())
                record(fid, cfg, STEP_LABELS[st], n, "mean_s", h, N_REPEATS)
                ax.bar(k, h, bottom=bottom, width=0.62, color=cols[i],
                       edgecolor="white", linewidth=0.3)
                bottom += h
            record(fid, cfg, "stack_total", n, "sum_of_step_means_s", bottom, N_REPEATS)
            tops.append(bottom)
        ymax = max(tops) * 1.13
        ax.set_ylim(0, ymax)
        for k, t in enumerate(tops):
            ax.text(k, t + ymax * 0.015, f"{t:.0f} s" if t >= 10 else f"{t:.1f} s",
                    ha="center", va="bottom", fontsize=7)
        ax.set_xticks(range(len(SIZES_1GPU)))
        ax.set_xticklabels([SIZE_LABELS[n] for n in SIZES_1GPU])
        ax.set_xlabel("Dataset size (cells)")
        ax.set_title(title, loc="left", pad=3)
    axes[0].set_ylabel("Wall time (s)")
    handles = [matplotlib.patches.Patch(facecolor=cols[i], edgecolor="white",
                                        linewidth=0.3, label=STEP_LABELS[s])
               for i, s in enumerate(STEPS)][::-1]   # top of stack first
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.71, 0.53),
               frameon=False, handlelength=1.2, handleheight=0.9,
               labelspacing=0.28, borderaxespad=0.0)
    STYLES[fid] = {"stacked": [{"step": s, "order": i, "color": to_hex(cols[i]),
                                "luminance": luminance(cols[i])}
                               for i, s in enumerate(STEPS)]}
    save(fig, output_dir, fid)


# ---------------------------------------------------------------------------
# Figure 5: concordance dot plot
# ---------------------------------------------------------------------------

def fig_concordance(conc: dict, output_dir: Path) -> None:
    fid = "fig3_concordance"
    cl = conc["cluster_concordance"]
    res = ["leiden_0.5", "leiden_1.0", "leiden_1.5"]
    ari = [cl[r]["ari"] for r in res]
    nmi = [cl[r]["nmi"] for r in res]
    others = [("HVG\nJaccard", conc["hvg_concordance"]["jaccard"]),
              ("PCA\n|\u03c1|", conc["pca_concordance"]["mean_abs_spearman_rho"]),
              ("kNN\nJaccard", conc["knn_concordance"]["mean_jaccard"]),
              ("DE logFC\n\u03c1", conc["de_concordance"]["mean_spearman_rho"])]
    knn_cap = 15 / 16

    fig = plt.figure(figsize=(TEXT_WIDTH_IN, 5.2 * CM))
    ax1 = fig.add_axes([0.10, 0.20, 0.38, 0.66])
    ax2 = fig.add_axes([0.60, 0.20, 0.38, 0.66], sharey=ax1)
    ylim = (0.80, 1.012)
    x = np.arange(3)
    series = {"ARI": dict(marker="o", color="black", mfc="black", dx=-0.15,
                          ha="right", tx=-0.11),
              "NMI": dict(marker="s", color="black", mfc="white", dx=+0.15,
                          ha="left", tx=+0.11)}
    for name, vals in (("ARI", ari), ("NMI", nmi)):
        st = series[name]
        ax1.plot(x + st["dx"], vals, linestyle="none", marker=st["marker"],
                 color=st["color"], mfc=st["mfc"], mew=0.8, ms=4, label=name)
        for xi, v, r in zip(x, vals, res):
            record(fid, "clustering", name, r, "value", v)
            ax1.text(xi + st["dx"] + st["tx"], v, f"{v:.3f}", ha=st["ha"],
                     va="center", fontsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(["r = 0.5", "r = 1.0", "r = 1.5"])
    ax1.set_xlim(-0.5, 2.5)
    ax1.set_xlabel("Leiden resolution")
    ax1.set_ylabel("Agreement (ARI, NMI)")
    ax1.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2,
               frameon=False, borderaxespad=0.2, handletextpad=0.3,
               columnspacing=1.0)

    x2 = np.arange(len(others))
    vals2 = [v for _, v in others]
    ax2.plot(x2, vals2, linestyle="none", marker="D", color="black", ms=4)
    for xi, (lab, v) in zip(x2, others):
        record(fid, "other", lab.replace("\n", " "), "", "value", v)
        ax2.text(xi, v - 0.009, f"{v:.3f}", ha="center", va="top", fontsize=7)
    k = 2  # kNN position
    ax2.hlines(knn_cap, k - 0.36, k + 0.36, colors="0.35", linestyles=(0, (2, 1.2)),
               linewidth=0.8)
    ax2.text(k, knn_cap + 0.003, "max 0.9375", ha="center", va="bottom",
             fontsize=7, color="0.25")
    record(fid, "other", "kNN Jaccard ceiling", "", "value", knn_cap)
    ax2.set_xticks(x2)
    ax2.set_xticklabels([lab for lab, _ in others])
    ax2.set_xlim(-0.5, len(others) - 0.4)
    ax2.set_ylabel("Agreement (Jaccard, Spearman)")
    ax2.tick_params(labelleft=True)
    for ax in (ax1, ax2):
        ax.set_ylim(*ylim)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(0.05))
        ax.axhline(1.0, color="0.6", linewidth=0.5, linestyle=(0, (1, 1)), zorder=0)
    STYLES[fid] = {"series": {"clustering": [
        {"name": n, "marker": series[n]["marker"], "fill": series[n]["mfc"],
         "linestyle": "none", "color": series[n]["color"]} for n in series],
        "other": [{"name": lab.replace("\n", " "), "x_position": i}
                  for i, (lab, _) in enumerate(others)]},
        "ylim": ylim}
    save(fig, output_dir, fid)


# ---------------------------------------------------------------------------
# Figure 6: memory profile
# ---------------------------------------------------------------------------

def fig_memory_profile(df: pd.DataFrame, output_dir: Path) -> None:
    fid = "fig4_memory_profile"
    configs = ["cpu", "gpu1", "gpu2", "gpu4", "gpu8"]
    dodge = {c: 10 ** (0.05 * k) for c, k in zip(configs, [-2, -1, 0, 1, 2])}
    fig = plt.figure(figsize=(TEXT_WIDTH_IN, 5.6 * CM))
    ax1 = fig.add_axes([0.095, 0.19, 0.38, 0.64])
    ax2 = fig.add_axes([0.595, 0.19, 0.38, 0.64])
    styles = []
    for c in configs:
        sizes = [n for n in SIZES_ALL
                 if not df[(df["config"] == c) & (df["n_cells"] == n)].empty]
        for ax, col, panel in ((ax1, "peak_ram_gb", "ram"), (ax2, "peak_vram_gb", "vram")):
            if panel == "vram" and c == "cpu":
                continue
            m, s = zip(*[mean_sd(sub(df, c, n)[col]) for n in sizes])
            for n, mi, si in zip(sizes, m, s):
                record(fid, panel, c, n, "mean_gib", mi, N_REPEATS)
                record(fid, panel, c, n, "sd_gib", si, N_REPEATS)
            ax.errorbar([n * dodge[c] for n in sizes], m, yerr=s,
                        color=COLORS[c], marker=MARKERS[c], linestyle=LINESTYLES[c],
                        mfc=COLORS[c] if c in ("cpu", "gpu2", "gpu8") else "white",
                        mew=0.8, ms=3.5, linewidth=0.9, capsize=1.5,
                        elinewidth=0.6, capthick=0.6)
        styles.append({"config": c, "color": COLORS[c], "marker": MARKERS[c],
                       "linestyle": str(LINESTYLES[c]),
                       "filled": c in ("cpu", "gpu2", "gpu8")})
    for ax in (ax1, ax2):
        ax.set_xscale("log")
        ax.set_xticks(SIZES_ALL)
        ax.set_xticklabels([SIZE_LABELS[n] for n in SIZES_ALL])
        ax.xaxis.set_minor_locator(mticker.NullLocator())
        ax.set_xlim(6_500, 2_100_000)
        ax.set_xlabel("Dataset size (cells)")
        ax.grid(True, axis="y", linewidth=0.4, alpha=0.4)
    ax1.set_yscale("log")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.set_ylabel("Peak CPU RAM (GiB)")
    ax2.set_ylim(0, None)
    ax2.set_ylabel("Peak aggregate VRAM (GiB)")
    handles = [Line2D([0], [0], color=COLORS[c], marker=MARKERS[c],
                      linestyle=LINESTYLES[c], linewidth=0.9, ms=3.5, mew=0.8,
                      mfc=COLORS[c] if c in ("cpu", "gpu2", "gpu8") else "white",
                      label=CONFIG_LABELS[c]) for c in configs]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.53, 1.0),
               ncol=5, frameon=False, handlelength=2.6, columnspacing=1.2,
               borderaxespad=0.2)
    STYLES[fid] = {"series": styles}
    save(fig, output_dir, fid)


# ---------------------------------------------------------------------------
# Summary table (same columns as the historical figures/summary_table.csv)
# ---------------------------------------------------------------------------

def export_summary_table(df: pd.DataFrame, output_dir: Path) -> None:
    rows = []
    for (pipe, n, g), grp in df.groupby(["pipeline", "n_cells", "n_gpus"]):
        m, s = mean_sd(grp["total"])
        rows.append({"pipeline": pipe, "n_cells": n, "n_gpus": g,
                     "n_repeats": len(grp),
                     "total_time_mean_s": round(m, 1),
                     "total_time_std_s": round(s, 1),
                     "peak_ram_gb": round(grp["peak_ram_gb"].mean(), 1),
                     "peak_vram_gb": round(grp["peak_vram_gb"].mean(), 1)})
    out = pd.DataFrame(rows).sort_values(["n_cells", "n_gpus", "pipeline"])
    out.to_csv(output_dir / "summary_table.csv", index=False)
    print(f"  summary_table.csv: {len(out)} rows")


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--output-dir", default="figures")
    ap.add_argument("--values-dir", default=None,
                    help="where to write figure_values.csv, figure_styles.json "
                         "and figure_inputs_md5.tsv")
    a = ap.parse_args()
    rd, od = Path(a.results_dir), Path(a.output_dir)
    od.mkdir(parents=True, exist_ok=True)

    df = load_main_results(rd)
    conc_path = rd / "concordance_10000_r1.json"
    INPUTS[str(conc_path)] = md5(conc_path)
    conc = json.loads(conc_path.read_text())

    fig_speedup_heatmap(df, od)
    fig_timing_breakdown(df, od)
    fig_concordance(conc, od)
    fig_memory_profile(df, od)
    export_summary_table(df, od)

    if a.values_dir:
        vd = Path(a.values_dir)
        vd.mkdir(parents=True, exist_ok=True)
        with open(vd / "figure_values.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(VALUES[0]))
            w.writeheader(); w.writerows(VALUES)
        (vd / "figure_styles.json").write_text(json.dumps(STYLES, indent=1, default=float))
        with open(vd / "figure_inputs_md5.tsv", "w") as f:
            f.write("path\tmd5\n")
            for p in sorted(INPUTS):
                f.write(f"{p}\t{INPUTS[p]}\n")
        print(f"  {len(VALUES)} values, {len(INPUTS)} input files recorded in {vd}")


if __name__ == "__main__":
    main()
