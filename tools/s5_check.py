#!/usr/bin/env python3
"""Independent check of step S5 (gates G2, G3, G4 of docs/steps/S5.md).

Written separately from tools/s5_numbers.py, tools/s5_apply.py and
scripts/generate_spatial_figures.py: it re-reads the S1 files with the Python
standard library and does its own rounding. PyMuPDF is used for the PDFs.
The bootstrap interval of the co-occurrence check is recomputed with the
standard-library random generator (another generator than the figure script),
so its bounds are compared with a relative tolerance of 1%.

  G2  every value of results_v2/S5/figure_values.csv (relative tolerance 1e-9)
      and every spatial number of the new text, tables and captions
  G3  print specifications and greyscale of the three spatial PDFs
  G4  text integrity: superseded values absent, no U+2013/U+2014, one diary
      row per S5 ledger row (pandoc and the OKF check run in the job script)

Usage: python3 -B tools/s5_check.py [--pdf-dir figures] [--out results_v2/S5/s5_check.json]
"""
import argparse, csv, json, math, random, re, statistics, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="SPATIAL/results_v2")
ap.add_argument("--ms", default="manuscript/full_paper_LNBI.md")
ap.add_argument("--values", default="results_v2/S5/figure_values.csv")
ap.add_argument("--styles", default="results_v2/S5/figure_styles.json")
ap.add_argument("--pdf-dir", default="figures")
ap.add_argument("--out", default="results_v2/S5/s5_check.json")
a = ap.parse_args()
R = Path(a.root)
P = ["visium", "visium_hd_square_008um", "visium_hd_square_002um"]
V1, H8, H2 = P
res = {"G2_values": [], "G2_text": [], "G3": {}, "G4": {}}

# ---------------------------------------------------------------- raw data
rows = list(csv.DictReader(open(R / "s1_step_stats.csv")))
spd = list(csv.DictReader(open(R / "s1_speedups.csv")))
extra = json.load(open(R / "s1_extra_numbers.json"))
cooc = json.load(open(R / "cooc_check/cooc_check_eval.json"))
conc = {p: json.load(open(R / f"concordance_reference/spatial_concordance_{p}.json")) for p in P}
concs = {p: json.load(open(R / f"concordance_server_control/spatial_concordance_{p}.json")) for p in P}

def reps(run, p, s):
    (x,) = [r for r in rows if r["run"] == run and r["platform"] == p and r["step"] == s]
    return [float(x[f"r{k}"]) for k in range(1, 6)]
def mean(run, p, s): return statistics.fmean(reps(run, p, s))
def sd(run, p, s): return statistics.stdev(reps(run, p, s))
def sp(p, s, cpu="reference_dgx"):
    (x,) = [r for r in spd if r["platform"] == p and r["step"] == s and r["cpu"] == cpu and r["convention"] == "1_5"]
    return float(x["speedup"]), float(x["ci_lo"]), float(x["ci_hi"])
def runjson(run, p):
    pre = "gpu" if run == "server_gpu" else "cpu"
    return [json.load(open(R / run / f"spatial_{pre}_{p}_r{k}_results.json")) for k in range(1, 6)]

# speedups must be ratios of the means of all five repeats
for p in P:
    for s in ("total", "umap", "spatial_autocorr_geary"):
        ratio = mean("dgx_cpu", p, s) / mean("server_gpu", p, s)
        assert abs(ratio / sp(p, s)[0] - 1) < 1e-9, (p, s)

