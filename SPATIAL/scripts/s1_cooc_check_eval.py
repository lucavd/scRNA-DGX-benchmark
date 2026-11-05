#!/usr/bin/env python3
"""Evaluate the D-13 co-occurrence check: V3, Q1, Q2, Q3. Writes cooc_check/cooc_check_eval.json."""
import json
from pathlib import Path
import numpy as np

R = Path("SPATIAL/results_v2"); O = R / "cooc_check"
rng = np.random.default_rng(20261103); B = 2000


def load(tag, plat):
    js = [json.loads((O / tag / f"cooc_gpu_{plat}_r{r}.json").read_text()) for r in range(1, 6)]
    ms = [np.load(O / tag / f"cooc_gpu_{plat}_r{r}.npy") for r in range(1, 6)]
    return js, ms


h8 = "visium_hd_square_008um"
j51, m51 = load("rsc0151", h8); j41, m41 = load("rsc0141", h8); jv, mv = load("rsc0151", "visium")
pipe = np.load(R / "server_gpu" / f"spatial_gpu_{h8}_r1_co_occurrence.npy")
t51 = np.array([j["timings"]["co_occurrence"] for j in j51]); t41 = np.array([j["timings"]["co_occurrence"] for j in j41])
bs = [rng.choice(t51, 5).mean() / rng.choice(t41, 5).mean() for _ in range(B)]
lo, hi = np.percentile(bs, [2.5, 97.5]); ratio = t51.mean() / t41.mean()
cpu_t = np.mean([json.loads((R / "dgx_cpu" / f"spatial_cpu_{h8}_r{r}_results.json").read_text())["timings"]["co_occurrence"] for r in range(1, 6)])
cpu_ts = np.mean([json.loads((R / "server_cpu" / f"spatial_cpu_{h8}_r{r}_results.json").read_text())["timings"]["co_occurrence"] for r in range(1, 6)])
out = {
    "versions": {"rsc0151": j51[0]["rapids_singlecell"], "rsc0141": j41[0]["rapids_singlecell"]},
    "V3_rsc0141_identical_to_pipeline": [bool(np.array_equal(m, pipe)) for m in m41],
    "Q1_hd8_rsc0151_equal_intervals": [j["comparison_with_cpu"]["n_intervals_equal_atol_1e-3"] for j in j51],
    "Q1_hd8_rsc0151_max_abs_diff": [j["comparison_with_cpu"]["max_abs_diff"] for j in j51],
    "hd8_rsc0141_equal_intervals": [j["comparison_with_cpu"]["n_intervals_equal_atol_1e-3"] for j in j41],
    "Q2_visium_rsc0151_equal_intervals": [j["comparison_with_cpu"]["n_intervals_equal_atol_1e-3"] for j in jv],
    "Q2_visium_rsc0151_max_abs_diff": [j["comparison_with_cpu"]["max_abs_diff"] for j in jv],
    "rsc0151_identical_across_reps": all(np.array_equal(m51[0], m) for m in m51),
    "t_hd8_rsc0151": t51.tolist(), "t_hd8_rsc0141": t41.tolist(),
    "t_visium_rsc0151": [j["timings"]["co_occurrence"] for j in jv],
    "Q3_ratio": float(ratio), "Q3_ci": [float(lo), float(hi)],
    "Q3_esito": "confermata" if 0.9 <= lo and hi <= 1.1 else ("smentita" if hi < 0.9 or lo > 1.1 else "indeterminata"),
    "speedup_cooc_hd8_dgx_over_rsc0151": float(cpu_t / t51.mean()),
    "speedup_cooc_hd8_server_over_rsc0151": float(cpu_ts / t51.mean()),
    "load1_start": [j["host_start"]["loadavg_1_5_15"][0] for j in j51 + j41 + jv],
}
out["V3_pass"] = all(out["V3_rsc0141_identical_to_pipeline"])
out["Q1_esito"] = "confermata" if all(x == 49 for x in out["Q1_hd8_rsc0151_equal_intervals"]) else "smentita"
out["Q2_esito"] = "confermata" if all(x == 49 for x in out["Q2_visium_rsc0151_equal_intervals"]) else "smentita"
(O / "cooc_check_eval.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
