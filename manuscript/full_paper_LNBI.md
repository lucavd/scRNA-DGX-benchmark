---
title: "GPU-accelerated single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics: per-step speedups, capacity and concordance against a 100-CPU reference"
bibliography: bibliography/cibb2026_references.bib
orcid:
  Luca Vedovelli: 0000-0003-4847-2333
---

Luca Vedovelli^1,2^, Corrado Lanera^1,2^, Daniele Sabbatini^1,2,3^, and Dario Gregori^1,2^

^1^ Unit of Biostatistics, Epidemiology and Public Health, Department of Cardiac, Thoracic, Vascular Sciences and Public Health, University of Padova, Padova, Italy. `{luca.vedovelli,corrado.lanera,daniele.sabbatini,dario.gregori}@ubep.unipd.it`

^2^ BIOSTAT-X, Biostatistics & AI for Biomedical Discovery, Pediatric Research Institute "Città della Speranza", Padova, Italy

^3^ Neuromuscular Unit, Department of Neuroscience, University of Padova, Padova, Italy

**Abstract.** Single-cell and spatial transcriptomics now yield millions of cells or bins, yet standard frameworks run on CPUs. We compared rapids-singlecell on NVIDIA H100 GPUs with Scanpy on 100 logical CPUs of a DGX H100 node, on 10,000 to 1.3 million mouse brain cells sampled from CELLxGENE Census, five repeats each. At 1.3 million cells the GPU pipeline took 435 s against 52,056 s on CPU (119.6-fold; 105.5-fold with two GPUs allocated, a difference due to data loading alone). Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold. Additional GPUs did no computation in this configuration. At 10,000 cells, HVG selection was identical and Leiden clusterings agreed with ARI 0.908-0.963. A memory-optimised pipeline completed 11.9 million cells, built from copies of a 3,436,470-cell dataset; larger runs stopped at a Dask time-out or were killed in CPU preprocessing. At 3.4 million cells, pseudo-bulk differential expression took 127 s against 5,598 s for a cell-level t-test. For spatial data we rebuilt the CPU reference: one fresh process per repeat, the same cell groups for CPU and GPU. Against 100 CPUs of a DGX H100 node, an RTX 4090 accelerated end-to-end analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occurrence) and 10.4-fold on Visium HD 2 um. At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances through 32-bit integer overflow; version 0.15.1 matched the CPU at all 49 in the same time.

**Keywords:** GPU computing · single-cell RNA-seq · spatial transcriptomics · benchmarking · rapids-singlecell

# Introduction

Single-cell RNA sequencing is now widely applied to dissect cellular heterogeneity in complex tissues [@Heumos2023].
Atlas-scale projects such as Tabula Sapiens [@TabulaSapiens2022] and the Allen Brain Cell Atlas of the whole mouse brain [@Yao2023] have produced datasets of millions of cells.
The Human Cell Atlas aims to define all human cell types [@Regev2017].
The widely used framework Scanpy [@Wolf2018] runs on the CPU.
A standard analysis of one million cells can require hours to days on a multi-core workstation.
It comprises quality control, principal component analysis (PCA), neighbour graph construction, Leiden clustering [@Traag2019], uniform manifold approximation and projection (UMAP) [@McInnes2018] and differential expression (DE) testing.
Spatial transcriptomics adds statistics such as spatial autocorrelation, co-occurrence and neighbourhood enrichment [@Palla2022].
The Visium HD section analysed here contains 6.3 million 2 um bins.

The RAPIDS ecosystem [@RAPIDS2024] provides GPU implementations of common data science primitives.
On this basis, rapids-singlecell [@Dicks2026] offers a near-drop-in replacement for Scanpy on NVIDIA GPUs.
GPU speedups have been reported for genomic analyses [@TaylorWeiner2019] and for single-cell pipelines on one to eight GPUs, with CPU-GPU concordance [@Nolet2022].
A simulated 13-million-cell dataset was processed on one A100 GPU [@Hu2025], and 100 million cells on a node with eight GPUs [@Dicks2026].
Gardner et al. [-@Gardner2025] found that CPU and GPU pipelines on NVIDIA H100 GPUs were not interchangeable (median ARI 0.45-0.55).

