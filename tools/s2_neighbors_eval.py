#!/usr/bin/env python3
"""Evaluate the neighbour measurement against the pre-registered expectations of S2."""
import glob, json, os, sys, numpy as np
D = sys.argv[1]; R = sys.argv[2] if len(sys.argv) > 2 else "results"
rng = np.random.default_rng(20261104); B = 2000
J = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(D, "nb_*_r*.json")))]
snap = {}
for f in glob.glob(os.path.join(D, "snap_*.json")):
    s = json.load(open(f)); snap[(s["size"], s["n_jobs"], s["rep"])] = s
out = {"runs": len(J), "per_size": {}}
for n in sorted({j["size"] for j in J}):
    w1 = np.array([j["warm"]["seconds"] for j in J if j["size"] == n and j["n_jobs"] == 1])
    w100 = np.array([j["warm"]["seconds"] for j in J if j["size"] == n and j["n_jobs"] == 100])
    c1 = np.array([j["cold"]["seconds"] for j in J if j["size"] == n and j["n_jobs"] == 1])
    c100 = np.array([j["cold"]["seconds"] for j in J if j["size"] == n and j["n_jobs"] == 100])
    Rw = w1.mean() / w100.mean()
    bs = [rng.choice(w1, len(w1)).mean() / rng.choice(w100, len(w100)).mean() for _ in range(B)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    es = "confermata" if lo > 1.1 else ("smentita" if hi <= 1.1 else "indeterminata")
    dg = [json.load(open(os.path.join(R, f"cpu_{n}_r{r}_results.json")))["timings"]["neighbors"] for r in range(1, 6)]
    dgw = float(np.mean(dg[1:])); q = dgw / w1.mean()
    calls1 = sorted({tuple(j["warm"]["set_num_threads_calls"]) for j in J if j["size"] == n and j["n_jobs"] == 1})
    calls100 = sorted({tuple(j["warm"]["set_num_threads_calls"]) for j in J if j["size"] == n and j["n_jobs"] == 100})
    knn = {nj: sorted({j["warm"]["knn_md5"] for j in J if j["size"] == n and j["n_jobs"] == nj}) for nj in (1, 100)}
    out["per_size"][n] = {"warm_nj1_mean": w1.mean(), "warm_nj1_sd": w1.std(ddof=1), "warm_nj100_mean": w100.mean(),
        "warm_nj100_sd": w100.std(ddof=1), "cold_nj1_mean": c1.mean(), "cold_nj100_mean": c100.mean(),
        "NP1_ratio_warm": Rw, "NP1_ci": [lo, hi], "NP1_esito": es,
        "dgx_neighbors_r1": dg[0], "dgx_neighbors_mean_r2_5": dgw, "NP2_dgx_over_server_nj1": q,
        "NP2_esito": "confermata" if 0.5 <= q <= 2 else "smentita", "dgx_over_server_nj100": dgw / w100.mean(),
        "calls_nj1": calls1, "calls_nj100": calls100, "knn_md5_distinct": {k: len(v) for k, v in knn.items()},
        "start_threads": sorted({j["numba_threads_at_start"] for j in J if j["size"] == n})}
g = [s for s in snap.values()]
out["N1_free"] = {"first_load1": min((s["start"]["load1"] for s in g), default=None),
                  "max_foreign_start": max((s["start"]["n_foreign"] for s in g), default=None),
                  "max_foreign_end": max((s["end"]["n_foreign"] for s in g), default=None),
                  "tctl_max": max((max(s["start"]["tctl"], s["end"]["tctl"]) for s in g), default=None)}
json.dump(out, open(os.path.join(D, "neighbors_eval.json"), "w"), indent=1, default=float)
print(json.dumps(out, default=lambda x: round(float(x), 4)))
