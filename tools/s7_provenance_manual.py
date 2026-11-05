#!/usr/bin/env python3
"""S7: numbers of the final text that tools/s7_provenance.py does not find in any
receipt or recomputed value file, recomputed here from the raw result files.

Writes results_v2/S7/provenance_manual.csv (doc, token, context, file, md5,
computation, value, ok); tools/s7_provenance.py reads it.
Usage: python3 -B tools/s7_provenance_manual.py
"""
import csv, hashlib, json, os, statistics

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
S1 = "SPATIAL/results_v2"


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def step(run, platform, name):
    for r in csv.DictReader(open(os.path.join(S1, "s1_step_stats.csv"), encoding="utf-8")):
        if (r["run"], r["platform"], r["step"]) == (run, platform, name):
            return float(r["mean_1_5"])
    raise KeyError((run, platform, name))


rows = []
# 1. CPU RAM on the Visium HD 2 um subsample (Table 2 and supplement): mean of the per-repeat peaks, DGX CPU
fs = [os.path.join(S1, "dgx_cpu", "spatial_cpu_visium_hd_square_002um_r%d_results.json" % k) for k in range(1, 6)]
v = statistics.mean(json.load(open(f))["memory"]["peak_ram_gb"] for f in fs)
for doc, ctx in (("chapter", "| 7.95 | 22.73 |"), ("supplement", "to 7.95 GiB (HD 2 um subsample)")):
    rows.append([doc, "7.95", ctx, ";".join(fs), ";".join(md5(f) for f in fs),
                 "mean of memory.peak_ram_gb over repeats 1-5, 2 decimals", "%.2f" % v, "%.2f" % v == "7.95"])
# 2. Table S4: CPU RAM at 10.3M cells (KMeans)
f = "results/maxpower_10309410_8gpu_results.json"
v = json.load(open(f))["memory"]["peak_ram_gb"]
rows.append(["supplement", "465", "| 10.3M | 91 | 465 |", f, md5(f), "memory.peak_ram_gb, 0 decimals", "%.0f" % v, "%.0f" % v == "465"])
# 3. Visium HD 2 um: UMAP share of the DGX CPU time
p = "visium_hd_square_002um"
v = 100 * step("dgx_cpu", p, "umap") / step("dgx_cpu", p, "total")
f = os.path.join(S1, "s1_step_stats.csv")
rows.append(["supplement", "72.0", "the largest CPU cost (72.0% of the CPU time)", f, md5(f),
             "100 * mean_1_5(dgx_cpu, umap) / mean_1_5(dgx_cpu, total), 1 decimal", "%.1f" % v, "%.1f" % v == "72.0"])
# 4. Visium HD 2 um: data loading share of the GPU pipeline time
v = 100 * step("server_gpu", p, "data_loading") / step("server_gpu", p, "total")
rows.append(["supplement", "27.8", "and data loading (27.8%)", f, md5(f),
             "100 * mean_1_5(server_gpu, data_loading) / mean_1_5(server_gpu, total), 1 decimal", "%.1f" % v, "%.1f" % v == "27.8"])
# 5. ratio of Leiden cluster counts on the 2 um subsample, DGX CPU / GPU
fc = os.path.join(S1, "s1_extra_numbers.json")
cl = json.load(open(fc))["own_leiden_clusters"]["visium_hd_square_002um"]
assert len(set(cl["dgx_cpu"])) == 1 and len(set(cl["server_gpu"])) == 1, cl
v = cl["dgx_cpu"][0] / cl["server_gpu"][0]
rows.append(["supplement", "5.63", "This 5.63-fold difference", fc, md5(fc),
             "own_leiden_clusters.visium_hd_square_002um: dgx_cpu %d / server_gpu %d (same in all 5 repeats), 2 decimals"
             % (cl["dgx_cpu"][0], cl["server_gpu"][0]), "%.2f" % v, "%.2f" % v == "5.63"])
with open("results_v2/S7/provenance_manual.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["doc", "token", "context", "file", "md5", "computation", "value", "ok"])
    w.writerows(rows)
print(json.dumps(rows, ensure_ascii=False, indent=0)[:3000])