# ---------------------------------------------------------------- G2: figure values
def close(x, y, tol=1e-9): return abs(x - y) <= tol * max(1.0, abs(y))
rng = random.Random(20261104)
cc = reps("dgx_cpu", H8, "co_occurrence"); gg = cooc["t_hd8_rsc0151"]
boot = sorted(statistics.fmean(rng.choices(cc, k=5)) / statistics.fmean(rng.choices(gg, k=5)) for _ in range(2000))
q = lambda f: boot[int(round(f * (len(boot) - 1)))]
cooc_sp = (statistics.fmean(cc) / statistics.fmean(gg), q(0.025), q(0.975))
def expected(fig, panel, series, x, stat):
    if fig == "fig7_spatial_speedup":
        run = {"CPU": "dgx_cpu", "GPU": "server_gpu"}.get(series)
        if stat == "mean_s": return mean(run, x, "total")
        if stat == "sd_s": return sd(run, x, "total")
        if stat == "mean_s_without_co_occurrence": return mean(run, x, "total") - mean(run, x, "co_occurrence")
        if series == "speedup": return sp(x, "total")[0]
        if series == "speedup_without_co_occurrence": return mean("dgx_cpu", x, "total") - mean("dgx_cpu", x, "co_occurrence"), "ratio"
    if fig == "fig8_spatial_perstep":
        i = {"speedup": 0, "ci_lo": 1, "ci_hi": 2}[stat]
        if series == "co_occurrence": return cooc_sp[i], ("boot" if i else None)
        return sp(x, series)[i]
    if fig == "fig9_spatial_concordance":
        g, k = series.split(".")
        vals = [r[g][k] for r in conc[x]]
        return {"mean": (min(vals) if min(vals) == max(vals) else statistics.fmean(vals)), "min": min(vals), "max": max(vals)}[stat]
    raise KeyError((fig, series, stat))
for r in csv.DictReader(open(a.values)):
    e = expected(r["figure"], r["panel"], r["series"], r["x"], r["stat"]); got = float(r["value"])
    tol, ok = 1e-9, None
    if isinstance(e, tuple):
        if e[1] == "ratio":
            e = e[0] / (mean("server_gpu", r["x"], "total") - mean("server_gpu", r["x"], "co_occurrence"))
        elif e[1] == "boot":
            e, tol = e[0], 0.01
        else:
            e = e[0]
    ok = close(got, e, tol)
    res["G2_values"].append({**r, "expected": e, "tolerance": tol, "ok": ok})

# ---------------------------------------------------------------- G2: text
ms = open(a.ms, encoding="utf-8").read()
def rd(x, d):
    return str(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d) if d else Decimal(1), rounding=ROUND_HALF_UP))
def commas(s):
    i, dot, f = s.partition("."); return f"{int(i):,}" + (dot + f if dot else "")
def sec(m, s=None):
    d = max(0, 2 - math.floor(math.log10(abs(m))))
    if s: d = min(max(d, -math.floor(math.log10(abs(s)))), 4)
    return commas(rd(m, d)) + ("" if s is None else f" +/- {rd(s, d)}")
def fx(v, d=None):
    if d is None: d = 0 if v >= 100 else (1 if v >= 1 else 2)
    return commas(rd(v, d)) + "x"
def fci(t, d=None):
    if d is None: d = 0 if t[0] >= 100 else (1 if t[0] >= 1 else 2)
    return f"{fx(t[0], d)} ({commas(rd(t[1], d))}-{commas(rd(t[2], d))})"
def span(vals, d):
    lo, hi = rd(min(vals), d), rd(max(vals), d); return lo if lo == hi else f"{lo}-{hi}"
def need(label, s):
    n = ms.count(s); res["G2_text"].append({"check": label, "string": s, "count": n, "ok": n >= 1})

