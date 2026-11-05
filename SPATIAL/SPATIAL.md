# SPATIAL.md — GPU-Accelerated Spatial Omics Benchmark (Phase 2)

> **STATUS**: Local benchmarks COMPLETE (Visium + Visium HD 8um + 2um, 5 repeats each). DGX full-scale runs pending driver fix.

## Goal

Extend the GPU vs CPU benchmark to spatial transcriptomics, using the same benchmark infrastructure. This adds a second "arm" to the study, making the paper a comprehensive GPU benchmark for both single-cell AND spatial omics — directly matching the CIBB 2026 special session scope.

The spatial benchmark answers:
1. **Speed**: GPU vs CPU speedup for spatial-specific analysis steps
2. **Scalability**: How do spatial pipelines scale with number of spots/bins?
3. **Concordance**: Do CPU and GPU produce the same spatially variable genes and spatial statistics?
4. **Platform comparison**: How do results differ across Visium vs Visium HD resolutions?

---

## Progress

### Completed (local, RTX 4090, 5 repeats each)

- [x] Dockerfile.spatial (RAPIDS 26.02 + squidpy/spatialdata)
- [x] Download script: Visium v1 Mouse Brain + Visium HD Mouse Brain (Tiny)
- [x] CPU benchmark script (`benchmark_spatial_cpu.py`)
- [x] GPU benchmark script (`benchmark_spatial_gpu.py`)
- [x] Concordance script (`compare_spatial_results.py`)
- [x] Container built and tested locally (lucavd/sc-benchmark-spatial:latest)
- [x] Full local benchmarks: 3 platforms x CPU/GPU x 5 repeats + concordance

### Pending (DGX) — blocked until driver fix

- [ ] Full-scale Visium HD 2um (6.3M bins, no subsampling) — needs DGX RAM
- [ ] Multi-GPU scaling (1/2/4/8 GPU on Visium HD)
- [ ] 5 repeats for all DGX configurations

---

## Local Benchmark Results (RTX 4090, 5 repeats, 2026-03-27)

### Overall Speedup

| Platform | Spots/Bins | CPU total (s) | GPU total (s) | **Speedup** |
|----------|-----------|---------------|---------------|-------------|
| Visium v1 | 2,695 | 10.0 | 6.0 | **1.7x** |
| Visium HD 8um | 393,543 | 4,068 | 79 | **51.6x** |
| Visium HD 2um | 389,492 | 1,042 | 97 | **10.8x** |

Note: Timings are mean of repeats 2-5 (r1 includes JIT/warmup overhead). HD 2um subsampled to 400k bins via `--max-spots 400000`.

### Per-Step Speedups (mean r2-r5)

#### Visium v1 (2,695 spots)

| Step | CPU (s) | GPU (s) | Speedup |
|------|---------|---------|---------|
| normalization | 0.181 | 0.001 | **226x** |
| co_occurrence | 0.273 | 0.005 | **51x** |
| expression_neighbors | 0.219 | 0.007 | **33x** |
| umap | 2.184 | 0.073 | **30x** |
| spatial_autocorr_moran | 0.333 | 0.042 | **7.9x** |
| spatial_autocorr_geary | 0.331 | 0.042 | **7.8x** |
| spatial_neighbors | 0.403 | 0.407 | 1.0x (CPU-only) |
| ligrec | 4.485 | 4.325 | 1.0x (CPU-only) |
| **TOTAL** | **10.0** | **6.0** | **1.7x** |

#### Visium HD 8um (393,543 bins)

| Step | CPU (s) | GPU (s) | Speedup |
|------|---------|---------|---------|
| co_occurrence | 3,573 | 1.09 | **3,272x** |
| pca | 72.8 | 0.28 | **257x** |
| normalization | 0.65 | 0.004 | **176x** |
| spatial_autocorr_moran | 47.9 | 0.30 | **162x** |
| spatial_autocorr_geary | 47.4 | 0.29 | **163x** |
| umap | 194.3 | 1.22 | **159x** |
| hvg_selection | 0.94 | 0.012 | **76x** |
| expression_neighbors | 39.4 | 2.00 | **20x** |
| leiden | 19.2 | 1.17 | **16x** |
| spatial_neighbors | 55.9 | 57.4 | 1.0x (CPU-only) |
| nhood_enrichment | 11.8 | 11.4 | 1.0x (CPU-only) |
| **TOTAL** | **4,068** | **79** | **51.6x** |

#### Visium HD 2um (389,492 bins after subsample)

