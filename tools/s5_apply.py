#!/usr/bin/env python3
"""Apply the spatial edits of step S5 to manuscript/full_paper_LNBI.md.

Every number is formatted from results_v2/S5/s5_numbers.json (written by
tools/s5_numbers.py from SPATIAL/results_v2); none is typed by hand. Each edit
names its target by an anchor that must occur exactly once before the edit.
The Results subsection on spatial transcriptomics (from its first heading to
the end of the memory paragraph) is replaced as one block, because most of the
49 plan entries of S5 touch it (one transaction, plan rule 3). Appends one
diary row per S5 ledger row to IMPL_diario.csv and writes the applied edits to
results_v2/S5/edits_applied.json.

Rounding: half-up on the decimal representation stored in the result files.
Times: three significant digits for the mean, more decimals if needed to show
the first significant digit of the SD (at most 4), SD with the same decimals.
Speedups: no decimal from 100x, one from 1x, two below 1x; intervals as the point.

Usage: python3 -B tools/s5_apply.py [--dry-run] [--preview OUT.md]
"""
import argparse, csv, hashlib, json, math, sys
from decimal import Decimal, ROUND_HALF_UP

MS = "manuscript/full_paper_LNBI.md"
DIARY = "manuscript/revisione_n2/piano/IMPL_diario.csv"
LEDGER = "manuscript/revisione_n2/piano/ledger.csv"
NUM = "results_v2/S5/s5_numbers.json"
OUT = "results_v2/S5/edits_applied.json"
DATE = "2026-11-04"

N = json.load(open(NUM))
def v(k): return N[k]["value"]

def r(x, d):
    q = Decimal(1).scaleb(-d) if d > 0 else Decimal(1)
    return str(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))
def thou(s):
    i, _, f = s.partition(".")
    neg = i.startswith("-"); i = i.lstrip("-")
    i = f"{int(i):,}"
    return ("-" if neg else "") + i + ("." + f if f else "")
def tdec(m): return max(0, 2 - math.floor(math.log10(abs(m))))
def t(m, sd=None):
    d = tdec(m)
    if sd:
        d = min(max(d, -math.floor(math.log10(abs(sd)))), 4)
    return thou(r(m, d)) + ("" if sd is None else f" +/- {r(sd, d)}")
def xdec(s): return 0 if s >= 100 else (1 if s >= 1 else 2)
def x(s): return f"{thou(r(s, xdec(s)))}x"
def xci(tr, d=None):
    s, lo, hi = tr; d = xdec(s) if d is None else d
    return f"{thou(r(s, d))}x ({thou(r(lo, d))}-{thou(r(hi, d))})"
def pct(a, b, d=1): return r(100 * a / b, d)
def mean(l): return sum(l) / len(l)
def rng(l, d):
    a, b = r(min(l), d), r(max(l), d)
    return a if a == b else f"{a}-{b}"
def floor4(y): return str(Decimal(repr(float(y))).quantize(Decimal("0.0001"), rounding="ROUND_FLOOR"))

V1, H8, H2 = "visium", "visium_hd_square_008um", "visium_hd_square_002um"
PL = [V1, H8, H2]
def T(run, p, s): return v(f"time.{run}.{p}.{s}")
def S(p, s, cpu="reference_dgx"): return v(f"speedup.{cpu}.{p}.{s}")
def C(p, g, k, tag="reference"): return v(f"conc.{tag}.{p}.{g}.{k}")
def ram(run, p): return mean(v(f"run.{run}.{p}.peak_ram_gb"))
def vram(p): return mean(v(f"run.server_gpu.{p}.peak_vram_gb"))
def bins(p):
    q = v(f"run.dgx_cpu.{p}.n_spots_after_qc"); assert len(set(q)) == 1
    for run in ("server_gpu", "server_cpu"): assert v(f"run.{run}.{p}.n_spots_after_qc") == q
    return q[0]