bins = {p: {j["results_summary"]["n_spots_after_qc"] for run in ("dgx_cpu", "server_gpu", "server_cpu") for j in runjson(run, p)} for p in P}
assert all(len(b) == 1 for b in bins.values()); bins = {p: b.pop() for p, b in bins.items()}
ram = {(run, p): statistics.fmean(j["memory"]["peak_ram_gb"] for j in runjson(run, p)) for run in ("dgx_cpu", "server_gpu") for p in P}
vram = {p: statistics.fmean(j["memory"]["peak_vram_gb"] for j in runjson("server_gpu", p)) for p in P}
names = {V1: "Visium v1", H8: "Visium HD 8 um", H2: "Visium HD 2 um (random 400k-bin subsample)"}
for p in P:
    need(f"Table 8 {p}", f"| {names[p]} | {bins[p]:,} | {sec(mean('dgx_cpu', p, 'total'), sd('dgx_cpu', p, 'total'))} | "
         f"{sec(mean('server_gpu', p, 'total'), sd('server_gpu', p, 'total'))} | {fci(sp(p, 'total'), 2)} | "
         f"{rd(sp(p, 'total', 'control_server')[0], 2)}x | {rd(ram[('dgx_cpu', p)], 2)} | {rd(vram[p], 2)} |")
woc = mean("dgx_cpu", H8, "total") - mean("dgx_cpu", H8, "co_occurrence"); wog = mean("server_gpu", H8, "total") - mean("server_gpu", H8, "co_occurrence")
wo = extra["speedup_total_without_co_occurrence"][H8]
assert close(woc / wog, wo["reference_dgx"][0])
need("Table 8 note", f"the totals are {sec(woc)} s (CPU) and {sec(wog)} s (GPU) and the speedup is {fci(wo['reference_dgx'])} ({fx(wo['control_server'][0])} with the workstation CPU)")
head = [sp(V1, "total")[0], wo["reference_dgx"][0], sp(H2, "total")[0]]
ctl = [sp(V1, "total", "control_server")[0], wo["control_server"][0], sp(H2, "total", "control_server")[0]]
need("headline", f"end-to-end GPU speedups were {fx(head[0])} on Visium v1 ({bins[V1]:,} spots), {fx(head[1])} on Visium HD 8 um ({bins[H8]:,} bins")
need("headline 2um", f"{fx(head[2])} on the random 400k-bin subsample of Visium HD 2 um ({bins[H2]:,} bins after QC)")
dev = [abs(c / h - 1) * 100 for c, h in zip(ctl, head)]
need("control", f"they were {fx(ctl[0])}, {fx(ctl[1])} and {fx(ctl[2])}: the choice of CPU changed the speedup by {rd(min(dev), 0)}-{rd(max(dev), 0)}%")
e41, e51 = set(cooc["hd8_rsc0141_equal_intervals"]), set(cooc["Q1_hd8_rsc0151_equal_intervals"])
assert len(e41) == len(e51) == 1; e41, e51 = e41.pop(), e51.pop()
assert extra["hd8_cpu_gpu_same_groups"]["n_unequal"] == 49 - e41
need("cooc 0.14.1", f"in only {e41} of 49 distance intervals")
need("cooc 0.15.1", f"matched the CPU in {e51} of 49 intervals (maximum absolute difference {rd(cooc['Q1_hd8_rsc0151_max_abs_diff'][0], 5)})")
need("cooc ratio", f"time ratio {rd(cooc['Q3_ratio'], 2)}, 95% CI {rd(cooc['Q3_ci'][0], 2)}-{rd(cooc['Q3_ci'][1], 2)}")
need("cooc check", f"took {sec(statistics.fmean(gg))} s against {sec(statistics.fmean(cc))} s on the DGX CPU ({fx(cooc_sp[0])}, 95% CI {rd(cooc_sp[1], 1)}-{rd(cooc_sp[2], 1)})")
assert close(cooc_sp[0], cooc["speedup_cooc_hd8_dgx_over_rsc0151"])
need("cooc share", f"co-occurrence took {rd(100 * mean('dgx_cpu', H8, 'co_occurrence') / mean('dgx_cpu', H8, 'total'), 1)}% of the pipeline time")
need("cooc groups", f"with the same {set(extra['own_leiden_clusters'][H8]['dgx_cpu']).pop()} cell groups as the CPU")
labels = {"data_loading": "Data loading", "qc_filtering": "QC and filtering", "normalization": "Normalisation", "hvg_selection": "HVG selection",
          "pca": "PCA", "expression_neighbors": "Expression neighbours", "leiden": "Leiden clustering", "umap": "UMAP",
          "spatial_neighbors": "Spatial neighbours (CPU in both)", "spatial_autocorr_moran": "Moran's I", "spatial_autocorr_geary": "Geary's C",
          "nhood_enrichment": "Neighbourhood enrichment (CPU in both)", "total": "Total"}
