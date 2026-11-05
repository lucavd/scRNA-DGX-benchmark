#!/usr/bin/env python3
"""Generate the spatial figures of the LNBI chapter (Figures 7, 8, 9) at LNCS print size.

Step S5 of the chapter. Replaces figures/generate_spatial_figures.py (March
2026 values, now in figures/retired/). Print settings, colours, markers and
the save routine are imported from scripts/generate_figures.py (step S4), so
CPU and GPU have the same colour in every figure of the chapter.

  Figure 7  fig7_spatial_speedup      total wall time, CPU reference vs GPU, three platforms
  Figure 8  fig8_spatial_perstep      per-step speedup on Visium HD 8 um, 95% bootstrap interval
  Figure 9  fig9_spatial_concordance  CPU-GPU concordance, three platforms

Inputs (step S1, read only), in --results-dir (default SPATIAL/results_v2):
  s1_step_stats.csv, s1_speedups.csv, s1_extra_numbers.json,
  cooc_check/cooc_check_eval.json, concordance_reference/spatial_concordance_<platform>.json

Conventions (decisions D-11, D-13, D-15, D-20 of the chapter):
  CPU reference = one DGX H100 node (poddgx02, 100 CPUs), run 'dgx_cpu', speedup cpu = reference_dgx;
  GPU = one RTX 4090, run 'server_gpu'; mean and sample SD (ddof = 1) of all five
  repeats (convention 1_5), each repeat in a fresh process; speedup = ratio of means
  with the 95% bootstrap interval of s1_speedups.csv.
  Visium HD 8 um: totals include co-occurrence (D-20), whose GPU result with
  rapids-singlecell 0.14.1 is wrong; the total without co-occurrence is marked.
  Co-occurrence in Figure 8: speedup of the separate check with rapids-singlecell
  0.15.1 (D-20), drawn with an open marker, not a pipeline step.
  Concordance: CPU repeat k against GPU repeat k (k = 1..5); point = mean of the
  five pairs, bar = min-max when the pairs differ.

Outputs in --output-dir: <name>.pdf and <name>.png; in --values-dir:
figure_values.csv, figure_styles.json, figure_inputs_md5.tsv.

Usage:
    python scripts/generate_spatial_figures.py --results-dir SPATIAL/results_v2 \
        --output-dir figures --values-dir results_v2/S5
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_figures as gf  # noqa: E402  (sets rcParams, palette, save)

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

plt.rcParams["svg.hashsalt"] = "lnbi-s5"
CM, W = gf.CM, gf.TEXT_WIDTH_IN
COL_CPU, COL_GPU = gf.COLORS["cpu"], gf.COLORS["gpu1"]
HATCH_GPU = "//////"
PLATS = ["visium", "visium_hd_square_008um", "visium_hd_square_002um"]
PLAT_SHORT = {"visium": "Visium v1", "visium_hd_square_008um": "Visium HD 8 \u00b5m",
              "visium_hd_square_002um": "Visium HD 2 \u00b5m\n(random 400k-bin subsample)"}
STEP_LABELS = {
    "data_loading": "Data loading", "qc_filtering": "QC and filtering",
    "normalization": "Normalisation", "hvg_selection": "HVG selection", "pca": "PCA",
    "expression_neighbors": "Expression neighbours", "leiden": "Leiden clustering",
    "umap": "UMAP", "spatial_neighbors": "Spatial neighbours",
    "spatial_autocorr_moran": "Moran's I", "spatial_autocorr_geary": "Geary's C",
    "co_occurrence": "Co-occurrence", "nhood_enrichment": "Neighbourhood enrichment",
}
CPU_IN_BOTH = {"spatial_neighbors", "nhood_enrichment"}   # Squidpy on the CPU in both pipelines


class Data:
    def __init__(self, root: Path):
        self.root = root
        self.files = {}
        self.stats = self._csv("s1_step_stats.csv")
        self.spd = self._csv("s1_speedups.csv")
        self.extra = self._json("s1_extra_numbers.json")
        self.cooc = self._json("cooc_check/cooc_check_eval.json")
        self.conc = {p: self._json(f"concordance_reference/spatial_concordance_{p}.json") for p in PLATS}

    def _path(self, rel):
        p = self.root / rel
        self.files[str(p)] = gf.md5(p)
        return p

    def _csv(self, rel):
        return list(csv.DictReader(open(self._path(rel))))

    def _json(self, rel):
        return json.loads(self._path(rel).read_text())

    def time(self, run, plat, step):
        r = [x for x in self.stats if x["run"] == run and x["platform"] == plat and x["step"] == step]
        assert len(r) == 1, (run, plat, step)
        return float(r[0]["mean_1_5"]), float(r[0]["sd_1_5"]), [float(r[0][f"r{k}"]) for k in range(1, 6)]

    def speedup(self, plat, step, cpu="reference_dgx"):
        r = [x for x in self.spd if x["platform"] == plat and x["step"] == step
             and x["cpu"] == cpu and x["convention"] == "1_5"]
        assert len(r) == 1, (plat, step, cpu)
        return float(r[0]["speedup"]), float(r[0]["ci_lo"]), float(r[0]["ci_hi"])


def fmt_x(v):
    return f"{v:.0f}x" if v >= 100 else (f"{v:.1f}x" if v >= 1 else f"{v:.2f}x")


# ---------------------------------------------------------------------------
# Figure 7: total wall time
# ---------------------------------------------------------------------------

def fig7(d: Data, out: Path):
    fid = "fig7_spatial_speedup"
    fig = plt.figure(figsize=(W, 5.6 * CM))
    ax = fig.add_axes([0.12, 0.20, 0.86, 0.60])
    x = np.arange(len(PLATS)); bw = 0.34
    for i, p in enumerate(PLATS):
        for run, dx, col, hatch, lab in (("dgx_cpu", -bw / 2, COL_CPU, None, "CPU"),
                                         ("server_gpu", bw / 2, COL_GPU, HATCH_GPU, "GPU")):
            m, s, _ = d.time(run, p, "total")
            ax.bar(i + dx, m, bw, color=col, hatch=hatch, edgecolor="white" if hatch else col,
                   linewidth=0.0)
            ax.errorbar(i + dx, m, yerr=s, color="black", capsize=1.8, elinewidth=0.6, capthick=0.6)
            gf.record(fid, "total", lab, p, "mean_s", m, 5)
            gf.record(fid, "total", lab, p, "sd_s", s, 5)
            if p == "visium_hd_square_008um":
                c, _, _ = d.time(run, p, "co_occurrence")
                ax.hlines(m - c, i + dx - bw / 2, i + dx + bw / 2, colors="black",
                          linestyles=(0, (2, 1)), linewidth=0.8)
                gf.record(fid, "total", lab, p, "mean_s_without_co_occurrence", m - c, 5)
        sp, lo, hi = d.speedup(p, "total")
        gf.record(fid, "total", "speedup", p, "speedup", sp, 5)
        top = d.time("dgx_cpu", p, "total")[0] + d.time("dgx_cpu", p, "total")[1]
        txt = fmt_x(sp)
        if p == "visium_hd_square_008um":
            wo = d.extra["speedup_total_without_co_occurrence"][p]["reference_dgx"][0]
            gf.record(fid, "total", "speedup_without_co_occurrence", p, "speedup", wo, 5)
            txt += f"\n({fmt_x(wo)} without\nco-occurrence)"
        ax.text(i, top * 1.35, txt, ha="center", va="bottom", fontsize=7)
    ax.set_yscale("log")
    ax.set_ylim(10, 6000)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylabel("Total wall time (s)")
    ax.set_xticks(x)
    ax.set_xticklabels([PLAT_SHORT[p] for p in PLATS])
    ax.set_xlim(-0.6, len(PLATS) - 0.4)
    handles = [Patch(facecolor=COL_CPU, label="CPU (DGX H100 node, 100 CPUs)"),
               Patch(facecolor=COL_GPU, hatch=HATCH_GPU, edgecolor="white", label="GPU (RTX 4090)"),
               Line2D([], [], color="black", linestyle=(0, (2, 1)), linewidth=0.8,
                      label="total without co-occurrence")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.10, 1.0), ncol=2, frameon=False,
               borderaxespad=0.2, handletextpad=0.4, columnspacing=1.2, handlelength=1.6)
    gf.STYLES[fid] = {"series": [{"name": "CPU", "color": COL_CPU, "hatch": None},
                                 {"name": "GPU", "color": COL_GPU, "hatch": HATCH_GPU}]}
    gf.save(fig, out, fid)


# ---------------------------------------------------------------------------
# Figure 8: per-step speedup, Visium HD 8 um
# ---------------------------------------------------------------------------

def fig8(d: Data, out: Path):
    fid = "fig8_spatial_perstep"
    p = "visium_hd_square_008um"
    steps = ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca",
             "expression_neighbors", "leiden", "umap", "spatial_neighbors",
             "spatial_autocorr_moran", "spatial_autocorr_geary", "co_occurrence", "nhood_enrichment"]
    fig = plt.figure(figsize=(W, 6.8 * CM))
    ax = fig.add_axes([0.30, 0.14, 0.66, 0.76])
    y = np.arange(len(steps))[::-1]
    styles = []
    for yi, s in zip(y, steps):
        if s == "co_occurrence":
            cpu = np.array(d.time("dgx_cpu", p, s)[2]); gpu = np.array(d.cooc["t_hd8_rsc0151"])
            rng = np.random.default_rng(20261104)
            boot = [cpu[rng.integers(0, 5, 5)].mean() / gpu[rng.integers(0, 5, 5)].mean() for _ in range(2000)]
            sp, lo, hi = float(cpu.mean() / gpu.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
            kw = dict(marker="D", mfc="white", mec="black", color="black")
            series = "separate check, rapids-singlecell 0.15.1"
        else:
            sp, lo, hi = d.speedup(p, s)
            if s in CPU_IN_BOTH:
                kw = dict(marker="o", mfc="white", mec="black", color="black"); series = "CPU in both pipelines"
            else:
                kw = dict(marker="o", mfc="black", mec="black", color="black"); series = "GPU step"
        ax.errorbar(sp, yi, xerr=[[sp - lo], [hi - sp]], linestyle="none", ms=3.8, mew=0.8,
                    elinewidth=0.7, capsize=1.5, capthick=0.6, **kw)
        ax.text(max(hi, sp) * 1.25, yi, fmt_x(sp), va="center", ha="left", fontsize=7)
        for stat, v in (("speedup", sp), ("ci_lo", lo), ("ci_hi", hi)):
            gf.record(fid, "per_step", s, p, stat, v, 5)
        styles.append({"step": s, "series": series, "marker": kw["marker"], "fill": kw["mfc"]})
    ax.axvline(1.0, color="0.5", linewidth=0.6, linestyle=(0, (1, 1)), zorder=0)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 1000)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}x"))
    ax.set_yticks(y)
    ax.set_yticklabels([STEP_LABELS[s] + (" *" if s == "co_occurrence" else "") for s in steps])
    ax.set_ylim(-0.7, len(steps) - 0.3)
    ax.set_xlabel("GPU speedup on Visium HD 8 \u00b5m (CPU time / GPU time)")
    handles = [Line2D([], [], marker="o", color="black", mfc="black", linestyle="none", ms=3.8, label="GPU step"),
               Line2D([], [], marker="o", color="black", mfc="white", linestyle="none", ms=3.8,
                      label="CPU in both pipelines"),
               Line2D([], [], marker="D", color="black", mfc="white", linestyle="none", ms=3.8,
                      label="* separate check (0.15.1)")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.02, 1.0), ncol=3, frameon=False,
               borderaxespad=0.2, handletextpad=0.3, columnspacing=1.0, fontsize=7)
    gf.STYLES[fid] = {"points": styles}
    gf.save(fig, out, fid)


# ---------------------------------------------------------------------------
# Figure 9: concordance
# ---------------------------------------------------------------------------

def fig9(d: Data, out: Path):
    fid = "fig9_spatial_concordance"
    left = [("moranI", "I_spearman_rho", "Moran's\nI \u03c1"), ("gearyC", "C_spearman_rho", "Geary's\nC \u03c1"),
            ("moranI", "svg_jaccard_top50", "SVG J\ntop 50"), ("moranI", "svg_jaccard_top100", "SVG J\ntop 100"),
            ("moranI", "svg_jaccard_top200", "SVG J\ntop 200"), ("moranI", "svg_jaccard_fdr005", "SVG J\nFDR<0.05")]
    right = [("clusters", "ari", "ARI"), ("clusters", "nmi", "NMI")]
    pst = {"visium": dict(marker="o", mfc="black", dx=-0.22, label="Visium v1"),
           "visium_hd_square_008um": dict(marker="s", mfc="white", dx=0.0, label="Visium HD 8 \u00b5m"),
           "visium_hd_square_002um": dict(marker="^", mfc="0.6", dx=0.22,
                                          label="Visium HD 2 \u00b5m (random 400k-bin subsample)")}
    fig = plt.figure(figsize=(W, 5.8 * CM))
    ax1 = fig.add_axes([0.115, 0.17, 0.60, 0.62])
    ax2 = fig.add_axes([0.82, 0.17, 0.16, 0.62])
    for ax, mets, panel in ((ax1, left, "spatial"), (ax2, right, "clustering")):
        for j, (g, k, lab) in enumerate(mets):
            for p in PLATS:
                vals = [r[g][k] for r in d.conc[p]]
                assert len(vals) == 5
                lo, hi = float(min(vals)), float(max(vals))
                mean = lo if lo == hi else float(np.mean(vals))
                st = pst[p]
                ax.errorbar(j + st["dx"], mean, yerr=[[max(mean - lo, 0.0)], [max(hi - mean, 0.0)]], linestyle="none",
                            marker=st["marker"], mfc=st["mfc"], mec="black", color="black", ms=3.6,
                            mew=0.7, elinewidth=0.7, capsize=1.2 if hi > lo else 0)
                for stat, v in (("mean", mean), ("min", lo), ("max", hi)):
                    gf.record(fid, panel, f"{g}.{k}", p, stat, v, 5)
        ax.set_xticks(range(len(mets)))
        ax.set_xticklabels([lab for _, _, lab in mets])
        ax.set_xlim(-0.5, len(mets) - 0.5)
        ax.axhline(1.0, color="0.6", linewidth=0.5, linestyle=(0, (1, 1)), zorder=0)
    ax1.set_ylim(0.970, 1.002)
    ax1.yaxis.set_major_locator(mticker.MultipleLocator(0.01))
    ax1.set_ylabel("Agreement (\u03c1, Jaccard)")
    ax2.set_ylim(0, 1.04)
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(0.2))
    ax2.set_ylabel("Leiden agreement")
    handles = [Line2D([], [], marker=pst[p]["marker"], mfc=pst[p]["mfc"], mec="black", color="black",
                      linestyle="none", ms=3.6, label=pst[p]["label"]) for p in PLATS]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.10, 1.0), ncol=2, frameon=False,
               handletextpad=0.3, columnspacing=1.2)
    gf.STYLES[fid] = {"platforms": {p: {"marker": pst[p]["marker"], "fill": pst[p]["mfc"], "color": "black"}
                                    for p in PLATS}}
    gf.save(fig, out, fid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="SPATIAL/results_v2", type=Path)
    ap.add_argument("--output-dir", default="figures", type=Path)
    ap.add_argument("--values-dir", default=None, type=Path)
    a = ap.parse_args()
    d = Data(a.results_dir)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    fig7(d, a.output_dir); fig8(d, a.output_dir); fig9(d, a.output_dir)
    if a.values_dir:
        a.values_dir.mkdir(parents=True, exist_ok=True)
        with open(a.values_dir / "figure_values.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["figure", "panel", "series", "x", "stat", "value", "n"])
            w.writeheader(); w.writerows(gf.VALUES)
        json.dump(gf.STYLES, open(a.values_dir / "figure_styles.json", "w"), indent=1)
        with open(a.values_dir / "figure_inputs_md5.tsv", "w") as f:
            for k in sorted(d.files):
                f.write(f"{k}\t{d.files[k]}\n")
        print(f"values: {len(gf.VALUES)} rows")


if __name__ == "__main__":
    main()