# ------------------------------------------------------------------ derived values
tot = {p: (T("dgx_cpu", p, "total"), T("server_gpu", p, "total")) for p in PL}
sp_tot = {p: S(p, "total") for p in PL}
ctl_tot = {p: S(p, "total", "control_server") for p in PL}
wo = v("speedup_wo_cooc.reference_dgx." + H8); wo_ctl = v("speedup_wo_cooc.control_server." + H8)
cpu_wo, gpu_wo = v("total_wo_cooc.dgx_cpu." + H8), v("total_wo_cooc.server_gpu." + H8)
assert abs(cpu_wo / gpu_wo - wo[0]) < 1e-9 * wo[0], "without-co-occurrence speedup not reproduced"
head = {V1: sp_tot[V1][0], H8: wo[0], H2: sp_tot[H2][0]}
head_ctl = {V1: ctl_tot[V1][0], H8: wo_ctl[0], H2: ctl_tot[H2][0]}
cpu_dep = [abs(head_ctl[p] / head[p] - 1) * 100 for p in PL]
cpu_dep_txt = f"{r(min(cpu_dep), 0)}-{r(max(cpu_dep), 0)}%"
signs = {p: head_ctl[p] > head[p] for p in PL}
assert len(set(signs.values())) == 2, "directions are not mixed"
n_cpu_groups = {p: v(f"leiden_groups.dgx_cpu.{p}") for p in PL}
n_srv_groups = {p: v(f"leiden_groups.server_cpu.{p}") for p in PL}
n_gpu_groups = {p: v(f"leiden_groups.server_gpu.{p}") for p in PL}
for d_ in (n_cpu_groups, n_srv_groups): assert all(len(set(l)) == 1 for l in d_.values())
cooc_groups = n_cpu_groups[H8][0]
eq41 = v("cooc.hd8_rsc0141_equal_intervals"); eq51 = v("cooc.Q1_hd8_rsc0151_equal_intervals")
assert len(set(eq41)) == 1 and len(set(eq51)) == 1
assert v("cooc.n_unequal_1e-4") == 49 - eq41[0]
maxdiff = v("cooc.Q1_hd8_rsc0151_max_abs_diff"); assert len(set(maxdiff)) == 1
q3, q3ci = v("cooc.Q3_ratio"), v("cooc.Q3_ci")
chk = v("cooc.check_speedup_dgx_rsc0151"); t51 = mean(v("cooc.t_hd8_rsc0151"))
cooc_cpu = T("dgx_cpu", H8, "co_occurrence")["mean"]
share_cooc = pct(cooc_cpu, tot[H8][0]["mean"])
# HD 2 um shares
h2_umap_cpu = pct(T("dgx_cpu", H2, "umap")["mean"], tot[H2][0]["mean"])
h2_sn_gpu = pct(T("server_gpu", H2, "spatial_neighbors")["mean"], tot[H2][1]["mean"])
h2_dl_gpu = pct(T("server_gpu", H2, "data_loading")["mean"], tot[H2][1]["mean"])
h8_sn_gpu = pct(T("server_gpu", H8, "spatial_neighbors")["mean"], tot[H8][1]["mean"])
# Visium v1
v1_lr_gpu = pct(T("server_gpu", V1, "ligrec")["mean"], tot[V1][1]["mean"])
GPU_STEPS = ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "expression_neighbors",
             "leiden", "umap", "spatial_autocorr_moran", "spatial_autocorr_geary", "co_occurrence"]
NAMES = {"data_loading": "data loading", "qc_filtering": "QC", "normalization": "normalisation",
         "hvg_selection": "HVG selection", "pca": "PCA", "expression_neighbors": "expression neighbours",
         "leiden": "Leiden", "umap": "UMAP", "spatial_autocorr_moran": "Moran's I",
         "spatial_autocorr_geary": "Geary's C", "co_occurrence": "co-occurrence"}
v1_slow = sorted([s for s in GPU_STEPS if S(V1, s)[2] < 1], key=lambda s: S(V1, s)[0])
def andlist(l): return l[0] if len(l) == 1 else ", ".join(l[:-1]) + " and " + l[-1]
v1_slow_txt = andlist([f"{NAMES[s]} ({x(S(V1, s)[0])})" for s in v1_slow])
# Moran and Geary on Visium HD
mor = [S(p, "spatial_autocorr_moran")[0] for p in (H8, H2)]; gea = [S(p, "spatial_autocorr_geary")[0] for p in (H8, H2)]
mor_c = [S(p, "spatial_autocorr_moran", "control_server")[0] for p in (H8, H2)]
gea_c = [S(p, "spatial_autocorr_geary", "control_server")[0] for p in (H8, H2)]
gpu_sa = [T("server_gpu", p, s)["mean"] for p in (H8, H2) for s in ("spatial_autocorr_moran", "spatial_autocorr_geary")]
cpu_sa = [T("dgx_cpu", p, s)["mean"] for p in (H8, H2) for s in ("spatial_autocorr_moran", "spatial_autocorr_geary")]
gpu_mor = [T("server_gpu", p, "spatial_autocorr_moran")["mean"] for p in (H8, H2)]
gpu_gea = [T("server_gpu", p, "spatial_autocorr_geary")["mean"] for p in (H8, H2)]
assert min(gpu_mor) > 3.5 and max(gpu_gea) < 1.0
rho_all = [y for p in PL for g, k in (("moranI", "I_spearman_rho"), ("gearyC", "C_spearman_rho")) for y in C(p, g, k)]
rho_min = floor4(min(rho_all))
top50 = [y for p in PL for y in C(p, "moranI", "svg_jaccard_top50")]; assert set(top50) == {1.0}
sn = {p: (T("dgx_cpu", p, "spatial_neighbors")["mean"], T("server_gpu", p, "spatial_neighbors")["mean"]) for p in (H8, H2)}
ratio_h2 = n_cpu_groups[H2][0] / n_gpu_groups[H2][0]
gpu_ram_max_p = max(PL, key=lambda p: ram("server_gpu", p))
vtot = {gi["gpu_vram_total_gb"] for p in PL for gi in v(f"run.server_gpu.{p}.gpu_info")}; assert len(vtot) == 1; vtot = vtot.pop()
vb = {y for p in PL for y in v(f"run.server_gpu.{p}.vram_before_loading_gb")}; assert len(vb) == 1; vb = vb.pop()
n_hd2_in = v(f"run.dgx_cpu.{H2}.n_spots_input")[0]
dense_gb = n_hd2_in * 2000 * 4 / 1e9; dense_gib = n_hd2_in * 2000 * 4 / 1024**3
def ari(p, tag="reference"): return C(p, "clusters", "ari", tag)
def nmi(p, tag="reference"): return C(p, "clusters", "nmi", tag)
gpu8 = n_gpu_groups[H8]; n3, n4 = gpu8.count(3), gpu8.count(4); assert n3 + n4 == 5
HD2 = "Visium HD 2 um (random 400k-bin subsample)"
WORDS = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