for s, lab in labels.items():
    need(f"Table 9 {s}", f"| {lab} | {sec(mean('dgx_cpu', H8, s), sd('dgx_cpu', H8, s))} | {sec(mean('server_gpu', H8, s), sd('server_gpu', H8, s))} | {fci(sp(H8, s), 2 if s == 'total' else None)} |")
need("Table 9 cooc", f"| Co-occurrence | {sec(mean('dgx_cpu', H8, 'co_occurrence'), sd('dgx_cpu', H8, 'co_occurrence'))} | n.r. | n.r. |")
need("Fig 8 caption", f"UMAP ({fx(sp(H8, 'umap')[0])}) and Geary's C ({fx(sp(H8, 'spatial_autocorr_geary')[0])}); Moran's I reached {fx(sp(H8, 'spatial_autocorr_moran')[0])}")
need("Fig 8 caption CPU steps", f"(open circles; {fx(sp(H8, 'spatial_neighbors')[0])} and {fx(sp(H8, 'nhood_enrichment')[0])})")
need("per-step text", f"PCA (with scaling) {fx(sp(H8, 'pca')[0])}, normalisation {fx(sp(H8, 'normalization')[0])}")
need("per-step text 2", f"accelerated {fx(sp(H8, 'expression_neighbors')[0])} and {fx(sp(H8, 'leiden')[0])}, and data loading, QC and HVG selection ran at {fx(sp(H8, 'data_loading')[0])}, {fx(sp(H8, 'qc_filtering')[0])} and {fx(sp(H8, 'hvg_selection')[0])}")
pc = lambda a_, b_: rd(100 * a_ / b_, 1)
need("HD2 shares", f"UMAP, the largest CPU cost ({pc(mean('dgx_cpu', H2, 'umap'), mean('dgx_cpu', H2, 'total'))}% of the CPU time), ran {fx(sp(H2, 'umap')[0])} faster on the GPU; the GPU pipeline time ({sec(mean('server_gpu', H2, 'total'))} s) was dominated by spatial neighbours ({pc(mean('server_gpu', H2, 'spatial_neighbors'), mean('server_gpu', H2, 'total'))}%) and data loading ({pc(mean('server_gpu', H2, 'data_loading'), mean('server_gpu', H2, 'total'))}%)")
umap_top = max(["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "expression_neighbors", "leiden", "umap", "spatial_neighbors", "spatial_autocorr_moran", "spatial_autocorr_geary"], key=lambda s: mean("dgx_cpu", H2, s))
assert umap_top == "umap"
need("v1", f"took {pc(mean('server_gpu', V1, 'ligrec'), mean('server_gpu', V1, 'total'))}% of the GPU pipeline time, and QC ({fx(sp(V1, 'qc_filtering')[0])}), Leiden ({fx(sp(V1, 'leiden')[0])}), Moran's I ({fx(sp(V1, 'spatial_autocorr_moran')[0])}) and PCA ({fx(sp(V1, 'pca')[0])}) were slower")
slow = [s for s in ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "expression_neighbors", "leiden", "umap", "spatial_autocorr_moran", "spatial_autocorr_geary", "co_occurrence"] if sp(V1, s)[2] < 1]
assert sorted(slow) == sorted(["qc_filtering", "leiden", "spatial_autocorr_moran", "pca"]), slow
need("spatial neighbours", f"spatial neighbours took {sec(mean('dgx_cpu', H8, 'spatial_neighbors'))} s and {sec(mean('dgx_cpu', H2, 'spatial_neighbors'))} s on the DGX CPU and {sec(mean('server_gpu', H8, 'spatial_neighbors'))} s and {sec(mean('server_gpu', H2, 'spatial_neighbors'))} s in the GPU pipeline on the workstation CPU, {pc(mean('server_gpu', H8, 'spatial_neighbors'), mean('server_gpu', H8, 'total'))}% (HD 8 um) and {pc(mean('server_gpu', H2, 'spatial_neighbors'), mean('server_gpu', H2, 'total'))}%")
def cv(p, g, k, d, C=conc): return span([r[g][k] for r in C[p]], d)
rhos = [r[g][k] for p in P for r in conc[p] for g, k in (("moranI", "I_spearman_rho"), ("gearyC", "C_spearman_rho"))]
rmin = str(Decimal(repr(min(rhos))).quantize(Decimal("0.0001"), rounding="ROUND_FLOOR"))
need("rho min", f"were at least {rmin} in all cases"); need("rho min concl", f"(Spearman rho at least {rmin})"); need("rho min disc", f"(Spearman rho >= {rmin})")
assert all(r["moranI"]["svg_jaccard_top50"] == 1.0 for p in P for r in conc[p])
for lab, g, k, d in (("Moran's I Spearman rho", "moranI", "I_spearman_rho", 4), ("Geary's C Spearman rho", "gearyC", "C_spearman_rho", 4),
                     ("SVG Jaccard (top 50)", "moranI", "svg_jaccard_top50", 3), ("SVG Jaccard (top 100)", "moranI", "svg_jaccard_top100", 3),
                     ("SVG Jaccard (top 200)", "moranI", "svg_jaccard_top200", 3), ("SVG Jaccard (FDR < 0.05)", "moranI", "svg_jaccard_fdr005", 3),
                     ("Cluster ARI", "clusters", "ari", 3), ("Cluster NMI", "clusters", "nmi", 3)):
    need(f"Table 10 {lab}", f"| {lab} | {cv(V1, g, k, d)} | {cv(H8, g, k, d)} | {cv(H2, g, k, d)} |")
oc = extra["own_leiden_clusters"]
def grp(l): l = sorted(set(l)); return f"{l[0]:,}" if len(l) == 1 else f"{l[0]:,}-{l[-1]:,}"
need("Table 10 N clusters", "| N clusters (CPU / GPU) | " + " | ".join(f"{grp(oc[p]['dgx_cpu'])} / {grp(oc[p]['server_gpu'])}" for p in P) + " |")
for p in P:   # Leiden groups in the concordance files agree with the extra numbers
    assert [r["clusters"]["n_clusters_cpu"] for r in conc[p]] == oc[p]["dgx_cpu"] and [r["clusters"]["n_clusters_gpu"] for r in conc[p]] == oc[p]["server_gpu"]
    assert [r["clusters"]["n_clusters_cpu"] for r in concs[p]] == oc[p]["server_cpu"]
need("Table 10 cooc", f"| Co-occurrence Spearman rho | {cv(V1, 'co_occurrence', 'spearman_rho', 4)} | {cv(H8, 'co_occurrence', 'spearman_rho', 4)} (0.14.1) | n.r. |")
need("Table 10 nhood", f"| Neighbourhood enrichment Spearman rho | {cv(V1, 'nhood_enrichment', 'spearman_rho', 4)} | {cv(H8, 'nhood_enrichment', 'spearman_rho', 4)} | n.r. |")
need("Table 10 control", f"CPU Leiden returned {oc[V1]['server_cpu'][0]:,}, {oc[H8]['server_cpu'][0]:,} and {oc[H2]['server_cpu'][0]:,} groups and the ARI was {cv(V1, 'clusters', 'ari', 3, concs)}, {cv(H8, 'clusters', 'ari', 3, concs)} and {cv(H2, 'clusters', 'ari', 3, concs)}")
need("clusters text", f"(ARI {cv(H2, 'clusters', 'ari', 3)}, NMI {cv(H2, 'clusters', 'nmi', 3)}): CPU Leiden returned {oc[H2]['dgx_cpu'][0]:,} clusters on the DGX reference and GPU Leiden {oc[H2]['server_gpu'][0]:,}")
need("granularity", f"This {rd(oc[H2]['dgx_cpu'][0] / oc[H2]['server_gpu'][0], 2)}-fold difference")
g8 = oc[H8]["server_gpu"]; w = {1: "one", 4: "four"}
need("GPU groups HD8", f"GPU Leiden returned 3 groups in {w[g8.count(3)]} repeats and 4 in {w[g8.count(4)]}")
need("SVG top100", f"the Jaccard index was {cv(V1, 'moranI', 'svg_jaccard_top100', 3)} on Visium v1 and {cv(H8, 'moranI', 'svg_jaccard_top100', 3)} on both Visium HD platforms")
assert cv(H8, 'moranI', 'svg_jaccard_top100', 3) == cv(H2, 'moranI', 'svg_jaccard_top100', 3) == cv(H8, 'moranI', 'svg_jaccard_top200', 3) == cv(H2, 'moranI', 'svg_jaccard_top200', 3)
vb = {j["memory"]["detailed"]["data_loading_vram_before_gb"] for p in P for j in runjson("server_gpu", p)}; assert len(vb) == 1
vt = {j["metadata"]["gpu_info"]["gpu_vram_total_gb"] for p in P for j in runjson("server_gpu", p)}; assert len(vt) == 1; vt = vt.pop()
need("VRAM", f"{rd(vb.pop(), 2)} GiB was reserved before data loading in every GPU run, and the peak reading was {rd(vram[V1], 2)} GiB on Visium v1, {rd(vram[H8], 2)} GiB on Visium HD 8 um and {rd(vram[H2], 2)} GiB on the HD 2 um subsample ({rd(100 * vram[H8] / vt, 0)}% of the {rd(vt, 1)} GiB")
need("RAM", f"Peak CPU RAM ranged from {rd(ram[('dgx_cpu', V1)], 2)} GiB (Visium v1) to {rd(ram[('dgx_cpu', H2)], 2)} GiB (HD 2 um subsample) on the DGX CPU reference, and reached {rd(max(ram[('server_gpu', p)] for p in P), 2)} GiB in the GPU pipeline")
nin = {j["metadata"]["n_spots_input"] for j in runjson("dgx_cpu", H2)}.pop()
need("dense", f"about {rd(nin * 2000 * 4 / 1e9, 0)} GB ({rd(nin * 2000 * 4 / 2**30, 0)} GiB) in float32")
mo = [sp(p, "spatial_autocorr_moran")[0] for p in (H8, H2)]; ge = [sp(p, "spatial_autocorr_geary")[0] for p in (H8, H2)]
moc = [sp(p, "spatial_autocorr_moran", "control_server")[0] for p in (H8, H2)]; gec = [sp(p, "spatial_autocorr_geary", "control_server")[0] for p in (H8, H2)]
need("disc autocorr", f"accelerated {span(mo, 1)}x (Moran's I) and {span(ge, 1)}x (Geary's C) on Visium HD ({span(moc, 1)}x and {span(gec, 1)}x against the workstation CPU)")
gt = [mean("server_gpu", p, s) for p in (H8, H2) for s in ("spatial_autocorr_moran", "spatial_autocorr_geary")]
ct = [mean("dgx_cpu", p, s) for p in (H8, H2) for s in ("spatial_autocorr_moran", "spatial_autocorr_geary")]
need("disc times", f"each statistic took {span(gt, 1)} s on the GPU instead of {span(ct, 0)} s on the CPU reference")
need("disc moran v1", f"on Visium v1 it was not accelerated ({fx(sp(V1, 'spatial_autocorr_moran')[0])})")
need("disc cpu steps", f"({fx(sp(H8, 'spatial_neighbors')[0])} and {fx(sp(H8, 'nhood_enrichment')[0])} at Visium HD 8 um)")
need("disc ligrec", f"Squidpy on the CPU in both pipelines, {fx(sp(V1, 'ligrec')[0])})")
need("disc summary", f"end-to-end speedups of {fx(head[0])} (Visium v1), {fx(head[1])} (Visium HD 8 um, co-occurrence excluded) and {fx(head[2])} (Visium HD 2 um subsample) against the 100-CPU DGX reference ({fx(ctl[0])}, {fx(ctl[1])} and {fx(ctl[2])} against the workstation CPU)")
need("conclusions", f"end-to-end speedups against a 100-CPU DGX node were {fx(head[0])} on Visium v1, {fx(head[1])} on Visium HD 8 um with co-occurrence excluded and {fx(head[2])} on a random 400k-bin subsample")
need("abstract", f"accelerated end-to-end analysis {rd(head[0], 1)}-fold on Visium v1, {rd(head[1], 1)}-fold on Visium HD 8 um (without co-occurrence) and {rd(head[2], 1)}-fold on Visium HD 2 um")
need("abstract cooc", f"was wrong at {49 - e41} of 49 distances")

# ---------------------------------------------------------------- G3: PDFs
try:
    import fitz
    g3 = {}
    for name in ("fig7_spatial_speedup", "fig8_spatial_perstep", "fig9_spatial_concordance"):
        doc = fitz.open(Path(a.pdf_dir) / f"{name}.pdf"); pg = doc[0]
        w_cm, h_cm = pg.rect.width / 72 * 2.54, pg.rect.height / 72 * 2.54
        sizes = [sp_["size"] for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for sp_ in l["spans"]]
        fonts = pg.get_fonts(full=True); imgs = pg.get_images(full=True)
        from PIL import Image
        im = Image.open(Path(a.pdf_dir) / f"{name}.png"); dpi = im.info.get("dpi", (0, 0))[0]
        g3[name] = {"width_cm": round(w_cm, 2), "height_cm": round(h_cm, 2), "min_pt": round(min(sizes), 2),
                    "fonts": sorted({f[3] for f in fonts}), "all_embedded": all(f[1] != "n/a" and f[2] in ("TrueType", "Type0", "CIDFontType2") for f in fonts),
                    "n_images": len(imgs), "png_dpi": round(dpi),
                    "ok": w_cm <= 12.2 + 1e-3 and h_cm <= 19.3 and min(sizes) >= 7.0 - 1e-6 and len(imgs) == 0 and round(dpi) >= 800}
    res["G3"]["pdf"] = g3
    res["G3"]["total_height_cm"] = round(sum(v["height_cm"] for v in g3.values()), 2)
except ImportError as e:
    res["G3"]["pdf"] = {"error": str(e)}
st = json.load(open(a.styles))
cpu_gpu = {s["name"]: s for s in st["fig7_spatial_speedup"]["series"]}
gf = Path("scripts/generate_figures.py").read_text()
res["G3"]["colours"] = {"cpu": cpu_gpu["CPU"]["color"], "gpu": cpu_gpu["GPU"]["color"],
                        "ok": f'"cpu": "{cpu_gpu["CPU"]["color"]}"' in gf and f'"gpu1": "{cpu_gpu["GPU"]["color"]}"' in gf and cpu_gpu["GPU"]["hatch"] and not cpu_gpu["CPU"]["hatch"]}
pts = st["fig8_spatial_perstep"]["points"]; kinds = {(p_["marker"], p_["fill"]) for p_ in pts}
by_series = {}
for p_ in pts: by_series.setdefault(p_["series"], set()).add((p_["marker"], p_["fill"]))
res["G3"]["fig8_series_distinct"] = all(len(v_) == 1 for v_ in by_series.values()) and len({next(iter(v_)) for v_ in by_series.values()}) == len(by_series)
pl = st["fig9_spatial_concordance"]["platforms"]
res["G3"]["fig9_platforms_distinct"] = len({(v_["marker"], v_["fill"]) for v_ in pl.values()}) == 3 and all(v_["color"] not in (cpu_gpu["CPU"]["color"], cpu_gpu["GPU"]["color"]) for v_ in pl.values())

# ---------------------------------------------------------------- G4: text integrity
spatial_part = ms[ms.find("## Spatial transcriptomics", ms.find("# Results")):]
bad = ["51.6x", "3,272x", "3,573", "41.5x", "162-170x", "162-163x", "257x", "176x", "4.75x", "0.080", "0.667",
       "12.9 GB", "22.6 GB", "10.8 GB", "repeats 2-5", "leidenalg", "exceeding 0.9995", "exceeded 0.9995"]
# "repeats 2-5" is legitimate in scRNA-seq sentences (plan, convention 10); it is searched in the spatial text only
meth = ms[ms.find("## Spatial transcriptomics"):ms.find("## Hardware and software environment")]
spatial_text = meth + spatial_part[:spatial_part.find("# Discussion")] + "\n".join(
    l for l in ms[ms.find("# Discussion"):].split("\n") if "spatial" in l.lower() or "Visium" in l)
found = {b: (spatial_text if b == "repeats 2-5" else ms).count(b) for b in bad}
found = {b: n for b, n in found.items() if n}
res["G4"]["superseded_found"] = found
res["G4"]["2559_contexts"] = [ms[max(0, m.start() - 80): m.end() + 40] for m in re.finditer(r"2,559", ms)]
res["G4"]["2559_only_control"] = all(("workstation" in c) for c in res["G4"]["2559_contexts"])
res["G4"]["dashes"] = len(re.findall("[\u2013\u2014]", ms))
led = [r["id"] for r in csv.DictReader(open("manuscript/revisione_n2/piano/ledger.csv", encoding="utf-8")) if r["step"] == "S5"]
dia = [r["id"] for r in csv.DictReader(open("manuscript/revisione_n2/piano/IMPL_diario.csv", encoding="utf-8"))]
res["G4"]["diary_rows"] = {"ledger_S5": len(led), "missing": [i for i in led if dia.count(i) != 1]}
res["G4"]["ok"] = not found and res["G4"]["2559_only_control"] and res["G4"]["dashes"] == 0 and not res["G4"]["diary_rows"]["missing"]

summary = {"G2_values": f"{sum(r['ok'] for r in res['G2_values'])}/{len(res['G2_values'])}",
           "G2_text": f"{sum(r['ok'] for r in res['G2_text'])}/{len(res['G2_text'])}",
           "G3_pdf_ok": all(v.get("ok") for v in res["G3"]["pdf"].values()) if "error" not in res["G3"]["pdf"] else None,
           "G3_colours": res["G3"]["colours"]["ok"], "G3_fig8": res["G3"]["fig8_series_distinct"], "G3_fig9": res["G3"]["fig9_platforms_distinct"],
           "G3_total_height_cm": res["G3"].get("total_height_cm"), "G4_ok": res["G4"]["ok"], "G4_superseded": found}
res["summary"] = summary
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
json.dump(res, open(a.out, "w"), indent=1, ensure_ascii=False, default=str)
print(json.dumps(summary, ensure_ascii=False))
fails = [r for r in res["G2_values"] + res["G2_text"] if not r["ok"]]
for f_ in fails[:20]: print("FAIL", f_.get("check") or (f_["figure"], f_["series"], f_["x"], f_["stat"]), f_.get("string", "")[:200])
