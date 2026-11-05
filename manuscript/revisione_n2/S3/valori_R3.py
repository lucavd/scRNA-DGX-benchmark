#!/usr/bin/env python3
"""Ricalcolo dei valori delle ricevute della regione R3 (Risultati scRNA), step S3.

Uso (sul server):  cd $REPO && python3 -B valori_R3.py
Stampa SOLO un JSON {ricevuta_id: valore} su stdout, nella stessa unita' del
valore scritto nel manoscritto (percentuali x100, GiB = byte/1024^3 come nei JSON,
secondi o minuti come nel testo). Solo libreria standard.
Con l'argomento --meta stampa anche voce, edit, file, chiave e arrotondamento.
Convenzione D-15: media delle 5 ripetizioni, speedup = rapporto fra medie.
"""
import glob
import json
import math
import re
import statistics
import sys

REPS = range(1, 6)


def J(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def get(d, key):
    for part in key.split("/"):
        d = d[part]
    return d


def rep_files(pfx, n):
    return [f"results/{pfx}_{n}_r{k}_results.json" for k in REPS]


def reps(pfx, n, key):
    return [get(J(f), key) for f in rep_files(pfx, n)]


def mean(x):
    return sum(x) / len(x)


def m(pfx, n, key):
    return mean(reps(pfx, n, key))


def spd_total(n, gpfx):
    return m("cpu", n, "timings/total") / m(gpfx, n, "timings/total")


def spd_step(n, step, gpfx="gpu", r=None):
    c = reps("cpu", n, "timings/" + step)
    g = reps(gpfx, n, "timings/" + step)
    if r == "2_5":
        c, g = c[1:], g[1:]
    return mean(c) / mean(g)


def nodde(gpfx):
    t = [a - b for a, b in zip(reps(gpfx, 1300000, "timings/total"), reps(gpfx, 1300000, "timings/de_testing"))]
    return mean(t)


def pca_nb(gpfx, n):
    return mean([a + b for a, b in zip(reps(gpfx, n, "timings/pca"), reps(gpfx, n, "timings/neighbors"))])


def pool_inc(gpfx, n):
    v = [get(J(f), "memory/detailed/pca_vram_before_gb") - get(J(f), "memory/detailed/scale_vram_after_gb") for f in rep_files(gpfx, n)]
    return mean(v)


def ram_slope():
    ns = [10000, 50000, 100000, 500000, 1300000]
    x = [math.log(n) for n in ns]
    y = [math.log(m("cpu", n, "memory/peak_ram_gb")) for n in ns]
    xm, ym = mean(x), mean(y)
    return sum((a - xm) * (b - ym) for a, b in zip(x, y)) / sum((a - xm) ** 2 for a in x)


def ram_local():
    return math.log(m("cpu", 1300000, "memory/peak_ram_gb") / m("cpu", 500000, "memory/peak_ram_gb")) / math.log(1300000 / 500000)


def max_change_100k_up():
    out = []
    for n, gs in [(100000, ["gpu", "gpu2", "gpu4", "gpu8"]), (500000, ["gpu2", "gpu4", "gpu8"]), (1300000, ["gpu2", "gpu4", "gpu8"])]:
        for g in gs:
            c = reps("cpu", n, "timings/total")
            gg = reps(g, n, "timings/total")
            s15 = mean(c) / mean(gg)
            s25 = mean(c[1:]) / mean(gg[1:])
            out.append(abs(s15 / s25 - 1) * 100)
    return max(out)


MP = "results/maxpower_11900000_8gpu_results.json"
MPD = "memory/detailed/"


def mp(key, f=MP):
    return get(J(f), key)


def dense_hvg_gib(f=MP):
    return get(J(f), "results_summary/n_cells_after_qc") * 2000 * 4 / 1024 ** 3


def residual_gib():
    return mp("memory/peak_ram_gb") - mp(MPD + "qc_filtering_ram_before_gb") - dense_hvg_gib()


CC = "results/concordance_10000_r1.json"


def de_rhos():
    return [v["spearman_rho"] for v in get(J(CC), "de_concordance/per_pair").values()]


def n_zero_overlap_low_pairs():
    pp = get(J(CC), "de_concordance/per_pair")
    low = sorted(pp.values(), key=lambda v: v["spearman_rho"])[:2]
    return sum(1 for v in low if v["overlap_fraction"] == 0.0)


def load_knn(path):
    """Legge un .npz di numpy (zip di .npy int32 1-D) con la sola libreria standard."""
    import zipfile
    import ast
    import struct
    out = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            raw = z.read(name)
            assert raw[:6] == b"\x93NUMPY"
            major = raw[6]
            if major == 1:
                hlen = struct.unpack("<H", raw[8:10])[0]
                off = 10
            else:
                hlen = struct.unpack("<I", raw[8:12])[0]
                off = 12
            header = ast.literal_eval(raw[off:off + hlen].decode("latin1"))
            assert header["descr"] in ("<i4", "<i8")
            size = 4 if header["descr"] == "<i4" else 8
            data = raw[off + hlen:]
            n = header["shape"][0] if header["shape"] else 1
            fmt = "<%d%s" % (n, "i" if size == 4 else "q")
            out[int(name[4:-4])] = list(struct.unpack(fmt, data[: n * size]))
    return [out[i] for i in range(len(out))]


_KNN = {}


def knn_stats():
    if "s" in _KNN:
        return _KNN["s"]
    ck = load_knn("results/cpu_10000_r1_knn.npz")
    gk = load_knn("results/gpu_10000_r1_knn.npz")
    contained = 0
    jac_noself = []
    for i, (a, b) in enumerate(zip(ck, gk)):
        A, B = set(a), set(b)
        A.discard(i)
        B.discard(i)
        if B <= A:
            contained += 1
        jac_noself.append(len(A & B) / len(A | B))
    s = {
        "cpu_size": statistics.mode(len(a) for a in ck),
        "gpu_size": statistics.mode(len(b) for b in gk),
        "frac_contained_pct": contained / len(ck) * 100,
        "jac_noself_mean": mean(jac_noself),
        "jac_noself_max": max(jac_noself),
    }
    _KNN["s"] = s
    return s


def label_hash_distinct(pfx, n):
    return [len(set(reps(pfx, n, f"results_summary/cluster_labels_hash_{r}"))) for r in ["0.5", "1.0", "1.5"]]


def gpu_labels_vary_from_50k():
    """1 se a ogni dimensione >= 50k la GPU da' etichette diverse fra ripetizioni ad almeno
    una risoluzione e la CPU mai; 0 altrimenti."""
    ok = True
    for n, gs in [(50000, ["gpu"]), (100000, ["gpu"]), (500000, ["gpu2", "gpu4", "gpu8"]), (1300000, ["gpu2", "gpu4", "gpu8"])]:
        ok &= max(label_hash_distinct("cpu", n)) == 1
        for g in gs:
            ok &= max(label_hash_distinct(g, n)) > 1
    return int(ok)


def identical_labels_10k():
    return int(max(label_hash_distinct("cpu", 10000)) == 1 and max(label_hash_distinct("gpu", 10000)) == 1)


def log_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def log_float(path, pattern):
    mt = re.search(pattern, log_text(path))
    return float(mt.group(1).replace(",", ""))


def maxpower_completed_sizes():
    fs = [f for f in glob.glob("results/maxpower_*_8gpu_results.json") if "chunked" not in f and "limit" not in f]
    return sorted(get(J(f), "metadata/target_cells") for f in fs)


DE = "results/de_benchmark_{}.json"


def de_t(name, key=None):
    return get(J(DE.format(name)), "results/" + (key or name) + "/time")


NE = "results_v2/S2/neighbors_dgxdata/neighbors_eval.json"

# (ricevuta_id, voce, edit_id, valore_scritto, file, chiave, funzione, arrotondamento)
R = []


def add(voce, edit, scritto, file, chiave, fn, arr):
    rid = "R3-V%03d" % (len(R) + 1)
    R.append((rid, voce, edit, scritto, file, chiave, fn, arr))


C13 = "results/cpu_1300000_r{1..5}_results.json"
# E001 riga 183 (R0558, scelta CIFRA)
add("R0558", "R3-001", "93.5", C13, "100*mean(timings.de_testing)/mean(timings.total)", lambda: 100 * m("cpu", 1300000, "timings/de_testing") / m("cpu", 1300000, "timings/total"), "1 decimale")
add("R0558", "R3-001", "48,688.3", C13, "mean(timings.de_testing) s", lambda: m("cpu", 1300000, "timings/de_testing"), "1 decimale")
add("R0558", "R3-001", "9.2", C13 + "; results/gpu8_1300000_r{1..5}_results.json", "mean(total-de_testing) CPU / mean(total-de_testing) 8 GPU", lambda: nodde("cpu") / nodde("gpu8"), "1 decimale")
add("R0558", "R3-001", "7.9", C13 + "; results/gpu2_1300000_r{1..5}_results.json", "mean(total-de_testing) CPU / mean(total-de_testing) 2 GPU", lambda: nodde("cpu") / nodde("gpu2"), "1 decimale")
add("R0558", "R3-001", "120", "manuscript/revisione_n2/script_e_calcoli.zip", "tracks/E_work/pdf_txt/2603.02402v1.txt riga 146 '>120 speedup' (B200)", lambda: 120, "nessun-controllo: valore letto nella fonte bibliografica Dicks2026")
add("R0558", "R3-001", "110", "manuscript/revisione_n2/script_e_calcoli.zip", "tracks/E_work/pdf_txt/2603.02402v1.txt riga 151 'H200 reached 110x'", lambda: 110, "nessun-controllo: valore letto nella fonte bibliografica Dicks2026")
add("R0558", "R3-001", "32", "manuscript/revisione_n2/script_e_calcoli.zip", "tracks/E_work/pdf_txt/2603.02402v1.txt riga 407 'Threadripper Pro 7975WX (32 cores'", lambda: 32, "nessun-controllo: valore letto nella fonte bibliografica Dicks2026")
add("R0558", "R3-001", "493.3", "results/gpu2_1300000_r{1..5}_results.json", "mean(timings.total) s", lambda: m("gpu2", 1300000, "timings/total"), "1 decimale")
add("R0558", "R3-001", "10.3", "results/gpu2_1300000_r{1..5}_results.json", "SD campionaria di timings.total s", lambda: statistics.stdev(reps("gpu2", 1300000, "timings/total")), "1 decimale")
add("R0558", "R3-001", "105.5", C13 + "; results/gpu2_1300000_r{1..5}_results.json", "mean(cpu total)/mean(gpu2 total)", lambda: spd_total(1300000, "gpu2"), "1 decimale")
add("R0558", "R3-001", "149.0", "results/gpu2_1300000_r{1..5}_results.json", "mean(timings.data_loading) s", lambda: m("gpu2", 1300000, "timings/data_loading"), "1 decimale")
add("R0558", "R3-001", "90.6", "results/gpu8_1300000_r{1..5}_results.json", "mean(timings.data_loading) s", lambda: m("gpu8", 1300000, "timings/data_loading"), "1 decimale")
# E002 riga 185 (R0082)
for n, s in [(10000, "12.0"), (50000, "33.7"), (100000, "43.8")]:
    add("R0082", "R3-002", s, f"results/cpu_{n}_r{{1..5}}_results.json; results/gpu_{n}_r{{1..5}}_results.json", "mean(cpu timings.total)/mean(gpu timings.total)", (lambda n=n: spd_total(n, "gpu")), "1 decimale")
add("R0082", "R3-002", "34.9", "results/cpu_500000_r{1..5}_results.json; results/gpu2_500000_r{1..5}_results.json", "mean(cpu total)/mean(gpu2 total)", lambda: spd_total(500000, "gpu2"), "1 decimale")
add("R0082", "R3-002", "119.6", C13 + "; results/gpu8_1300000_r{1..5}_results.json", "mean(cpu total)/mean(gpu8 total)", lambda: spd_total(1300000, "gpu8"), "1 decimale")
add("R0082", "R3-002", "105.5", C13 + "; results/gpu2_1300000_r{1..5}_results.json", "mean(cpu total)/mean(gpu2 total)", lambda: spd_total(1300000, "gpu2"), "1 decimale")
# E004 riga 217 (R0349 + D-16)
G10 = "results/cpu_10000_r{1..5}_results.json; results/gpu_10000_r{1..5}_results.json"
add("R0349", "R3-004", "0.36", G10, "mean(cpu leiden_0.5)/mean(gpu leiden_0.5); minimo su tutti gli step e 10k-100k", lambda: min(spd_step(n, s) for n in [10000, 50000, 100000] for s in ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "neighbors", "leiden_0.5", "leiden_1.0", "leiden_1.5", "umap", "de_testing"]), "2 decimali")
add("R0349", "R3-004", "329", G10, "mean(cpu normalization)/mean(gpu normalization); massimo su tutti gli step e 10k-100k", lambda: max(spd_step(n, s) for n in [10000, 50000, 100000] for s in ["data_loading", "qc_filtering", "normalization", "hvg_selection", "pca", "neighbors", "leiden_0.5", "leiden_1.0", "leiden_1.5", "umap", "de_testing"]), "0 decimali")
add("R0349", "R3-004", "1.16", NE, "per_size.10000.NP1_ratio_warm (n_jobs 1 / n_jobs 100)", lambda: get(J(NE), "per_size/10000/NP1_ratio_warm"), "2 decimali")
add("R0349", "R3-004", "2.48", NE, "per_size.100000.NP1_ratio_warm", lambda: get(J(NE), "per_size/100000/NP1_ratio_warm"), "2 decimali")
add("R0349", "R3-004", "100", NE, "per_size.10000.calls_nj100[0][0] (n_jobs passato a pynndescent)", lambda: get(J(NE), "per_size/10000/calls_nj100")[0][0], "intero")
# E005 riga 223 (R0114, R0116, R0367, R0548)
for n, s in [(10000, "0.85"), (100000, "0.76")]:
    add("R0114", "R3-005", s, f"results/cpu_{n}_r{{1..5}}_results.json; results/gpu_{n}_r{{1..5}}_results.json", "mean(cpu data_loading)/mean(gpu data_loading)", (lambda n=n: spd_step(n, "data_loading")), "2 decimali")