# ------------------------------------------------------------------ new texts
def row8(name, p):
    c, g = tot[p]
    return (f"| {name} | {bins(p):,} | {t(c['mean'], c['sd'])} | {t(g['mean'], g['sd'])} | "
            f"{xci(sp_tot[p], 2)} | {r(ctl_tot[p][0], 2)}x | {r(ram('dgx_cpu', p), 2)} | {r(vram(p), 2)} |")

T9_STEPS = ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "expression_neighbors", "leiden",
            "umap", "spatial_neighbors", "spatial_autocorr_moran", "spatial_autocorr_geary", "co_occurrence",
            "nhood_enrichment", "total"]
T9_LAB = {"data_loading": "Data loading", "qc_filtering": "QC and filtering", "normalization": "Normalisation",
          "hvg_selection": "HVG selection", "pca": "PCA", "expression_neighbors": "Expression neighbours",
          "leiden": "Leiden clustering", "umap": "UMAP", "spatial_neighbors": "Spatial neighbours (CPU in both)",
          "spatial_autocorr_moran": "Moran's I", "spatial_autocorr_geary": "Geary's C",
          "co_occurrence": "Co-occurrence", "nhood_enrichment": "Neighbourhood enrichment (CPU in both)",
          "total": "Total"}
def row9(s):
    c = T("dgx_cpu", H8, s)
    if s == "co_occurrence":
        return f"| {T9_LAB[s]} | {t(c['mean'], c['sd'])} | n.r. | n.r. |"
    g = T("server_gpu", H8, s)
    return f"| {T9_LAB[s]} | {t(c['mean'], c['sd'])} | {t(g['mean'], g['sd'])} | {xci(S(H8, s), 2 if s == 'total' else None)} |"

def c4(p, g, k): return rng(C(p, g, k), 4)
def c3(p, g, k): return rng(C(p, g, k), 3)
def ngr(p):
    a = sorted(set(n_cpu_groups[p])); b = sorted(set(n_gpu_groups[p]))
    f = lambda l: f"{l[0]:,}" if len(l) == 1 else f"{l[0]:,}-{l[-1]:,}"
    return f"{f(a)} / {f(b)}"

