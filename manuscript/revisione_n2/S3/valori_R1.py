#!/usr/bin/env python3
"""Ricalcolo dei valori delle ricevute della regione R1 (fronte, abstract, Introduction).
Uso: cd $REPO && python3 -B valori_R1.py  -> stampa SOLO un JSON {ricevuta_id: valore}.
Solo libreria standard. Convenzione D-15: media di r1-r5, SD campionaria, speedup = rapporto fra medie."""
import csv, glob, json, statistics as st, zipfile, re

def J(p):
    with open(p) as f:
        return json.load(f)

def runs(cfg, n):
    return [J(f"results/{cfg}_{n}_r{k}_results.json") for k in range(1, 6)]

def mean_t(cfg, n, key="total"):
    return st.mean(r["timings"][key] for r in runs(cfg, n))

def sd_t(cfg, n, key="total"):
    return st.stdev([r["timings"][key] for r in runs(cfg, n)])

N = 1300000
def spd(cfg):
    return mean_t("cpu", N) / mean_t(cfg, N)
def node(cfg):
    return (mean_t("cpu", N) - mean_t("cpu", N, "de_testing")) / (mean_t(cfg, N) - mean_t(cfg, N, "de_testing"))

def s1spd(platform):
    with open("SPATIAL/results_v2/s1_speedups.csv") as f:
        for r in csv.DictReader(f):
            if r["platform"] == platform and r["step"] == "total" and r["cpu"] == "reference_dgx" and r["convention"] == "1_5":
                return float(r["speedup"])

ZIP = "manuscript/revisione_n2/script_e_calcoli.zip"
def ztext(name):
    with zipfile.ZipFile(ZIP) as z:
        return z.read("tracks/E_work/pdf_txt/" + name).decode("utf-8", "replace")
def zfind(name, pattern):
    m = re.search(pattern, ztext(name))
    return m.group(0) if m else None

cpu_sizes = sorted({J(p)["metadata"]["n_cells_input"] for p in glob.glob("results/cpu_*_r1_results.json")})
ex = J("SPATIAL/results_v2/s1_extra_numbers.json")
ce = J("SPATIAL/results_v2/cooc_check/cooc_check_eval.json")
ov = J("SPATIAL/results_v2/s1_cooc_overflow_check.json")
pb = J("results/de_benchmark_pseudobulk.json")
tt = J("results/de_benchmark_ttest_cpu.json")
mp = J("results/maxpower_11900000_8gpu_results.json")
lim = J("results/maxpower_limit_8gpu.json")
cc = J("results/concordance_10000_r1.json")
aris = [v["ari"] for v in cc["cluster_concordance"].values()]
dgx_sp = J("SPATIAL/results_v2/dgx_cpu/spatial_cpu_visium_hd_square_002um_r1_results.json")
hd2_old = J("SPATIAL/results/spatial_cpu_visium_hd_square_002um_r1_results.json")
sp_gpu = J("SPATIAL/results/spatial_gpu_visium_r1_results.json")
h100 = J("results/gpu8_1300000_r1_results.json")["metadata"]["gpu_info"]["gpus"][0]["gpu_name"]
def gname(d):
    gi = d["metadata"].get("gpu_info", {})
    if "gpu_name" in gi:
        return gi["gpu_name"]
    return gi["gpus"][0]["gpu_name"]
rtx = gname(sp_gpu)
hd8_eq = ex["hd8_cpu_gpu_same_groups"]["intervals_equal_1e-4"]

