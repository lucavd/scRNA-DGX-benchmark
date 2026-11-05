#!/usr/bin/env python3
"""Checks of step S4 (scRNA figures at LNCS print size).

Gate G2: recomputes every value of figure_values.csv from the raw JSON with
the standard library only (json, statistics), independently of
scripts/generate_figures.py, and re-reads the numbers written in the new
captions of Figures 1, 2, 5, 6 and Table 4; compares the regenerated
summary_table.csv with the tracked one.
Gate G3: PDF size, smallest text, embedded fonts, raster images (PyMuPDF);
PNG resolution; byte-identical PDFs over two runs (--rerun-dir).
Gate G4: greyscale distinguishability from figure_styles.json.
Gate G5 (with --manuscript): integrity of the manuscript after the caption
edits.
Predictions P1-P5: bootstrap over repeats (B = 2000, seed 20261104).

Usage (from the repo root, figure venv):
  python -B tools/s4_check.py --results-dir results --fig-dir figures \
      --values-dir results_v2/S4 --rerun-dir /tmp/lnbi_s4_rerun \
      --old-fig-dir <dir with the pre-S4 PNGs> --manuscript manuscript/full_paper_LNBI.md \
      --out results_v2/S4/s4_check.json
"""
import argparse, csv, hashlib, json, os, re, statistics, subprocess, sys
from itertools import combinations

ap = argparse.ArgumentParser()
ap.add_argument("--results-dir", default="results")
ap.add_argument("--fig-dir", default="figures")
ap.add_argument("--values-dir", default="results_v2/S4")
ap.add_argument("--rerun-dir", default=None)
ap.add_argument("--old-fig-dir", default=None)
ap.add_argument("--tracked-summary", default=None)
ap.add_argument("--manuscript", default=None)
ap.add_argument("--diary", default="manuscript/revisione_n2/piano/IMPL_diario.csv")
ap.add_argument("--ledger", default="manuscript/revisione_n2/piano/ledger.csv")
ap.add_argument("--out", required=True)
a = ap.parse_args()

FIGS = ["fig1_speedup_heatmap", "fig5_timing_breakdown", "fig3_concordance", "fig4_memory_profile"]
STEPS = ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "neighbors",
         "leiden_0.5", "leiden_1.0", "leiden_1.5", "umap", "de_testing"]
LABEL2STEP = {"Data loading": "data_loading", "QC and filtering": "qc_filtering",
              "Normalisation": "normalization", "HVG selection": "hvg_selection", "PCA": "pca",
              "Neighbour graph": "neighbors", "Leiden r = 0.5": "leiden_0.5",
              "Leiden r = 1.0": "leiden_1.0", "Leiden r = 1.5": "leiden_1.5", "UMAP": "umap",
              "DE testing": "de_testing"}
PAT = re.compile(r"^(cpu|gpu[0-9]*)_([0-9]+)_r([0-9]+)_results\.json$")
out = {"gates": {}, "predictions": {}, "details": {}}


def md5(p):
    h = hashlib.md5(); h.update(open(p, "rb").read()); return h.hexdigest()


# ---------------------------------------------------------------- raw data
raw = {}   # (config, n) -> list of dicts ordered by repeat
for f in sorted(os.listdir(a.results_dir)):
    m = PAT.match(f)
    if not m:
        continue
    cfg = "gpu1" if m.group(1) == "gpu" else m.group(1)
    d = json.load(open(os.path.join(a.results_dir, f)))
    raw.setdefault((cfg, int(m.group(2))), []).append((int(m.group(3)), d))
for k in raw:
    raw[k] = [d for _, d in sorted(raw[k], key=lambda t: t[0])]
conc = json.load(open(os.path.join(a.results_dir, "concordance_10000_r1.json")))
n_per_cfg = sorted({len(v) for v in raw.values()})


def steps_mean(cfg, n, s):
    return statistics.mean(d["timings"][s] for d in raw[(cfg, n)])


def mem(cfg, n, key):
    return [d["memory"][key] for d in raw[(cfg, n)]]


