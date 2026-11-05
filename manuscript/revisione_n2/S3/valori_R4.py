#!/usr/bin/env python3
"""valori_R4.py: ricalcola i valori delle ricevute della regione R4 (S3, capitolo LNBI).
Uso: cd $REPO && python3 -B valori_R4.py          -> JSON {ricevuta_id: valore}
     cd $REPO && python3 -B valori_R4.py --full   -> JSON {ricevuta_id: {valore, file, md5}}
Solo libreria standard; nessuna scrittura su disco."""
import json, sys, glob, os, re, hashlib, zipfile, statistics as st, subprocess

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def J(p): return json.load(open(p))
def RF(p, n): return [f"results/{p}_{n}_r{k}_results.json" for k in range(1, 6)]
def runs(p, n): return [J(f) for f in RF(p, n)]
def mean(p, n, k): return st.mean(r["timings"][k] for r in runs(p, n))
def spd(n, k, g="gpu"): return mean("cpu", n, k) / mean(g, n, k)
ZIP = "manuscript/revisione_n2/script_e_calcoli.zip"
def ztxt(member): return zipfile.ZipFile(ZIP).read(member).decode("utf-8", "replace")
DICKS = "tracks/E_work/pdf_txt/2603.02402v1.txt"; NOLET = "tracks/E_work/pdf_txt/2022.05.26.493607v1.full.txt"; GARD = "tracks/E_work/pdf_txt/3731599.3767378.txt"
def lit(member, pattern, group=1):
    m = re.search(pattern, ztxt(member), re.S)
    return m.group(group) if m else None
def P3(n, k): return J("results_v2/S3/p3_neighbors.json")["sizes"][str(n)][k]
def NP1(n): return J("results_v2/S2/neighbors_dgxdata/neighbors_eval.json")["per_size"][str(n)]["NP1_ratio_warm"]
def hashes(p, n, res):
    return len(set(r["results_summary"][f"cluster_labels_hash_{res}"] for r in runs(p, n)))
def slurm(f, key):
    m = re.search(r"#SBATCH\s+--" + key + r"=(\S+)", open(f).read()); return m.group(1)
def drivers(prefix):
    s = set()
    for f in glob.glob(f"results/{prefix}_*_results.json"): s.add(J(f)["metadata"]["gpu_info"]["driver_version"])
    return sorted(s)
def first_varying_size():
    for n in [10000, 50000, 100000, 500000, 1300000]:
        for p in ["gpu", "gpu2", "gpu4", "gpu8"]:
            if not os.path.exists(f"results/{p}_{n}_r1_results.json"): continue
            if any(hashes(p, n, r) > 1 for r in ("0.5", "1.0", "1.5")): return n
def cpu_all_deterministic():
    return all(hashes("cpu", n, r) == 1 for n in [10000, 50000, 100000, 500000, 1300000] for r in ("0.5", "1.0", "1.5"))
def norm_max_every_size():
    out = []
    for n in [10000, 50000, 100000]:
        ks = [k for k in J(RF("cpu", n)[0])["timings"] if k != "total"]
        out.append(max(ks, key=lambda k: spd(n, k)))
    return ";".join(out)
def de_t(f, k): return J(f"results/{f}")["results"][k]["time"]
TT = ("de_benchmark_ttest_cpu.json", "ttest_cpu")
MP = "results/maxpower_11900000_8gpu_results.json"; CH = "results/maxpower_chunked_12000000_8gpu_results.json"; LIM = "results/maxpower_limit_8gpu.json"
G = lambda n: RF("cpu", n) + RF("gpu", n)

V = {}   # rid -> (callable, files)
def R(rid, files, fn): V[rid] = (fn, files)

