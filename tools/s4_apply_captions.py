#!/usr/bin/env python3
"""Apply the caption edits of step S4 to manuscript/full_paper_LNBI.md.

Each edit names its target by a unique anchor: the caption line is found by
its opening ("![**Figure n.**") or by an exact sentence, and must occur
exactly once; the old text is recorded. Removes Figures 3 and 4 (decision
D-02), rewrites the captions of Figures 1, 2, 5, 6 and the Table 4 sentence
on repeats, and appends one row per S4 plan entry to IMPL_diario.csv.

Usage: python3 -B tools/s4_apply_captions.py [--dry-run]
"""
import argparse, csv, hashlib, json, sys

MS = "manuscript/full_paper_LNBI.md"
DIARY = "manuscript/revisione_n2/piano/IMPL_diario.csv"
LEDGER = "manuscript/revisione_n2/piano/ledger.csv"
OUT = "results_v2/S4/caption_edits_applied.json"
DATE = "2026-11-04"

F1 = ("![**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy "
      "(100 logical CPUs) at 10k, 50k, and 100k cells: ratio of mean times, mean of five repeats (first repeat included). "
      "Values > 1 indicate GPU is faster; the colour scale is logarithmic and centred on 1. Normalisation achieves up to "
      "329x speedup; data loading shows a modest CPU advantage (0.76-0.85x). The PCA row includes scaling (`sc.pp.scale`), "
      "which is timed together with PCA.](../figures/fig1_speedup_heatmap.png)")
F2 = ("![**Figure 2.** Step-level wall time decomposition for CPU vs single-GPU at 10k, 50k, and 100k cells, mean of five "
      "repeats (first repeat included); the CPU and GPU panels have separate time axes. On CPU, DE testing and UMAP dominate; "
      "on GPU, the longest step, DE testing at 100k cells, takes 6.4 s on average. CPU neighbour search ran on one Numba "
      "thread, the Scanpy default (see Methods).](../figures/fig5_timing_breakdown.png)")
F5 = ("![**Figure 5.** Concordance between CPU and GPU pipelines on 10,000 cells, from the separate concordance run (see text). "
      "Left: ARI and NMI for Leiden clustering at three resolutions. Right: HVG Jaccard (1.000), PCA Spearman |rho| (1.000), "
      "kNN Jaccard (0.930) and mean Spearman rho of DE log-fold-changes over 40 matched cluster pairs (0.946). Both panels "
      "share the vertical axis. kNN Jaccard is bounded at 0.9375 by construction (see text).](../figures/fig3_concordance.png)")
F6 = ("![**Figure 6.** Peak memory usage across dataset sizes, mean of five repeats (first repeat included); error bars: SD. "
      "Left: CPU RAM; right: aggregate GPU VRAM summed over the allocated devices (for 2, 4 and 8 GPUs dominated by the RMM "
      "pools pre-allocated by each Dask worker). CPU RAM grows roughly linearly; GPU VRAM is approximately constant for "
      "single-GPU runs due to RMM pool pre-allocation. All repeats of a configuration ran in one process; in the multi-GPU "
      "runs VRAM grew from the first to later repeats.](../figures/fig4_memory_profile.png)")
T4_OLD = "Times are mean +/- SD over five repeats."
T4_NEW = "Times are mean +/- SD over five repeats (first repeat included)."

ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
text = open(MS, encoding="utf-8").read()
md5_before = hashlib.md5(text.encode()).hexdigest()
lines = text.split("\n")

def hits_of(prefix):
    return [i for i, l in enumerate(lines) if l.startswith(prefix)]

edits = []
for eid, prefix, new, ids in (("E1", "![**Figure 1.**", F1, "R0375;R0377;R0378;R0379;R0383"),
                              ("E2", "![**Figure 2.**", F2, "R0351;R0113;R0383;D-16"),
                              ("E5", "![**Figure 5.**", F5, "R0376"),
                              ("E6", "![**Figure 6.**", F6, "R0359;R0139;R0373;R0383")):
    h = hits_of(prefix)
    edits.append({"edit": eid, "anchor": prefix, "count_before": len(h), "line": h[0] + 1 if h else None,
                  "old": lines[h[0]] if len(h) == 1 else None, "new": new, "entries": ids})
    if len(h) == 1:
        lines[h[0]] = new
for eid, prefix, ids in (("E3", "![**Figure 3.**", "R0354;R0122"), ("E4", "![**Figure 4.**", "R0355;R0369")):
    h = hits_of(prefix)
    edits.append({"edit": eid, "anchor": prefix, "count_before": len(h), "line": h[0] + 1 if h else None,
                  "old": lines[h[0]] if len(h) == 1 else None, "new": "(line removed with the blank line before it)", "entries": ids})
    if len(h) == 1:
        i = h[0]
        assert lines[i - 1] == "", "expected a blank line before the figure"
        del lines[i - 1:i + 1]
text2 = "\n".join(lines)
n_t4 = text2.count(T4_OLD)
edits.append({"edit": "E7", "anchor": T4_OLD, "count_before": n_t4, "line": None, "old": T4_OLD, "new": T4_NEW, "entries": "R0383"})
if n_t4 == 1:
    text2 = text2.replace(T4_OLD, T4_NEW)
ok = all(e["count_before"] == 1 for e in edits)
md5_after = hashlib.md5(text2.encode()).hexdigest()
print(json.dumps({"all_anchors_unique": ok, "md5_before": md5_before, "md5_after": md5_after,
                  "counts": {e["edit"]: e["count_before"] for e in edits}}))