BLOCK = f"""### End-to-end and per-step GPU speedup on three Visium platforms

Table 8 summarises the spatial benchmark on the three platforms.

: **Table 8.** Spatial transcriptomics benchmark: mean +/- SD of five repeats (n = 5, ddof = 1), each in a fresh process. CPU: one DGX H100 node (`poddgx02`, 100 CPUs), the reference; GPU: one RTX 4090. Speedup: ratio of mean totals with 95% bootstrap interval; the next column uses the 128-thread workstation CPU as reference. At Visium HD 8 um the totals include co-occurrence, whose GPU result with rapids-singlecell 0.14.1 was incorrect (see text); without co-occurrence the totals are {t(cpu_wo)} s (CPU) and {t(gpu_wo)} s (GPU) and the speedup is {xci(wo)} ({x(wo_ctl[0])} with the workstation CPU). Memory: mean of the per-repeat peaks in GiB; GPU VRAM is the device-wide NVML reading and includes the RMM pool. {{#tbl:spatial_summary}}

| Platform | Spots/bins | CPU total (s) | GPU total (s) | Speedup | Speedup, workstation CPU | CPU RAM (GiB) | GPU VRAM (GiB) |
|:---------|----------:|---------------:|--------------:|--------:|--------:|-------------:|--------------:|
{row8("Visium v1", V1)}
{row8("Visium HD 8 um", H8)}
{row8(HD2, H2)}

Against the DGX CPU reference, end-to-end GPU speedups were {x(head[V1])} on Visium v1 ({bins(V1):,} spots), {x(head[H8])} on Visium HD 8 um ({bins(H8):,} bins; co-occurrence excluded, see below) and {x(head[H2])} on the random 400k-bin subsample of Visium HD 2 um ({bins(H2):,} bins after QC) (Table 8, Fig. 7).
With the 128-thread workstation CPU as reference they were {x(head_ctl[V1])}, {x(head_ctl[H8])} and {x(head_ctl[H2])}: the choice of CPU changed the speedup by {cpu_dep_txt}, in different directions per platform.
Visium HD 8 um and the 2 um subsample have similar numbers of bins but ran different steps (co-occurrence and neighbourhood enrichment were skipped at 2 um, see below), so the order of the speedups does not show an effect of resolution.

![**Figure 7.** Total pipeline wall time on three Visium platforms: CPU reference (one DGX H100 node, 100 CPUs) and GPU (one RTX 4090), mean of five repeats, each in a fresh process; error bars: SD. Labels give the speedup (ratio of means). At Visium HD 8 um the bars include co-occurrence, whose GPU result with rapids-singlecell 0.14.1 was incorrect (see text); the dashed lines mark the totals without it ({x(head[H8])}). Visium HD 2 um was randomly subsampled to 400,000 bins ({bins(H2):,} after QC) to fit in the {r(vtot, 0)} GiB of the RTX 4090.](../figures/fig7_spatial_speedup.png)

At Visium HD 8 um, with the same {cooc_groups} cell groups as the CPU, the GPU co-occurrence computed with rapids-singlecell 0.14.1 was incorrect: it matched the CPU result within an absolute tolerance of 0.001 in only {eq41[0]} of 49 distance intervals, because the number of bin pairs within the larger distance thresholds exceeds the range of its 32-bit integer counters.
The GPU co-occurrence of the original March runs had the same defect.
With rapids-singlecell 0.15.1 the GPU result matched the CPU in {eq51[0]} of 49 intervals (maximum absolute difference {r(maxdiff[0], 5)}) at unchanged runtime (0.15.1/0.14.1 time ratio {r(q3, 2)}, 95% CI {r(q3ci[0], 2)}-{r(q3ci[1], 2)}).
In this separate check, co-occurrence with 0.15.1 took {t(t51)} s against {t(cooc_cpu)} s on the DGX CPU ({x(chk[0])}, 95% CI {r(chk[1], 1)}-{r(chk[2], 1)}); because the check ran outside the pipeline and the pipeline result was incorrect, co-occurrence is excluded from the Visium HD speedups.
Squidpy counts co-occurring cluster pairs with a Numba-parallel loop over all pairs of bins for each distance interval (O(n^2) per interval); rapids-singlecell performs the same counting on the GPU.
On the DGX CPU, co-occurrence took {share_cooc}% of the pipeline time at Visium HD 8 um.

![**Figure 8.** Per-step GPU speedup on Visium HD 8 um ({bins(H8):,} bins) against the DGX CPU reference: ratio of means over five repeats; error bars: 95% bootstrap interval. The largest speedups were for UMAP ({x(S(H8, "umap")[0])}) and Geary's C ({x(S(H8, "spatial_autocorr_geary")[0])}); Moran's I reached {x(S(H8, "spatial_autocorr_moran")[0])}. Spatial neighbours and neighbourhood enrichment ran in Squidpy on the CPU in both pipelines (open circles; {x(S(H8, "spatial_neighbors")[0])} and {x(S(H8, "nhood_enrichment")[0])}). Co-occurrence (open diamond) is the speedup of the separate check with rapids-singlecell 0.15.1 ({x(chk[0])}), because the pipeline result with 0.14.1 was incorrect (see text).](../figures/fig8_spatial_perstep.png)

On Visium HD 8 um the GPU accelerated UMAP {x(S(H8, "umap")[0])}, Geary's C {x(S(H8, "spatial_autocorr_geary")[0])}, PCA (with scaling) {x(S(H8, "pca")[0])}, normalisation {x(S(H8, "normalization")[0])} and Moran's I {x(S(H8, "spatial_autocorr_moran")[0])}; expression neighbours and Leiden clustering were accelerated {x(S(H8, "expression_neighbors")[0])} and {x(S(H8, "leiden")[0])}, and data loading, QC and HVG selection ran at {x(S(H8, "data_loading")[0])}, {x(S(H8, "qc_filtering")[0])} and {x(S(H8, "hvg_selection")[0])} (Table 9, Fig. 8).
As in the scRNA-seq pipeline, CPU expression neighbour search ran pynndescent on one Numba thread (Methods), so its speedup is relative to a single-threaded search.

: **Table 9.** Per-step wall time and GPU speedup on Visium HD 8 um ({bins(H8):,} bins): mean +/- SD of five repeats, each in a fresh process; CPU reference: one DGX H100 node (100 CPUs); speedup: ratio of means with 95% bootstrap interval. Spatial neighbours and neighbourhood enrichment have no GPU implementation in rapids-singlecell 0.14.1: the GPU pipeline calls Squidpy on the CPU, so the GPU column for these rows is CPU time on the workstation. PCA includes scaling. CPU expression neighbour search ran on one Numba thread (Methods). Co-occurrence: the GPU result with rapids-singlecell 0.14.1 was incorrect (see text), so no GPU time or speedup is reported (n.r.); with 0.15.1, in a separate check, it took {t(t51)} s ({x(chk[0])}). The total includes co-occurrence. {{#tbl:spatial_steps}}

| Step | CPU (s) | GPU (s) | Speedup |
|:-----|--------:|--------:|--------:|
""" + "\n".join(row9(s) for s in T9_STEPS) + f"""

On the Visium HD 2 um subsample, CPU Leiden returned {n_cpu_groups[H2][0]:,} groups, so co-occurrence and neighbourhood enrichment were skipped (more than 500 groups, Methods) and the totals contain fewer steps than at Visium HD 8 um.
UMAP, the largest CPU cost ({h2_umap_cpu}% of the CPU time), ran {x(S(H2, "umap")[0])} faster on the GPU; the GPU pipeline time ({t(tot[H2][1]['mean'])} s) was dominated by spatial neighbours ({h2_sn_gpu}%) and data loading ({h2_dl_gpu}%).

On Visium v1 ({bins(V1):,} spots) the end-to-end speedup was {x(head[V1])}: ligand-receptor analysis, run in Squidpy on the CPU in both pipelines, took {v1_lr_gpu}% of the GPU pipeline time, and {v1_slow_txt} were slower on the GPU than on the CPU.

Three steps ran in Squidpy on the CPU inside the GPU pipeline: spatial neighbours (Delaunay triangulation via scipy.spatial), neighbourhood enrichment and ligand-receptor analysis (Visium v1 only).
On the two Visium HD platforms spatial neighbours took {t(sn[H8][0])} s and {t(sn[H2][0])} s on the DGX CPU and {t(sn[H8][1])} s and {t(sn[H2][1])} s in the GPU pipeline on the workstation CPU, {h8_sn_gpu}% (HD 8 um) and {h2_sn_gpu}% (HD 2 um subsample) of the GPU pipeline time.

### Spatial concordance: close for spatial statistics, divergent for clustering on the Visium HD 2 um subsample

Spatial autocorrelation statistics agreed closely between CPU and GPU on all three platforms (Table 10, Fig. 9).

![**Figure 9.** Concordance between the CPU reference (DGX node) and GPU spatial pipelines on three Visium platforms, CPU repeat k against GPU repeat k (k = 1-5); points: mean of the five pairs, bars: range where the pairs differ. Left: Spearman rho of per-gene Moran's I and Geary's C over 2,000 HVGs, and Jaccard index (J) of spatially variable gene (SVG) sets ranked by Moran's I (top 50, 100 and 200, and FDR < 0.05). Right: adjusted Rand index and normalised mutual information of the expression-based Leiden partitions. On the Visium HD 2 um subsample the partitions diverge (ARI {c3(H2, "clusters", "ari")}): CPU Leiden (igraph, 2 iterations) returned {n_cpu_groups[H2][0]:,} groups and GPU Leiden (cuGraph, up to 100 iterations) {n_gpu_groups[H2][0]:,}; the number of CPU groups also depends on the CPU machine (Table 10).](../figures/fig9_spatial_concordance.png)

Moran's I and Geary's C Spearman correlations between CPU and GPU were at least {rho_min} in all cases.
The top-50 spatially variable genes by Moran's I formed the same set on CPU and GPU on all three platforms (Jaccard = 1.000); for the top 100 and top 200 the Jaccard index was {c3(V1, "moranI", "svg_jaccard_top100")} on Visium v1 and {c3(H8, "moranI", "svg_jaccard_top100")} on both Visium HD platforms.
At FDR < 0.05, the Jaccard index of the SVG sets was {c3(V1, "moranI", "svg_jaccard_fdr005")} (Visium v1), {c3(H8, "moranI", "svg_jaccard_fdr005")} (HD 8 um) and {c3(H2, "moranI", "svg_jaccard_fdr005")} (HD 2 um subsample).

: **Table 10.** Spatial concordance between the CPU reference (DGX node) and GPU pipelines, CPU repeat k against GPU repeat k (k = 1-5): a single value when it is the same in the five pairs, otherwise the range. SVG Jaccard reports the overlap of spatially variable genes ranked by Moran's I. Co-occurrence and neighbourhood enrichment were skipped on the HD 2 um subsample (more than 500 groups); at Visium HD 8 um the GPU co-occurrence is the incorrect result of rapids-singlecell 0.14.1 (see text). N clusters: groups returned by each pipeline's own Leiden run in each repeat. With the workstation CPU as reference, CPU Leiden returned {n_srv_groups[V1][0]:,}, {n_srv_groups[H8][0]:,} and {n_srv_groups[H2][0]:,} groups and the ARI was {c3(V1, "clusters", "ari")}, {rng(ari(H8, "control"), 3)} and {rng(ari(H2, "control"), 3)}. {{#tbl:spatial_concordance}}

| Metric | Visium v1 | HD 8 um | {HD2} |
|:-------|----------:|------------:|------------:|
| Moran's I Spearman rho | {c4(V1, "moranI", "I_spearman_rho")} | {c4(H8, "moranI", "I_spearman_rho")} | {c4(H2, "moranI", "I_spearman_rho")} |
| Geary's C Spearman rho | {c4(V1, "gearyC", "C_spearman_rho")} | {c4(H8, "gearyC", "C_spearman_rho")} | {c4(H2, "gearyC", "C_spearman_rho")} |
| SVG Jaccard (top 50) | {c3(V1, "moranI", "svg_jaccard_top50")} | {c3(H8, "moranI", "svg_jaccard_top50")} | {c3(H2, "moranI", "svg_jaccard_top50")} |
| SVG Jaccard (top 100) | {c3(V1, "moranI", "svg_jaccard_top100")} | {c3(H8, "moranI", "svg_jaccard_top100")} | {c3(H2, "moranI", "svg_jaccard_top100")} |
| SVG Jaccard (top 200) | {c3(V1, "moranI", "svg_jaccard_top200")} | {c3(H8, "moranI", "svg_jaccard_top200")} | {c3(H2, "moranI", "svg_jaccard_top200")} |
| SVG Jaccard (FDR < 0.05) | {c3(V1, "moranI", "svg_jaccard_fdr005")} | {c3(H8, "moranI", "svg_jaccard_fdr005")} | {c3(H2, "moranI", "svg_jaccard_fdr005")} |
| Cluster ARI | {c3(V1, "clusters", "ari")} | {c3(H8, "clusters", "ari")} | {c3(H2, "clusters", "ari")} |
| Cluster NMI | {c3(V1, "clusters", "nmi")} | {c3(H8, "clusters", "nmi")} | {c3(H2, "clusters", "nmi")} |
| N clusters (CPU / GPU) | {ngr(V1)} | {ngr(H8)} | {ngr(H2)} |
| Co-occurrence Spearman rho | {c4(V1, "co_occurrence", "spearman_rho")} | {c4(H8, "co_occurrence", "spearman_rho")} (0.14.1) | n.r. |
| Neighbourhood enrichment Spearman rho | {c4(V1, "nhood_enrichment", "spearman_rho")} | {c4(H8, "nhood_enrichment", "spearman_rho")} | n.r. |

Expression-based Leiden clustering agreed on Visium v1 (ARI {c3(V1, "clusters", "ari")}, NMI {c3(V1, "clusters", "nmi")}) and Visium HD 8 um (ARI {c3(H8, "clusters", "ari")}, NMI {c3(H8, "clusters", "nmi")} over the five repeat pairs), where GPU Leiden returned 3 groups in {WORDS[n3]} repeats and 4 in {WORDS[n4]}, against {n_cpu_groups[H8][0]} for the DGX CPU ({n_srv_groups[H8][0]} for the workstation CPU).
On the Visium HD 2 um subsample the partitions diverged (ARI {c3(H2, "clusters", "ari")}, NMI {c3(H2, "clusters", "nmi")}): CPU Leiden returned {n_cpu_groups[H2][0]:,} clusters on the DGX reference and GPU Leiden {n_gpu_groups[H2][0]:,}, in each of the five repeats.
The number of CPU clusters depended on the CPU machine ({n_srv_groups[H2][0]:,} on the 128-thread workstation).
This {r(ratio_h2, 2)}-fold difference in cluster granularity coincides with the use of two Leiden implementations with different settings (igraph with 2 iterations on the CPU, cuGraph with up to 100 iterations on the GPU); we did not test which of the two factors, or the subsampling, causes it.
The 2 um subsample retains {bins(H2):,} of 6.3 million bins; we did not test whether its sparsity contributes to the fragmented partition.

### Memory use on spatial platforms

GPU memory readings (NVML, device-wide) reflect the RMM memory pool: {r(vb, 2)} GiB was reserved before data loading in every GPU run, and the peak reading was {r(vram(V1), 2)} GiB on Visium v1, {r(vram(H8), 2)} GiB on Visium HD 8 um and {r(vram(H2), 2)} GiB on the HD 2 um subsample ({r(100 * vram(H8) / vtot, 0)}% of the {r(vtot, 1)} GiB of the RTX 4090); the 2 um data had to be subsampled to fit (Methods).
Peak CPU RAM ranged from {r(ram('dgx_cpu', V1), 2)} GiB (Visium v1) to {r(ram('dgx_cpu', H2), 2)} GiB (HD 2 um subsample) on the DGX CPU reference, and reached {r(ram('server_gpu', gpu_ram_max_p), 2)} GiB in the GPU pipeline (Visium HD 8 um).
Whether the full-resolution Visium HD 2 um dataset ({n_hd2_in / 1e6:.1f} million bins) fits in GPU memory was not tested; the CPU pipeline densifies the HVG matrix, which at this size would need about {r(dense_gb, 0)} GB ({r(dense_gib, 0)} GiB) in float32."""
assert gpu_ram_max_p == H8