for n, s in [(10000, "0.10"), (50000, "0.55"), (100000, "1.38")]:
    add("R0114", "R3-005", s, f"results/cpu_{n}_r{{1..5}}_results.json; results/gpu_{n}_r{{1..5}}_results.json", "mean(gpu data_loading)-mean(cpu data_loading) s", (lambda n=n: m("gpu", n, "timings/data_loading") - m("cpu", n, "timings/data_loading")), "2 decimali")
add("R0116", "R3-005", "0.36", G10, "mean(cpu leiden_0.5)/mean(gpu leiden_0.5) 10k", lambda: spd_step(10000, "leiden_0.5"), "2 decimali")
add("R0116", "R3-005", "1.70", "results/gpu_10000_r1_results.json", "timings.leiden_0.5 r1 s", lambda: get(J("results/gpu_10000_r1_results.json"), "timings/leiden_0.5"), "2 decimali")
add("R0116", "R3-005", "0.09", "results/gpu_10000_r{2..5}_results.json", "min timings.leiden_0.5 r2-5 s", lambda: min(reps("gpu", 10000, "timings/leiden_0.5")[1:]), "2 decimali")
add("R0116", "R3-005", "0.23", "results/gpu_10000_r{2..5}_results.json", "max timings.leiden_0.5 r2-5 s", lambda: max(reps("gpu", 10000, "timings/leiden_0.5")[1:]), "2 decimali")
add("R0116", "R3-005", "1.36", G10, "speedup leiden_1.0 10k", lambda: spd_step(10000, "leiden_1.0"), "2 decimali")
add("R0116", "R3-005", "1.60", G10, "speedup leiden_1.5 10k", lambda: spd_step(10000, "leiden_1.5"), "2 decimali")
add("R0116", "R3-005", "1.80", "results/cpu_50000_r{1..5}_results.json; results/gpu_50000_r{1..5}_results.json", "speedup leiden_0.5 50k", lambda: spd_step(50000, "leiden_0.5"), "2 decimali")
add("R0116", "R3-005", "3.58", "results/cpu_100000_r{1..5}_results.json; results/gpu_100000_r{1..5}_results.json", "speedup leiden_0.5 100k", lambda: spd_step(100000, "leiden_0.5"), "2 decimali")
add("R0367", "R3-005", "115.1", G10, "speedup normalization 10k, ripetizioni 2-5", lambda: spd_step(10000, "normalization", r="2_5"), "1 decimale")
add("R0367", "R3-005", "329", G10, "speedup normalization 10k, ripetizioni 1-5", lambda: spd_step(10000, "normalization"), "0 decimali")
add("R0367", "R3-005", "1.12", G10, "speedup leiden_0.5 10k, ripetizioni 2-5", lambda: spd_step(10000, "leiden_0.5", r="2_5"), "2 decimali")
add("R0367", "R3-005", "6", "results/cpu_{100000,500000,1300000}_r{1..5}_results.json; results/gpu_100000_r{1..5}_results.json; results/gpu{2,4,8}_{100000,500000,1300000}_r{1..5}_results.json", "max |speedup_r1-5/speedup_r2-5 - 1| x100 da 100k in su", max_change_100k_up, "0 decimali")
# E007 riga 227 (R0352)
for g, s in [("gpu2", "17.23"), ("gpu4", "16.99"), ("gpu8", "17.01")]:
    add("R0352", "R3-007", s, f"results/{g}_1300000_r{{1..5}}_results.json", "mean(timings.pca+timings.neighbors) s", (lambda g=g: pca_nb(g, 1300000)), "2 decimali")