if not ok or a.dry_run:
    sys.exit(0 if ok else 1)
open(MS, "w", encoding="utf-8").write(text2)
json.dump({"manuscript": MS, "md5_before": md5_before, "md5_after": md5_after, "all_anchors_unique": ok, "edits": edits},
          open(OUT, "w"), indent=1, ensure_ascii=False)

ledger = {r["id"]: r for r in csv.DictReader(open(LEDGER, encoding="utf-8")) if r["step"] == "S4"}
SRC = "scripts/generate_figures.py; results/{cpu,gpu,gpu2,gpu4,gpu8}_*_r*_results.json; results_v2/S4/figure_values.csv"
rows = {
 "R0351": ("fatto", "Fig. 2: 'DE testing and UMAP dominate'; 'the longest step, DE testing at 100k cells, takes 6.4 s on average'; pannelli CPU e GPU con assi propri", SRC,
           "Al posto di 'less than 7 s' il valore misurato (previsione P2 di S4 indeterminata: media + 2 SD = 7,66 s a 100.000 cellule); riga in arbitrati.csv. Assorbita chiusa: R0113."),
 "R0113": ("fatto", "come R0351", SRC, "Assorbita: chiusa con R0351."),
 "R0354": ("fatto", "Figure 3 e didascalia tolte; fig2_scaling_plot.png spostata in figures/retired/", "docs/decisions/D-02.md",
           "Funzione fig_scaling_plot tolta da scripts/generate_figures.py. Assorbita chiusa: R0122."),
 "R0122": ("fatto", "come R0354", "docs/decisions/D-02.md", "Assorbita: chiusa con R0354."),
 "R0355": ("fatto", "Figure 4 e didascalia tolte; fig6_multigpu_breakdown.png spostata in figures/retired/", "docs/decisions/D-02.md",
           "Funzione fig_multigpu_breakdown tolta da scripts/generate_figures.py. Assorbita chiusa: R0369."),
 "R0369": ("fatto", "come R0355", "docs/decisions/D-02.md", "Assorbita: chiusa con R0355."),
 "R0359": ("fatto", "Fig. 6: 'aggregate GPU VRAM summed over the allocated devices (...)'; 'roughly linearly'; linea 80 GB tolta; tick 1.3M", SRC + "; scripts/benchmark_multigpu.py",
           "Assorbita chiusa: R0139."),
 "R0139": ("fatto", "come R0359", SRC, "Assorbita: chiusa con R0359."),
 "R0373": ("fatto", "Fig. 6: barre SD sulle 5 ripetizioni; marcatori e tratteggi diversi per 2 e 4 GPU, punti sfalsati; 'in the multi-GPU runs VRAM grew from the first to later repeats'", SRC,
           "Frase ristretta ai run multi-GPU: con 1 GPU la ripetizione 1 ha piu' VRAM delle altre (40,93 contro 40,64 GiB); riga in arbitrati.csv."),
 "R0375": ("fatto", "Fig. 1: scala log centrata su 1 (tick 0.5, 1, 10, 100), valori nelle celle; '100 logical CPUs'; 'The PCA row includes scaling (sc.pp.scale), which is timed together with PCA.'", SRC,
           "'values include the first repeat' reso con la dicitura di R0383."),
 "R0376": ("fatto", "Fig. 5: dot plot su asse comune 0.80-1.01, DE logFC rho 0.946, tetto 0.9375 annotato; tolto 'near-identical biological outputs'", "results/concordance_10000_r1.json",
           "La dicitura di R0383 non si applica: concordanza da una sola coppia di run (Methods)."),
 "R0377": ("fatto", "Fig. 1, 2, 5, 6 fra 8,4 e 12,2 cm di larghezza, testo di almeno 7 pt alla dimensione di stampa", "results_v2/S4/s4_check.json (G3)",
           "Pannello legenda vuoto di Fig. 2 tolto. Figure 7-9 a S5."),
 "R0378": ("fatto", "PDF vettoriali figures/fig1_speedup_heatmap.pdf, fig5_timing_breakdown.pdf, fig3_concordance.pdf, fig4_memory_profile.pdf; PNG a 800 dpi come anteprima", "results_v2/S4/s4_check.json (G3)",
           "Gli includegraphics passano ai PDF in S7, a dimensione naturale."),
 "R0379": ("fatto", "palette e marcatori leggibili in scala di grigi", "results_v2/S4/s4_check.json (G4); results_v2/S4/greyscale_montage.png", ""),
 "R0383": ("fatto", "'mean of five repeats (first repeat included)' nelle didascalie di Fig. 1, 2, 6; 'Times are mean +/- SD over five repeats (first repeat included).' in Table 4", "docs/decisions/D-15.md",
           "Fig. 5: non applicabile (una sola coppia di run)."),
 "R0380": ("rimandato", "", "", "Assorbita in R0735 (S7): rinomina dei file e rinumerazione delle figure."),
}
missing, extra = set(ledger) - set(rows), set(rows) - set(ledger)
assert not missing and not extra, (missing, extra)
existing = [r["id"] for r in csv.DictReader(open(DIARY, encoding="utf-8"))]
assert not set(rows) & set(existing), "S4 rows already in the diary"
with open(DIARY, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    for i in sorted(rows):
        esito, val, src, note = rows[i]
        w.writerow([i, ledger[i]["level"], esito, val, ledger[i]["decision"] or "CONV", src, ledger[i]["line"], DATE, note])
print(f"diary: {len(rows)} rows appended")