DISC1 = (f"The spatial benchmark, repeated with a fresh process per repeat and the same cell groups on CPU and GPU, gave end-to-end speedups of "
         f"{x(head[V1])} (Visium v1), {x(head[H8])} (Visium HD 8 um, co-occurrence excluded) and {x(head[H2])} (Visium HD 2 um subsample) against the 100-CPU DGX reference "
         f"({x(head_ctl[V1])}, {x(head_ctl[H8])} and {x(head_ctl[H2])} against the workstation CPU); among the spatial-specific steps of the pipeline only spatial autocorrelation gained substantially, "
         f"and GPU co-occurrence at Visium HD 8 um was incorrect in rapids-singlecell 0.14.1 (correct, and {x(chk[0])} faster than the DGX CPU, with 0.15.1).")
DISC2 = (f"In the spatial benchmark, the GPU advantage was concentrated in a few steps rather than spread across spatial statistics as a whole. "
         f"At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was incorrect: on the same {cooc_groups} cell groups as the CPU it matched the CPU result at only {eq41[0]} of 49 distances, "
         f"because its 32-bit pair counters overflow at this number of bins. With rapids-singlecell 0.15.1 it matched at {eq51[0]} of 49 distances in the same time "
         f"(time ratio {r(q3, 2)}, 95% CI {r(q3ci[0], 2)}-{r(q3ci[1], 2)}), so we excluded co-occurrence from the Visium HD speedups; in a separate check the corrected version was {x(chk[0])} faster than the DGX CPU. "
         f"Spatial autocorrelation statistics were accelerated {rng(mor, 1)}x (Moran's I) and {rng(gea, 1)}x (Geary's C) on Visium HD ({rng(mor_c, 1)}x and {rng(gea_c, 1)}x against the workstation CPU), "
         f"with near-perfect numerical concordance (Spearman rho >= {rho_min}); the top-50 spatially variable genes formed the same set on CPU and GPU, and each statistic took "
         f"{rng(gpu_sa, 1)} s on the GPU instead of {rng(cpu_sa, 0)} s on the CPU reference. "
         f"On the GPU, Moran's I remained slower than Geary's C (about {r(mean(gpu_mor), 0)} s against less than 1 s), and on Visium v1 it was not accelerated ({x(S(V1, 'spatial_autocorr_moran')[0])}). "
         f"In rapids-singlecell 0.14.1, spatial neighbour computation and neighbourhood enrichment have no GPU implementation and ran on the CPU inside the GPU pipeline "
         f"({x(S(H8, 'spatial_neighbors')[0])} and {x(S(H8, 'nhood_enrichment')[0])} at Visium HD 8 um); ligand-receptor analysis, run on Visium v1 only, has a GPU implementation in rapids-singlecell 0.14.1 "
         f"that our pipeline did not use (Squidpy on the CPU in both pipelines, {x(S(V1, 'ligrec')[0])}).")