# ---- riga 412 (R4-001)
R("R4-V001", G(10000) + RF("cpu", 1300000) + RF("gpu8", 1300000) + RF("gpu4", 10000),
  lambda: "%.2f-%.2f" % (min(__import__("math").log10(mean("cpu", n, "total") / mean(p, n, "total")) for n in [10000, 50000, 100000, 500000, 1300000] for p in ["gpu", "gpu2", "gpu4", "gpu8"] if os.path.exists(f"results/{p}_{n}_r1_results.json")),
                         max(__import__("math").log10(mean("cpu", n, "total") / mean(p, n, "total")) for n in [10000, 50000, 100000, 500000, 1300000] for p in ["gpu", "gpu2", "gpu4", "gpu8"] if os.path.exists(f"results/{p}_{n}_r1_results.json"))))
R("R4-V002", RF("gpu8", 1300000), lambda: J(RF("gpu8", 1300000)[0])["metadata"]["n_cells_input"])
R("R4-V003", ["results/concordance_10000_r1.json"], lambda: J("results/concordance_10000_r1.json")["metadata"]["n_cells"])
R("R4-V004", [LIM], lambda: J(LIM)["max_cells"] / 1e6)
R("R4-V005", [CH], lambda: J(CH)["metadata"]["n_cells_input"] / 1e6)
R("R4-V006", ["results/maxpower_3436470_8gpu_results.json"], lambda: J("results/maxpower_3436470_8gpu_results.json")["metadata"]["n_cells_source_file"] / 1e6)
# ---- riga 416 (R4-002)
R("R4-V010", G(100000), lambda: spd(100000, "normalization"))
R("R4-V011", G(10000), lambda: spd(10000, "normalization"))
R("R4-V012", G(10000) + G(50000) + G(100000), norm_max_every_size)
R("R4-V013", G(100000), lambda: spd(100000, "neighbors"))
R("R4-V014", G(10000), lambda: spd(10000, "neighbors"))
R("R4-V015", ["results_v2/S2/neighbors_dgxdata/neighbors_eval.json"], lambda: J("results_v2/S2/neighbors_dgxdata/neighbors_eval.json")["per_size"]["10000"]["calls_nj1"][0][0])
R("R4-V016", ["results_v2/S2/neighbors_dgxdata/neighbors_eval.json"], lambda: J("results_v2/S2/neighbors_dgxdata/neighbors_eval.json")["per_size"]["10000"]["calls_nj100"][0][0])
R("R4-V017", ["results_v2/S2/neighbors_dgxdata/neighbors_eval.json"], lambda: NP1(10000))
R("R4-V018", ["results_v2/S2/neighbors_dgxdata/neighbors_eval.json"], lambda: NP1(50000))
R("R4-V019", ["results_v2/S2/neighbors_dgxdata/neighbors_eval.json"], lambda: NP1(100000))
R("R4-V020", RF("gpu", 10000), lambda: J(RF("gpu", 10000)[0])["metadata"]["n_cells_input"])
R("R4-V021", RF("gpu", 50000), lambda: J(RF("gpu", 50000)[0])["metadata"]["n_cells_input"])
R("R4-V022", RF("gpu", 100000), lambda: J(RF("gpu", 100000)[0])["metadata"]["n_cells_input"])
R("R4-V023", ["results_v2/S3/p3_neighbors.json"], lambda: P3(10000, "adjusted"))
R("R4-V024", ["results_v2/S3/p3_neighbors.json"], lambda: P3(50000, "adjusted"))
R("R4-V025", ["results_v2/S3/p3_neighbors.json"], lambda: P3(100000, "adjusted"))
R("R4-V026", ["results_v2/S3/p3_neighbors.json"], lambda: 95)
R("R4-V027", ["results_v2/S3/p3_neighbors.json"], lambda: P3(100000, "adjusted_ci95")[0])
R("R4-V028", ["results_v2/S3/p3_neighbors.json"], lambda: P3(100000, "adjusted_ci95")[1])
R("R4-V029", G(100000), lambda: spd(100000, "pca"))
R("R4-V030", G(100000), lambda: spd(100000, "data_loading"))
R("R4-V031", G(10000), lambda: spd(10000, "data_loading"))
R("R4-V032", G(10000), lambda: spd(10000, "leiden_0.5"))
R("R4-V033", RF("gpu", 10000), lambda: len(RF("gpu", 10000)))
R("R4-V034", RF("gpu", 10000), lambda: "1.0;1.5" if all(k in J(RF("gpu", 10000)[0])["timings"] for k in ("leiden_1.0", "leiden_1.5")) else None)
R("R4-V035", G(10000), lambda: spd(10000, "leiden_1.0"))
R("R4-V036", G(10000), lambda: spd(10000, "leiden_1.5"))
R("R4-V037", G(10000), lambda: mean("gpu", 10000, "data_loading") - mean("cpu", 10000, "data_loading"))
R("R4-V038", G(50000), lambda: mean("gpu", 50000, "data_loading") - mean("cpu", 50000, "data_loading"))
R("R4-V039", G(100000), lambda: mean("gpu", 100000, "data_loading") - mean("cpu", 100000, "data_loading"))
R("R4-V040", G(10000), lambda: spd(10000, "total"))
R("R4-V041", RF("cpu", 10000), lambda: 100 * mean("cpu", 10000, "de_testing") / mean("cpu", 10000, "total"))
R("R4-V042", [ZIP], lambda: int(lit(DICKS, r"fewer than\s+approximately\s+([0-9,]+)\s+cells").replace(",", "")))
R("R4-V043", RF("gpu", 10000), lambda: J(RF("gpu", 10000)[0])["timings"]["leiden_0.5"])
R("R4-V044", RF("gpu", 10000), lambda: st.mean(r["timings"]["leiden_0.5"] for r in runs("gpu", 10000)[1:]))
R("R4-V057", RF("gpu2", 1300000) + RF("gpu4", 1300000) + RF("gpu8", 1300000), lambda: "; ".join("%s %s..%s" % (p, min(r["metadata"]["timestamp"] for r in runs(p, 1300000))[:16], max(r["metadata"]["timestamp"] for r in runs(p, 1300000))[:16]) for p in ("gpu2", "gpu4", "gpu8")))
# ---- riga 418 (R4-003)
R("R4-V050", RF("gpu2", 1300000) + RF("gpu8", 1300000), lambda: 100 * (1 - mean("gpu8", 1300000, "total") / mean("gpu2", 1300000, "total")))
R("R4-V051", RF("gpu8", 1300000), lambda: J(RF("gpu8", 1300000)[0])["metadata"]["n_gpus"])
R("R4-V052", RF("gpu8", 1300000), lambda: J(RF("gpu8", 1300000)[0])["metadata"]["n_cells_input"])
R("R4-V053", [ZIP], lambda: lit(NOLET, r"contains\s+(\d)xV100"))
R("R4-V054", [ZIP], lambda: lit(NOLET, r"scaled this workflow to\s+([0-9.]+) million"))
R("R4-V055", [ZIP], lambda: lit(DICKS, r"equipped with\s+(\d)\s+NVIDIA\s+\S*\s*DGX B300"))
R("R4-V056", [ZIP], lambda: lit(DICKS, r"the\s+(\d+) million cell Tahoe"))
# ---- riga 420 (R4-004)
R("R4-V060", sorted(glob.glob("results/gpu_*_results.json")), lambda: sorted(set(J(f)["metadata"]["n_cells_input"] for f in glob.glob("results/gpu_*_results.json"))))
R("R4-V061", sorted(glob.glob("results/maxpower_*8gpu_results.json")), lambda: sorted(set(J(f)["metadata"]["n_gpus"] for f in glob.glob("results/maxpower_*8gpu_results.json"))))
R("R4-V062", sorted(glob.glob("results/gpu*_500000_*_results.json")), lambda: sorted(set(os.path.basename(f).split("_")[0] for f in glob.glob("results/gpu*_500000_*_results.json") + glob.glob("results/gpu*_1300000_*_results.json"))))
# ---- riga 422 (R4-005)
R("R4-V070", ["results/concordance_10000_r1.json"], lambda: J("results/concordance_10000_r1.json")["metadata"]["n_cells"])
R("R4-V071", ["results/concordance_10000_r1.json"], lambda: min(v["ari"] for v in J("results/concordance_10000_r1.json")["cluster_concordance"].values()))
R("R4-V072", ["results/concordance_10000_r1.json"], lambda: max(v["ari"] for v in J("results/concordance_10000_r1.json")["cluster_concordance"].values()))
R("R4-V073", RF("cpu", 10000) + RF("gpu", 10000) + RF("gpu2", 10000) + RF("gpu8", 10000), lambda: "%d repeats; distinct label hashes per pipeline/resolution max=%d" % (len(RF("cpu", 10000)), max(hashes(p, 10000, r) for p in ("cpu", "gpu", "gpu2", "gpu4", "gpu8") for r in ("0.5", "1.0", "1.5"))))
R("R4-V074", ["scripts/benchmark_cpu.py"], lambda: int(re.search(r"n_iterations\s*=\s*(\d+)", open("scripts/benchmark_cpu.py").read()).group(1)))
R("R4-V076", sorted(glob.glob("results/*pu*_*_r?_results.json")), lambda: "first_varying=%s; cpu_all_deterministic=%s" % (first_varying_size(), cpu_all_deterministic()))
R("R4-V077", [ZIP], lambda: lit(GARD, r"ARI\s*≈\s*([0-9.]+)"))
R("R4-V078", [ZIP], lambda: lit(NOLET, r"Adjusted Rand\s+Index\s*=\s*([0-9.]+)") + " @ " + lit(NOLET, r"full\s+([0-9.]+)\s+million cells, we"))
# ---- riga 424 (R4-006)
R("R4-V080", [LIM], lambda: J(LIM)["max_cells"] / 1e6)
R("R4-V081", [MP], lambda: J(MP)["memory"]["peak_vram_gb"])
R("R4-V082", [MP], lambda: 100 * J(MP)["memory"]["peak_vram_gb"] / (80 * J(MP)["metadata"]["n_gpus"]))
R("R4-V083", [MP], lambda: 80 * J(MP)["metadata"]["n_gpus"])
R("R4-V084", [MP], lambda: J(MP)["memory"]["peak_ram_gb"])
R("R4-V085", [LIM], lambda: J(LIM)["first_oom_at"] / 1e6)
R("R4-V086", [MP, "slurm/maxpower.sh"], lambda: 100 * J(MP)["memory"]["peak_ram_gb"] / float(slurm("slurm/maxpower.sh", "mem").rstrip("G")))
R("R4-V087", ["slurm/maxpower.sh"], lambda: float(slurm("slurm/maxpower.sh", "mem").rstrip("G")))
R("R4-V088", [MP, CH], lambda: J(MP)["memory"]["peak_vram_gb"] / J(CH)["memory"]["peak_vram_gb"])
R("R4-V089", [CH], lambda: J(CH)["memory"]["peak_vram_gb"])
R("R4-V090", [CH], lambda: J(CH)["metadata"]["n_cells_input"] / 1e6)
R("R4-V091", [CH], lambda: J(CH)["memory"]["peak_ram_gb"])
# ---- riga 426 (R4-007)
R("R4-V100", ["results/de_benchmark_ttest_cpu.json", "results/de_benchmark_pseudobulk.json"], lambda: de_t(*TT) / de_t("de_benchmark_pseudobulk.json", "pseudobulk"))
R("R4-V101", ["results/de_benchmark_ttest_cpu.json", "results/de_benchmark_ttest_scatter.json", "results/de_benchmark_ttest_chunk.json", "results/de_benchmark_ttest_scatter_clean.json"], lambda: min(de_t(*TT) / de_t(f, k) for f, k in [("de_benchmark_ttest_scatter.json", "ttest_scatter"), ("de_benchmark_ttest_chunk.json", "ttest_chunk"), ("de_benchmark_ttest_scatter_clean.json", "ttest_scatter_clean"), ("de_benchmark_wilcoxon_scatter.json", "wilcoxon_scatter"), ("de_benchmark_wilcoxon_chunk.json", "wilcoxon_chunk")]))
R("R4-V102", ["results/de_benchmark_ttest_cpu.json", "results/de_benchmark_wilcoxon_scatter.json", "results/de_benchmark_wilcoxon_chunk.json"], lambda: max(de_t(*TT) / de_t(f, k) for f, k in [("de_benchmark_ttest_scatter.json", "ttest_scatter"), ("de_benchmark_ttest_chunk.json", "ttest_chunk"), ("de_benchmark_ttest_scatter_clean.json", "ttest_scatter_clean"), ("de_benchmark_wilcoxon_scatter.json", "wilcoxon_scatter"), ("de_benchmark_wilcoxon_chunk.json", "wilcoxon_chunk")]))
R("R4-V103", ["results/de_benchmark_wilcoxon_scatter.json"], lambda: de_t("de_benchmark_wilcoxon_scatter.json", "wilcoxon_scatter"))
R("R4-V104", ["results/de_benchmark_ttest_scatter.json"], lambda: de_t("de_benchmark_ttest_scatter.json", "ttest_scatter"))
# ---- riga 432 (R4-008)
R("R4-V110", ["results/maxpower_3436470_8gpu_results.json"], lambda: J("results/maxpower_3436470_8gpu_results.json")["metadata"]["n_cells_source_file"])
R("R4-V111", ["results/de_benchmark_pseudobulk.json"], lambda: J("results/de_benchmark_pseudobulk.json")["n_cells"] / 1e6)
R("R4-V112", ["results/de_benchmark_pseudobulk.json"], lambda: J("results/de_benchmark_pseudobulk.json")["results"]["pseudobulk"]["n_donors"])
R("R4-V113", ["slurm/cpu_benchmark.sh"], lambda: int(slurm("slurm/cpu_benchmark.sh", "cpus-per-task")))
R("R4-V114", RF("gpu8", 1300000), lambda: J(RF("gpu8", 1300000)[0])["metadata"]["n_cpus"])
R("R4-V115", RF("gpu2", 1300000), lambda: J(RF("gpu2", 1300000)[0])["metadata"]["n_cells_input"])
R("R4-V116", RF("gpu2", 1300000), lambda: mean("gpu2", 1300000, "qc_filtering"))
R("R4-V117", ["slurm/gpu_2.sh"], lambda: int(slurm("slurm/gpu_2.sh", "cpus-per-task")))
R("R4-V118", RF("gpu8", 1300000), lambda: mean("gpu8", 1300000, "qc_filtering"))
R("R4-V119", ["results_v2/S3/R2_dgx_evidence/sacct_u0044_2026-02-01_2026-11-04.txt"], lambda: int(re.search(r"cpu=(\d+)", [l for l in open("results_v2/S3/R2_dgx_evidence/sacct_u0044_2026-02-01_2026-11-04.txt") if l.startswith("16317|")][0]).group(1)))
R("R4-V120", sorted(glob.glob("results/gpu*_results.json")), lambda: "gpu=%s gpu2=%s gpu4=%s" % (drivers("gpu"), drivers("gpu2"), drivers("gpu4")))
R("R4-V121", sorted(glob.glob("results/gpu8_*_results.json")) + sorted(glob.glob("results/maxpower_*_results.json")), lambda: "gpu8=%s maxpower=%s" % (drivers("gpu8"), sorted(set(J(f)["metadata"]["gpu_info"]["driver_version"] for f in glob.glob("results/maxpower_*8gpu_results.json")))))
R("R4-V122", [".git"], lambda: subprocess.run(["git", "show", "-s", "--format=%s", "d65ff4d"], capture_output=True, text=True).stdout.strip())
R("R4-V123", [".git"], lambda: subprocess.run(["git", "show", "-s", "--format=%s", "524af6f"], capture_output=True, text=True).stdout.strip())
R("R4-V124", RF("gpu8", 1300000), lambda: J(RF("gpu8", 1300000)[0])["metadata"]["software_versions"]["rapids_singlecell"])
R("R4-V125", RF("gpu8", 1300000), lambda: 100 * sum(mean("gpu8", 1300000, k) for k in ("data_loading", "qc_filtering", "normalization", "hvg_selection")) / mean("gpu8", 1300000, "total"))
R("R4-V126", RF("gpu8", 1300000), lambda: len(RF("gpu8", 1300000)))
R("R4-V127", RF("gpu2", 500000) + RF("gpu4", 500000) + RF("gpu8", 500000), lambda: sorted(set(J(f)["metadata"]["n_cells_input"] for f in glob.glob("results/gpu[248]_*_results.json")) - set(J(f)["metadata"]["n_cells_input"] for f in glob.glob("results/gpu_*_results.json"))))
# ---- riga 436 (R4-009)
R("R4-V130", RF("cpu", 1300000), lambda: mean("cpu", 1300000, "total") / 3600)
R("R4-V131", RF("gpu8", 1300000), lambda: mean("gpu8", 1300000, "total") / 60)
R("R4-V132", RF("gpu2", 1300000), lambda: mean("gpu2", 1300000, "total") / 60)
R("R4-V133", RF("cpu", 1300000), lambda: 100 * mean("cpu", 1300000, "de_testing") / mean("cpu", 1300000, "total"))
R("R4-V134", RF("cpu", 1300000) + RF("gpu2", 1300000), lambda: (mean("cpu", 1300000, "total") - mean("cpu", 1300000, "de_testing")) / (mean("gpu2", 1300000, "total") - mean("gpu2", 1300000, "de_testing")))
R("R4-V135", RF("cpu", 1300000) + RF("gpu8", 1300000), lambda: (mean("cpu", 1300000, "total") - mean("cpu", 1300000, "de_testing")) / (mean("gpu8", 1300000, "total") - mean("gpu8", 1300000, "de_testing")))
R("R4-V136", RF("gpu2", 1300000), lambda: J(RF("gpu2", 1300000)[0])["metadata"]["n_gpus"])
# ---- riga 437 (R4-010)
R("R4-V140", ["results/maxpower_3436470_8gpu_results.json"], lambda: J("results/maxpower_3436470_8gpu_results.json")["metadata"]["n_cells_source_file"] / 1e6)
R("R4-V141", [LIM], lambda: J(LIM)["max_cells"] / 1e6)
R("R4-V142", [CH], lambda: J(CH)["metadata"]["n_cells_input"] / 1e6)
R("R4-V143", [MP], lambda: 100 * J(MP)["memory"]["peak_vram_gb"] / (80 * J(MP)["metadata"]["n_gpus"]))
# ---- riga 439 (R4-012)
R("R4-V150", ["results/de_benchmark_ttest_cpu.json", "results/de_benchmark_pseudobulk.json"], lambda: de_t(*TT) / de_t("de_benchmark_pseudobulk.json", "pseudobulk"))
# ---- riga 455 (R4-016)
R("R4-V160", ["docs/decisions/D-05.md"], lambda: re.search(r"\*\*(B53C\d+)\*\*", open("docs/decisions/D-05.md").read()).group(1))
# ---- bib
R("R4-V170", ["manuscript/full_paper_LNBI.md"], lambda: re.search(r"rapidsai/base:(\d+\.\d+)-", open("manuscript/full_paper_LNBI.md").read()).group(1))
R("R4-V171", ["manuscript/full_paper_LNBI.md"], lambda: "20" + re.search(r"rapidsai/base:(\d+)\.\d+-", open("manuscript/full_paper_LNBI.md").read()).group(1))

def main():
    full = "--full" in sys.argv
    out = {}
    for rid, (fn, files) in V.items():
        try: val = fn()
        except Exception as e: val = "ERRORE: %s" % e
        if full:
            fs = [f for f in files if os.path.isfile(f)]
            agg = hashlib.md5("".join(md5(f) for f in sorted(fs)).encode()).hexdigest() if len(fs) > 1 else (md5(fs[0]) if fs else "")
            out[rid] = {"valore": val, "file": files[0] if len(files) == 1 else ";".join(files) if len(files) <= 3 else files[0] + " (+%d)" % (len(files) - 1), "md5": agg, "n_file": len(fs)}
        else: out[rid] = val
    print(json.dumps(out, ensure_ascii=False))
if __name__ == "__main__": main()