# ---------------------------------------------------------------- G2 values
expected = {}
for n in (10000, 50000, 100000):
    for s in STEPS:
        expected[("fig1_speedup_heatmap", "main", s, str(n), "speedup_ratio_of_means")] = \
            steps_mean("cpu", n, s) / steps_mean("gpu1", n, s)
        for cfg in ("cpu", "gpu1"):
            expected[("fig5_timing_breakdown", cfg, s, str(n), "mean_s")] = steps_mean(cfg, n, s)
    for cfg in ("cpu", "gpu1"):
        expected[("fig5_timing_breakdown", cfg, "stack_total", str(n), "sum_of_step_means_s")] = \
            sum(steps_mean(cfg, n, s) for s in STEPS)
cl = conc["cluster_concordance"]
for r in ("leiden_0.5", "leiden_1.0", "leiden_1.5"):
    expected[("fig3_concordance", "clustering", "ARI", r, "value")] = cl[r]["ari"]
    expected[("fig3_concordance", "clustering", "NMI", r, "value")] = cl[r]["nmi"]
expected[("fig3_concordance", "other", "HVG Jaccard", "", "value")] = conc["hvg_concordance"]["jaccard"]
expected[("fig3_concordance", "other", "PCA |\u03c1|", "", "value")] = conc["pca_concordance"]["mean_abs_spearman_rho"]
expected[("fig3_concordance", "other", "kNN Jaccard", "", "value")] = conc["knn_concordance"]["mean_jaccard"]
expected[("fig3_concordance", "other", "DE logFC \u03c1", "", "value")] = conc["de_concordance"]["mean_spearman_rho"]
expected[("fig3_concordance", "other", "kNN Jaccard ceiling", "", "value")] = 15 / 16
for (cfg, n), reps in raw.items():
    for panel, key in (("ram", "peak_ram_gb"), ("vram", "peak_vram_gb")):
        if panel == "vram" and cfg == "cpu":
            continue
        v = mem(cfg, n, key)
        expected[("fig4_memory_profile", panel, cfg, str(n), "mean_gib")] = statistics.mean(v)
        expected[("fig4_memory_profile", panel, cfg, str(n), "sd_gib")] = statistics.stdev(v)

vals = list(csv.DictReader(open(os.path.join(a.values_dir, "figure_values.csv"))))
mism, seen = [], set()
for row in vals:
    series = row["series"]
    if row["figure"] != "fig3_concordance" and series in LABEL2STEP:
        series = LABEL2STEP[series]
    key = (row["figure"], row["panel"], series, row["x"], row["stat"])
    seen.add(key)
    e = expected.get(key)
    v = float(row["value"])
    if e is None or abs(v - e) > 1e-9 * max(1.0, abs(e)):
        mism.append({"key": key, "figure_value": v, "recomputed": e})
missing = [k for k in expected if k not in seen]
out["details"]["values"] = {"n_values": len(vals), "n_expected": len(expected),
                            "mismatches": mism[:20], "n_mismatches": len(mism),
                            "missing_from_figures": [list(k) for k in missing]}

# caption numbers (only when the manuscript has the new captions)
cap = {}
cap["fig1_max_normalisation"] = max(expected[("fig1_speedup_heatmap", "main", "normalization", str(n), "speedup_ratio_of_means")] for n in (10000, 50000, 100000))
cap["fig1_max_any"] = max(v for k, v in expected.items() if k[0] == "fig1_speedup_heatmap")
dl = [expected[("fig1_speedup_heatmap", "main", "data_loading", str(n), "speedup_ratio_of_means")] for n in (10000, 50000, 100000)]
cap["fig1_data_loading_min_max"] = [min(dl), max(dl)]
cap["cpu_n_cpus"] = sorted({d["metadata"]["n_cpus"] for (c_, n), r in raw.items() if c_ == "cpu" for d in r})
cap["gpu1_names"] = sorted({d["metadata"]["gpu_info"]["gpu_name"] for (c_, n), r in raw.items() if c_ == "gpu1" for d in r})
cap["fig2_max_gpu_step_mean"] = max(steps_mean("gpu1", n, s) for n in (10000, 50000, 100000) for s in STEPS)
rank = {}
for n in (10000, 50000, 100000):
    order = sorted(STEPS, key=lambda s: -steps_mean("cpu", n, s))
    rank[n] = order[:3]
cap["fig2_cpu_top3"] = rank
cap["fig5_values"] = {k[2]: v for k, v in expected.items() if k[0] == "fig3_concordance"}
cap["fig5_de_pairs"] = conc["de_concordance"]["n_pairs_compared"]
cap["repeats_per_config"] = n_per_cfg
# VRAM first repeat vs later repeats
vr = {}
for (cfg, n), reps in sorted(raw.items()):
    if cfg == "cpu":
        continue
    v = mem(cfg, n, "peak_vram_gb")
    vr[f"{cfg}_{n}"] = {"r1": v[0], "r2_5_min": min(v[1:]), "r2_5_max": max(v[1:]),
                        "r1_below_all_later": v[0] < min(v[1:])}