DISC3 = (f"A notable finding from spatial analysis concerns clustering on the Visium HD 2 um subsample. "
         f"At {bins(H2):,} spatial bins and resolution 0.1, the igraph (CPU) and cuGraph (GPU) implementations returned very different partitions (ARI {c3(H2, 'clusters', 'ari')}): "
         f"CPU Leiden returned {n_cpu_groups[H2][0]:,} clusters on the DGX reference and {n_srv_groups[H2][0]:,} on the workstation and {n_gpu_groups[H2][0]:,} on the GPU, each the same in all five repeats. "
         f"The divergence is therefore systematic between implementations and machines rather than run-to-run stochasticity; we did not test whether different seeds of the same implementation diverge to a similar extent. "
         f"Users working at this resolution should therefore check how stable Leiden partitions are across implementations and settings before interpreting them.")
CONCL = (f"For spatial transcriptomics on one RTX 4090, end-to-end speedups against a 100-CPU DGX node were {x(head[V1])} on Visium v1, {x(head[H8])} on Visium HD 8 um with co-occurrence excluded "
         f"and {x(head[H2])} on a random 400k-bin subsample of Visium HD 2 um; Moran's I and Geary's C agreed between CPU and GPU (Spearman rho at least {rho_min}). "
         f"The GPU co-occurrence of rapids-singlecell 0.14.1 was incorrect at Visium HD 8 um because of 32-bit integer overflow; version 0.15.1 corrects it at unchanged runtime.")
