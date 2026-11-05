#!/usr/bin/env python3
"""Read every spatial value used in the LNBI chapter from SPATIAL/results_v2 (step S5).

Sources (all from step S1, read only):
  s1_step_stats.csv       per-step mean and SD over 5 repeats (convention 1_5 = all five)
  s1_speedups.csv         ratio of means with 95% bootstrap interval, cpu = reference_dgx | control_server
  s1_extra_numbers.json   speedup without co-occurrence, Leiden groups per machine
  cooc_check/cooc_check_eval.json   co-occurrence check with rapids-singlecell 0.15.1 and 0.14.1
  concordance_reference/*.json      CPU (DGX reference) repeat k against GPU repeat k, k = 1..5
  concordance_server_control/*.json CPU (workstation control) repeat k against GPU repeat k
  {dgx_cpu,server_gpu,server_cpu}/spatial_*_r{1..5}_results.json   memory, bins after QC

Every quantity is written with its file, md5 and key to results_v2/S5/s5_numbers.json.
Memory values are GiB (bytes / 1024**3, as in the benchmark scripts).
The only computation not already in the S1 files is the bootstrap interval of the
co-occurrence speedup of the check (decision D-20): B = 2000, seed 20261104,
CPU and GPU repeats resampled separately, ratio of means.

Usage: python3 -B tools/s5_numbers.py [--root SPATIAL/results_v2] [--out results_v2/S5/s5_numbers.json]
"""
import argparse, csv, glob, hashlib, json, os, statistics
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="SPATIAL/results_v2")
ap.add_argument("--out", default="results_v2/S5/s5_numbers.json")
a = ap.parse_args()
R = a.root
PLATS = ["visium", "visium_hd_square_008um", "visium_hd_square_002um"]
MD5 = {}

def md5(p):
    if p not in MD5:
        h = hashlib.md5(); h.update(open(p, "rb").read()); MD5[p] = h.hexdigest()
    return MD5[p]

OUT = {}
def put(name, value, src, key):
    OUT[name] = {"value": value, "file": os.path.relpath(src), "md5": md5(src), "key": key}

stats_f = f"{R}/s1_step_stats.csv"; spd_f = f"{R}/s1_speedups.csv"
extra_f = f"{R}/s1_extra_numbers.json"; cooc_f = f"{R}/cooc_check/cooc_check_eval.json"
ST = list(csv.DictReader(open(stats_f))); SP = list(csv.DictReader(open(spd_f)))
EX = json.load(open(extra_f)); CO = json.load(open(cooc_f))

def stat(run, plat, step):
    r = [x for x in ST if x["run"] == run and x["platform"] == plat and x["step"] == step]
    assert len(r) == 1, (run, plat, step)
    r = r[0]
    if any(r[f"r{k}"] in ("", None) for k in range(1, 6)):   # step skipped (empty in the table)
        return None
    reps = [float(r[f"r{k}"]) for k in range(1, 6)]
    if any(v < 0 for v in reps):          # -1 = step skipped
        return None
    return {"mean": float(r["mean_1_5"]), "sd": float(r["sd_1_5"]), "reps": reps}

def speedup(plat, step, cpu):
    r = [x for x in SP if x["platform"] == plat and x["step"] == step and x["cpu"] == cpu and x["convention"] == "1_5"]
    if not r:
        return None
    assert len(r) == 1
    return [float(r[0]["speedup"]), float(r[0]["ci_lo"]), float(r[0]["ci_hi"])]

STEPS = sorted({x["step"] for x in ST})
for run in ("dgx_cpu", "server_gpu", "server_cpu"):
    for p in PLATS:
        for s in STEPS:
            v = stat(run, p, s)
            if v is not None:
                put(f"time.{run}.{p}.{s}", v, stats_f, f"run={run} platform={p} step={s} mean_1_5 sd_1_5 r1-r5")
for cpu in ("reference_dgx", "control_server"):
    for p in PLATS:
        for s in STEPS:
            v = speedup(p, s, cpu)
            if v is not None:
                put(f"speedup.{cpu}.{p}.{s}", v, spd_f, f"platform={p} step={s} cpu={cpu} convention=1_5 [speedup, ci_lo, ci_hi]")

# Totals without co-occurrence (D-13) and Leiden groups per machine
for p in PLATS:
    for cpu in ("reference_dgx", "control_server"):
        put(f"speedup_wo_cooc.{cpu}.{p}", EX["speedup_total_without_co_occurrence"][p][cpu], extra_f,
            f"speedup_total_without_co_occurrence.{p}.{cpu}")
    for run in ("dgx_cpu", "server_cpu", "server_gpu"):
        put(f"leiden_groups.{run}.{p}", EX["own_leiden_clusters"][p][run], extra_f, f"own_leiden_clusters.{p}.{run}")
# HD 8 um totals without co-occurrence, from the step table (check of the extra-numbers value)
for run in ("dgx_cpu", "server_gpu", "server_cpu"):
    t = stat(run, "visium_hd_square_008um", "total")["mean"]; c = stat(run, "visium_hd_square_008um", "co_occurrence")["mean"]
    put(f"total_wo_cooc.{run}.visium_hd_square_008um", t - c, stats_f, "mean_1_5(total) - mean_1_5(co_occurrence)")