We address four questions, with one DGX H100 node and one RTX 4090 workstation, both against 100 CPUs of a DGX H100 node.
First, what is the per-step and end-to-end speedup of rapids-singlecell over Scanpy, and how much of it comes from DE testing?
Second, do the two pipelines agree on HVG selection, PCA, clustering and DE rankings?
Third, how many cells can a hybrid CPU-GPU pipeline complete on one node, and where do larger runs stop?
Fourth, do speedup and concordance extend to spatial transcriptomics?
This chapter extends our CIBB 2026 short paper with a new CPU reference for the spatial benchmark.
In it, every repeat runs in a fresh process, and CPU and GPU spatial statistics use the same cell groups.
Extended methods, eight tables and three figures are in the Supplementary Material, archived with the code.

# Data and Methods

## Single-cell RNA-seq

All single-cell experiments used mouse brain cells from the CZ CELLxGENE Census (release 2025-11-08) [@CZCellxGene2025].
We selected primary-data cells with `tissue_general` = brain profiled with 10x Genomics 3' chemistry, 3,436,470 cells in total.
From them we drew 1,300,000 cells uniformly at random without replacement (seed = 42).
Subsamples of 50,000, 100,000 and 500,000 cells came from this sample; the 10,000-cell set was drawn directly from the Census selection.