cap["vram_r1_vs_later"] = vr
out["details"]["caption_values"] = cap

caption_checks = []
if a.manuscript:
    ms = open(a.manuscript, encoding="utf-8").read()
    def capline(tag):
        ls = [l for l in ms.splitlines() if l.startswith(f"![**{tag}.**") or l.startswith(f": **{tag}.**")]
        return ls[0] if len(ls) == 1 else None
    f1, f2, f5, f6, t4 = (capline(t) for t in ("Figure 1", "Figure 2", "Figure 5", "Figure 6", "Table 4"))
    def chk(name, ok, detail):
        caption_checks.append({"check": name, "ok": bool(ok), "detail": detail})
    chk("Fig1 '329x'", f1 and "329x" in f1 and round(cap["fig1_max_normalisation"]) == 329 and abs(cap["fig1_max_any"] - cap["fig1_max_normalisation"]) < 1e-12, round(cap["fig1_max_normalisation"], 3))
    chk("Fig1 '0.76-0.85x'", f1 and "0.76-0.85x" in f1 and f"{min(dl):.2f}" == "0.76" and f"{max(dl):.2f}" == "0.85", [round(x, 4) for x in dl])
    chk("Fig1 '100 logical CPUs'", f1 and "100 logical CPUs" in f1 and cap["cpu_n_cpus"] == [100], cap["cpu_n_cpus"])
    chk("Fig1 '1xH100 80 GB'", f1 and "1xH100 80 GB" in f1 and all("H100 80GB" in g for g in cap["gpu1_names"]), cap["gpu1_names"])
    chk("Fig1 'first repeat included'", f1 and "five repeats (first repeat included)" in f1 and n_per_cfg == [5], n_per_cfg)
    top100 = max(STEPS, key=lambda s: steps_mean("gpu1", 100000, s))
    chk("Fig2 'longest step, DE testing at 100k cells, takes 6.4 s'", f2 and "the longest step, DE testing at 100k cells, takes 6.4 s on average" in f2
        and top100 == "de_testing" and abs(cap["fig2_max_gpu_step_mean"] - steps_mean("gpu1", 100000, "de_testing")) < 1e-12
        and f"{cap['fig2_max_gpu_step_mean']:.1f}" == "6.4" and "less than 7 s" not in f2, round(cap["fig2_max_gpu_step_mean"], 4))
    chk("Fig2 'DE testing and UMAP dominate'", f2 and "DE testing and UMAP dominate" in f2 and all(r[:2] == ["de_testing", "umap"] for r in rank.values()), rank)
    chk("Fig2 'first repeat included'", f2 and "five repeats (first repeat included)" in f2, "")
    chk("Fig2 'one Numba thread'", f2 and "one Numba thread" in f2, "decision D-16")
    v5 = cap["fig5_values"]
    for lab, txt in (("HVG Jaccard", "HVG Jaccard (1.000)"), ("PCA |\u03c1|", "PCA Spearman |rho| (1.000)"),
                     ("kNN Jaccard", "kNN Jaccard (0.930)"), ("DE logFC \u03c1", "(0.946")):
        num = re.search(r"\(([0-9.]+)", txt).group(1)
        chk(f"Fig5 {txt}", f5 and txt in f5 and f"{v5[lab]:.3f}" == num, round(v5[lab], 5))
    chk("Fig5 '40 matched cluster pairs'", f5 and "40 matched cluster pairs" in f5 and cap["fig5_de_pairs"] == 40, cap["fig5_de_pairs"])
    chk("Fig5 '0.9375'", f5 and "bounded at 0.9375" in f5, 15 / 16)
    chk("Fig6 'first repeat included'", f6 and "five repeats (first repeat included)" in f6, "")
    chk("Fig6 'aggregate GPU VRAM'", f6 and "aggregate GPU VRAM summed over the allocated devices" in f6 and "per-device" not in f6 and "80 GB VRAM limit" not in f6, "")
    chk("Fig6 'roughly linearly'", f6 and "roughly linearly" in f6 and "super-linearly" not in f6, "")
    multi = {k: v for k, v in vr.items() if not k.startswith("gpu1_")}
    chk("Fig6 'in the multi-GPU runs VRAM grew'", f6 and "in the multi-GPU runs VRAM grew from the first to later repeats" in f6
        and all(v["r1_below_all_later"] for v in multi.values()) and len(multi) == 15, f"{sum(v['r1_below_all_later'] for v in multi.values())}/{len(multi)}")
    chk("Table4 'first repeat included'", t4 and "five repeats (first repeat included)" in t4, "")
    out["details"]["caption_checks"] = caption_checks

