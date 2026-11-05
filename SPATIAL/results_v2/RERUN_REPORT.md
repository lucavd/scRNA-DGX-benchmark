# Rerun del benchmark spatial: report (step S1)

Generato da `SPATIAL/scripts/s1_rerun_report.py` dai file di `SPATIAL/results_v2/`. Tutti i numeri sono in `s1_evaluation.json`, `s1_step_stats.csv` e `s1_speedups.csv`.

## Esito dei controlli

- G1: superato
- G2: superato
- G3: superato
- G4: superato
- G5: superato

## Previsioni

- P1: `{"dgx_cpu": {"times": [102.9906, 102.8054, 103.5889, 103.3106, 103.5277], "max_over_min": 1.0076211949955935, "esito": "confermata"}, "server_cpu": {"times": [72.352, 72.2882, 72.206, 72.1566, 72.149], "max_over_min": 1.0028136218104202, "esito": "confermata"}}`
- P2: `{"threads_after_nhood": [1, 1], "n_cpus": 100, "esito": "confermata"}`
- P3: `{"visium": {"new_sums": [4.8199, 4.8464, 4.7761, 4.8519, 4.7692], "march_r1": 5.1135, "ratio": 0.9411753202307616, "ci": [0.9351911606531729, 0.9471594798083502], "rel2sd_new": 0.01603569637641269, "esito": "confermata"}, "visium_hd_square_008um": {"new_sums": [8.4175, 8.3808, 8.5513, 9.1425, 8.363299999999999], "march_r1": 8.2547, "ratio": 1.038327255987498, "ci": [1.0153173343670876, 1.0743479472300628], "rel2sd_new": 0.07649569672571202, "esito": "confermata"}, "visium_hd_square_002um": {"new_sums": [15.293700000000001, 16.1714, 16.6725, 15.0779, 15.3535], "march_r1": 15.0947, "ratio": 1.04`
- P3b_spatial_neighbors: `{"visium": {"ratio": 0.9694850603941512, "ci": [0.9385789036138685, 1.0281187344124405], "march_mean_1_5": 0.40898, "esito": "confermata"}, "visium_hd_square_008um": {"ratio": 0.9835650814187598, "ci": [0.9717821147895764, 0.9953480480479433], "march_mean_1_5": 57.28778, "esito": "confermata"}, "visium_hd_square_002um": {"ratio": 1.007411655630776, "ci": [1.0015035560900565, 1.014073895584081], "march_mean_1_5": 55.02954, "esito": "confermata"}}`
- P4: `{"visium": {"ratio": 0.9702891632428402, "ci": [0.9652832812307134, 0.97802218286886], "march_r1_total": 39.6973, "rel2sd_new": 0.01723742705963063, "esito": "confermata"}, "visium_hd_square_008um": {"ratio": 1.0558432545672973, "ci": [1.0411272189030276, 1.0703547046055544], "march_r1_total": 584.5963, "rel2sd_new": 0.03675965488146363, "esito": "confermata"}, "visium_hd_square_002um": {"ratio": 1.0220097194352076, "ci": [1.0023480088423302, 1.0416714300280854], "march_r1_total": 1010.141, "rel2sd_new": 0.05058884793986008, "esito": "confermata"}}`
- P5: `{"visium": {"server_over_dgx_cpu_total": 1.136794827827403, "ci": [1.1109637758860058, 1.1648447047750572], "esito": "smentita"}, "visium_hd_square_008um": {"server_over_dgx_cpu_total": 0.8584355924422208, "ci": [0.8458957224866712, 0.8705888071389724], "esito": "smentita"}, "visium_hd_square_002um": {"server_over_dgx_cpu_total": 0.9008042996499811, "ci": [0.865433246725768, 0.9322520881629157], "esito": "indeterminata"}}`
- P6: `{"speedup": 7.798128790848107, "ci": [7.7513585081005, 7.852369768712381], "esito": "smentita"}`

## Visium v1

Tempi in secondi: media (SD) sulle ripetizioni 1-5 e 2-5.