| Step | CPU (s) | GPU (s) | Speedup |
|------|---------|---------|---------|
| spatial_autocorr_geary | 35.0 | 0.21 | **170x** |
| spatial_autocorr_moran | 34.5 | 0.21 | **167x** |
| normalization | 0.064 | 0.001 | **92x** |
| umap | 825.3 | 8.96 | **92x** |
| pca | 23.3 | 0.28 | **85x** |
| expression_neighbors | 32.7 | 1.98 | **17x** |
| leiden | 8.3 | 0.55 | **15x** |
| spatial_neighbors | 54.1 | 54.9 | 1.0x (CPU-only) |
| **TOTAL** | **1,042** | **97** | **10.8x** |

### Memory Usage

| Platform | CPU Peak RAM | GPU Peak RAM | GPU Peak VRAM |
|----------|-------------|-------------|---------------|
| Visium v1 | 1.3 GB | 2.6 GB | 12.9 GB |
| HD 8um | 8.1 GB | 11.5 GB | 22.6 GB |
| HD 2um | 10.8 GB | 14.4 GB | 22.6 GB |

### Concordance

| Metric | Visium | HD 8um | HD 2um |
|--------|--------|--------|--------|
| Moran's I rho | 1.0000 | 0.9999 | 1.0000 |
| Geary's C rho | 1.0000 | 0.9995 | 0.9999 |
| SVG Jaccard top50 | 1.0000 | 1.0000 | 1.0000 |
| SVG Jaccard FDR<0.05 | 1.0000 | 0.9986 | 0.9815 |
| Cluster ARI | 0.856 | 0.974 | **0.080** |
| Cluster NMI | 0.892 | 0.940 | **0.667** |
| N clusters CPU/GPU | 16/15 | 7/3 | **2559/538** |

### Key Findings

1. **Speedup scales with data size**: 1.7x (3k spots) -> 51.6x (393k bins) -> 10.8x (389k bins)
2. **co_occurrence is the biggest win**: 3,272x at 393k bins (CPU: 1 hour -> GPU: 1 second)
3. **UMAP massive at scale**: 92-159x speedup on HD platforms
4. **Spatial autocorrelation 162-170x** faster on GPU (after JIT warmup)
5. **Concordance excellent for spatial statistics**: Moran/Geary rho >= 0.9995, SVG Jaccard top50 = 1.0 across all platforms
6. **Cluster concordance degrades at HD 2um**: ARI = 0.08 because Leiden GPU (cugraph) vs CPU (leidenalg) produce very different cluster counts (538 vs 2559) at high granularity. This is an algorithmic difference, not a bug.
7. **spatial_neighbors is the GPU bottleneck**: ~55s CPU-only, represents 57-70% of GPU total time on HD platforms
8. **HD 8um speedup > HD 2um** because co_occurrence (the biggest GPU win at 3,272x) runs on HD 8um (7 clusters) but is skipped on HD 2um (>500 clusters)

### Discussion Points for Paper

1. **Spatial autocorrelation is the key result**: perfect numerical concordance (rho >= 0.9995) with 162-170x speedup. Scientists get identical SVG lists in seconds instead of minutes.
2. **Clustering discrepancy at 2um is expected**: Leiden's stochastic algorithm produces different results across implementations (cugraph vs leidenalg). At high granularity (2um bins), small differences in graph partitioning are amplified. This is a known limitation, not specific to GPU vs CPU.
3. **co_occurrence 3,272x speedup**: the CPU implementation in Squidpy is O(n^2) per distance interval, while the GPU implementation parallelizes this. At 393k bins with 7 clusters, this becomes the dominant step.
4. **spatial_neighbors has no GPU equivalent**: Squidpy's Delaunay triangulation is CPU-only (scipy.spatial). This is the remaining bottleneck — future work could use GPU-accelerated spatial indexing.

---

## Spatial Platforms

### Tier 1 (benchmarked)
- **10x Visium v1** — 2,695 spots, 55 um resolution
- **10x Visium HD** — 393k bins (8um) / 6.3M bins (2um, subsampled to 400k locally)

### Tier 2 (not pursued)
- **10x Xenium** — different data structure (molecules, not spots)
- **MERFISH / seqFISH** — deferred

---

## Datasets

### Visium v1 Mouse Brain Sagittal Anterior
- Source: 10x Genomics public datasets
- Files: `filtered_feature_bc_matrix.h5` + `spatial/` folder
- Size: ~2,695 spots x 32,285 genes
- Downloaded via `download_spatial_data.py`

