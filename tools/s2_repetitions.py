#!/usr/bin/env python3
"""S2 analyses on the scRNA timing JSONs (read only).

P1: thread check. For every CPU run (5 repeats in one process) and timed step
    (excluding data_loading and total) with mean(r2-5) >= 1 s:
    R = mean(r2-5) / r1, interval R +/- 2 SD(r2-5) / r1, relevance R <= 1.20.
P3: convention. End-to-end speedup with repeats 1-5 divided by speedup with
    repeats 2-5, per GPU configuration and size. Bootstrap percentile 95%
    resampling repeats 2-5 of each run with r1 fixed, B = 2000, seed 20261104.
P3b: same ratio for every step (information).
Usage: python -B tools/s2_repetitions.py --results results --out results_v2/S2
Needs numpy.
"""
import argparse, csv, glob, json, os, re
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--results", default="results")
ap.add_argument("--out", default="results_v2/S2")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
T = {}
for f in sorted(glob.glob(os.path.join(a.results, "*_results.json"))):
    m = re.match(r".*/(cpu|gpu\d?)_(\d+)_r(\d)_results\.json$", f)
    if not m: continue
    d = json.load(open(f))
    for k, v in d["timings"].items():
        T.setdefault((m.group(1), int(m.group(2)), k), {})[int(m.group(3))] = float(v)
def reps(key): return np.array([T[key][r] for r in range(1, 6)])
def wcsv(name, rows):
    with open(os.path.join(a.out, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
p1 = []
for (cfg, n, step) in sorted(T):
    if cfg != "cpu" or step in ("data_loading", "total"): continue
    x = reps((cfg, n, step)); r1, w = x[0], x[1:]
    R = w.mean() / r1; half = 2 * w.std(ddof=1) / r1
    if w.mean() < 1: continue
    lo, hi = R - half, R + half
    es = "confermata" if hi <= 1.2 else ("smentita" if lo > 1.2 else "indeterminata")
    p1.append({"n": n, "step": step, "r1_s": round(r1, 3), "mean_r2_5_s": round(w.mean(), 3), "R": round(R, 4),
               "lo": round(lo, 4), "hi": round(hi, 4), "noise_2sd_over_r1": round(half, 4),
               "max_rep_over_r1": round(w.max() / r1, 4), "esito": es,
               "per_rep_s": ";".join(f"{v:.2f}" for v in x)})
wcsv("S2_P1_threads.csv", p1)
rng = np.random.default_rng(20261104); B = 2000
p3 = []
for n in (10000, 50000, 100000, 500000, 1300000):
    for g in ("gpu", "gpu2", "gpu4", "gpu8"):
        if (g, n, "total") not in T: continue
        c, q = reps(("cpu", n, "total")), reps((g, n, "total"))
        A = c.mean() / q.mean(); Bv = c[1:].mean() / q[1:].mean()
        out = []
        for _ in range(B):
            cw = rng.choice(c[1:], 4, replace=True); gw = rng.choice(q[1:], 4, replace=True)
            out.append(((c[0] + cw.sum()) / (q[0] + gw.sum())) / (cw.mean() / gw.mean()))
        lo, hi = np.percentile(out, [2.5, 97.5])
        es = "informazione" if n < 100000 else ("confermata" if lo >= 0.9 and hi <= 1.1 else ("smentita" if hi < 0.9 or lo > 1.1 else "indeterminata"))
        p3.append({"n": n, "gpu": g, "speedup_r1_5": round(A, 3), "speedup_r2_5": round(Bv, 3), "ratio": round(A / Bv, 4),
                   "lo": round(lo, 4), "hi": round(hi, 4), "esito": es})
wcsv("S2_P3_convenzione.csv", p3)
p3b = []
for (cfg, n, step) in sorted(T):
    if cfg == "cpu" or step == "data_loading" or ("cpu", n, step) not in T: continue
    c, q = reps(("cpu", n, step)), reps((cfg, n, step))
    A = c.mean() / q.mean(); Bv = c[1:].mean() / q[1:].mean()
    p3b.append({"cfg": cfg, "n": n, "step": step, "speedup_r1_5": round(A, 3), "speedup_r2_5": round(Bv, 3),
                "ratio": round(A / Bv, 4), "differ_over_10pct": bool(A / Bv < 0.9 or A / Bv > 1.1)})
wcsv("S2_P3b_per_step.csv", p3b)
s = {"P1": {"n": len(p1), "esiti": {e: sum(1 for r in p1 if r["esito"] == e) for e in ("confermata", "indeterminata", "smentita")},
            "R_max": max(r["R"] for r in p1)},
     "P3": {"n_judged": sum(1 for r in p3 if r["esito"] != "informazione"),
            "esiti": {e: sum(1 for r in p3 if r["esito"] == e) for e in ("confermata", "indeterminata", "smentita")},
            "ratio_range_ge_100k": [min(r["ratio"] for r in p3 if r["n"] >= 100000), max(r["ratio"] for r in p3 if r["n"] >= 100000)],
            "ratio_range_lt_100k": [min(r["ratio"] for r in p3 if r["n"] < 100000), max(r["ratio"] for r in p3 if r["n"] < 100000)],
            "speedup_8gpu_1.3M": [r for r in p3 if r["n"] == 1300000 and r["gpu"] == "gpu8"][0]},
     "P3b": {"n": len(p3b), "differ_over_10pct": sum(r["differ_over_10pct"] for r in p3b)}}
json.dump(s, open(os.path.join(a.out, "S2_summary.json"), "w"), indent=1)
print(json.dumps(s))