| step | CPU reference, DGX poddgx02 (100 CPU) 1-5 | 2-5 | GPU, RTX 4090 workstation 1-5 | 2-5 | CPU control, workstation (128 threads) 1-5 | 2-5 |
|---|---|---|---|---|---|---|
| total | 33.88 (1.00) | 33.86 (1.15) | 23.96 (0.20) | 23.90 (0.17) | 38.52 (0.33) | 38.51 (0.38) |
| co_occurrence | 3.40 (0.01) | 3.40 (0.01) | 1.49 (0.09) | 1.45 (0.01) | 8.05 (0.04) | 8.05 (0.03) |
| nhood_enrichment | 1.12 (0.00) | 1.12 (0.00) | 1.68 (0.01) | 1.68 (0.01) | 1.38 (0.01) | 1.37 (0.00) |
| spatial_autocorr_moran | 1.65 (0.03) | 1.66 (0.03) | 3.25 (0.02) | 3.24 (0.02) | 1.59 (0.02) | 1.58 (0.02) |
| spatial_autocorr_geary | 1.41 (0.01) | 1.42 (0.01) | 0.22 (0.01) | 0.21 (0.00) | 1.62 (0.01) | 1.62 (0.01) |
| spatial_neighbors | 0.31 (0.00) | 0.31 (0.00) | 0.40 (0.03) | 0.40 (0.03) | 0.38 (0.00) | 0.38 (0.00) |
| pca | 0.46 (0.01) | 0.46 (0.01) | 0.68 (0.00) | 0.68 (0.00) | 0.65 (0.31) | 0.70 (0.33) |
| leiden | 0.13 (0.01) | 0.13 (0.01) | 0.50 (0.03) | 0.50 (0.03) | 0.06 (0.00) | 0.06 (0.00) |
| umap | 2.88 (0.04) | 2.88 (0.04) | 0.17 (0.01) | 0.17 (0.01) | 2.45 (0.01) | 2.45 (0.01) |
| expression_neighbors | 8.84 (0.37) | 8.81 (0.42) | 2.23 (0.04) | 2.24 (0.03) | 9.01 (0.04) | 9.00 (0.04) |
| ligrec | 8.83 (0.12) | 8.77 (0.04) | 9.15 (0.14) | 9.11 (0.13) | 9.43 (0.08) | 9.42 (0.09) |

Speedup (media CPU / media GPU; intervallo bootstrap 95%):

| step | riferimento DGX 1-5 | riferimento DGX 2-5 | controllo server 1-5 | controllo server 2-5 |
|---|---|---|---|---|
| total | 1.41 [1.38, 1.45] | 1.42 [1.37, 1.46] | 1.61 [1.59, 1.62] | 1.61 [1.60, 1.63] |
| co_occurrence | 2.28 [2.17, 2.35] | 2.34 [2.33, 2.35] | 5.40 [5.13, 5.57] | 5.54 [5.50, 5.57] |
| nhood_enrichment | 0.67 [0.66, 0.67] | 0.66 [0.66, 0.67] | 0.82 [0.81, 0.83] | 0.82 [0.81, 0.82] |
| spatial_autocorr_moran | 0.51 [0.50, 0.52] | 0.51 [0.50, 0.52] | 0.49 [0.48, 0.49] | 0.49 [0.48, 0.49] |
| spatial_autocorr_geary | 6.56 [6.41, 6.71] | 6.64 [6.50, 6.78] | 7.54 [7.38, 7.71] | 7.59 [7.43, 7.76] |
| spatial_neighbors | 0.79 [0.74, 0.82] | 0.78 [0.73, 0.82] | 0.95 [0.90, 0.99] | 0.94 [0.88, 0.98] |
| umap | 17.26 [16.13, 18.02] | 17.06 [15.75, 17.95] | 14.64 [13.70, 15.23] | 14.50 [13.39, 15.18] |

Gruppi usati negli step spaziali: 16 (etichette: ripetizione 1 CPU del DGX, md5 7b2c133ef17a0869d2fa891ccf06a707).
Thread numba all'inizio di ogni step CPU (ripetizione 1): dgx_cpu: data_loading=100, qc_filtering=100, normalization=100, hvg_selection=100, pca=100, expression_neighbors=100, leiden=100, umap=100, spatial_neighbors=100, spatial_autocorr_moran=100, spatial_autocorr_geary=100, co_occurrence=100, nhood_enrichment=100, ligrec=1; server_cpu: data_loading=128, qc_filtering=128, normalization=128, hvg_selection=128, pca=128, expression_neighbors=128, leiden=128, umap=128, spatial_neighbors=128, spatial_autocorr_moran=128, spatial_autocorr_geary=128, co_occurrence=128, nhood_enrichment=128, ligrec=1

## Visium HD 8 um

Tempi in secondi: media (SD) sulle ripetizioni 1-5 e 2-5.

