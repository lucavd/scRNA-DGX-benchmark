#!/usr/bin/env python3
"""Reference values from the March 2026 spatial run used by the S1 pre-registration.

Reads SPATIAL/results/spatial_{cpu,gpu}_*_results.json (read-only) and prints,
per platform: repetition-1 totals, the GPU sum of PCA+Leiden+UMAP+Moran+Geary
(repetition 1 and 2-5), relative 2 SD over repetitions 2-5, and the March
speedups (repetition 1 over repetition 1; mean 2-5 over mean 2-5).

    python3 tools/s1_march_reference.py [SPATIAL/results]
"""
import json
import statistics as st
import sys
from pathlib import Path

RES = Path(sys.argv[1] if len(sys.argv) > 1 else "SPATIAL/results")
PLATS = ["visium", "visium_hd_square_008um", "visium_hd_square_002um"]
GSTEPS = ["pca", "leiden", "umap", "spatial_autocorr_moran", "spatial_autocorr_geary"]


def load(dev, plat, r):
    return json.loads((RES / f"spatial_{dev}_{plat}_r{r}_results.json").read_text())["timings"]


def rel2sd(x):
    return 2 * st.stdev(x) / st.mean(x)


out = {}
for p in PLATS:
    t = {d: {r: load(d, p, r) for r in range(1, 6)} for d in ("cpu", "gpu")}
    g = {r: sum(t["gpu"][r][s] for s in GSTEPS) for r in range(1, 6)}
    tot = {d: {r: t[d][r]["total"] for r in range(1, 6)} for d in ("cpu", "gpu")}
    w = [2, 3, 4, 5]
    out[p] = {
        "cpu_total_r1": tot["cpu"][1],
        "gpu_total_r1": tot["gpu"][1],
        "gpu_5step_sum_r1": round(g[1], 3),
        "gpu_5step_sum_r2_5_mean": round(st.mean(g[r] for r in w), 3),
        "gpu_5step_sum_r2_5_rel2sd": round(rel2sd([g[r] for r in w]), 4),
        "cpu_total_r2_5_rel2sd": round(rel2sd([tot["cpu"][r] for r in w]), 4),
        "gpu_total_r2_5_rel2sd": round(rel2sd([tot["gpu"][r] for r in w]), 4),
        "speedup_r1_over_r1": round(tot["cpu"][1] / tot["gpu"][1], 2),
        "speedup_mean_r2_5": round(st.mean(tot["cpu"][r] for r in w) / st.mean(tot["gpu"][r] for r in w), 2),
        "cpu_co_occurrence_by_rep": [t["cpu"][r]["co_occurrence"] for r in range(1, 6)],
    }
print(json.dumps(out, indent=2))