METH_T3_OLD = "| 14 | Ligand-receptor interaction | No | Squidpy re-implementation of CellPhoneDB [@Palla2022] |"
METH_T3_NEW = "| 14 | Ligand-receptor interaction | Not used | Squidpy re-implementation of CellPhoneDB [@Palla2022]; the GPU version in rapids-singlecell 0.14.1 was not used |"
METH_136_OLD = "Steps without GPU implementations (spatial neighbours, neighbourhood enrichment, ligand-receptor) were executed identically on CPU in both pipelines."
METH_136_NEW = ("Spatial neighbours and neighbourhood enrichment, which have no GPU implementation in rapids-singlecell 0.14.1, and ligand-receptor analysis, "
                "whose GPU implementation in rapids-singlecell 0.14.1 (`rsc.gr.ligrec`) our GPU pipeline did not use, ran in Squidpy on the CPU in both pipelines. "
                "On Visium HD (more than 8,192 bins), CPU expression neighbour search used pynndescent with one Numba thread, as in the scRNA-seq CPU pipeline.")
METH_142_OLD = "Finally, co-occurrence concordance was the Spearman rho between the full CPU and GPU co-occurrence matrices."
METH_142_NEW = ("Co-occurrence and neighbourhood enrichment concordance were the Spearman rho between the full CPU and GPU matrices, computed on the same cell groups; "
                "for co-occurrence we also counted the distance intervals at which the CPU and GPU matrices agreed within an absolute tolerance of 0.001. "
                "Each metric was computed for the five pairs of CPU repeat k and GPU repeat k; we report the value when it is the same in all pairs and the range otherwise. "
                "To check the GPU co-occurrence at Visium HD 8 um, we repeated it alone five times on the same cell groups, with rapids-singlecell 0.15.1 and, as a control, 0.14.1, in images that differ only in this package.")
AVAIL_OLD = "All code, Dockerfiles, SLURM submission scripts, and benchmark result JSON\nfiles are available at <https://github.com/lucavd/2026.scRNA_DGX>."
AVAIL_NEW = "All code, Dockerfiles, SLURM submission scripts, benchmark result JSON files and the scripts that generate every figure are available at <https://github.com/lucavd/2026.scRNA_DGX>."