| step | CPU reference, DGX poddgx02 (100 CPU) 1-5 | 2-5 | GPU, RTX 4090 workstation 1-5 | 2-5 | CPU control, workstation (128 threads) 1-5 | 2-5 |
|---|---|---|---|---|---|---|
| total | 719.03 (3.16) | 719.70 (3.21) | 92.21 (0.68) | 92.18 (0.79) | 617.24 (11.34) | 613.68 (9.34) |
| co_occurrence | 103.24 (0.34) | 103.31 (0.36) | 2.55 (0.11) | 2.56 (0.12) | 72.23 (0.09) | 72.20 (0.06) |
| nhood_enrichment | 13.50 (0.15) | 13.47 (0.16) | 12.78 (0.42) | 12.85 (0.46) | 12.11 (0.29) | 12.05 (0.30) |
| spatial_autocorr_moran | 82.65 (1.43) | 82.45 (1.56) | 3.98 (0.32) | 4.02 (0.35) | 51.94 (2.88) | 51.02 (2.32) |
| spatial_autocorr_geary | 82.08 (2.05) | 82.45 (2.16) | 0.67 (0.00) | 0.67 (0.00) | 50.73 (4.24) | 50.01 (4.53) |
| spatial_neighbors | 45.23 (0.34) | 45.10 (0.23) | 56.35 (0.88) | 56.21 (0.94) | 55.79 (1.28) | 55.69 (1.45) |
| pca | 33.65 (0.14) | 33.68 (0.14) | 0.91 (0.03) | 0.91 (0.03) | 77.48 (3.29) | 76.55 (2.95) |
| leiden | 21.25 (0.21) | 21.20 (0.21) | 1.65 (0.02) | 1.65 (0.03) | 19.36 (0.68) | 19.49 (0.72) |
| umap | 269.13 (5.03) | 269.63 (5.66) | 1.37 (0.01) | 1.36 (0.00) | 198.37 (3.72) | 197.66 (3.88) |
| expression_neighbors | 58.06 (0.20) | 58.12 (0.17) | 4.29 (0.11) | 4.30 (0.12) | 70.16 (0.71) | 69.96 (0.62) |
| ligrec | skipped | skipped | skipped | skipped | skipped | skipped |

Speedup (media CPU / media GPU; intervallo bootstrap 95%):

| step | riferimento DGX 1-5 | riferimento DGX 2-5 | controllo server 1-5 | controllo server 2-5 |
|---|---|---|---|---|
| total | 7.80 [7.75, 7.85] | 7.81 [7.75, 7.87] | 6.69 [6.60, 6.80] | 6.66 [6.56, 6.76] |
| co_occurrence | 40.45 [38.95, 41.33] | 40.33 [38.50, 41.41] | 28.30 [27.27, 28.90] | 28.19 [26.91, 28.91] |
| nhood_enrichment | 1.06 [1.03, 1.08] | 1.05 [1.02, 1.08] | 0.95 [0.92, 0.98] | 0.94 [0.91, 0.97] |
| spatial_autocorr_moran | 20.77 [19.41, 21.92] | 20.53 [18.95, 21.93] | 13.05 [12.06, 14.01] | 12.71 [11.62, 13.69] |
| spatial_autocorr_geary | 122.36 [120.03, 124.92] | 123.08 [120.37, 126.13] | 75.62 [69.90, 79.07] | 74.66 [67.94, 78.44] |
| spatial_neighbors | 0.80 [0.79, 0.81] | 0.80 [0.79, 0.81] | 0.99 [0.97, 1.01] | 0.99 [0.96, 1.02] |
| umap | 197.09 [194.39, 200.45] | 197.90 [194.84, 201.61] | 145.27 [142.96, 147.40] | 145.08 [142.73, 147.46] |

Gruppi usati negli step spaziali: 4 (etichette: ripetizione 1 CPU del DGX, md5 c9e94bed95b6f55c71d87e04112f0f0c).
Thread numba all'inizio di ogni step CPU (ripetizione 1): dgx_cpu: data_loading=100, qc_filtering=100, normalization=100, hvg_selection=100, pca=100, expression_neighbors=100, leiden=100, umap=100, spatial_neighbors=100, spatial_autocorr_moran=100, spatial_autocorr_geary=100, co_occurrence=100, nhood_enrichment=100; server_cpu: data_loading=128, qc_filtering=128, normalization=128, hvg_selection=128, pca=128, expression_neighbors=128, leiden=128, umap=128, spatial_neighbors=128, spatial_autocorr_moran=128, spatial_autocorr_geary=128, co_occurrence=128, nhood_enrichment=128

## Visium HD 2 um

Tempi in secondi: media (SD) sulle ripetizioni 1-5 e 2-5.