for g, s in [("gpu2", "2.98"), ("gpu4", "2.97"), ("gpu8", "3.00")]:
    add("R0352", "R3-007", s, f"results/{g}_500000_r{{1..5}}_results.json", "mean(timings.pca+timings.neighbors) s", (lambda g=g: pca_nb(g, 500000)), "2 decimali")
for g, s in [("gpu2", "124.5"), ("gpu4", "125.0"), ("gpu8", "124.6")]:
    add("R0352", "R3-007", s, f"results/{g}_500000_r{{1..5}}_results.json", "mean(timings.total) s", (lambda g=g: m(g, 500000, "timings/total")), "1 decimale")
add("R0352", "R3-007", "435.2", "results/gpu8_1300000_r{1..5}_results.json", "mean(timings.total) s", lambda: m("gpu8", 1300000, "timings/total"), "1 decimale")
add("R0352", "R3-007", "493.3", "results/gpu2_1300000_r{1..5}_results.json", "mean(timings.total) s", lambda: m("gpu2", 1300000, "timings/total"), "1 decimale")
add("R0368", "R3-007", "12", "results/gpu{2,8}_1300000_r{1..5}_results.json", "100*(1 - mean gpu8 total / mean gpu2 total)", lambda: 100 * (1 - m("gpu8", 1300000, "timings/total") / m("gpu2", 1300000, "timings/total")), "0 decimali")
add("R0368", "R3-007", "149.0", "results/gpu2_1300000_r{1..5}_results.json", "mean(timings.data_loading) s", lambda: m("gpu2", 1300000, "timings/data_loading"), "1 decimale")
add("R0368", "R3-007", "90.6", "results/gpu8_1300000_r{1..5}_results.json", "mean(timings.data_loading) s", lambda: m("gpu8", 1300000, "timings/data_loading"), "1 decimale")
add("R0352", "R3-007", "78.6", "results/gpu8_1300000_r{1..5}_results.json", "mean(memory.detailed.pca_vram_before_gb - scale_vram_after_gb) GiB", lambda: pool_inc("gpu8", 1300000), "1 decimale")
add("R0352", "R3-007", "78.6", "results/gpu8_10000_r{1..5}_results.json", "mean(memory.detailed.pca_vram_before_gb - scale_vram_after_gb) GiB, 10k", lambda: pool_inc("gpu8", 10000), "1 decimale")
add("R0352", "R3-007", "49", "results/gpu{,2}_10000_r{1..5}_results.json", "100*(mean gpu2 total/mean gpu total - 1) 10k", lambda: 100 * (m("gpu2", 10000, "timings/total") / m("gpu", 10000, "timings/total") - 1), "0 decimali")
add("R0352", "R3-007", "82", "results/gpu{,2}_100000_r{1..5}_results.json", "100*(mean gpu2 total/mean gpu total - 1) 100k", lambda: 100 * (m("gpu2", 100000, "timings/total") / m("gpu", 100000, "timings/total") - 1), "0 decimali")
# E012 riga 240 (R0244, R0371; scelte CONC_11MARZO, JACCARD)
add("R0244", "R3-012", "11 March 2026", CC, "metadata.cpu_timestamp e gpu_timestamp (UTC)", lambda: get(J(CC), "metadata/cpu_timestamp")[:10], "nessun-controllo: data (2026-03-11, UTC)")
for r, s in [("0.5", "31"), ("1.0", "40"), ("1.5", "45")]:
    add("R0244", "R3-012", s, CC, f"cluster_concordance.leiden_{r}.n_clusters_cpu", (lambda r=r: get(J(CC), f"cluster_concordance/leiden_{r}/n_clusters_cpu")), "intero")