# Co-occurrence check (D-13, D-20)
for k in ("Q1_hd8_rsc0151_equal_intervals", "Q1_hd8_rsc0151_max_abs_diff", "hd8_rsc0141_equal_intervals",
          "Q2_visium_rsc0151_equal_intervals", "rsc0151_identical_across_reps", "t_hd8_rsc0151", "t_hd8_rsc0141",
          "Q3_ratio", "Q3_ci", "speedup_cooc_hd8_dgx_over_rsc0151", "speedup_cooc_hd8_server_over_rsc0151"):
    put(f"cooc.{k}", CO[k], cooc_f, k)
put("cooc.n_unequal_1e-4", EX["hd8_cpu_gpu_same_groups"]["n_unequal"], extra_f, "hd8_cpu_gpu_same_groups.n_unequal")
rng = np.random.default_rng(20261104)
cpu = np.array(stat("dgx_cpu", "visium_hd_square_008um", "co_occurrence")["reps"]); gpu = np.array(CO["t_hd8_rsc0151"])
boot = [cpu[rng.integers(0, 5, 5)].mean() / gpu[rng.integers(0, 5, 5)].mean() for _ in range(2000)]
put("cooc.check_speedup_dgx_rsc0151", [float(cpu.mean() / gpu.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
    cooc_f, "mean(dgx_cpu co_occurrence r1-5 from s1_step_stats.csv) / mean(t_hd8_rsc0151); bootstrap B=2000 seed 20261104")
OUT["cooc.check_speedup_dgx_rsc0151"]["file2"] = os.path.relpath(stats_f)

# Concordance: 5 pairs per platform and CPU machine
METRICS = [("moranI", "I_spearman_rho"), ("gearyC", "C_spearman_rho"), ("moranI", "svg_jaccard_top50"),
           ("moranI", "svg_jaccard_top100"), ("moranI", "svg_jaccard_top200"), ("moranI", "svg_jaccard_fdr005"),
           ("gearyC", "svg_jaccard_top50"), ("gearyC", "svg_jaccard_fdr005"), ("moranI", "n_svg_cpu"), ("moranI", "n_svg_shared"),
           ("clusters", "ari"), ("clusters", "nmi"), ("clusters", "n_clusters_cpu"), ("clusters", "n_clusters_gpu"),
           ("co_occurrence", "spearman_rho"), ("co_occurrence", "max_abs_diff"), ("nhood_enrichment", "spearman_rho")]
for tag, d in (("reference", "concordance_reference"), ("control", "concordance_server_control")):
    for p in PLATS:
        f = f"{R}/{d}/spatial_concordance_{p}.json"
        J = json.load(open(f)); assert [x["repeat_id"] for x in J] == [1, 2, 3, 4, 5], f
        for g, k in METRICS:
            vals = [x.get(g, {}).get(k) if isinstance(x.get(g), dict) else None for x in J]
            if all(v is None for v in vals):
                continue
            put(f"conc.{tag}.{p}.{g}.{k}", vals, f, f"[repeat 1..5].{g}.{k}")

# Memory and bins after QC from the per-run files
for run, pre in (("dgx_cpu", "cpu"), ("server_gpu", "gpu"), ("server_cpu", "cpu")):
    for p in PLATS:
        fs = sorted(glob.glob(f"{R}/{run}/spatial_{pre}_{p}_r[1-5]_results.json")); assert len(fs) == 5, (run, p)
        js = [json.load(open(f)) for f in fs]
        for key, getter in (("peak_ram_gb", lambda j: j["memory"]["peak_ram_gb"]),
                            ("peak_vram_gb", lambda j: j["memory"]["peak_vram_gb"]),
                            ("vram_before_loading_gb", lambda j: j["memory"]["detailed"].get("data_loading_vram_before_gb")),
                            ("n_spots_after_qc", lambda j: j["results_summary"]["n_spots_after_qc"]),
                            ("n_spots_input", lambda j: j["metadata"]["n_spots_input"]),
                            ("n_genes_input", lambda j: j["metadata"]["n_genes_input"])):
            vals = [getter(j) for j in js]
            if all(v is None for v in vals):
                continue
            OUT[f"run.{run}.{p}.{key}"] = {"value": vals, "file": [os.path.relpath(f) for f in fs],
                                            "md5": [md5(f) for f in fs], "key": key}
        if run == "server_gpu":
            OUT[f"run.{run}.{p}.software"] = {"value": [j["metadata"].get("software_versions") for j in js][0],
                                               "file": os.path.relpath(fs[0]), "md5": md5(fs[0]), "key": "metadata.software_versions"}
            OUT[f"run.{run}.{p}.gpu_info"] = {"value": [j["metadata"]["gpu_info"] for j in js],
                                              "file": [os.path.relpath(f) for f in fs], "md5": [md5(f) for f in fs], "key": "metadata.gpu_info"}
os.makedirs(os.path.dirname(a.out), exist_ok=True)
json.dump(OUT, open(a.out, "w"), indent=1, sort_keys=True)
print(json.dumps({"n_quantities": len(OUT), "n_files": len(MD5), "out": a.out}))