# summary table vs tracked
sum_diff = None
if a.tracked_summary:
    new = list(csv.DictReader(open(os.path.join(a.fig_dir, "summary_table.csv"))))
    old = list(csv.DictReader(open(a.tracked_summary)))
    keyf = lambda r: (r["pipeline"], r["n_cells"], r["n_gpus"])
    on = {keyf(r): r for r in old}; nn = {keyf(r): r for r in new}
    sum_diff = {"only_old": [list(k) for k in on if k not in nn], "only_new": [list(k) for k in nn if k not in on],
                "changed": [{"key": list(k), "old": on[k], "new": nn[k]} for k in nn if k in on and on[k] != nn[k]]}
    out["details"]["summary_table_vs_tracked"] = sum_diff

g2_ok = (len(mism) == 0 and not missing and (not caption_checks or all(c["ok"] for c in caption_checks)))
out["gates"]["G2"] = {"ok": g2_ok, "values": f"{len(vals)} values, {len(mism)} mismatches, {len(missing)} missing",
                      "captions": f"{sum(c['ok'] for c in caption_checks)}/{len(caption_checks)} caption checks"}

# ---------------------------------------------------------------- G3 print spec
import fitz  # PyMuPDF
from PIL import Image
spec = {}
for f in FIGS:
    p = os.path.join(a.fig_dir, f + ".pdf")
    doc = fitz.open(p); pg = doc[0]
    w_cm, h_cm = pg.rect.width / 72 * 2.54, pg.rect.height / 72 * 2.54
    sizes = [s["size"] for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"] if s["text"].strip()]
    fonts = pg.get_fonts()
    emb = all(ft[1] not in ("n/a", "") for ft in fonts)
    imgs = len(pg.get_images())
    dpi = Image.open(os.path.join(a.fig_dir, f + ".png")).info.get("dpi", (0, 0))
    spec[f] = {"width_cm": round(w_cm, 3), "height_cm": round(h_cm, 3), "min_text_pt": round(min(sizes), 3),
               "n_text_spans": len(sizes), "fonts": [ft[3] + ":" + ft[1] for ft in fonts], "fonts_embedded": emb,
               "raster_images": imgs, "png_dpi": [round(x) for x in dpi], "pdf_md5": md5(p)}
    if a.rerun_dir:
        spec[f]["rerun_pdf_md5"] = md5(os.path.join(a.rerun_dir, f + ".pdf"))
        spec[f]["rerun_png_md5_equal"] = md5(os.path.join(a.rerun_dir, f + ".png")) == md5(os.path.join(a.fig_dir, f + ".png"))
g3_ok = all(s["width_cm"] <= 12.2 + 1e-6 and s["height_cm"] <= 19.3 and s["min_text_pt"] >= 7 - 1e-6 and s["fonts_embedded"]
            and s["raster_images"] == 0 and min(s["png_dpi"]) >= 799 and s.get("rerun_pdf_md5", s["pdf_md5"]) == s["pdf_md5"]
            for s in spec.values()) and bool(a.rerun_dir)
out["details"]["print_spec"] = spec
out["gates"]["G3"] = {"ok": g3_ok}

# ---------------------------------------------------------------- G4 greyscale
st = json.load(open(os.path.join(a.values_dir, "figure_styles.json")))
g4 = {}
cells = st["fig1_speedup_heatmap"]["heatmap_cells"]
lo_c = min(cells, key=lambda c: c["value"]); hi_c = max(cells, key=lambda c: c["value"])
g4["fig1_min_contrast"] = min(c["contrast"] for c in cells)
g4["fig1_extreme_luminance_diff"] = abs(lo_c["luminance"] - hi_c["luminance"])
stk = sorted(st["fig5_timing_breakdown"]["stacked"], key=lambda r: r["order"])
lum = [r["luminance"] for r in stk]
g4["fig2_luminance_by_order"] = [round(x, 1) for x in lum]
g4["fig2_min_adjacent_diff"] = min(b - x for x, b in zip(lum, lum[1:]))
clu = st["fig3_concordance"]["series"]["clustering"]
g4["fig5_clustering_pairs_distinct"] = all((p["marker"], p["fill"]) != (q["marker"], q["fill"]) for p, q in combinations(clu, 2))
g4["fig5_other_distinct_positions"] = len({o["x_position"] for o in st["fig3_concordance"]["series"]["other"]}) == len(st["fig3_concordance"]["series"]["other"])
ser = st["fig4_memory_profile"]["series"]
g4["fig6_pairs_distinct"] = all(p["marker"] != q["marker"] or p["linestyle"] != q["linestyle"] for p, q in combinations(ser, 2))
g4_ok = (g4["fig1_min_contrast"] >= 4.5 and g4["fig1_extreme_luminance_diff"] >= 80 and g4["fig2_min_adjacent_diff"] >= 8
         and g4["fig5_clustering_pairs_distinct"] and g4["fig5_other_distinct_positions"] and g4["fig6_pairs_distinct"])
out["details"]["greyscale"] = g4
out["gates"]["G4"] = {"ok": g4_ok}

# ---------------------------------------------------------------- G5 manuscript
if a.manuscript:
    g5 = {}
    g5["forbidden_left"] = [t for t in ("fig2_scaling_plot", "fig6_multigpu_breakdown", "Fig. 3", "Fig. 4", "Figure 3", "Figure 4") if t in ms]
    g5["dashes"] = sum(ms.count(ch) for ch in ("\u2013", "\u2014"))
    pd_ = subprocess.run(["pandoc", a.manuscript, "-o", "/tmp/lnbi_s4_pandoc.docx"], capture_output=True, text=True)
    g5["pandoc_rc"] = pd_.returncode; g5["pandoc_stderr"] = pd_.stderr[-500:]
    s4ids = [r["id"] for r in csv.DictReader(open(a.ledger, encoding="utf-8")) if r["step"] == "S4"]
    diary = [r["id"] for r in csv.DictReader(open(a.diary, encoding="utf-8"))]
    g5["s4_entries"] = len(s4ids)
    g5["diary_rows_per_entry"] = {i: diary.count(i) for i in s4ids}
    anchors_path = os.path.join(a.values_dir, "caption_edits_applied.json")
    g5["anchors"] = json.load(open(anchors_path)) if os.path.exists(anchors_path) else None
    okf = subprocess.run([sys.executable, "-B", "tools/okf.py", "check", "--bundle", "docs"], capture_output=True, text=True)
    g5["okf_rc"] = okf.returncode; g5["okf_tail"] = okf.stdout[-300:] + okf.stderr[-300:]
    g5_ok = (not g5["forbidden_left"] and g5["dashes"] == 0 and g5["pandoc_rc"] == 0
             and all(v == 1 for v in g5["diary_rows_per_entry"].values()) and g5["anchors"] is not None
             and all(e["count_before"] == 1 for e in g5["anchors"]["edits"]) and g5["okf_rc"] == 0)
    out["details"]["manuscript"] = g5
    out["gates"]["G5"] = {"ok": g5_ok}

# ---------------------------------------------------------------- predictions
import random
B, SEED = 2000, 20261104
rng = random.Random(SEED)


def boot_means(cfg, n, fn):
    reps = raw[(cfg, n)]
    return [fn([reps[rng.randrange(5)] for _ in range(5)]) for _ in range(B)]


def q(xs, p):
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


p1 = {}
for n in (10000, 50000, 100000):
    second_umap = 0; first_de = 0; shares = []
    reps = raw[("cpu", n)]
    for _ in range(B):
        smp = [reps[rng.randrange(5)] for _ in range(5)]
        m = {s: statistics.mean(d["timings"][s] for d in smp) for s in STEPS}
        o = sorted(STEPS, key=lambda s: -m[s])
        second_umap += o[1] == "umap"; first_de += o[0] == "de_testing"
        shares.append(100 * m["de_testing"] / sum(m.values()))
    m = {s: steps_mean("cpu", n, s) for s in STEPS}
    p1[n] = {"order_top3": sorted(STEPS, key=lambda s: -m[s])[:3], "frac_umap_second": second_umap / B,
             "frac_de_first": first_de / B, "de_share_pct": 100 * m["de_testing"] / sum(m.values()),
             "de_share_ci95": [q(shares, .025), q(shares, .975)],
             "umap_share_pct": 100 * m["umap"] / sum(m.values())}
ok_rank = all(p1[n]["frac_umap_second"] >= 0.95 and p1[n]["frac_de_first"] >= 0.95 for n in p1)
share_ok = 83.9 <= p1[100000]["de_share_pct"] <= 89.9
p1_out = "confermata" if ok_rank and share_ok else ("smentita" if any(p1[n]["frac_umap_second"] < 0.05 for n in p1) else "indeterminata")
out["predictions"]["P1"] = {"outcome": p1_out, "by_size": p1}

p2 = {}
for n in (10000, 50000, 100000):
    m = {s: steps_mean("gpu1", n, s) for s in STEPS}
    top = max(m, key=m.get)
    sd = statistics.stdev(d["timings"][top] for d in raw[("gpu1", n)])
    p2[n] = {"step": top, "mean_s": m[top], "sd_s": sd, "mean_plus_2sd": m[top] + 2 * sd,
             "all_steps_mean_plus_2sd_max": max(m[s] + 2 * statistics.stdev(d["timings"][s] for d in raw[("gpu1", n)]) for s in STEPS)}
conf = all(p2[n]["all_steps_mean_plus_2sd_max"] < 7 for n in p2)
ref = any(p2[n]["mean_s"] - 2 * p2[n]["sd_s"] > 7 for n in p2)
out["predictions"]["P2"] = {"outcome": "confermata" if conf else ("smentita" if ref else "indeterminata"), "by_size": p2}

p3 = {}
for n in (10000, 50000, 100000):
    rc, rg = raw[("cpu", n)], raw[("gpu1", n)]
    bs = []
    for _ in range(B):
        sc = [rc[rng.randrange(5)] for _ in range(5)]; sg = [rg[rng.randrange(5)] for _ in range(5)]
        bs.append(statistics.mean(d["timings"]["data_loading"] for d in sc) / statistics.mean(d["timings"]["data_loading"] for d in sg))
    est = steps_mean("cpu", n, "data_loading") / steps_mean("gpu1", n, "data_loading")
    p3[n] = {"speedup": est, "ci95": [q(bs, .025), q(bs, .975)]}
conf = all(p3[n]["ci95"][1] < 1 for n in p3)
ref = any(p3[n]["ci95"][0] >= 1 for n in p3)
out["predictions"]["P3"] = {"outcome": "confermata" if conf else ("smentita" if ref else "indeterminata"), "by_size": p3}

p4 = {n: {"mean_gib": statistics.mean(mem("gpu1", n, "peak_vram_gb")), "sd_gib": statistics.stdev(mem("gpu1", n, "peak_vram_gb"))}
      for n in (10000, 50000, 100000)}
conf = all(abs(p4[n]["mean_gib"] - 40.7) <= 0.05 * 40.7 for n in p4)
out["predictions"]["P4"] = {"outcome": "confermata" if conf else "smentita", "by_size": p4}

if a.old_fig_dir:
    old_h = {}
    for f in FIGS:
        w, h = Image.open(os.path.join(a.old_fig_dir, f + ".png")).size
        old_h[f] = 12.2 * h / w
    new_h = {f: spec[f]["height_cm"] for f in FIGS}
    red = 100 * (1 - sum(new_h.values()) / sum(old_h.values()))
    out["predictions"]["P5"] = {"outcome": "confermata" if 20 <= red <= 40 else ("smentita" if red < 20 else "fuori intervallo (riduzione oltre il 40%)"),
                                "old_height_cm_at_12.2cm": {k: round(v, 2) for k, v in old_h.items()},
                                "new_height_cm": new_h, "old_total_cm": round(sum(old_h.values()), 2),
                                "new_total_cm": round(sum(new_h.values()), 2), "reduction_pct": round(red, 1)}

out["inputs"] = {"n_result_files": sum(len(v) for v in raw.values()), "concordance_md5": md5(os.path.join(a.results_dir, "concordance_10000_r1.json")),
                 "figure_values_md5": md5(os.path.join(a.values_dir, "figure_values.csv"))}
json.dump(out, open(a.out, "w"), indent=1, default=str)
print(json.dumps({"gates": out["gates"], "predictions": {k: v["outcome"] for k, v in out["predictions"].items()}}, indent=1))