for r, s in [("0.5", "31"), ("1.0", "41"), ("1.5", "46")]:
    add("R0244", "R3-012", s, "results/cpu_10000_r{1..5}_results.json", f"results_summary.n_clusters_{r}, uguale in r1-5 (valore unico)", (lambda r=r: (lambda v: v[0] if len(set(v)) == 1 else -1)(reps("cpu", 10000, f"results_summary/n_clusters_{r}"))), "intero")
add("R0371", "R3-012", "0.9375", CC, "knn_concordance.max_jaccard (= median_jaccard)", lambda: get(J(CC), "knn_concordance/max_jaccard"), "4 decimali")
add("R0371", "R3-012", "15/16", CC, "knn_concordance.median_jaccard", lambda: get(J(CC), "knn_concordance/median_jaccard"), "nessun-controllo: frazione 15/16 = 0.9375")
add("R0371", "R3-012", "16", "results/cpu_10000_r1_knn.npz", "numero di indici per cella (moda), cella inclusa", lambda: knn_stats()["cpu_size"], "intero")
add("R0371", "R3-012", "15", "results/gpu_10000_r1_knn.npz", "numero di indici per cella (moda), cella inclusa", lambda: knn_stats()["gpu_size"], "intero")
add("R0371", "R3-012", "95.0", "results/cpu_10000_r1_knn.npz; results/gpu_10000_r1_knn.npz", "% di celle con vicini GPU (senza la cella) tutti fra i vicini CPU", lambda: knn_stats()["frac_contained_pct"], "1 decimale")
add("R0371", "R3-012", "no cell reaches 1", CC, "knn_concordance.fraction_perfect (0 = nessuna cella con Jaccard 1)", lambda: get(J(CC), "knn_concordance/fraction_perfect"), "nessun-controllo: 0.0 = nessuna cella a 1")
# E013 riga 242 (R0128, R0129, R0709)
add("R0128", "R3-013", "40", CC, "cluster_concordance.leiden_1.0.n_clusters_cpu (= n_clusters_gpu)", lambda: get(J(CC), "cluster_concordance/leiden_1.0/n_clusters_gpu") if get(J(CC), "cluster_concordance/leiden_1.0/n_clusters_cpu") == get(J(CC), "cluster_concordance/leiden_1.0/n_clusters_gpu") else -1, "intero")
add("R0128", "R3-013", "five", "results/{cpu,gpu}_10000_r{1..5}_results.json", "1 se cluster_labels_hash_* identici in r1-5 per CPU e GPU", identical_labels_10k, "nessun-controllo: 1 = etichette identiche nelle cinque ripetizioni")
add("R0128", "R3-013", "n_iterations=2", "scripts/benchmark_cpu.py", "sc.tl.leiden(..., flavor='igraph', n_iterations=2) righe 236-239", lambda: int(re.search(r"n_iterations=(\d+)", log_text("scripts/benchmark_cpu.py")).group(1)), "nessun-controllo: parametro del codice (valore 2)")
add("R0128", "R3-013", "100", "scripts/benchmark_gpu.py", "rsc.tl.leiden senza n_iterations: default 100 in rapids_singlecell 0.14.1 tools/_clustering.py:130 (wheel PyPI)", lambda: 100, "nessun-controllo: default di libreria letto nel sorgente del wheel 0.14.1, non nel repo")
add("R0129", "R3-013", "34", CC, "numero di per_pair.spearman_rho > 0.97", lambda: sum(1 for r in de_rhos() if r > 0.97), "intero")
add("R0129", "R3-013", "0.9995", CC, "mediana di de_concordance.per_pair.spearman_rho", lambda: statistics.median(de_rhos()), "4 decimali")
add("R0129", "R3-013", "two", CC, "coppie con rho piu' bassi: cpu17_gpu24 (-0.157, overlap 0) e cpu38_gpu5 (0.448); conteggio con overlap 0", n_zero_overlap_low_pairs, "nessun-controllo: 1 = una delle due coppie piu' basse ha overlap_fraction 0")
# E014 riga 244 (R0498, CONC_INTERCAMB)
add("R0498", "R3-014", "50,000", "results/cpu_{50000,100000,500000,1300000}_r{1..5}_results.json; results/gpu_{50000,100000}_r{1..5}_results.json; results/gpu{2,4,8}_{500000,1300000}_r{1..5}_results.json", "1 se da 50k in su le etichette GPU variano fra ripetizioni (>=1 risoluzione) e le CPU no", gpu_labels_vary_from_50k, "nessun-controllo: 1 = vero")
add("R0498", "R3-014", "0.5", "manuscript/revisione_n2/script_e_calcoli.zip", "tracks/E_work/pdf_txt/3731599.3767378.txt righe 27-28 'Adjusted Rand Index approximately 0.5'", lambda: 0.5, "nessun-controllo: valore letto nella fonte bibliografica Gardner2025")
add("R0498", "R3-014", "1.3-million", "manuscript/revisione_n2/script_e_calcoli.zip", "tracks/E_work/pdf_txt/3731599.3767378.txt riga 23 '1.3-million-cell dataset'", lambda: 1.3, "nessun-controllo: valore letto nella fonte bibliografica Gardner2025")
# E015 riga 250 (R0680, R0641, R0252)
add("R0680", "R3-015", "0.92", "results/cpu_{10000,50000,100000,500000,1300000}_r{1..5}_results.json", "OLS log-log di mean(memory.peak_ram_gb) su n", ram_slope, "2 decimali")
add("R0680", "R3-015", "1.35", "results/cpu_{500000,1300000}_r{1..5}_results.json", "pendenza log-log fra 500k e 1.3M", ram_local, "2 decimali")
add("R0252", "R3-015", "1.2", "results/cpu_10000_r{1..5}_results.json", "mean(memory.peak_ram_gb) GiB", lambda: m("cpu", 10000, "memory/peak_ram_gb"), "1 decimale")
add("R0252", "R3-015", "107.4", C13, "mean(memory.peak_ram_gb) GiB", lambda: m("cpu", 1300000, "memory/peak_ram_gb"), "1 decimale")
add("R0252", "R3-015", "9.7", "results/cpu_1300000_r1_results.json", "results_summary.n_cells_after_qc x 2000 x 4 B / 1024^3", lambda: get(J("results/cpu_1300000_r1_results.json"), "results_summary/n_cells_after_qc") * 2000 * 4 / 1024 ** 3, "1 decimale")
add("R0252", "R3-015", "40.7", "results/gpu_{10000,50000,100000}_r{1..5}_results.json", "mean(memory.peak_vram_gb) GiB (10k; uguale a 50k e 100k)", lambda: m("gpu", 10000, "memory/peak_vram_gb"), "1 decimale")
add("R0641", "R3-015", "134.2", "results/gpu8_1300000_r{1..5}_results.json", "mean(memory.peak_vram_gb) GiB", lambda: m("gpu8", 1300000, "memory/peak_vram_gb"), "1 decimale")
# E017 riga 260 (R0142, R0143, R0243)
add("R0142", "R3-017", "119", MP, "timings.total / 60 min", lambda: mp("timings/total") / 60, "0 decimali")
add("R0243", "R3-017", "3,436,470", MP, "metadata.n_cells_source_file", lambda: mp("metadata/n_cells_source_file"), "intero")
for r, s in [("0.5", "135,710"), ("1.0", "142,959"), ("1.5", "147,154")]:
    add("R0243", "R3-017", s, MP, f"results_summary.n_clusters_{r}", (lambda r=r: mp(f"results_summary/n_clusters_{r}")), "intero")
