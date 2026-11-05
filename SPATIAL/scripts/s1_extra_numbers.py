#!/usr/bin/env python3
"""S1 supplementary numbers (read-only on results): speedup without co-occurrence,
own-Leiden cluster counts per run, and an all-zero-slice diagnostic of the GPU
co-occurrence matrices (new run and March), used to judge the int32 overflow.

    python SPATIAL/scripts/s1_extra_numbers.py --root SPATIAL > SPATIAL/results_v2/s1_extra_numbers.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

B, SEED = 2000, 20261104
ap = argparse.ArgumentParser(); ap.add_argument("--root", default="SPATIAL"); a = ap.parse_args()
R = Path(a.root)
rng = np.random.default_rng(SEED)
PL = ["visium", "visium_hd_square_008um", "visium_hd_square_002um"]
RUNS = {"dgx_cpu": "cpu", "server_cpu": "cpu", "server_gpu": "gpu"}


def js(run, p, r):
    return json.loads((R / "results_v2" / run / f"spatial_{RUNS[run]}_{p}_r{r}_results.json").read_text())


def boot(num, den):
    num, den = np.asarray(num, float), np.asarray(den, float)
    bs = [rng.choice(num, 5).mean() / rng.choice(den, 5).mean() for _ in range(B)]
    return [float(num.mean() / den.mean()), *map(float, np.percentile(bs, [2.5, 97.5]))]


out = {"speedup_total_without_co_occurrence": {}, "own_leiden_clusters": {}, "gpu_cooc_zero_slices": {}}
for p in PL:
    tot = {run: [js(run, p, r)["timings"]["total"] - max(js(run, p, r)["timings"].get("co_occurrence", -1), 0) for r in range(1, 6)] for run in RUNS}
    out["speedup_total_without_co_occurrence"][p] = {
        "reference_dgx": boot(tot["dgx_cpu"], tot["server_gpu"]),
        "control_server": boot(tot["server_cpu"], tot["server_gpu"])}
    out["own_leiden_clusters"][p] = {run: [js(run, p, r)["results_summary"]["n_clusters"] for r in range(1, 6)] for run in RUNS}
for label, d, pre in (("new_r1", R / "results_v2" / "server_gpu", "spatial_gpu"), ("march_r1", R / "results", "spatial_gpu")):
    for p in PL[:2]:
        f = d / f"{pre}_{p}_r1_co_occurrence.npy"
        if f.exists():
            m = np.load(f)
            z = [int(k) for k in range(m.shape[2]) if np.all(m[:, :, k] == 0)]
            out["gpu_cooc_zero_slices"][f"{label}:{p}"] = {"shape": list(m.shape), "all_zero_intervals": z}
cpu = np.load(R / "results_v2" / "dgx_cpu" / "spatial_cpu_visium_hd_square_008um_r1_co_occurrence.npy")
gpu = np.load(R / "results_v2" / "server_gpu" / "spatial_gpu_visium_hd_square_008um_r1_co_occurrence.npy")
same = [bool(np.allclose(cpu[:, :, k], gpu[:, :, k], atol=1e-4)) for k in range(cpu.shape[2])]
out["hd8_cpu_gpu_same_groups"] = {"intervals_equal_1e-4": same, "first_unequal_interval": same.index(False) if False in same else None,
                                  "n_unequal": int(len(same) - sum(same))}
print(json.dumps(out, indent=1))