Both pipelines ran the standard Scanpy workflow [@Luecken2019; @Heumos2023] in ten timed steps (Supplementary Table S1).
The steps were QC (`min_genes` = 200, `min_cells` = 3), library-size normalisation and `log1p`, selection of 2,000 HVGs with the Seurat v1 method [@Satija2015; @Yip2019], scaling, PCA with 50 components, a k = 15 neighbour graph, Leiden clustering at r = 0.5, 1.0 and 1.5 [@Traag2019], UMAP [@McInnes2018] and a Wilcoxon one-vs-rest DE test on the r = 1.0 clusters [@Soneson2018].
The CPU pipeline used Scanpy 1.12 [@Wolf2018] with the igraph Leiden backend.
`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `NUMBA_NUM_THREADS` were set to the 100 allocated CPUs.
The GPU pipeline used rapids-singlecell 0.14.1 [@Dicks2026] with CuPy 13.6.0, the RAPIDS Memory Manager (RMM) 26.2.0 and the cuGraph Leiden backend.
Both shared the AnnData format [@Virshup2024].
The pipelines differed in Leiden iterations (2 on the CPU, 100 on the GPU), PCA solver and neighbour search.
From 8,192 cells upward, Scanpy 1.12 builds the neighbour graph with pynndescent and `n_jobs` = 1, so the CPU search ran on one Numba thread.
In a separate measurement, 100 threads made it 1.16, 1.91 and 2.48 times faster at 10,000, 50,000 and 100,000 cells.
The reported total is the sum of the timed steps.

At 500k and 1.3M cells the single-GPU pipeline failed during QC.
Results at these sizes come from a hybrid configuration with a Dask [@Rocklin2015] and Dask-CUDA [@RAPIDS2024] cluster of 2, 4 or 8 workers.
Preprocessing ran in Scanpy on the CPU, and the HVG matrix was transferred to GPU 0 as a CuPy array.
All later steps therefore ran on that GPU, and the additional GPUs did not take part in the computation.

Concordance was measured once, at 10,000 cells, on a separate pair of CPU and GPU runs made on 11 March 2026 (Supplementary Table S2).
We used six metrics: HVG Jaccard, the mean absolute Spearman rho of the first 10 PC loadings, the per-cell Jaccard of neighbour sets [@Gardner2025], the adjusted Rand index (ARI) [@Hubert1985] and normalised mutual information (NMI) [@Vinh2010] of Leiden labels, and the Spearman rho of DE log-fold-changes over matched clusters.
ARI is used as a clustering metric in published scRNA-seq benchmarks [@Tian2019; @Duo2020; @Luecken2022].

To find the largest dataset processable on one node, we ran a memory-optimised pipeline at 15 sizes from 3.4M to 11.9M cells.
It scaled on the CPU, computed a covariance PCA across the 8 GPUs and kept only the PCA embedding on the GPU.
Above 3,436,470 cells the input was built by concatenating whole copies of the dataset, so these runs contain duplicated cells.
CPU memory was sampled between steps for the parent process only, so the reported peaks are lower bounds.
DE was benchmarked separately on a 3,400,000-cell subset with 81 Leiden clusters.
We timed a CPU t-test, GPU t-tests and Wilcoxon rank-sum tests, and pseudo-bulk aggregation over donor x cluster groups followed by a CPU Wilcoxon test.
The GPU tests were custom CuPy kernels, used for timing only.

## Spatial transcriptomics

We used two 10x Genomics datasets: Visium v1 Mouse Brain Sagittal Anterior (2,695 spots) and Visium HD Mouse Brain (FFPE).
Visium HD was analysed at 8 um (393,543 bins) and at 2 um (6,296,688 bins).
The 2 um data were randomly subsampled to 400,000 bins (seed 42; 389,492 after QC) to fit in the 24 GB of the RTX 4090.
The subsample kept 6.35% of the bins, so its spatial statistics do not describe the native 2 um resolution.
After the expression steps, the pipeline computed spatial neighbours (Delaunay triangulation), Moran's I and Geary's C over 2,000 HVGs, co-occurrence, neighbourhood enrichment and ligand-receptor analysis (Supplementary Table S3).
The CPU pipeline used Scanpy 1.12 and Squidpy 1.8.1 [@Palla2022].
The GPU pipeline used rapids-singlecell 0.14.1 for the expression steps, Moran's I, Geary's C and co-occurrence.
The other spatial steps ran in Squidpy on the CPU in both pipelines.
Co-occurrence and neighbourhood enrichment were skipped above 500 cell groups.
Concordance was computed for the five pairs of CPU repeat k and GPU repeat k.
We compared Moran's I and Geary's C (Spearman rho), spatially variable gene (SVG) sets (Jaccard), Leiden partitions (ARI, NMI), and co-occurrence and neighbourhood enrichment matrices.

## Hardware, software and repeats

Single-cell benchmarks ran on DGX H100 nodes of the UPSCALE/CONVECS cluster at the University of Padova.
Each node has 8 x NVIDIA H100 80 GB, two Intel Xeon Platinum 8480C CPUs and 2 TB of RAM.
Jobs were submitted via SLURM without exclusive allocation, in a Singularity container built from `nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`.
The 8-GPU runs, the stress test and the DE benchmark ran on a different node from the 1-, 2- and 4-GPU runs.
The spatial GPU pipeline ran on a workstation with an NVIDIA GeForce RTX 4090 (24 GB) and an AMD Ryzen Threadripper PRO 5995WX CPU (128 threads).
Its CPU reference ran on DGX node `poddgx02`, reserved exclusively, with 100 CPUs; the workstation CPU was measured as a control.
Each configuration was run five times.
We report the mean +/- sample standard deviation (SD) of all five repeats, and speedups are ratios of means.
The scRNA-seq repeats ran in the same process, so the first includes JIT compilation.
Each spatial repeat ran in a fresh process.
Co-occurrence, neighbourhood enrichment and ligand-receptor analysis used the same cell groups in all spatial runs.
Random seeds were fixed at 42.
The stress test, the DE benchmark and the concordance analysis were run once.

# Results

## Single-cell RNA-seq

At 1.3 million cells the GPU pipeline with eight GPUs allocated took 435.2 +/- 16.2 s (7.3 min).
The CPU pipeline took 52,056.2 +/- 392.0 s (14.5 h), a 119.6-fold speedup (Table 1).
With two GPUs allocated the GPU pipeline took 493.3 +/- 10.3 s (105.5-fold).
The difference lies in data loading (149.0 against 90.6 s, runs on different nodes).
Wilcoxon DE accounted for 93.5% of the CPU time (48,688.3 s of 52,056.2 s).
Without it, the speedup was 7.9-fold with two GPUs and 9.2-fold with eight.
With a single GPU the speedup was 12.0x at 10k, 33.7x at 50k and 43.8x at 100k cells.
With two GPUs it was 34.9x at 500k cells.
Because this series mixes two pipelines, it is not a monotonic function of dataset size.
In the hybrid configuration at 1.3M cells, PCA plus neighbour search took 17.23, 16.99 and 17.01 s with 2, 4 and 8 GPUs.
Multi-GPU scaling was therefore not measured.

: **Table 1.** scRNA-seq benchmark: total time, mean and SD over five repeats (first repeat included), and peak memory. Single-GPU results at 500k and 1.3M cells are absent because the single-GPU pipeline failed during QC.

| Pipeline | Cells | GPUs | Total time (s) | SD (s) | Peak RAM (GiB) | Peak VRAM (GiB) |
|:---------------|-----:|-----:|------------:|-------:|-----------:|------------:|
| CPU (Scanpy) | 10k | 0 | 39.5 | 10.2 | 1.2 | n.a. |
| GPU (rapids) | 10k | 1 | 3.3 | 1.7 | 2.4 | 40.7 |
| GPU | 10k | 2 | 4.9 | 2.6 | 2.3 | 52.4 |
| GPU | 10k | 4 | 4.9 | 2.6 | 2.3 | 65.0 |
| GPU | 10k | 8 | 4.9 | 2.3 | 2.3 | 106.5 |
| CPU (Scanpy) | 50k | 0 | 282.5 | 9.1 | 3.6 | n.a. |
| GPU (rapids) | 50k | 1 | 8.4 | 2.2 | 5.4 | 40.7 |
| GPU | 50k | 2 | 14.7 | 2.4 | 3.5 | 52.4 |
| GPU | 50k | 4 | 14.6 | 2.6 | 3.5 | 65.0 |
| GPU | 50k | 8 | 15.1 | 2.2 | 3.4 | 106.5 |
| CPU (Scanpy) | 100k | 0 | 646.7 | 10.5 | 6.7 | n.a. |
| GPU (rapids) | 100k | 1 | 14.8 | 2.2 | 8.8 | 40.7 |
| GPU | 100k | 2 | 26.9 | 2.4 | 4.9 | 52.4 |
| GPU | 100k | 4 | 26.9 | 2.3 | 4.9 | 65.1 |
| GPU | 100k | 8 | 26.4 | 2.6 | 4.9 | 106.6 |
| CPU (Scanpy) | 500k | 0 | 4,346.7 | 40.3 | 29.7 | n.a. |
| GPU | 500k | 2 | 124.5 | 2.9 | 15.6 | 52.7 |
| GPU | 500k | 4 | 125.0 | 6.0 | 15.9 | 65.5 |
| GPU | 500k | 8 | 124.6 | 3.7 | 15.5 | 107.0 |
| CPU (Scanpy) | 1.3M | 0 | 52,056.2 | 392.0 | 107.4 | n.a. |
| GPU | 1.3M | 2 | 493.3 | 10.3 | 60.7 | 74.9 |
| GPU | 1.3M | 4 | 486.6 | 20.2 | 60.7 | 92.7 |
| GPU | 1.3M | 8 | 435.2 | 16.2 | 52.3 | 134.2 |

Per-step speedups ranged from 0.36x to 329x (Fig. 1).
Normalisation reached 329x, 206x and 173x at 10k, 50k and 100k cells.
HVG selection reached 24-94x, UMAP 27-45x and DE 16-88x.
Neighbour graph construction reached 44-88x against the single-threaded CPU search.
PCA rose from 4.8x at 10k to 36.5x at 100k cells.
Data loading was slower on the GPU at all three sizes (0.76-0.85x).
Its GPU excess grew from 0.10 s at 10k to 1.38 s at 100k cells.
Both extremes were set by the first repeat.
Excluding it, normalisation was 115.1x faster at 10k cells (instead of 329x), and Leiden at resolution 0.5 was 1.12x faster (instead of 0.36x).
End-to-end speedups changed by at most 6% from 100k cells upwards.
Absolute step times are in Supplementary Fig. S1.

![**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) over CPU Scanpy (100 logical CPUs) at 10k, 50k and 100k cells: ratio of mean times over five repeats (first repeat included); logarithmic colour scale centred on 1. The PCA row includes scaling.](../figures/fig1_speedup_heatmap.png)

At 10,000 cells HVG selection was identical (Jaccard = 1.000) (Fig. 2).
PCA loadings were perfectly correlated (mean absolute Spearman rho = 1.000).
Neighbour sets had a mean Jaccard of 0.930.
This value is bounded at 0.9375 = 15/16, because the CPU and GPU sets hold 16 and 15 indices.
For 95.0% of cells every GPU neighbour was also a CPU neighbour.
Leiden ARI ranged from 0.908 (resolution 1.0) to 0.963 (resolution 1.5), and NMI from 0.951 to 0.971.
Each pipeline returned identical labels in all five repeats at this size.
DE log-fold-changes over 40 matched cluster pairs had a mean Spearman rho of 0.946 (median 0.9995).
For 34 of the 40 pairs, rho was above 0.97.
From 50,000 cells upwards, GPU Leiden labels varied across the five repeats at one or more resolutions despite a fixed seed; CPU labels did not.

![**Figure 2.** CPU-GPU concordance at 10,000 cells, from the separate concordance run. Left: ARI and NMI of Leiden clustering at three resolutions. Right: HVG Jaccard, PCA Spearman |rho|, kNN Jaccard (bounded at 0.9375 by construction) and mean Spearman rho of DE log-fold-changes over 40 matched cluster pairs.](../figures/fig3_concordance.png)

Up to 1.3M cells, CPU RAM grew from 1.2 to 107.4 GiB (Table 1, Supplementary Fig. S2).
Single-GPU VRAM stayed at 40.7 GiB, dominated by the pre-allocated RMM pool.
The memory-optimised pipeline completed 11.9 million cells in 119 min (Supplementary Tables S4 and S5).
Its recorded peak was 535 GiB of CPU RAM, 30% of the 1.8 TB SLURM job allocation.
Aggregate VRAM peaked at 48.8 GiB out of 640 GiB (7.6%).
At 11.9M cells Leiden returned 135,710, 142,959 and 147,154 clusters at the three resolutions.
On a 3,400,000-cell subset of the source dataset it returned 58, 66 and 87.
A pass therefore denotes computational completion on replicated data.
The single run at 12.0M cells exited with a timeout while the Dask cluster was being shut down after neighbour search.
The runs at 13.7M cells were killed (signal 9) after HVG selection, before scaling.
A chunked variant inspired by ScaleSC [@Hu2025] completed 12.0 million cells (862 GiB peak RAM, 10 GiB aggregate VRAM).
It was killed at 15.0 million cells.

At 3.4 million cells, pseudo-bulk aggregation to 2,431 donor x cluster pseudo-samples completed the DE analysis in 127 s.
This was 43.9 times sooner than the cell-level CPU t-test (5,598 s).
The GPU Wilcoxon test took 826 s with gene chunks scattered across 8 GPUs and 831 s streamed through one GPU (Supplementary Table S6).
The GPU t-test took 1,655 and 1,649 s.

## Spatial transcriptomics

Against the DGX CPU reference, end-to-end GPU speedups were 1.4x on Visium v1 and 6.9x on Visium HD 8 um, with co-occurrence excluded (Table 2, Supplementary Fig. S3).
On the random 400k-bin subsample of Visium HD 2 um the speedup was 10.4x.
With the 128-thread workstation CPU as reference the speedups were 1.6x, 6.1x and 9.4x.
The choice of CPU changed the speedup by 10-14%, in different directions per platform.

: **Table 2.** Spatial benchmark: mean +/- SD of five repeats, each in a fresh process. CPU: one DGX H100 node (`poddgx02`, 100 CPUs), the reference; GPU: one RTX 4090. Speedup: ratio of mean totals with 95% bootstrap interval; the next column uses the 128-thread workstation CPU as reference. At Visium HD 8 um the totals include co-occurrence, whose GPU result with rapids-singlecell 0.14.1 was incorrect; without it the totals are 616 s (CPU) and 89.7 s (GPU) and the speedup is 6.9x (6.8-6.9) (6.1x with the workstation CPU). Memory: mean of the per-repeat peaks (GiB); GPU VRAM includes the RMM pool.

| Platform | Spots/bins | CPU total (s) | GPU total (s) | Speedup | Speedup, workstation CPU | CPU RAM (GiB) | GPU VRAM (GiB) |
|:-------------------------------------------------|-----------------------------------------:|--------------------------------------------:|-------------------------------------------------:|------------------------------------------------------:|--------------------------------------------:|-----------------------:|-----------------------------:|
| Visium v1 | 2,695 | 33.9 +/- 1.0 | 24.0 +/- 0.2 | 1.41x (1.38-1.45) | 1.61x | 0.97 | 12.74 |
| Visium HD 8 um | 393,543 | 719 +/- 3 | 92.2 +/- 0.7 | 7.80x (7.75-7.85) | 6.69x | 6.95 | 22.74 |
| Visium HD 2 um (random 400k-bin subsample) | 389,492 | 1,146 +/- 50 | 109.9 +/- 0.8 | 10.43x (10.15-10.82) | 9.39x | 7.95 | 22.73 |

At Visium HD 8 um the CPU and GPU co-occurrence used the same 4 cell groups.
The GPU result of rapids-singlecell 0.14.1 matched the CPU within an absolute tolerance of 0.001 in only 8 of 49 distance intervals.
The cause is that the number of bin pairs within the larger distance thresholds exceeds the range of its 32-bit integer counters.
The GPU co-occurrence of the original March runs had the same defect.
With rapids-singlecell 0.15.1 the GPU result matched in 49 of 49 intervals at unchanged runtime (time ratio 0.98, 95% CI 0.95-1.00).
In this separate check it took 4.41 s against 103 s on the DGX CPU (23.4x).
Co-occurrence is therefore excluded from the Visium HD speedups.

On Visium HD 8 um the GPU accelerated UMAP 197x, Geary's C 122x, PCA 37.0x, normalisation 30.4x and Moran's I 20.8x (Fig. 3, Supplementary Table S7).
Expression neighbours and Leiden clustering were accelerated 13.5x and 12.9x.
Spatial neighbours and neighbourhood enrichment ran in Squidpy on the CPU in both pipelines (0.80x and 1.1x).
Spatial neighbours took 61.1% of the GPU pipeline time.
On Visium v1, ligand-receptor analysis, run on the CPU in both pipelines, took 38.2% of the GPU pipeline time.
On this platform QC, Leiden, Moran's I and PCA were slower on the GPU than on the CPU.

![**Figure 3.** Per-step GPU speedup on Visium HD 8 um (393,543 bins) against the DGX CPU reference: ratio of means over five repeats; error bars: 95% bootstrap interval. Open circles: steps run in Squidpy on the CPU in both pipelines. Open diamond: co-occurrence from the separate check with rapids-singlecell 0.15.1.](../figures/fig8_spatial_perstep.png)

Moran's I and Geary's C correlated between CPU and GPU with a Spearman rho of at least 0.9995 on all three platforms (Fig. 4, Supplementary Table S8).
The top-50 SVGs by Moran's I formed the same set on CPU and GPU (Jaccard = 1.000).
Leiden partitions agreed on Visium v1 (ARI 0.856) and Visium HD 8 um (ARI 0.971-0.974).
They diverged on the 2 um subsample (ARI 0.071).
There, CPU Leiden returned 3,027 groups on the DGX reference (2,559 on the workstation) and GPU Leiden 538, in each of the five repeats.
Peak GPU memory was 22.74 GiB on Visium HD 8 um and 22.73 GiB on the 2 um subsample, of the 24.0 GiB of the RTX 4090.

![**Figure 4.** CPU-GPU spatial concordance on three Visium platforms, CPU repeat k against GPU repeat k (k = 1-5); points: mean of the five pairs, bars: range where the pairs differ. Left: Spearman rho of per-gene Moran's I and Geary's C over 2,000 HVGs, and Jaccard index of SVG sets ranked by Moran's I. Right: ARI and NMI of the Leiden partitions.](../figures/fig9_spatial_concordance.png)

# Discussion

On one DGX H100 node, rapids-singlecell shortened the standard Scanpy pipeline by one to two orders of magnitude.
At 1.3M cells most of the gain came from the CPU Wilcoxon test.
Dicks et al. report more than 120-fold on one B200 GPU against a 32-core workstation CPU, with DE and I/O excluded [@Dicks2026].
In our hybrid pipeline a similar end-to-end factor arises mainly from the CPU Wilcoxon test.
The speedup depended on the operation.
Element-wise normalisation gained the most, whereas data loading through CPU RAM was slower on the GPU.
The neighbour speedup is relative to a single-threaded CPU search.
Against 100 threads it would shrink to about 76x, 32x and 18x at 10,000, 50,000 and 100,000 cells.
Even at 10,000 cells the GPU pipeline was 12.0-fold faster end to end, partly because CPU DE took 54.9% of the CPU time.
Only one GPU computed in our multi-GPU configuration.
We therefore expect most of the benefit to be available on a single H100, although we did not run the hybrid pipeline with one GPU at 500k or 1.3M cells.
Multi-GPU workflows built on Dask have been reported with RAPIDS on 8 V100 GPUs [@Nolet2022] and with rapids-singlecell on 8 B300 GPUs for 100 million cells [@Dicks2026].

At 10,000 cells the differences in Leiden labels reflect the two implementations and their settings (igraph with two iterations, cuGraph with up to 100).
They do not reflect run-to-run stochasticity.
At larger sizes GPU labels varied between repeats.
Other studies report CPU-GPU adjusted Rand indices of about 0.5 for up to 1.3 million cells [@Nolet2022; @Gardner2025].
Whether the two pipelines are interchangeable at atlas scale therefore remains to be shown.

GPU VRAM did not limit the number of cells in the memory-optimised pipeline.
The chunked variant reduced aggregate VRAM from 48.8 GiB to 9.6 GiB, while host RAM reached 862 GiB.
ScaleSC [@Hu2025] and Dicks et al. [@Dicks2026] reach larger datasets with chunked or out-of-core preprocessing.
The limit we observed therefore belongs to the pipeline rather than to GPU analysis in general.
Pseudo-bulk aggregation was also the fastest route to a DE result.
For multi-donor designs, pseudo-bulk aggregation of raw counts analysed with DESeq2 [@Love2014] or edgeR [@Robinson2010] is recommended [@Squair2021].
It accounts for variation between biological replicates.
Our pseudo-bulk timing aggregated log-normalised values and used a Wilcoxon test, so it measures computational cost only.

In the spatial benchmark the GPU advantage was concentrated in the expression steps and in spatial autocorrelation.
Spatial neighbours and neighbourhood enrichment have no GPU implementation in rapids-singlecell 0.14.1.
The new spatial reference used the same cell groups on CPU and GPU.
It showed that the GPU co-occurrence of rapids-singlecell 0.14.1 was incorrect at Visium HD 8 um.
On the Visium HD 2 um subsample the igraph and cuGraph implementations returned very different partitions in every repeat.
Users working at this resolution should check how stable Leiden partitions are across implementations and settings before interpreting them.

All scRNA-seq experiments used mouse brain cells from one Census selection.
The stress test replicated it by concatenation beyond 3,436,470 cells, and concordance was measured only at 10,000 cells.
The CPU baseline was an allocation of 100 logical CPUs on a node with 224.
We did not measure how Scanpy runtimes scale with the number of threads.
In the hybrid runs at 1.3M cells, Scanpy QC took 188.2 s with 32 allocated CPUs and 186.6 s with 100.
Our multi-GPU configuration did not distribute any step.
rapids-singlecell 0.14.1 provides Dask-based routes for preprocessing that we did not use.
The memory peaks of the stress test are lower bounds.
The spatial GPU pipeline ran on a workstation and its CPU reference on a DGX node.
The GPU components of the spatial stack did not run with the drivers of the cluster nodes (Supplementary Material).
The full Visium HD 2 um resolution was not benchmarked.
We did not benchmark integration methods such as Harmony [@Korsunsky2019] or scVI [@Lopez2018].

# Conclusions

In our hybrid pipeline on one DGX H100 node, the steps left on the CPU and the choice of DE test bounded the achievable speedup.
The CPU Wilcoxon test produced most of the end-to-end gain, and the additional GPUs took no part in the computation.
CPU and GPU outputs agreed closely at 10,000 cells; agreement at atlas scale remains to be shown.
On one RTX 4090, spatial autocorrelation agreed with the CPU and was accelerated.
Co-occurrence in rapids-singlecell 0.14.1 was incorrect at Visium HD 8 um and is corrected in 0.15.1.

# Availability of Data and Software Code

All code, Dockerfiles, SLURM submission scripts, benchmark result JSON files and the scripts that generate every figure are available at <https://github.com/lucavd/scRNA-DGX-benchmark> (release v1.0.0) and archived on Zenodo (<https://doi.org/10.5281/zenodo.23984290>). The Supplementary Material (extended methods, results and discussion, Supplementary Tables S1-S8 and Figures S1-S3) is included in the archive.

# Acknowledgements

The computational resources for the scRNA-seq benchmarks and for the CPU reference of the spatial benchmarks were provided by the
UPSCALE/CONVECS DGX H100 cluster at the University of Padova. This work was supported in part by the high-performance computing infrastructure developed under the project "CONVECS", funded by the PR Veneto FESR 2021-2027 program, Priority 1 - Specific Objective 1.1 - Action 1.1.2. The authors used a large language model-based assistant (Claude Opus 5.5, Anthropic) to check the analysis code against the text, to recompute reported values from the result files with scripts and to draft revisions of the text; the authors reviewed every change and take full responsibility for the content of this chapter.

# Funding

This study was co-funded by the BIRD 2024/START (SID) programs, Department of Cardio-Thoracic-Vascular Sciences (DCTV), University of Padova (PI: Daniele Sabbatini; 2024DCTV1SIDPROGETTI-00183) and by the Italian Complementary National Plan PNC-I.1 "Research initiatives for innovative technologies and pathways in the health and welfare sector" D.D. 931 of 06/06/2022, "DARE-DigitAl lifelong pRevEntion" initiative, code PNC0000002, CUP: B53C22006440001.

# Disclosure of Interests

The authors have no competing interests to declare that are relevant to the content of this article.

# References