| step | CPU reference, DGX poddgx02 (100 CPU) 1-5 | 2-5 | GPU, RTX 4090 workstation 1-5 | 2-5 | CPU control, workstation (128 threads) 1-5 | 2-5 |
|---|---|---|---|---|---|---|
| total | 1146.06 (49.81) | 1156.12 (51.31) | 109.92 (0.82) | 110.05 (0.89) | 1032.37 (26.11) | 1025.18 (23.76) |
| co_occurrence | skipped | skipped | skipped | skipped | skipped | skipped |
| nhood_enrichment | skipped | skipped | skipped | skipped | skipped | skipped |
| spatial_autocorr_moran | 82.88 (1.97) | 83.14 (2.18) | 3.96 (0.35) | 3.99 (0.40) | 36.67 (1.54) | 36.86 (1.71) |
| spatial_autocorr_geary | 85.79 (3.46) | 85.96 (3.97) | 0.67 (0.10) | 0.68 (0.11) | 36.69 (1.07) | 36.94 (1.06) |
| spatial_neighbors | 44.99 (0.29) | 44.97 (0.33) | 55.44 (0.47) | 55.42 (0.54) | 54.89 (0.76) | 54.76 (0.80) |
| pca | 17.46 (0.11) | 17.42 (0.06) | 0.88 (0.01) | 0.88 (0.01) | 23.95 (0.54) | 23.79 (0.48) |
| leiden | 9.24 (0.29) | 9.11 (0.05) | 0.99 (0.01) | 0.99 (0.00) | 8.27 (0.39) | 8.10 (0.04) |
| umap | 824.77 (46.25) | 834.54 (47.06) | 9.22 (0.60) | 9.27 (0.68) | 775.65 (26.26) | 768.72 (24.48) |
| expression_neighbors | 51.15 (0.26) | 51.16 (0.30) | 4.25 (0.04) | 4.26 (0.03) | 63.27 (0.62) | 63.11 (0.58) |
| ligrec | skipped | skipped | skipped | skipped | skipped | skipped |

Speedup (media CPU / media GPU; intervallo bootstrap 95%):

| step | riferimento DGX 1-5 | riferimento DGX 2-5 | controllo server 1-5 | controllo server 2-5 |
|---|---|---|---|---|
| total | 10.43 [10.15, 10.82] | 10.51 [10.20, 10.98] | 9.39 [9.21, 9.59] | 9.32 [9.15, 9.53] |
| co_occurrence | n/a | n/a | n/a | n/a |
| nhood_enrichment | n/a | n/a | n/a | n/a |
| spatial_autocorr_moran | 20.95 [19.35, 22.14] | 20.81 [18.95, 22.29] | 9.27 [8.52, 9.92] | 9.23 [8.36, 9.98] |
| spatial_autocorr_geary | 128.93 [114.30, 144.97] | 125.89 [109.80, 144.95] | 55.14 [48.96, 61.91] | 54.10 [47.88, 61.93] |
| spatial_neighbors | 0.81 [0.80, 0.82] | 0.81 [0.80, 0.82] | 0.99 [0.98, 1.00] | 0.99 [0.97, 1.00] |
| umap | 89.43 [83.77, 95.41] | 90.06 [82.73, 96.99] | 84.10 [79.32, 88.39] | 82.95 [77.11, 87.99] |

Gruppi usati negli step spaziali: 3027 (etichette: ripetizione 1 CPU del DGX, md5 c8df12a0b077c2f8988f0bd09542bec8).
Thread numba all'inizio di ogni step CPU (ripetizione 1): dgx_cpu: data_loading=100, qc_filtering=100, normalization=100, hvg_selection=100, pca=100, expression_neighbors=100, leiden=100, umap=100, spatial_neighbors=100, spatial_autocorr_moran=100, spatial_autocorr_geary=100; server_cpu: data_loading=128, qc_filtering=128, normalization=128, hvg_selection=128, pca=128, expression_neighbors=128, leiden=128, umap=128, spatial_neighbors=128, spatial_autocorr_moran=128, spatial_autocorr_geary=128

## Provenienza dei dataset

- VISIUM_SAMPLE: `V1_Mouse_Brain_Sagittal_Anterior`
- VISIUM_BASE_URL: `https://cf.10xgenomics.com/samples/spatial-exp/1.1.0`
- VISIUM_HD_URL: `https://cf.10xgenomics.com/samples/spatial-exp/4.0.1/Visium_HD_Tiny_3prime_Dataset/Visium_HD_Tiny_3prime_Dataset_outs.zip`
- VISIUM_HD_ARCHIVE: `Visium_HD_Tiny_3prime_Dataset_outs.zip`