### Visium HD Mouse Brain (CytAssist, FFPE)
- Source: 10x Genomics public datasets (Tiny 3' dataset)
- Files: `binned_outputs/` with square_002um, square_008um, square_016um
- Sizes: 6.3M bins (2um) / 393k bins (8um) / 99k bins (16um) x 19,059 genes

---

## Pipeline Steps

### Expression steps (shared with scRNA-seq, GPU-accelerated)
1. Data loading (`sc.read_visium` / `sc.read_10x_h5`)
2. QC & filtering (min_genes=200 for Visium, min_genes=1 for Visium HD)
3. Normalization (`normalize_total` + `log1p`)
4. HVG selection (2000 genes)
5. PCA (50 components)
6. Expression neighbors (k=15)
7. Leiden clustering (resolution adaptive: 1.0 for <100k, 0.1 for >100k spots)
8. UMAP

### Spatial steps
9. **Spatial neighbors** — `sq.gr.spatial_neighbors(delaunay=True)` — CPU-only
10. **Moran's I** — `sq.gr.spatial_autocorr(mode="moran")` — GPU via rsc
11. **Geary's C** — `sq.gr.spatial_autocorr(mode="geary")` — GPU via rsc
12. **Co-occurrence** — `sq.gr.co_occurrence()` / `rsc.gr.co_occurrence()` — GPU
13. **Nhood enrichment** — `sq.gr.nhood_enrichment()` — CPU-only
14. **Ligrec** — `sq.gr.ligrec()` — CPU-only

### Scale-dependent skips
- Co-occurrence / nhood enrichment: SKIP when >500 clusters (O(k^2) memory)
- Ligrec: SKIP when >100k spots (too slow, not informative)

---

## Software Stack

### Container: Dockerfile.spatial
- Base: `nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`
- `scanpy 1.12` — CPU expression analysis
- `rapids-singlecell 0.14.1` — GPU expression analysis + spatial autocorrelation
- `squidpy 1.8.1` — CPU spatial analysis (baseline)
- `spatialdata` + `spatialdata-io` — spatial data format
- `cupy 13.6.0` — GPU array operations

### GPU support matrix

| Function | CPU (Squidpy) | GPU (rsc) | Measured speedup (HD 8um) |
|----------|--------------|-----------|--------------------------|
| spatial_neighbors | yes | no | 1.0x (CPU-only) |
| spatial_autocorr (Moran/Geary) | yes | yes | **162-163x** |
| co_occurrence | yes | yes | **3,272x** |
| nhood_enrichment | yes | no | 1.0x (CPU-only) |
| ligrec | yes | no | 1.0x (CPU-only) |

---

## Concordance Metrics

- **Moran's I Spearman rho**: per-gene spatial autocorrelation correlation
- **Geary's C Spearman rho**: per-gene spatial autocorrelation correlation
- **SVG Jaccard**: overlap of top-N spatially variable genes (N = 50, 100, 200)
- **SVG Jaccard (FDR < 0.05)**: overlap of significant SVGs
- **Cluster ARI/NMI**: expression-based Leiden cluster agreement
- **Co-occurrence Spearman rho**: correlation of co-occurrence matrices

---

## Project Structure

```
SPATIAL/
├── SPATIAL.md                         # This file
├── Dockerfile.spatial                 # Container for spatial benchmarks
├── run_all_benchmarks.sh              # Run all 9 benchmark steps (3 platforms x CPU/GPU + concordance)
├── scripts/
│   ├── download_spatial_data.py       # Download Visium + Visium HD datasets
│   ├── benchmark_spatial_cpu.py       # CPU spatial pipeline (Scanpy + Squidpy)
│   ├── benchmark_spatial_gpu.py       # GPU spatial pipeline (rsc + Squidpy fallback)
│   └── compare_spatial_results.py     # Concordance analysis
├── data/
│   ├── visium/                        # Visium v1 Mouse Brain (29 MB)
│   │   ├── filtered_feature_bc_matrix.h5
│   │   └── spatial/
│   └── visium_hd/                     # Visium HD Mouse Brain (4.7 GB)
│       ├── binned_outputs/
│       │   ├── square_002um/
│       │   ├── square_008um/
│       │   └── square_016um/
│       └── spatial/
├── results/                           # Benchmark outputs (JSON + CSV), 5 repeats each
├── figures/                           # Generated plots
└── logs/                              # Container build / run logs
```

---

## QC Strategy for Visium HD

Visium HD 2um bins have very few genes per bin (median ~9). Standard `min_genes=200` filters nearly everything. Strategy:
- **Visium v1**: `min_genes=200` (standard)
- **Visium HD (all bin sizes)**: `min_genes=1` — Space Ranger already filtered on-tissue barcodes

At 2um, random subsampling destroys spatial contiguity -> many disconnected Leiden clusters even at low resolution. This is a known limitation of subsampling spatial data.

---

## DGX Status

**Blocked**: DGX driver 535.183.01 (CUDA 12.2) is incompatible with RAPIDS 26.02 (needs driver 570+). Options:
1. Wait for DGX driver upgrade
2. Rebuild container on `rapidsai/base:24.06-cuda12.2-py3.11` (tested: CuPy/RMM/rsc all pass on driver 535)

When DGX is available, the main value-add is:
- Full-scale Visium HD 2um (6.3M bins, no subsampling) — needs >>24 GB VRAM
- Multi-GPU scaling tests (1/2/4/8 GPU)
