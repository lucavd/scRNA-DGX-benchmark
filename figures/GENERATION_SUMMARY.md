# Spatial figures (Figures 7, 8, 9): how they are generated

Step S5 of the LNBI chapter, 4 November 2026. Supersedes the summary of 7 April 2026 (March runs), now in `figures/retired/GENERATION_SUMMARY_2026-04-07.md`.

Command, from the repository root (figure environment of `scripts/requirements_figures.txt`):

    python scripts/generate_spatial_figures.py --results-dir SPATIAL/results_v2 --output-dir figures --values-dir results_v2/S5

Inputs (step S1, read only): `SPATIAL/results_v2/s1_step_stats.csv`, `s1_speedups.csv`, `s1_extra_numbers.json`, `cooc_check/cooc_check_eval.json`, `concordance_reference/spatial_concordance_<platform>.json`. Input md5 in `results_v2/S5/figure_inputs_md5.tsv`; every drawn value in `results_v2/S5/figure_values.csv`, re-checked by `tools/s5_check.py`.

| file | figure | content |
|---|---|---|
| `fig7_spatial_speedup.pdf` | 7 | total wall time, CPU reference (DGX node, 100 CPUs) and GPU (RTX 4090), mean and SD of 5 repeats; Visium HD 8 um totals include co-occurrence, dashed line without it |
| `fig8_spatial_perstep.pdf` | 8 | per-step speedup on Visium HD 8 um, 95% bootstrap interval; co-occurrence from the separate check with rapids-singlecell 0.15.1 |
| `fig9_spatial_concordance.pdf` | 9 | CPU-GPU concordance (Spearman rho, SVG Jaccard, ARI, NMI), mean and range over 5 repeat pairs |

Print settings, colours and markers come from `scripts/generate_figures.py`: width at most 12.2 cm, text at least 7 pt, vector PDF with embedded fonts, PNG previews at 800 dpi. The PNG files are previews; the chapter includes the PDFs.