V = {}
# abstract (R1-002)
V["R1-V001"] = J("results/cpu_1300000_r1_results.json")["metadata"]["n_cpus"]
V["R1-V002"] = cpu_sizes[0]
V["R1-V003"] = cpu_sizes[-1] / 1e6
V["R1-V004"] = len(glob.glob("results/cpu_1300000_r*_results.json"))
V["R1-V005"] = mean_t("gpu8", N)
V["R1-V006"] = mean_t("cpu", N)
V["R1-V007"] = spd("gpu8")
V["R1-V008"] = spd("gpu2")
V["R1-V009"] = runs("gpu2", N)[0]["metadata"]["n_gpus"]
V["R1-V010"] = 100 * mean_t("cpu", N, "de_testing") / mean_t("cpu", N)
V["R1-V011"] = node("gpu2")
V["R1-V012"] = node("gpu8")
V["R1-V013"] = cc["metadata"]["n_cells"]
V["R1-V014"] = min(aris)
V["R1-V015"] = max(aris)
V["R1-V016"] = lim["max_cells"] / 1e6  # first_oom_at non e' un OOM: log SLURM 16531 = TimeoutError Dask
V["R1-V017"] = mp["metadata"]["n_cells_source_file"]
V["R1-V018"] = pb["n_cells"] / 1e6
V["R1-V019"] = pb["results"]["pseudobulk"]["time"]
V["R1-V020"] = tt["results"]["ttest_cpu"]["time"]
V["R1-V021"] = dgx_sp["metadata"]["n_cpus"]
V["R1-V022"] = s1spd("visium")
V["R1-V023"] = ex["speedup_total_without_co_occurrence"]["visium_hd_square_008um"]["reference_dgx"][0]
V["R1-V024"] = s1spd("visium_hd_square_002um")
V["R1-V025"] = ce["versions"]["rsc0141"]["version"]
V["R1-V026"] = ex["hd8_cpu_gpu_same_groups"]["n_unequal"]
V["R1-V027"] = len(hd8_eq)
V["R1-V028"] = "uint32 first exceeded at interval %d; first unequal interval %d" % (ov["first_threshold_index_over_uint32"], ex["hd8_cpu_gpu_same_groups"]["first_unequal_interval"])
V["R1-V029"] = ce["versions"]["rsc0151"]["version"]
V["R1-V030"] = min(ce["Q1_hd8_rsc0151_equal_intervals"])
V["R1-V031"] = h100
V["R1-V032"] = rtx
# titolo (R1-001)
V["R1-V033"] = J("results/cpu_1300000_r1_results.json")["metadata"]["n_cpus"]
V["R1-V034"] = h100
V["R1-V035"] = rtx
# riga 28 (R1-006)
V["R1-V036"] = hd2_old["metadata"]["n_spots_input"] / 1e6
# righe 34-35 (R1-007, R1-008): letteratura, testo estratto nel pacchetto della revisione
V["R1-V037"] = zfind("2022.05.26.493607v1.full.txt", r"1-8 V100 GPUs")
V["R1-V038"] = "fuori repo: articles/10.1093_bioadv_vbaf167.pdf ('a simulated dataset containing 13 million cells')"
V["R1-V039"] = "fuori repo: articles/10.1093_bioadv_vbaf167.pdf ('on a single A100 GPU')"
V["R1-V040"] = zfind("2603.02402v1.txt", r"100 million cell Tahoe 100M dataset")
V["R1-V041"] = zfind("2603.02402v1.txt", r"node equipped with 8 NVIDIA")
V["R1-V042"] = zfind("3731599.3767378.txt", r"median ARI between 0\.45 and 0\.55")
V["R1-V043"] = zfind("3731599.3767378.txt", r"median ARI between 0\.45 and 0\.55")
V["R1-V044"] = zfind("3731599.3767378.txt", r"NVIDIA H100 GPUs \(80 GB\)")
# riga 37 (R1-009)
V["R1-V045"] = 4
# riga 44 (R1-015)
V["R1-V046"] = [J("results/cpu_1300000_r1_results.json")["metadata"]["n_cpus"], dgx_sp["metadata"]["n_cpus"]]
V["R1-V047"] = "CIBB 2026"
V["R1-V048"] = V["R1-V028"]
V["R1-V049"] = V["R1-V029"]
V["R1-V050"] = J("SPATIAL/results_v2/dgx_cpu/spatial_cpu_visium_hd_square_008um_r1_results.json")["metadata"]["bin_size"]
# solo nel testo delle scelte del PI (scelte_R1.md)
V["R1-V051"] = mean_t("gpu8", N)
V["R1-V052"] = sd_t("gpu8", N)
V["R1-V053"] = mean_t("cpu", N)
V["R1-V054"] = sd_t("cpu", N)
V["R1-V055"] = mean_t("gpu2", N)
V["R1-V056"] = sd_t("gpu2", N)
V["R1-V057"] = mean_t("gpu8", N, "data_loading")
V["R1-V058"] = mean_t("gpu2", N, "data_loading")
V["R1-V059"] = tt["results"]["ttest_cpu"]["time"] / pb["results"]["pseudobulk"]["time"]
V["R1-V060"] = mean_t("cpu", N) / 3600
V["R1-V061"] = mean_t("gpu8", N) / 60
print(json.dumps(V, indent=1, default=str))