M34 = "results/maxpower_3400000_8gpu_results.json"
for r, s in [("0.5", "58"), ("1.0", "66"), ("1.5", "87")]:
    add("R0243", "R3-017", s, M34, f"results_summary.n_clusters_{r}", (lambda r=r: mp(f"results_summary/n_clusters_{r}", M34)), "intero")
add("R0243", "R3-017", "3,400,000", M34, "metadata.target_cells", lambda: mp("metadata/target_cells", M34), "intero")
L12 = "logs/slurm-maxpower_8gpu_16531.err"
add("R0142", "R3-017", "12.0", "logs/slurm-maxpower_8gpu_16531.out; " + L12, "'target=12,000,000 cells' e 'failed with exit code 1' dopo TimeoutError in run_pipeline (chiusura del cluster Dask)", lambda: (log_float(L12, r"exit code 1 for target=([\d,]+) cells") / 1e6) if "TimeoutError" in log_text(L12) else -1, "1 decimale")
L137a = "logs/slurm-maxpower_8gpu_16463.err"
L137b = "logs/slurm-maxpower_8gpu_16662.err"
add("R0143", "R3-017", "13.7", L137a + "; " + L137b, "'exit code -9 for target=13,745,880 cells' in entrambi i log (Leiden 16463, KMeans 16662)", lambda: log_float(L137a, r"exit code -9 for target=([\d,]+) cells") / 1e6 if log_float(L137b, r"exit code -9 for target=([\d,]+) cells") == log_float(L137a, r"exit code -9 for target=([\d,]+) cells") else -1, "1 decimale")
add("R0143", "R3-017", "9", L137a + "; " + L137b, "codice di uscita del sottoprocesso -9 (SIGKILL) in entrambi i log", lambda: -int(re.search(r"exit code (-\d+) for target=13,745,880", log_text(L137b)).group(1)), "intero")
# E018 riga 262 (R0145, R0148, R0151, R0152, R0674, R0697)
add("R0697", "R3-018", "535", MP, "memory.peak_ram_gb GiB", lambda: mp("memory/peak_ram_gb"), "0 decimali")
add("R0697", "R3-018", "48.8", MP, "memory.peak_vram_gb GiB", lambda: mp("memory/peak_vram_gb"), "1 decimale")
add("R0697", "R3-018", "7.6", MP, "100 * memory.peak_vram_gb / 640 (8 x 80 GiB nominali)", lambda: 100 * mp("memory/peak_vram_gb") / 640, "1 decimale")
add("R0148", "R3-018", "124", MP, MPD + "data_loading_ram_after_gb GiB", lambda: mp(MPD + "data_loading_ram_after_gb"), "0 decimali")
add("R0148", "R3-018", "426", MP, MPD + "qc_filtering_ram_before_gb GiB", lambda: mp(MPD + "qc_filtering_ram_before_gb"), "0 decimali")
add("R0148", "R3-018", "302", MP, "qc_filtering_ram_before_gb - data_loading_ram_after_gb GiB", lambda: mp(MPD + "qc_filtering_ram_before_gb") - mp(MPD + "data_loading_ram_after_gb"), "0 decimali")
add("R0148", "R3-018", "3.4M", MP, "metadata.n_cells_source_file / 1e6", lambda: mp("metadata/n_cells_source_file") / 1e6, "1 decimale")
add("R0148", "R3-018", "0.1", MP, "max(normalization, hvg_selection) ram_after - ram_before GiB (sotto 0.1)", lambda: max(mp(MPD + "normalization_ram_after_gb") - mp(MPD + "normalization_ram_before_gb"), mp(MPD + "hvg_selection_ram_after_gb") - mp(MPD + "hvg_selection_ram_before_gb")), "nessun-controllo: soglia, il valore letto deve essere < 0.1")
add("R0151", "R3-018", "0.48", MP, "leiden_1.5_ram_after_gb - leiden_0.5_ram_before_gb GiB", lambda: mp(MPD + "leiden_1.5_ram_after_gb") - mp(MPD + "leiden_0.5_ram_before_gb"), "2 decimali")
add("R0151", "R3-018", "20", MP, "leiden_0.5_vram_before_gb - neighbors_vram_after_gb GiB", lambda: mp(MPD + "leiden_0.5_vram_before_gb") - mp(MPD + "neighbors_vram_after_gb"), "0 decimali")
# E019 riga 264 (R0153)
L_KM = "logs/slurm-maxpower_8gpu_16662.out"
add("R0153", "R3-019", "3.4M, 6.9M and 10.3M", L_KM, "'>>> SUCCESS at' 3,436,470 / 6,872,940 / 10,309,410 con 'Clustering: kmeans'", lambda: sum(1 for t in ["3,436,470", "6,872,940", "10,309,410"] if (">>> SUCCESS at " + t) in log_text(L_KM)) if "Clustering: kmeans" in log_text(L_KM) else -1, "nessun-controllo: 3 = tre successi KMeans nel log")
# E020 riga 265 (R0154)
L14 = "logs/slurm-memopt_16683.out"
add("R0154", "R3-020", "14M", L14, "'Target cells: 14,000,000' e 'Exit code: 137' dopo 'HVG selection (2000 genes)...'", lambda: (log_float(L14, r"Target cells: ([\d,]+)") / 1e6) if re.search(r"HVG selection \(2000 genes\)\.\.\.\s*\nExit code: 137", log_text(L14)) else -1, "0 decimali")
# E021 riga 267 (R0156)
MC = "results/maxpower_chunked_12000000_8gpu_results.json"
add("R0156", "R3-021", "862", MC, "memory.peak_ram_gb GiB", lambda: mp("memory/peak_ram_gb", MC), "0 decimali")
add("R0156", "R3-021", "10", MC, "memory.peak_vram_gb GiB", lambda: mp("memory/peak_vram_gb", MC), "0 decimali")
add("R0156", "R3-021", "131.5", MC, "timings.total / 60 min", lambda: mp("timings/total", MC) / 60, "1 decimale")
L15 = "logs/slurm-chunked_single_16825.out"
add("R0156", "R3-021", "15.0", L15, "'CHUNKED SINGLE TARGET: 15000000' e 'Exit code: 137' dopo 'Converting to CSC'", lambda: (log_float(L15, r"CHUNKED SINGLE TARGET: (\d+)") / 1e6) if re.search(r"Converting to CSC for column slicing\.\.\.\s*\n\s*\nExit code: 137", log_text(L15)) else -1, "1 decimale")
# E022 riga 269 (T5_PUNTI)
add("R0161", "R3-022", "16", "results/maxpower_*_8gpu_results.json", "numero di JSON maxpower completati (escluso chunked e limit)", lambda: len(maxpower_completed_sizes()), "intero")
add("R0161", "R3-022", "1.7M", "results/maxpower_*_8gpu_results.json", "min metadata.target_cells / 1e6", lambda: min(maxpower_completed_sizes()) / 1e6, "1 decimale")
add("R0161", "R3-022", "11.9M", "results/maxpower_*_8gpu_results.json", "max metadata.target_cells / 1e6", lambda: max(maxpower_completed_sizes()) / 1e6, "1 decimale")
add("R0161", "R3-022", "3.4M", MP, "metadata.n_cells_source_file / 1e6 (oltre questa dimensione l'input e' replicato)", lambda: mp("metadata/n_cells_source_file") / 1e6, "1 decimale")
# E024 riga 275 (R0161)
add("R0161", "R3-024", "91", "results/maxpower_10309410_8gpu_results.json", "timings.total / 60 min", lambda: mp("timings/total", "results/maxpower_10309410_8gpu_results.json") / 60, "0 decimali")
# E027 riga 281 (R0166, KMEANS)
MK = "results/maxpower_10309410_8gpu_results.json"
ML = "results/maxpower_10200000_8gpu_results.json"
add("R0166", "R3-027", "465.4", MK, "memory.peak_ram_gb GiB (KMeans)", lambda: mp("memory/peak_ram_gb", MK), "1 decimale")
add("R0166", "R3-027", "10.31M", MK, "metadata.target_cells / 1e6", lambda: mp("metadata/target_cells", MK) / 1e6, "2 decimali")
add("R0166", "R3-027", "460.5", ML, "memory.peak_ram_gb GiB (Leiden)", lambda: mp("memory/peak_ram_gb", ML), "1 decimale")
add("R0166", "R3-027", "10.2M", ML, "metadata.target_cells / 1e6", lambda: mp("metadata/target_cells", ML) / 1e6, "1 decimale")
add("R0166", "R3-027", "91.5", MK, "timings.total / 60 min", lambda: mp("timings/total", MK) / 60, "1 decimale")
add("R0166", "R3-027", "69.2", ML, "timings.total / 60 min", lambda: mp("timings/total", ML) / 60, "1 decimale")
add("R0166", "R3-027", "3,156", MK, "timings.qc_filtering s", lambda: mp("timings/qc_filtering", MK), "0 decimali")
add("R0166", "R3-027", "2,218", ML, "timings.qc_filtering s", lambda: mp("timings/qc_filtering", ML), "0 decimali")
# Table 6 (T6)
add("R0167", "R3-028", "11.9M", MP, "metadata.target_cells / 1e6", lambda: mp("metadata/target_cells") / 1e6, "1 decimale")
add("R0167", "R3-028", "535", MP, "memory.peak_ram_gb GiB", lambda: mp("memory/peak_ram_gb"), "0 decimali")
add("R0171", "R3-031", "426", MP, MPD + "qc_filtering_ram_before_gb GiB", lambda: mp(MPD + "qc_filtering_ram_before_gb"), "0 decimali")
add("R0170", "R3-032", "89", MP, "results_summary.n_cells_after_qc x 2000 x 4 B / 1024^3", dense_hvg_gib, "0 decimali")
add("R0173", "R3-033", "20", MP, "peak_ram_gb - qc_filtering_ram_before_gb - densa HVG (P4: 19.79 GiB attesi)", residual_gib, "0 decimali")
add("R0177", "R3-035", "+426", MP, MPD + "qc_filtering_ram_before_gb GiB (una seconda copia della matrice sparsa)", lambda: mp(MPD + "qc_filtering_ram_before_gb"), "0 decimali")
add("R0178", "R3-036", "81.7", MP, "scale_ram_after_gb - scale_ram_before_gb GiB", lambda: mp(MPD + "scale_ram_after_gb") - mp(MPD + "scale_ram_before_gb"), "1 decimale")
add("R0178", "R3-036", "+89", MP, "densa HVG n_cells_after_qc x 2000 x 4 B / 1024^3", dense_hvg_gib, "0 decimali")
add("R0182", "R3-038", "< 1", MP, "leiden_1.5_ram_after_gb - leiden_0.5_ram_before_gb GiB (< 1)", lambda: mp(MPD + "leiden_1.5_ram_after_gb") - mp(MPD + "leiden_0.5_ram_before_gb"), "nessun-controllo: soglia, il valore letto deve essere < 1")
add("R0167", "R3-039", "2,016", "logs/slurm-maxpower_8gpu_16591.out", "'System RAM: 2016 GB' (psutil total / 1024^3, benchmark_maxpower.py riga 937)", lambda: log_float("logs/slurm-maxpower_8gpu_16591.out", r"System RAM: (\d+) GB"), "intero")
# E040 riga 304 (R0185, R0180)
add("R0185", "R3-040", "629.0", L14, "'RAM: 629.0 / 2016 GB' dopo la costruzione del dataset (rss / 1024^3, test_memopt.py riga 70)", lambda: log_float(L14, r"Done: 14,000,000 x 53,384 \(\d+s\)\n\[MEMOPT \+\s*[\d.]+s\] RAM: ([\d.]+) /"), "1 decimale")
add("R0185", "R3-040", "14M", L14, "'Target cells: 14,000,000'", lambda: log_float(L14, r"Target cells: ([\d,]+)") / 1e6, "0 decimali")
# Table 7 e riga 321 (R0191, R0194, R0195, R0196, R0197)
add("R0191", "R3-043", "127", "results/de_benchmark_pseudobulk.json", "results.pseudobulk.time s", lambda: de_t("pseudobulk"), "0 decimali")
add("R0191", "R3-043", "43.9", "results/de_benchmark_ttest_cpu.json; results/de_benchmark_pseudobulk.json", "ttest_cpu.time / pseudobulk.time", lambda: de_t("ttest_cpu") / de_t("pseudobulk"), "1 decimale")
add("R0194", "R3-044", "1,655", "results/de_benchmark_ttest_scatter.json", "results.ttest_scatter.time s", lambda: de_t("ttest_scatter"), "0 decimali")
add("R0195", "R3-045", "1,649", "results/de_benchmark_ttest_chunk.json", "results.ttest_chunk.time s", lambda: de_t("ttest_chunk"), "0 decimali")
add("R0196", "R3-046", "2,431", "results/de_benchmark_pseudobulk.json", "results.pseudobulk.n_pseudobulk_samples", lambda: get(J(DE.format("pseudobulk")), "results/pseudobulk/n_pseudobulk_samples"), "intero")
add("R0196", "R3-046", "30", "results/de_benchmark_pseudobulk.json", "n_pseudobulk_samples / n_clusters", lambda: get(J(DE.format("pseudobulk")), "results/pseudobulk/n_pseudobulk_samples") / get(J(DE.format("pseudobulk")), "results/pseudobulk/n_clusters"), "0 decimali")
add("R0196", "R3-046", "127", "results/de_benchmark_pseudobulk.json", "results.pseudobulk.time s", lambda: de_t("pseudobulk"), "0 decimali")
add("R0196", "R3-046", "2.1", "results/de_benchmark_pseudobulk.json", "results.pseudobulk.time / 60 min", lambda: de_t("pseudobulk") / 60, "1 decimale")
add("R0196", "R3-046", "43.9", "results/de_benchmark_ttest_cpu.json; results/de_benchmark_pseudobulk.json", "ttest_cpu.time / pseudobulk.time", lambda: de_t("ttest_cpu") / de_t("pseudobulk"), "1 decimale")
add("R0196", "R3-046", "5,598", "results/de_benchmark_ttest_cpu.json", "results.ttest_cpu.time s", lambda: de_t("ttest_cpu"), "0 decimali")
add("R0196", "R3-046", "93", "results/de_benchmark_ttest_cpu.json", "results.ttest_cpu.time / 60 min", lambda: de_t("ttest_cpu") / 60, "0 decimali")
add("R0197", "R3-046", "826", "results/de_benchmark_wilcoxon_scatter.json", "results.wilcoxon_scatter.time s", lambda: de_t("wilcoxon_scatter"), "0 decimali")
add("R0197", "R3-046", "1,655", "results/de_benchmark_ttest_scatter.json", "results.ttest_scatter.time s", lambda: de_t("ttest_scatter"), "0 decimali")


def main():
    out = {}
    for rid, voce, edit, scritto, file, chiave, fn, arr in R:
        v = fn()
        out[rid] = v
    if "--meta" in sys.argv:
        meta = [dict(ricevuta_id=rid, voce=voce, edit_id=edit, valore_scritto=scritto, file=file, chiave=chiave, valore_letto=out[rid], arrotondamento=arr)
                for rid, voce, edit, scritto, file, chiave, fn, arr in R]
        print(json.dumps(meta, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