BLOCK_START = "### GPU speedup scales dramatically with platform resolution"
BLOCK_END = "These modest requirements suggest that spatial benchmarks at full Visium HD resolution (6.3M bins at 2 um) would fit comfortably within DGX H100 memory."
SENT = [
 ("M1", METH_T3_OLD, METH_T3_NEW, "S5-N1 (rsc.gr.ligrec presente in 0.14.1)"),
 ("M2", METH_136_OLD, METH_136_NEW, "S5-N1; D-16 (vicini spatial a 1 thread)"),
 ("M3", METH_142_OLD, METH_142_NEW, "R0343; R0701; D-15"),
 ("D1", "The extension to spatial transcriptomics shows that GPU advantages are even more pronounced for spatial-specific operations, with co-occurrence analysis achieving over three orders of magnitude speedup.", DISC1, "R0572; D-20"),
 ("D2", None, DISC2, "R0610; R0611; R0612; R0613; R0555; R0713; D-20"),
 ("D3", None, DISC3, "R0615; R0616; R0617; R0337"),
 ("C1", "For spatial transcriptomics, GPU acceleration delivers 51.6x end-to-end speedup on Visium HD, with co-occurrence analysis achieving a 3,272x speedup and spatial autocorrelation concordance exceeding 0.9995.", CONCL, "R0340"),
 ("A1", AVAIL_OLD, AVAIL_NEW, "R0382"),
 ("M4", "We compared CPU and GPU spatial outputs along four complementary axes.", "We compared CPU and GPU spatial outputs along five axes.", "R0343 (co-occurrence and neighbourhood enrichment)"),
]
LINE_PREFIX = {"D2": "Beyond scRNA-seq, the extension to spatial transcriptomics demonstrates",
               "D3": "A notable finding from spatial analysis concerns clustering at extreme resolution."}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--preview")
    a = ap.parse_args()
    text = open(MS, encoding="utf-8").read()
    md5_before = hashlib.md5(text.encode()).hexdigest()
    edits = []
    i0, i1 = text.find(BLOCK_START), text.find(BLOCK_END)
    edits.append({"edit": "R1", "anchor": BLOCK_START + " ... " + BLOCK_END,
                  "count_before": min(text.count(BLOCK_START), text.count(BLOCK_END)) if text.count(BLOCK_START) == text.count(BLOCK_END) else -1,
                  "old": text[i0:i1 + len(BLOCK_END)] if i0 >= 0 and i1 > i0 else None, "new": BLOCK,
                  "entries": "Results spatial (R0280 ... R0720)"})
    if edits[-1]["count_before"] == 1:
        text = text[:i0] + BLOCK + text[i1 + len(BLOCK_END):]
    lines = text.split("\n")
    for eid, old, new, ids in SENT:
        if old is None:
            hits = [k for k, l in enumerate(lines) if l.startswith(LINE_PREFIX[eid])]
            e = {"edit": eid, "anchor": LINE_PREFIX[eid], "count_before": len(hits),
                 "old": lines[hits[0]] if len(hits) == 1 else None, "new": new, "entries": ids}
            if len(hits) == 1:
                lines[hits[0]] = new
        else:
            joined = "\n".join(lines); n = joined.count(old)
            e = {"edit": eid, "anchor": old, "count_before": n, "old": old, "new": new, "entries": ids}
            if n == 1:
                lines = joined.replace(old, new).split("\n")
        edits.append(e)
    text2 = "\n".join(lines)
    ok = all(e["count_before"] == 1 for e in edits)
    md5_after = hashlib.md5(text2.encode()).hexdigest()
    print(json.dumps({"all_anchors_unique": ok, "md5_before": md5_before, "md5_after": md5_after,
                      "counts": {e["edit"]: e["count_before"] for e in edits}}))
    if a.preview:
        open(a.preview, "w", encoding="utf-8").write(text2)
    if not ok or a.dry_run:
        sys.exit(0 if ok else 1)
    open(MS, "w", encoding="utf-8").write(text2)
    json.dump({"manuscript": MS, "md5_before": md5_before, "md5_after": md5_after, "all_anchors_unique": ok,
               "numbers": NUM, "edits": edits}, open(OUT, "w"), indent=1, ensure_ascii=False)
    write_diary()

DIARY_ROWS = None  # filled by tools/s5_diary.py data (imported below)

def write_diary():
    import importlib.util
    spec = importlib.util.spec_from_file_location("s5_diary", "tools/s5_diary.py"); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ledger = {r_["id"]: r_ for r_ in csv.DictReader(open(LEDGER, encoding="utf-8")) if r_["step"] == "S5"}
    rows = m.ROWS
    missing, extra = set(ledger) - set(rows), set(rows) - set(ledger)
    assert not missing and not extra, (missing, extra)
    existing = [r_["id"] for r_ in csv.DictReader(open(DIARY, encoding="utf-8"))]
    assert not set(rows) & set(existing), "S5 rows already in the diary"
    with open(DIARY, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for i in sorted(rows):
            esito, val, src, note = rows[i]
            w.writerow([i, ledger[i]["level"], esito, val, ledger[i]["decision"] or "CONV", src, ledger[i]["line"], DATE, note])
    print(f"diary: {len(rows)} rows appended")

if __name__ == "__main__":
    main()
