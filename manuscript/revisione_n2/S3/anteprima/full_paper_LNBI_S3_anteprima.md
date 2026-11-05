---
title: "GPU-accelerated single-cell (NVIDIA DGX H100) and spatial (RTX 4090) transcriptomics: per-step speedups, capacity and concordance against a 100-CPU reference"
bibliography: bibliography/cibb2026_references.bib
---

Luca Vedovelli^1,2^, Corrado Lanera^1,2^, Daniele Sabbatini^1,2,3^, and Dario Gregori^1,2^

^1^ Unit of Biostatistics, Epidemiology and Public Health, Department of Cardiac, Thoracic, Vascular Sciences and Public Health, University of Padova, Padova, Italy. `{luca.vedovelli,corrado.lanera,daniele.sabbatini,dario.gregori}@ubep.unipd.it`

^2^ BIOSTAT-X, Biostatistics & AI for Biomedical Discovery, Pediatric Research Institute "Città della Speranza", Padova, Italy

^3^ Neuromuscular Unit, Department of Neuroscience, University of Padua, Padua, Italy

**Abstract.** Single-cell and spatial transcriptomics now yield millions of cells or bins, yet standard frameworks run on CPUs. We compared rapids-singlecell on NVIDIA H100 GPUs with Scanpy on 100 logical CPUs of a DGX H100 node, on 10,000 to 1.3 million mouse brain cells sampled from CELLxGENE Census, five repeats each. At 1.3 million cells the GPU pipeline took 435 s against 52,056 s on CPU (119.6-fold; 105.5-fold with two GPUs allocated, a difference due to data loading alone). Wilcoxon differential expression accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold. Additional GPUs did no computation in this configuration. At 10,000 cells, HVG selection was identical and Leiden clusterings agreed with ARI 0.908-0.963. A memory-optimised pipeline completed 11.9 million cells, built from copies of a 3,436,470-cell dataset; larger runs stopped at a Dask time-out or were killed in CPU preprocessing. At 3.4 million cells, pseudo-bulk differential expression took 127 s against 5,598 s for a cell-level t-test. For spatial data we rebuilt the CPU reference: one fresh process per repeat, the same cell groups for CPU and GPU. Against 100 CPUs of a DGX H100 node, an RTX 4090 accelerated end-to-end analysis 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occurrence) and 10.4-fold on Visium HD 2 um. At Visium HD 8 um, GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances through 32-bit integer overflow; version 0.15.1 matched the CPU at all 49 in the same time.

**Keywords:** GPU computing · single-cell RNA-seq · spatial transcriptomics · benchmarking · rapids-singlecell

# Introduction

Single-cell RNA sequencing is now widely applied to dissect cellular heterogeneity in complex tissues [@Heumos2023].
Atlas-scale projects such as Tabula Sapiens [@TabulaSapiens2022] and the Allen Brain Cell Atlas of the whole mouse brain [@Yao2023] have produced datasets of hundreds of thousands to millions of cells, placing severe computational demands on analysis pipelines; the Human Cell Atlas aims to define all human cell types [@Regev2017].
The widely used analysis framework Scanpy [@Wolf2018] runs on the CPU and builds on NumPy, SciPy and scikit-learn for linear algebra and graph operations.
While multi-threaded CPU implementations scale modestly with core count, a standard analysis of one million cells, encompassing quality control, normalisation, principal component analysis (PCA), neighbourhood graph construction, Leiden clustering [@Traag2019], uniform manifold approximation and projection (UMAP) [@McInnes2018], and differential expression (DE) testing, can require hours to days on a multi-core workstation.

In parallel, spatial transcriptomics has matured from low-throughput technologies to platforms that tile entire tissue sections with hundreds of thousands of measurement points.
The Visium HD section (10x Genomics) analysed in this chapter contains 6.3 million 2 um bins, and spatial analysis pipelines built on Squidpy [@Palla2022] add computationally intensive operations such as spatial autocorrelation (Moran's I, Geary's C), co-occurrence analysis, and neighbourhood enrichment on top of the standard expression analysis workflow.
As both single-cell and spatial datasets grow, the need for GPU-accelerated analysis becomes increasingly pressing.

GPU-accelerated alternatives have emerged to address this scalability challenge.
The RAPIDS ecosystem [@RAPIDS2024] provides GPU-native implementations of common data science primitives, and rapids-singlecell [@Dicks2026] offers a near-drop-in replacement for Scanpy that executes the same analytical pipeline on NVIDIA GPUs via cuML, cuGraph, and CuPy.
Prior work has demonstrated substantial GPU speedups for genomic analyses [@TaylorWeiner2019], including single-cell pipelines [@Nolet2022], and proposed GPU frameworks for datasets exceeding ten million cells [@Hu2025].
Earlier studies have reported per-step timings on one to eight GPUs with CPU-GPU concordance [@Nolet2022], a simulated 13-million-cell dataset processed on one A100 GPU [@Hu2025] and 100 million cells analysed on a node with eight GPUs [@Dicks2026].
Gardner et al. [-@Gardner2025] evaluated accuracy-performance trade-offs on NVIDIA H100 GPUs and found that CPU and GPU pipelines were not interchangeable (median ARI 0.45-0.55).
We complement these studies with three analyses: the share of the end-to-end speedup due to differential expression testing on one DGX H100 node, the largest cell count that a hybrid CPU-GPU pipeline completed on that node and where larger runs stopped, and a spatial benchmark of an RTX 4090 against a matched CPU reference.

Here we address four questions.
First, speed: what is the per-step and end-to-end speedup of rapids-singlecell relative to Scanpy?
Second, concordance: do CPU and GPU pipelines yield biologically equivalent results in terms of HVG selection, PCA embeddings, clustering, and DE gene rankings?
Third, capacity: how many cells can the hybrid pipeline complete on one DGX H100 node, and where do larger runs stop?
Fourth, spatial generalisability: do the GPU speedup and concordance patterns extend from single-cell to spatial transcriptomics?

We ran the single-cell benchmark on an NVIDIA DGX H100 node and the spatial benchmark on an RTX 4090 workstation, both against 100 CPUs of a DGX H100 node, and we release the code, the container definitions and the per-run result files.
In this hybrid pipeline, the steps left on the CPU and the choice of differential expression test bounded the achievable speedup.
This chapter extends our CIBB 2026 short paper with a new CPU reference for the spatial benchmark, in which every repeat runs in a fresh process and CPU and GPU spatial statistics use the same cell groups; the new reference removes a slowdown of the CPU between repeats of the original spatial runs and shows that GPU co-occurrence at Visium HD 8 um was wrong because of 32-bit integer overflow, an error that rapids-singlecell 0.15.1 corrects.

# Data and Methods

## Single-cell RNA-seq

### Dataset and subsampling

All single-cell experiments used mouse brain cells from the CZ CELLxGENE Census (release 2025-11-08) [@CZCellxGene2025]: primary-data cells (`is_primary_data`) with `tissue_general` = brain profiled with 10x Genomics 3' chemistry (v1 to v3), 3,436,470 cells in total. For the scaling benchmark we drew 1,300,000 of these cells uniformly at random without replacement (seed = 42).

To evaluate performance across scales, we created reproducible subsamples of 50,000, 100,000 and 500,000 cells from the 1.3M-cell sample by uniform random sampling without replacement (`numpy.random.choice`, seed = 42); the 10,000-cell set was drawn in the same way (seed = 42) directly from the Census selection in a preliminary test job, and the 1.3M-cell sample itself was the largest size.
All subsamples were therefore drawn from the same Census selection, so that the expected biological composition is the same across benchmarking tiers.

### Analysis pipeline

Both the CPU and GPU pipelines implemented the standard Scanpy workflow (cf. [@Luecken2019; @Heumos2023]) with the same parameter values, except for the implementation-specific settings listed in Table 1 (Leiden iterations, PCA solver and neighbour search).
The CPU pipeline used Scanpy 1.12 [@Wolf2018] with NumPy 2.2.6 and the igraph Leiden backend (igraph 1.0.0); the GPU pipeline used rapids-singlecell 0.14.1 [@Dicks2026] with CuPy 13.6.0, the RAPIDS Memory Manager (RMM) 26.2.0, and the cuGraph Leiden backend.
Both pipelines shared the AnnData format [@Virshup2024] for data interchange.

The pipeline comprised ten steps (Table 1), timed with `time.perf_counter()`; in the CPU and single-GPU pipelines scaling (step 5) was timed together with PCA (step 6), whereas the multi-GPU configuration timed scaling and the host-to-GPU transfer as separate steps, and each of the three Leiden resolutions had its own timer. The reported total is the sum of the timed steps, not the wall-clock time of the job: RMM initialisation, the GPU warm-up, the copy of `adata.raw`, HVG subsetting and Dask cluster start-up and shutdown were not timed.

: **Table 1.** Pipeline steps, parameters, and implementations for the scRNA-seq benchmark. All steps used identical parameters for the CPU and GPU pipelines except where noted. {#tbl:pipeline}

| Step | Operation | Key parameters | Implementation note |
|-----:|:----------|:---------------|:--------------------|
| 1 | Data loading | --- | `read_h5ad()` from disk |
| 2 | QC and filtering | `min_genes` = 200, `min_cells` = 3, mt prefix = `mt-` | Mitochondrial percentage calculated, cells/genes filtered |
| 3 | Normalisation | `target_sum` = 10,000 | Library-size scaling + `log1p` |
| 4 | HVG selection | `n_top_genes` = 2,000, Seurat v1 method | On log-normalised data [@Satija2015; @Yip2019] |
| 5 | Scaling | `max_value` = 10 | Sparse to dense float32, mean-centre, unit-variance; timed with PCA in the CPU and single-GPU pipelines |
| 6 | PCA | 50 components, seed = 42 | CPU: scikit-learn PCA (ARPACK) on the dense scaled matrix; GPU: cuML PCA (default solver) |
| 7 | Neighbour graph | k = 15, 50 PCs, seed = 42 | k-NN in PCA space; CPU: pynndescent (Scanpy default from 8,192 cells, `n_jobs` = 1); GPU: brute-force k-NN (rapids-singlecell default) |
| 8 | Leiden clustering | r in {0.5, 1.0, 1.5}, seed = 42; `n_iterations` = 2 (CPU) / 100 (GPU, rapids-singlecell default) | igraph (CPU) / cuGraph (GPU) [@Traag2019] |
| 9 | UMAP | 2 components, seed = 42 | 2D embedding [@McInnes2018] |
| 10 | DE testing | Wilcoxon, one-vs-rest, `use_raw` = True | On Leiden r = 1.0 clusters [@Soneson2018] |

For the CPU pipeline, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `NUMBA_NUM_THREADS` were set to 100, the number of CPUs (hardware threads) allocated by SLURM, before any numerical library was imported, so that the OpenMP, BLAS and Numba thread pools used by NumPy, SciPy, scikit-learn and umap-learn were all sized to the allocation. Neighbour search was the exception: from 8,192 cells upward, that is at every benchmark size, Scanpy 1.12 builds the k-NN graph with pynndescent and passes it the Scanpy default `n_jobs` = 1, so Numba ran on one thread during this step. In a separate measurement on the spatial GPU workstation (PCA embeddings recomputed from the 10,000-, 50,000- and 100,000-cell benchmark files; five repeats per setting, one process each, timing the call after JIT compilation), `n_jobs` = 100 made this step 1.16, 1.91 and 2.48 times faster than `n_jobs` = 1.
For single-GPU runs, RMM was initialised at the start of each repeat with a pool allocator (initial pool 50% and maximum 100% of device memory, the RMM defaults), which also served the CuPy allocations: the out-of-memory error of the single-GPU pipeline at 500,000 cells was raised by this pool. Before timing, a 100 x 100 matrix product created the CUDA context; it does not compile the rapids-singlecell kernels, so the first repeat also includes JIT compilation. The wall-clock interval between consecutive repeats, an upper bound on the untimed overhead because it also includes writing the results, was 8.2 s against 2.5 s of timed steps for one GPU at 10,000 cells (means of repeats 2-5: the first repeat has no preceding timestamp, so this figure is the one exception to the five-repeat convention).

### Multi-GPU configuration

At every dataset size we also ran a hybrid configuration with a Dask [@Rocklin2015] and Dask-CUDA [@RAPIDS2024] cluster of 2, 4 or 8 workers, one per GPU, each with a 10 GB initial / 70 GB maximum RMM pool. Data loading, QC, normalisation and HVG selection ran in Scanpy on the host CPU, and the HVG-subset matrix was then transferred to GPU 0 as a CuPy array. Because it was not converted to a Dask array, scaling, PCA, neighbour search, Leiden, UMAP and DE all ran on GPU 0, and the additional GPUs did not take part in the computation; rapids-singlecell 0.14.1 provides Dask-based routes for QC metrics, total-count normalisation, scaling and PCA, among other steps, which this configuration did not use. The 8-GPU runs ran on a different node from the 1-, 2- and 4-GPU runs (Section "Hardware and software environment"). Results at 500k and 1.3M cells come only from this configuration, because the single-GPU pipeline failed during QC at these sizes (at 500k cells an allocation of 23.8 GiB exceeded the RMM pool, whose maximum is the whole device memory; at 1.3M cells QC stopped with a CUDA illegal-memory-access error).

### Concordance metrics

To assess whether the GPU pipeline produces biologically equivalent results, we selected six concordance metrics covering five stages of the analysis pipeline (two for clustering), such that a divergence at any stage would be detected independently of the others (Table 2). The panel progresses from upstream operations (feature selection, dimensionality reduction) through graph and clustering steps to downstream differential expression. ARI is used as a clustering metric in published scRNA-seq benchmarks [@Tian2019; @Duo2020; @Luecken2022], NMI and an HVG overlap score in [@Luecken2022] and a kNN Jaccard in [@Gardner2025]; the PCA and DE metrics were defined for this study.

: **Table 2.** Concordance metrics used to compare CPU and GPU pipeline outputs. Concordance was computed once, at 10,000 cells, on a separate pair of CPU and GPU runs made on 11 March 2026 (UTC) in a preliminary test job (16 CPUs, one GPU), with the same input file and parameters as the benchmark but before the timed repeats; at Leiden r = 1.0 and 1.5 its CPU run found 40 and 45 clusters, against 41 and 46 in all five timed CPU repeats. {#tbl:concordance}

| Metric | Definition | Scope |
|:-------|:-----------|:------|
| HVG Jaccard | size of intersection divided by size of union of the CPU and GPU gene sets for 2,000 HVGs | Feature selection |
| PCA loading |rho| | Mean absolute Spearman rho across first 10 PC loadings, accounting for sign flips | Dimensionality reduction |
| kNN Jaccard | Mean per-cell Jaccard overlap of the CPU and GPU neighbour index sets (k = 15) as stored by each pipeline (CPU sets: 16 indices, GPU sets: 15, both including the cell itself); a stability metric also used in [@Gardner2025] | Graph structure |
| ARI | Adjusted Rand Index of Leiden cluster assignments, adjusted for chance [@Hubert1985] | Clustering |
| NMI | Normalised Mutual Information of cluster assignments [@Vinh2010] | Clustering |
| DE logFC rho | Spearman rho of log-fold-changes of the top 100 CPU DE genes of each cluster against the GPU values for the same genes, averaged over CPU-GPU cluster pairs matched with the Hungarian algorithm on shared cells (Leiden r = 1.0); metric defined for this study | Differential expression |

### Stress test: maximum capacity

To determine the maximum dataset size processable on a single DGX H100 node, we implemented a memory-optimised pipeline variant. The stress test used the 3,436,470-cell Census selection described above (and random subsets of it at 1.7M and 3.4M cells, seed = 42). Larger sizes were built by concatenating whole copies of the dataset, with renamed cell identifiers, plus a random draw of the remaining cells (6.9M cells: 2 copies; 10.3M: 3 copies; 11.9M: 3 copies plus 1,590,590 cells), so duplicated cells are present in the expression matrix and in the k-NN graph. Because duplicated cells reach the `min_cells` = 3 threshold, the number of genes passing QC grew with replication (41,344 at 3.44M, 42,394 at 6.87M and 44,158 from 10.3M cells). At 3,436,470, 6,872,940 and 10,309,410 cells, cuML KMeans with k = 50, 100 and 200 replaced the three Leiden resolutions. DE was skipped (`--skip-de`) at every size except 1.7M and 3.4M cells.
The key optimisations were: (i) scaling on CPU rather than GPU (leveraging 2 TB system RAM); (ii) a covariance PCA in which the parent process scattered the scaled matrix across the 8 GPUs, computed per-GPU partial products (2,000 x 2,000), summed and eigendecomposed them on GPU 0 and projected locally; the matrix was not re-centred after clipping at `max_value` = 10 and partial products were accumulated in float32, so the result approximates, but is not identical to, standard PCA; (iii) lean GPU transfer that replaces the dense matrix with an empty sparse placeholder after PCA, since downstream steps (neighbours, clustering, UMAP) only require the PCA embedding; and (iv) a reduced RMM pool (2 GB) for each Dask-CUDA worker; the workers were started but performed no computation.
We ran the memory-optimised pipeline at 15 sizes from 3.4M to 11.9M cells, refining the step size towards the failure point; single attempts at 12.0M and 13.7M cells (4 copies of the dataset) did not complete. Two further variants were run: a sparse-scatter variant computes per-gene mean and standard deviation from the sparse matrix on CPU and lets each GPU densify and scale its own chunk, so the dense matrix never exists on CPU; a chunked variant selects HVGs from per-gene statistics accumulated over 100,000-cell batches and computes PCA by batch-wise covariance accumulation. CPU memory was recorded as the resident set size of the parent Python process (`psutil.Process().memory_info().rss`), sampled immediately before and after each pipeline step, with an explicit garbage collection before each pre-step sample; the reported peak is the maximum over these post-step samples. This instrumentation yields a lower bound on the job's true memory use for two reasons: it cannot observe allocations that are made and released within a single step, and it excludes the resident memory of the eight Dask-CUDA worker processes, which the SLURM cgroup does account for. The replication of the dataset for sizes above 3,436,470 cells ran between data loading and QC, outside any timed step: at 11.9M cells it accounts for the 302.34 GiB increase between these two samples, and its transient peak was not sampled. GPU memory was recorded with NVML as device memory in use, summed over the eight GPUs; it includes the RMM pools of the Dask-CUDA workers. All memory values are in GiB (bytes / 1024^3).

### Differential expression at scale

DE was benchmarked on a 3,400,000-cell random subset of the Census selection (seed = 42; 3,399,892 cells and 41,321 genes in `adata.raw` after QC). Differential expression testing at atlas scale is constrained by hardware, which shaped the design of this benchmark. The matrix used for DE, `adata.raw.X`, holds log-normalised values rather than raw counts in this pipeline, and the GPU tests processed it in gene chunks, either scattered across GPUs or streamed through a single GPU. We timed six DE configurations (Table 7): a t-test on CPU (Scanpy); a t-test and a Wilcoxon test with gene chunks scattered across 8 GPUs; the same two tests with gene chunks streamed through one GPU; and pseudo-bulk aggregation followed by a Wilcoxon test on CPU. A Wilcoxon test on CPU was not run at this size and pseudo-bulk was not run on GPU, so the design is not a full factorial. In the scatter strategy a single host thread processed the chunks in sequence, alternating devices, so the GPUs did not work concurrently. Gene chunks of 500 were used for GPU strategies, giving 500 x 3.4M x 4 bytes approximately 6.8 GB per chunk, well within the 80 GB per-device limit. The GPU tests were custom CuPy kernels, not `rank_genes_groups`: the Wilcoxon kernel assigned ordinal ranks without averaging ties and computed neither p-values nor a multiple-testing correction, so it yields a rank-sum statistic used here for timing only. GPU timings start after `adata.raw.X` was converted to CSC format, whereas CPU timings cover the whole `rank_genes_groups` call. Pseudo-bulk aggregation summed the values of `adata.raw.X` over donor x cluster groups (Census `donor_id`, 202 donors; groups with fewer than 5 cells discarded; 2,431 pseudo-samples over 81 clusters), re-normalised the sums to counts per million, applied a second log transformation and compared clusters with a Wilcoxon test. We use this aggregation as a timing proxy for pseudo-bulk analysis; count-based methods such as edgeR or DESeq2 are recommended for pseudo-bulk DE between conditions [@Squair2021].

## Spatial transcriptomics

### Datasets

Spatial benchmarks used two 10x Genomics public datasets, both obtained from the 10x Genomics public data portal. The first is Visium v1 Mouse Brain Sagittal Anterior, the standard spot-based spatial transcriptomics platform, consisting of 2,695 spots at 55 um resolution and approximately 32,285 genes. The second is the Visium HD Spatial Gene Expression Library, Mouse Brain (FFPE), processed by 10x Genomics with Space Ranger 3.0.0 (CytAssist; Visium Mouse Transcriptome Probe Set v2.0), benchmarked at two bin sizes: 8 um (393,543 bins) and 2 um (6,296,688 bins, randomly subsampled to 400,000 bins with seed 42; 389,492 after QC), each quantifying 19,059 genes. The Visium HD 2 um dataset was subsampled to 400,000 bins using the `--max-spots` flag so that the benchmark would fit within the RTX 4090's 24 GB VRAM. Random subsampling kept 6.35% of the 2 um bins, so the subsample has the bin density of a regular grid with a spacing of about 8 um, and its spatial neighbour graph and autocorrelation statistics do not describe the native 2 um resolution.

### Spatial analysis pipeline

The spatial pipeline comprised two phases: an expression analysis phase (shared with the scRNA-seq pipeline) and a spatial statistics phase (Table 3).

: **Table 3.** Spatial analysis pipeline steps. Steps 1-8 share parameters with the scRNA-seq pipeline (Table 1) except for QC filtering, which used `min_genes` = 1 for Visium HD (Space Ranger pre-filters on-tissue barcodes). Steps 9-14 are spatial-specific. {#tbl:spatial_pipeline}

| Step | Operation | GPU support | Notes |
|-----:|:----------|:-----------:|:------|
| 1-8 | Expression analysis (QC through UMAP) | Yes | As in Table 1; Leiden r = 1.0 for Visium, r = 0.1 for HD |
| 9 | Spatial neighbours | No | Delaunay triangulation (scipy.spatial) |
| 10 | Moran's I | Yes | Spatial autocorrelation per gene |
| 11 | Geary's C | Yes | Spatial autocorrelation per gene |
| 12 | Co-occurrence | Yes | Cluster co-occurrence across distance intervals |
| 13 | Neighbourhood enrichment | No | Cluster-cluster proximity enrichment |
| 14 | Ligand-receptor interaction | No | Squidpy re-implementation of CellPhoneDB [@Palla2022] |

The CPU baseline used Scanpy 1.12 for expression steps and Squidpy 1.8.1 [@Palla2022] for spatial steps.
The GPU pipeline used rapids-singlecell 0.14.1 for both expression and GPU-accelerated spatial steps (Moran's I, Geary's C, co-occurrence).
Steps without GPU implementations (spatial neighbours, neighbourhood enrichment, ligand-receptor) were executed identically on CPU in both pipelines.

Co-occurrence and neighbourhood enrichment were skipped when the number of cell groups exceeded 500, because their memory grows with the square of the number of groups, and ligand-receptor analysis was skipped above 100,000 spots. These limits, and the Leiden resolution of 0.1 used above 100,000 spots (that is, for Visium HD), were practical choices to keep memory and run time tractable; we did not test their sensitivity.

### Spatial concordance metrics

We compared CPU and GPU spatial outputs along four complementary axes. Spatial autocorrelation concordance was measured as the Spearman rho between CPU and GPU per-gene Moran's I (and separately Geary's C) statistics across the 2,000 highly variable genes on which spatial autocorrelation was computed. Spatially variable gene (SVG) Jaccard overlap was computed for the top-N SVGs ranked by Moran's I (with N taking the values 50, 100, and 200) and for the complete set of genes passing FDR < 0.05. Clustering agreement was assessed by the adjusted Rand index and normalised mutual information of Leiden cluster assignments from the expression-based pipeline. Finally, co-occurrence concordance was the Spearman rho between the full CPU and GPU co-occurrence matrices.

## Hardware and software environment

Single-cell benchmarks ran on DGX H100 nodes of the UPSCALE/CONVECS cluster at the University of Padova; each node has 8 x NVIDIA H100 80 GB SXM GPUs connected via NVLink 4.0, two Intel Xeon Platinum 8480C CPUs (112 cores, 224 hardware threads) and 2 TB of DDR5 RAM.
The software environment was encapsulated in a Singularity container built from the NVIDIA RAPIDS base image (`nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`).
Key software versions: Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, Dask 2026.1.1, Dask-CUDA 26.2.0, Python 3.12.12.
Jobs were submitted via SLURM without exclusive allocation. The single-GPU, 2-GPU and 4-GPU benchmarks ran concurrently on node `poddgx01` (NVIDIA driver 535.247.01) with 16, 32 and 56 allocated CPUs, and the 8-GPU benchmark ran at the same time on node `poddgx02` (driver 535.183.01) with 100 CPUs, as many as the CPU baseline, which ran earlier on `poddgx01`. The stress test and the DE benchmark were pinned to `poddgx02` with 200 CPUs (100 for the 1.7M-cell stress-test run).

GPU spatial benchmarks ran on a workstation with an NVIDIA GeForce RTX 4090 (24 GB) and an AMD Ryzen Threadripper PRO 5995WX CPU (64 cores, 128 threads). The CPU reference ran on DGX node `poddgx02`, reserved exclusively, as a SLURM step with 100 CPUs (50 physical cores with two hardware threads each), the same number of CPUs as the scRNA-seq CPU baseline; the workstation CPU at 128 threads was measured as a control. CPU reference and GPU therefore ran on different machines. The NVIDIA driver of the workstation was 580.126.09 for preliminary runs in March 2026 and 595.99.02 for the runs reported here; GPU times of the steps that do not depend on the cell groups changed by a factor of 0.94 to 1.04 between the two.
The spatial container was built on the same `nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12` image as the scRNA-seq container, with Squidpy 1.8.1 [@Palla2022] and spatialdata [@Marconato2024] added on top for the spatial pipeline.
The GPU part of the spatial pipeline was run only on the workstation: on DGX node `poddgx02` (driver 535.183.01) a container based on RAPIDS 24.06 passed basic CuPy, RMM and rapids-singlecell tests, but smoke tests of the spatial GPU pipeline in it failed when CuPy initialised cuSPARSE and cuRAND, and the cause was not investigated further.

Each benchmark configuration was run five times; we report the mean +/- sample standard deviation (n = 5, ddof = 1) of all five repeats, and speedups are ratios of means. The five scRNA-seq repeats ran in the same process, so the first includes JIT compilation and library loading (for example, CPU neighbour search at 10k cells took 19.90 s in the first repeat and 1.12 s on average in the others). Peak RAM and VRAM are means of per-repeat peaks. The stress test, the DE benchmark and the concordance analysis were run once.
For the spatial benchmarks each repeat ran in a new process with empty Numba and CuPy JIT caches, so every repeat includes JIT compilation and, for ligand-receptor analysis, the download of the OmniPath database. Co-occurrence, neighbourhood enrichment and ligand-receptor analysis used the same cell groups in all runs, the Leiden labels of the first CPU reference repeat. Squidpy 1.8.1 sets the Numba thread count to one during neighbourhood enrichment and keeps it for the rest of the process, so ligand-receptor analysis, which follows it, ran with one Numba thread in both pipelines.

## Reproducibility

All code, Dockerfiles, SLURM submission scripts and result JSON files are available at <https://github.com/lucavd/2026.scRNA_DGX>. Per-cell outputs (cluster labels, HVG lists, DE tables, k-NN indices, PCA loadings, Moran's I and Geary's C values) and SLURM logs are not in the repository because of their size; the stress-test results at 1.7M and 3.4M cells and the chunked 12M-cell run were produced by intermediate versions of the scripts that were not committed.
The scRNA-seq benchmarks ran in a Singularity container built from the Docker image `lucavd/sc-benchmark:latest`, whose digest was not recorded; the spatial benchmarks ran in Docker (workstation) and Apptainer (DGX CPU reference) containers from `lucavd/sc-benchmark-spatial:latest` (image id sha256:738c8cc7301590c95a3ddc3b7dd74bafeefee1f1ce188063e14a166a707a6ddd). Both images derive from `nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`; their Dockerfiles do not pin package versions, so the versions used are those recorded at runtime in each result file (Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, RMM 26.2.0, NumPy 2.2.6, igraph 1.0.0).
Random seeds were fixed at 42 for all stochastic operations: subsampling (`numpy.random.choice`), PCA (`sc.pp.pca` / `rsc.pp.pca`), Leiden (`sc.tl.leiden` / `rsc.tl.leiden`), and UMAP (`sc.tl.umap` / `rsc.tl.umap`).
GPU reductions that use atomic operations can make results vary between runs because floating-point addition is not associative [@Collange2015; @Shanmugavelu2024]. In our runs GPU Leiden labels were identical across the five repeats at 10,000 cells in every GPU configuration, but differed between repeats in every configuration from 100,000 cells upward (and in three of the four at 50,000 cells), whereas CPU labels were identical across repeats at every size. CPU-GPU differences also arise from different algorithms and settings (Leiden implementation and iterations, PCA solver, neighbour search), which the concordance metrics capture together with numerical effects.

# Results

## Single-cell RNA-seq

### GPU acceleration achieves up to 120-fold end-to-end speedup

Table 4 summarises the benchmark results across all 23 pipeline-dataset-GPU configurations, each averaged over five repeats.
At 1.3 million cells, the GPU pipeline with eight GPUs allocated completed the full analysis in 435.2 +/- 16.2 s (7.3 min), compared with 52,056.2 +/- 392.0 s (14.5 h) for the CPU pipeline, a 119.6-fold speedup. With two GPUs allocated the time was 493.3 +/- 10.3 s (105.5-fold); the difference lies in data loading (149.0 against 90.6 s, runs on different nodes), because the additional GPUs did not take part in the computation. Wilcoxon differential expression accounted for 93.5% of the CPU time (48,688.3 s of 52,056.2 s); without it the speedup was 7.9-fold with two GPUs and 9.2-fold with eight. Dicks et al. report, on the 10x Genomics mouse brain dataset and with differential expression and I/O excluded, more than 120-fold on one B200 GPU and 110-fold on one H200 GPU against a 32-core workstation CPU [@Dicks2026]; in our hybrid pipeline a similar end-to-end factor arises mainly from the CPU Wilcoxon test.
Even at 10,000 cells, the single-GPU pipeline was 12-fold faster than the CPU baseline (3.3 +/- 1.7 s vs 39.5 +/- 10.2 s).
With a single GPU the speedup grew from 12.0x at 10k to 33.7x at 50k and 43.8x at 100k. At 500k and 1.3M cells only the hybrid pipeline could run (Section "Multi-GPU configuration"), and the speedup was 34.9x at 500k (2 GPUs) and 119.6x at 1.3M (8 GPUs; 105.5x with 2 GPUs); because the series mixes two pipelines, it is not a monotonic function of dataset size.

: **Table 4.** Summary of scRNA-seq benchmark results across all pipeline configurations. Times are mean +/- SD over five repeats. Single-GPU results for 500k and 1.3M cells are absent because the single-GPU pipeline failed during QC (Methods, Multi-GPU configuration). {#tbl:summary}

| Pipeline | Cells | GPUs | Total time (s) | SD (s) | Peak RAM (GiB) | Peak VRAM (GiB) |
|:---------|------:|-----:|---------------:|-------:|---------------:|---------------:|
| CPU (Scanpy) | 10k | 0 | 39.5 | 10.2 | 1.2 | --- |
| GPU (rapids) | 10k | 1 | 3.3 | 1.7 | 2.4 | 40.7 |
| GPU | 10k | 2 | 4.9 | 2.6 | 2.3 | 52.4 |
| GPU | 10k | 4 | 4.9 | 2.6 | 2.3 | 65.0 |
| GPU | 10k | 8 | 4.9 | 2.3 | 2.3 | 106.5 |
| CPU (Scanpy) | 50k | 0 | 282.5 | 9.1 | 3.6 | --- |
| GPU (rapids) | 50k | 1 | 8.4 | 2.2 | 5.4 | 40.7 |
| GPU | 50k | 2 | 14.7 | 2.4 | 3.5 | 52.4 |
| GPU | 50k | 4 | 14.6 | 2.6 | 3.5 | 65.0 |
| GPU | 50k | 8 | 15.1 | 2.2 | 3.4 | 106.5 |
| CPU (Scanpy) | 100k | 0 | 646.7 | 10.5 | 6.7 | --- |
| GPU (rapids) | 100k | 1 | 14.8 | 2.2 | 8.8 | 40.7 |
| GPU | 100k | 2 | 26.9 | 2.4 | 4.9 | 52.4 |
| GPU | 100k | 4 | 26.9 | 2.3 | 4.9 | 65.1 |
| GPU | 100k | 8 | 26.4 | 2.6 | 4.9 | 106.6 |
| CPU (Scanpy) | 500k | 0 | 4,346.7 | 40.3 | 29.7 | --- |
| GPU | 500k | 2 | 124.5 | 2.9 | 15.6 | 52.7 |
| GPU | 500k | 4 | 125.0 | 6.0 | 15.9 | 65.5 |
| GPU | 500k | 8 | 124.6 | 3.7 | 15.5 | 107.0 |
| CPU (Scanpy) | 1.3M | 0 | 52,056.2 | 392.0 | 107.4 | --- |
| GPU | 1.3M | 2 | 493.3 | 10.3 | 60.7 | 74.9 |
| GPU | 1.3M | 4 | 486.6 | 20.2 | 60.7 | 92.7 |
| GPU | 1.3M | 8 | 435.2 | 16.2 | 52.3 | 134.2 |

### Per-step speedup differs widely between operations

The per-step speedup heatmap (Fig. 1) and the corresponding absolute wall-time breakdown (Fig. 2) reveal that GPU advantage varies dramatically by operation type, from 0.36x (Leiden at resolution 0.5, 10k cells) to 329x (normalisation, 10k cells), nearly three orders of magnitude; both extremes are set by the first repeat (see below). Trivially parallelisable operations achieve the highest speedups: normalisation, which involves only element-wise division and logarithm, reached 329x at 10k cells, 206x at 50k cells, and 173x at 100k cells. Similarly efficient GPU operations include HVG selection (24-94x speedup), neighbours graph construction (44-88x; the CPU search ran on one numba thread, the Scanpy default, and in a separate measurement on another machine it was 1.16 to 2.48 times faster with 100 threads at 10k to 100k cells, see Methods), UMAP (27-45x), and differential expression testing (16-88x), all reflecting the fine-grained parallelism available on modern GPUs. PCA showed a more moderate but still substantial speedup that increased with dataset size, from 4.8x at 10k cells to 36.5x at 100k cells, consistent with the increasing arithmetic intensity of singular value decomposition on larger matrices.

![**Figure 1.** Per-step speedup of single-GPU rapids-singlecell (1xH100 80 GB) relative to CPU Scanpy (100 cores) at 10k, 50k, and 100k cells. Values > 1 indicate GPU is faster. Normalisation achieves up to 329x speedup; data loading shows a modest CPU advantage (0.76-0.85x).](../figures/fig1_speedup_heatmap.png)

![**Figure 2.** Step-level wall time decomposition for CPU vs single-GPU at 10k, 50k, and 100k cells. On CPU, DE testing and neighbour graph construction dominate; on GPU, all steps complete in seconds.](../figures/fig5_timing_breakdown.png)

However, not all operations benefited equally from GPU acceleration. Data loading was slightly slower on GPU at all three sizes (0.76-0.85x, CPU time divided by GPU time). The GPU timer covers reading the file and copying the matrix to the device (`anndata_to_GPU`), whereas CUDA context creation and RMM pool allocation happen before the timer starts; the GPU excess grew with dataset size (0.10 s at 10k, 0.55 s at 50k and 1.38 s at 100k cells), so it is a size-dependent transfer cost rather than a fixed overhead. We note that our pipeline relies on `h5py`-based readers that route data through CPU RAM, precluding GPU Direct Storage (GDS) optimisations that would bypass the CPU entirely; this remains an avenue for future improvement. For Leiden clustering at resolution 0.5, the CPU was faster at 10k cells (0.36x), but this reflects the first Leiden call of the first repeat (1.70 s against 0.09 to 0.23 s in later repeats); at resolutions 1.0 and 1.5 the GPU was already faster at 10k cells (1.36x and 1.60x). At resolution 0.5 the GPU was 1.80x faster at 50k and 3.58x faster at 100k cells. The first repeat of each configuration includes one-off library loading and compilation on both CPU and GPU, and it sets the extreme per-step values at 10k cells: excluding it, normalisation was 115.1x faster on GPU (instead of 329x) and Leiden at resolution 0.5 was 1.12x faster (instead of 0.36x). End-to-end speedups changed by at most 6% from 100k cells upwards.

### Multi-GPU configuration

At 500k and 1.3M cells only the hybrid Dask-CUDA pipeline could run. In the configuration used, the expression matrix was passed to PCA and neighbour search as a CuPy array on one device, so these steps ran on a single GPU whatever the number of GPUs allocated: PCA plus neighbour search took 17.23, 16.99 and 17.01 s with 2, 4 and 8 GPUs at 1.3M cells, and 2.98, 2.97 and 3.00 s at 500k cells, where total wall time was 124.5, 125.0 and 124.6 s. At 1.3M cells the 8-GPU run (435.2 s) was 12% faster than the 2-GPU run (493.3 s), but the difference arose in CPU-side data loading (149.0 s against 90.6 s), the jobs ran concurrently, and the 8-GPU job ran on a different node. The aggregate VRAM of the multi-GPU runs reflects the RMM pools pre-allocated by the Dask workers (78.6 GiB added at cluster start-up with 8 GPUs, at 10k as at 1.3M cells), not distributed data. Multi-GPU scaling was therefore not measured. Between 10k and 100k cells the 2-GPU hybrid pipeline was 49-82% slower than the single-GPU pipeline, because it runs preprocessing on the CPU.

![**Figure 3.** Total pipeline wall time vs number of GPUs (1, 2, 4, 8 H100), one line per dataset size. Error bars: SD over five repeats. Horizontal dotted lines: CPU baselines. Logarithmic y-axis. Flat GPU curves demonstrate sublinear multi-GPU scaling.](../figures/fig2_scaling_plot.png)

![**Figure 4.** Multi-GPU hybrid pipeline breakdown at 500k and 1.3M cells. CPU preprocessing (blue) dominates wall time; the multi-GPU phase (PCA + neighbours, pink) is a small fraction, explaining flat multi-GPU scaling.](../figures/fig6_multigpu_breakdown.png)

### CPU and GPU outputs agree closely at 10,000 cells

Concordance analysis on the 10,000-cell dataset (Fig. 5) demonstrated that the two pipelines yield closely agreeing outputs, despite computing on different processors and hardware. Concordance was computed on a separate pair of 10,000-cell runs made on 11 March 2026 (UTC), before the timed benchmark; in that run the CPU pipeline found 31, 40 and 45 clusters at resolutions 0.5, 1.0 and 1.5, against 31, 41 and 46 in all five benchmark repeats. Upstream analysis steps showed deterministic agreement: HVG selection was perfectly concordant with all 2,000 genes identical between CPU and GPU (Jaccard = 1.000), and PCA loadings were perfectly correlated with mean absolute Spearman rho = 1.000 across all 10 inspected principal components. Neighbourhood graph construction achieved high overlap with mean Jaccard = 0.930 (median = 0.938). This value is bounded by construction: the CPU and GPU neighbour sets compared have different sizes (the maximum and the median per-cell Jaccard are both 0.9375 = 15/16, and no cell reaches 1), so at least half of the cells reach that maximum and differ only by the size mismatch. In the saved neighbour lists of the benchmark runs at 10,000 cells, identical in all five repeats, each cell has 16 CPU and 15 GPU neighbour indices, the cell itself included, and for 95.0% of cells every GPU neighbour is also a CPU neighbour. The remaining differences are consistent with approximate neighbour search on CPU (PyNNDescent, the Scanpy default at this size) against exact brute-force search on GPU [@Gardner2025], rather than with floating-point precision.

Clustering concordance was high but not perfect. Leiden clustering at different resolutions yielded adjusted Rand indices ranging from 0.908 (resolution 1.0) to 0.963 (resolution 1.5), with corresponding normalised mutual information values from 0.951 to 0.971. The lower agreement at resolution 1.0 (40 clusters in both pipelines in the concordance run) does not reflect run-to-run stochasticity: at 10,000 cells each pipeline returned identical labels in all five benchmark repeats. It reflects differences between the two pipelines, which include the neighbour graph (above) and the Leiden implementation: igraph with `n_iterations=2` on CPU and cuGraph with up to 100 iterations on GPU. The downstream biological results also aligned well: differential expression log-fold-changes across 40 matched cluster pairs showed mean Spearman correlation of 0.946 (median 0.9995; the mean is lowered by two pairs, one of which shares no cells), with 34 of the 40 pairs above rho = 0.97.

At 10,000 cells the two pipelines therefore agreed closely. This does not establish interchangeability at atlas scale: from 50,000 cells upwards GPU Leiden labels varied across the five repeats at one or more resolutions despite a fixed seed, whereas CPU labels did not, and a comparison of Scanpy and rapids-singlecell on the 1.3-million-cell mouse brain data and its subsamples reported CPU-GPU ARI near 0.5 and concluded that the two are not interchangeable [@Gardner2025].

![**Figure 5.** Concordance between CPU and GPU pipelines on 10,000 cells. Left: ARI and NMI for Leiden clustering at three resolutions. Right: HVG Jaccard (1.000), PCA Spearman |rho| (1.000), and kNN Jaccard (0.930). All metrics indicate near-identical biological outputs.](../figures/fig3_concordance.png)

### Memory is not a bottleneck at benchmark scale

At the scales covered by the main benchmark (10k to 1.3M cells), neither memory tier was saturated. CPU RAM grew roughly in proportion to cell count (log-log slope 0.92 over 10k-1.3M cells, least squares on the five mean peaks; steeper, 1.35, between 500k and 1.3M cells), from 1.2 GiB at 10k to 107.4 GiB at 1.3M cells (Fig. 6, left panel), well below 6% of the 2 TB system memory. The dominant in-memory objects at 1.3M cells were the dense float32 matrix created during scaling (1.3M x 2,000 HVGs x 4 bytes, approximately 9.7 GiB) and the sparse raw count matrix (1.3M x 39,182 genes). GPU VRAM for single-GPU runs was approximately constant at 40.7 GiB across dataset sizes, dominated by the pre-allocated RMM pool. For multi-GPU runs, aggregate VRAM grew with the number of Dask workers, each of which pre-allocates an RMM pool (134.2 GiB with 8 GPUs at 1.3M cells, averaged over five repeats). At these scales neither memory tier limited the runs; CPU memory was pushed further only in the stress test described in the next subsection.

![**Figure 6.** Peak memory usage across dataset sizes. Left: CPU RAM; right: GPU VRAM (per-device maximum). Dashed red line: H100 80 GB VRAM limit. CPU RAM grows super-linearly; GPU VRAM is approximately constant for single-GPU runs due to RMM pool pre-allocation.](../figures/fig4_memory_profile.png)

### Stress test: 11.9 million cells on one DGX H100 node

To locate the true capacity limit of the DGX H100 node, we ran a separate stress test with the *memory-optimised pipeline* described in Methods (Section "Stress test: maximum capacity"). This variant moves scaling to CPU (exploiting the 2 TB system RAM), distributes PCA across all 8 GPUs via a covariance-matrix method, and replaces the full data matrix on GPU with an empty sparse placeholder after PCA so that only the low-dimensional embedding (n x 50 floats) resides on any GPU.

A binary search for the maximum processable cell count (Table 5) showed that the pipeline succeeded at 11.9 million cells (119 min). Above 3,436,470 cells the input was built by concatenating whole copies of the source dataset plus a random remainder, so these runs contain duplicated cells; the construction happens between data loading and QC and is not timed. "Pass" therefore denotes computational completion only: at 11.9M cells Leiden returned 135,710, 142,959 and 147,154 clusters at the three resolutions, against 58, 66 and 87 in a Leiden run on a 3,400,000-cell subset of the source dataset, a run not listed in Table 5. With this memory-optimised pipeline the single run at 12.0 million cells did not complete (the chunked variant described below completed at that size): after neighbour search had finished, the benchmark process exited with a timeout error while the Dask cluster was being shut down, before Leiden clustering started, and the job log records no out-of-memory error. Two runs at 13.7 million cells, one with Leiden and one with KMeans, were killed (signal 9) after HVG selection, while the full matrix was being copied to `adata.raw` and subset to the HVGs, before scaling.

The recorded peak RAM at 11.9M was 535 GiB (26% of the 2 TB machine, 30% of the 1.8 TB SLURM job allocation), leaving apparent headroom, while recorded peak aggregate VRAM was only 48.8 GiB out of 640 GiB (7.6%). As described in Methods, 535 GiB is the largest between-step resident set size of the parent process alone. Two features of the 11.9M trace show what between-step sampling misses. First, RAM rises from 124 GiB at the end of data loading to 426 GiB at the start of quality control; this 302 GiB increase is the construction of the replicated 11.9M-cell dataset from the 3.4M-cell source, which runs between the two timed steps. Second, normalisation and HVG selection each register a between-step delta below 0.1 GiB, which is possible only if their working memory is allocated and released inside the call. The step-level trace therefore records the pipeline's resting footprint between operations, not the peaks against which the SLURM cgroup enforces its limit. We report an indicative budget in Table 6. At 11.9M the three Leiden calls together changed between-step host RAM by less than 1 GiB (+0.48 GiB), which, as for normalisation and HVG selection, does not exclude transient allocations within the calls; the 20 GiB rise in aggregate VRAM just before the first Leiden call occurs when the script re-initialises the RMM pool on device 0 after neighbour search, so it does not come from Leiden itself.

We also tested cuML KMeans as a GPU-native clustering alternative to Leiden (Table 5): it completed at 3.4M, 6.9M and 10.3M cells and, like Leiden, was killed at 13.7M cells during CPU preprocessing, before clustering was invoked.
A sparse-scatter variant that avoided the CPU-side dense matrix was killed at 14M cells during Scanpy's HVG selection step, according to the job log.

Inspired by the chunked-preprocessing strategy of ScaleSC [@Hu2025], we also implemented a third variant that performs HVG selection on per-gene running statistics accumulated over 100,000-cell batches and computes PCA via batch-wise covariance accumulation, both directly from the sparse matrix without ever materialising a dense intermediate on CPU. This variant succeeded at 12.0 million cells (862 GiB peak RAM, 10 GiB aggregate VRAM, 131.5 min) but was killed at 15.0 million cells during the CSR-to-CSC layout conversion required for HVG column slicing, according to the job log.

: **Table 5.** Stress test results: maximum cell count on a single DGX H100 node (8xH100, 2 TB RAM) using the memory-optimised pipeline. Timings exclude DE testing, which was benchmarked separately (Table 7). Memory in GiB. Rows are a selection of the 16 sizes that completed (1.7M to 11.9M cells); the result files of all of them are in the repository. Above 3.4M cells the input contains replicated cells (see text). {#tbl:stress}

| Cells | Runtime (min) | CPU RAM (GiB) | GPU VRAM (GiB) | Clustering | Status |
|------:|--------------:|-------------:|--------------:|:-----------|:-------|
| 3.4M | 18 | 155 | 49 | KMeans | Pass |
| 6.9M | 38 | 308 | 49 | KMeans | Pass |
| 10.3M | 91 | 465 | 49 | KMeans | Pass |
| 11.5M | 114 | 517 | 49 | Leiden | Pass |
| 11.9M | 119 | 535 | 49 | Leiden | **Pass (max)** |
| 12.0M | --- | --- | --- | Leiden | Fail (Dask shutdown timeout after neighbours) |
| 13.7M | --- | --- | --- | Leiden, KMeans | Fail (killed after HVG selection) |

The three smaller rows were run with cuML KMeans instead of Leiden. Peak CPU RAM was similar for the two clustering methods at about 10M cells (465.4 GiB with KMeans at 10.31M, 460.5 GiB with Leiden at 10.2M), but runtimes were not (91.5 against 69.2 min, with QC taking 3,156 against 2,218 s; the runs were made on different days), so the runtime column combines two series and should not be read as a single curve.

: **Table 6.** Indicative memory budget at 11.9M cells, the largest completed run (GiB). Baseline components are read from the 11.9M-cell memory trace and sum to the 535 GiB recorded there; all rows refer to 11.9M cells. The transient contributions are estimated from the operations in the pipeline code; they are not measured, because the instrumentation samples only between steps and only the parent process (Methods). The budget does not account for the full working set at any moment, and is presented to indicate which operations dominate. {#tbl:memory_budget}

| Memory at 11.9M cells | GiB |
|:--------------------------|---:|
| **Baseline (largest between-step sample, measured at 11.9M)** | |
| &nbsp;&nbsp;&nbsp;&nbsp;Sparse raw matrix `adata.raw` (11.9M cells, replicated; RAM at the start of QC) | ~426 |
| &nbsp;&nbsp;&nbsp;&nbsp;Dense scaled HVG matrix `adata.X` (11.9M x 2,000, float32) | 89 |
| &nbsp;&nbsp;&nbsp;&nbsp;Remainder, by difference | 20 |
| &nbsp;&nbsp;&nbsp;&nbsp;*Measured subtotal (11.9M)* | **535** |
| **Contributions not represented in that subtotal** | |
| &nbsp;&nbsp;&nbsp;&nbsp;`adata.raw = adata.copy()`, a second copy of the full sparse matrix while the first is held (estimated) | +426 |
| &nbsp;&nbsp;&nbsp;&nbsp;Sparse to dense conversion before `sc.pp.scale`, one dense HVG matrix (estimated; measured net change between steps +81.7) | +89 |
| &nbsp;&nbsp;&nbsp;&nbsp;Scanpy `highly_variable_genes` internal temporaries | n.q. |
| &nbsp;&nbsp;&nbsp;&nbsp;Eight Dask-CUDA worker processes | n.q. |
| &nbsp;&nbsp;&nbsp;&nbsp;Leiden calls (host delta between steps at 11.9M) | < 1 |
| SLURM job allocation (`#SBATCH --mem=1800G`) | 1,800 |
| Physical machine memory (reported by the operating system) | 2,016 |

Two contributions could not be quantified (n.q.) with the present instrumentation. In the sparse-scatter variant at 14M cells the job was killed during Scanpy's `highly_variable_genes`, with 629.0 GiB in use after the dataset had been built (job log); the log does not record the size of the temporaries. The resident memory of the eight Dask-CUDA worker processes is charged to the SLURM cgroup but is invisible to parent-process sampling. Either could dominate the budget above.

### Differential expression: run-time comparison

The factorial differential expression benchmark at 3.4 million cells across 41,000 genes and 81 Leiden clusters (Table 7) compares run times only; statistical properties of the tests were not assessed. To keep the table tractable we reported all wall times against a single CPU denominator, the t-test (5,598 s): a CPU Wilcoxon baseline was not run at this scale, and pseudo-bulk operates on a different sample unit (donor x cluster pseudo-samples rather than individual cells), so no strict within-method CPU-to-GPU ratio exists for it. Consequently, the speedup column should be read as "which approach finishes fastest overall", not as a within-method GPU acceleration factor; t-test and Wilcoxon are distinct statistical tests with different computational complexity, and any direct runtime comparison between them is descriptive, not inferential.

: **Table 7.** Differential expression benchmark at 3.4M cells x 41k genes x 81 Leiden clusters. Speedup is relative to CPU t-test (5,598 s). {#tbl:de}

| Method | Backend | GPUs | Time (s) | Speedup |
|:-------|:--------|-----:|---------:|--------:|
| t-test | CPU | 0 | 5,598 | 1.0x |
| Pseudo-bulk (Wilcoxon) | CPU (aggregated) | 0 | 127 | 43.9x |
| Wilcoxon (scatter) | GPU | 8 | 826 | 6.8x |
| Wilcoxon (chunk-stream) | GPU | 1 | 831 | 6.7x |
| t-test (scatter) | GPU | 8 | 1,655 | 3.4x |
| t-test (chunk-stream) | GPU | 1 | 1,649 | 3.4x |

Pseudo-bulk aggregation was the fastest strategy: aggregating log-normalised expression by donor and cluster reduced 3.4 million cells to 2,431 pseudo-samples (about 30 per cluster), and the analysis completed in 127 s (2.1 min), 43.9 times sooner than the cell-level CPU t-test (5,598 s, 93 min). Among cell-level tests on GPU, the Wilcoxon implementation (826 s) finished sooner than the t-test (1,655 s), and multi-GPU scatter (826 s for Wilcoxon) was essentially equivalent to single-GPU chunk-and-stream (831 s).

## Spatial transcriptomics

### GPU speedup scales dramatically with platform resolution

Table 8 summarises the spatial benchmark results across three Visium platforms.

: **Table 8.** Spatial transcriptomics benchmark results (RTX 4090, mean of repeats 2-5). {#tbl:spatial_summary}

| Platform | Spots/Bins | CPU total (s) | GPU total (s) | Speedup | CPU RAM (GB) | GPU VRAM (GB) |
|:---------|----------:|---------------:|--------------:|--------:|-------------:|--------------:|
| Visium v1 | 2,695 | 10.0 | 6.0 | 1.7x | 1.3 | 12.9 |
| Visium HD 8 um | 393,543 | 4,068 | 79 | 51.6x | 8.1 | 22.6 |
| Visium HD 2 um | 389,492 | 1,042 | 97 | 10.8x | 10.8 | 22.6 |

End-to-end speedup increased from 1.7x on Visium v1 (2,695 spots) to 51.6x on Visium HD 8 um (393,543 bins) (Fig. 7), demonstrating that GPU acceleration becomes increasingly valuable as spatial resolution increases.

![**Figure 7.** Total pipeline wall time (CPU vs GPU) for three Visium spatial platforms on a single RTX 4090. End-to-end speedups range from 1.7x (Visium v1, 2,695 spots) to 51.6x (Visium HD 8 um, 393,543 bins). Error bars: standard deviation across repeats 2-5 (repeat 1 excluded for JIT warmup). HD 2 um was subsampled to 400k bins due to local VRAM constraints.](../figures/fig7_spatial_speedup.png)

The dominant contributor to the HD 8 um speedup was co-occurrence analysis, which achieved a 3,272x speedup (from 3,573 s on CPU to 1.09 s on GPU; Fig. 8).
The CPU implementation computes pairwise cluster co-occurrence across distance intervals with O(n^2) complexity per interval, while the GPU implementation parallelises this computation across all bins and intervals simultaneously.
At 393,543 bins with 7 Leiden clusters, co-occurrence alone consumed 88% of the CPU pipeline time.

![**Figure 8.** Per-step GPU speedup for Visium HD 8 um (393,543 bins). Co-occurrence analysis achieves a 3,272x speedup (CPU: 3,573 s to GPU: 1.09 s), the single largest acceleration measured in this study. Spatial autocorrelation (Moran's I, Geary's C) shows 162-163x speedup. Steps without GPU implementations (spatial_neighbors, nhood_enrichment) remain at 1.0x.](../figures/fig8_spatial_perstep.png)

Other large GPU advantages on HD 8 um included PCA (257x), normalisation (176x), spatial autocorrelation (162-163x), and UMAP (159x).
Leiden clustering achieved a 16x speedup, and k-NN graph construction achieved 20x.

: **Table 9.** Per-step wall time and GPU speedup for spatial-specific operations on Visium HD 8 um (393,543 bins), the platform showing the largest overall speedup. Steps labelled "CPU-only" in the Speedup column lack a GPU implementation in rapids-singlecell 0.14.1; the "GPU (s)" value for those rows reports the wall time of the CPU fallback executed transparently inside the GPU pipeline, not a GPU-accelerated measurement. {#tbl:spatial_steps}

| Step | CPU (s) | GPU (s) | Speedup |
|:-----|--------:|--------:|--------:|
| Co-occurrence | 3,573 | 1.09 | 3,272x |
| PCA | 72.8 | 0.28 | 257x |
| Normalisation | 0.65 | 0.004 | 176x |
| Moran's I | 47.9 | 0.30 | 162x |
| Geary's C | 47.4 | 0.29 | 163x |
| UMAP | 194.3 | 1.22 | 159x |
| HVG selection | 0.94 | 0.012 | 76x |
| Expression neighbours | 39.4 | 2.00 | 20x |
| Leiden clustering | 19.2 | 1.17 | 16x |
| Spatial neighbours | 55.9 | 57.4 | 1.0x (CPU-only) |
| Nhood enrichment | 11.8 | 11.4 | 1.0x (CPU-only) |

Visium HD 2 um showed a lower overall speedup (10.8x) despite a similar bin count (389,492) because co-occurrence analysis was skipped (>500 clusters exceeded the O(k^2) memory threshold).
Without this step, UMAP dominated the GPU pipeline time (92x speedup, but consuming 92% of the 97 s total GPU time).

On Visium v1, the modest 1.7x overall speedup reflects the small dataset size (2,695 spots): GPU kernel launch overhead is not amortised, and CPU-only steps (spatial neighbours, ligand-receptor) dominate.

Three pipeline steps lacked GPU implementations and constituted the GPU pipeline's primary bottleneck: spatial neighbours (Delaunay triangulation via scipy.spatial, ~55 s on all HD platforms), neighbourhood enrichment (CPU-only), and ligand-receptor interaction (CPU-only, Visium v1 only).
Spatial neighbours alone represented 57-73% of total GPU pipeline time on HD platforms.

### Spatial concordance: near-perfect for spatial statistics, divergent for clustering at high resolution

Spatial autocorrelation concordance was near-perfect across all platforms (Table 10, Fig. 9).

![**Figure 9.** Concordance between CPU and GPU spatial analysis pipelines across three Visium platforms. Spatial autocorrelation statistics (Moran's I, Geary's C) show near-perfect agreement (Spearman rho >= 0.9995). SVG Jaccard overlap of the top 50 genes equals 1.0 for all platforms. Cluster concordance (ARI) degrades at HD 2 um resolution (0.080) due to algorithmic differences between cugraph and leidenalg Leiden implementations at high granularity.](../figures/fig9_spatial_concordance.png)
Moran's I and Geary's C Spearman correlations between CPU and GPU exceeded 0.9995 in all cases.
The top-50 spatially variable genes were identical (Jaccard = 1.0) across all three platforms, confirming that GPU-accelerated spatial autocorrelation produces scientifically equivalent results.
At the FDR < 0.05 threshold, SVG overlap remained high: 100% (Visium v1), 99.9% (HD 8 um), and 98.2% (HD 2 um).

: **Table 10.** Spatial concordance between CPU and GPU pipelines. SVG Jaccard reports the overlap of top-N spatially variable genes ranked by Moran's I. {#tbl:spatial_concordance}

| Metric | Visium v1 | HD 8 um | HD 2 um |
|:-------|----------:|------------:|------------:|
| Moran's I Spearman rho | 1.0000 | 0.9999 | 1.0000 |
| Geary's C Spearman rho | 1.0000 | 0.9995 | 0.9999 |
| SVG Jaccard (top 50) | 1.000 | 1.000 | 1.000 |
| SVG Jaccard (FDR < 0.05) | 1.000 | 0.999 | 0.982 |
| Cluster ARI | 0.856 | 0.974 | 0.080 |
| Cluster NMI | 0.892 | 0.940 | 0.667 |
| N clusters (CPU / GPU) | 16 / 15 | 7 / 3 | 2,559 / 538 |

Expression-based Leiden clustering showed platform-dependent concordance.
On Visium v1 (ARI = 0.856, NMI = 0.892) and HD 8 um (ARI = 0.974, NMI = 0.940), concordance was high, consistent with the scRNA-seq results.
However, on HD 2 um, clustering diverged substantially (ARI = 0.080, NMI = 0.667): the CPU pipeline identified 2,559 clusters while the GPU pipeline found 538.
This 4.75x difference in cluster granularity arises from algorithmic differences between the leidenalg (CPU) and cuGraph (GPU) Leiden implementations, which are amplified at high resolution where the graph has many near-degenerate partitions.
Subsampling from 6.3 million to 389,492 bins also disrupts spatial contiguity, compounding the effect.
This is a known limitation of comparing stochastic graph-partitioning algorithms across implementations, not a deficiency of GPU computation per se.

### Memory usage is modest across spatial platforms

Peak GPU VRAM was 12.9 GB on Visium v1 and plateaued at 22.6 GB for both HD platforms (Table 8), well within the RTX 4090's 24 GB capacity.
CPU RAM ranged from 1.3 GB (Visium v1) to 10.8 GB (HD 2 um).
These modest requirements suggest that spatial benchmarks at full Visium HD resolution (6.3M bins at 2 um) would fit comfortably within DGX H100 memory.

# Discussion

Our benchmark demonstrates that rapids-singlecell on NVIDIA H100 GPUs shortened the standard Scanpy pipeline by about one to two orders of magnitude, with speedups that grew with dataset size within each configuration and that, at 1.3M cells, were driven mainly by CPU differential expression (Table 4); CPU and GPU results agreed closely at 10,000 cells, and the memory-optimised variant processed up to 11.9 million cells (12.0 million with chunked preprocessing), obtained by replicating a 3.4M-cell dataset.
The extension to spatial transcriptomics shows that GPU advantages are even more pronounced for spatial-specific operations, with co-occurrence analysis achieving over three orders of magnitude speedup.
These results reveal several important insights about GPU-accelerated single-cell analysis that merit detailed discussion.

The fundamental constraint underlying our results is that GPU speedup is inherently operation-specific and highly dependent on the computational structure of each step. Normalisation (173-329x), an element-wise operation limited by memory bandwidth rather than by arithmetic, had the largest speedup at every size, and neighbour graph construction (44-88x) benefited strongly from the GPU. The CPU neighbour search, however, ran pynndescent with a single numba thread (Scanpy's default `n_jobs = 1`; Methods); on a separate server, 100 threads made it 1.16, 1.91 and 2.48 times faster at 10,000, 50,000 and 100,000 cells, so against a multi-threaded CPU search the neighbour speedup would shrink to about 76x, 32x and 18x, and at 100,000 cells (95% bootstrap interval 8.6-33.1x) it would fall below that of PCA (36.5x). In contrast, data loading was slower on the GPU at every size tested (0.76-0.85x), and Leiden at 10,000 cells was slower on the GPU only at the first resolution (0.36x, mean of five repeats), an effect of the first cuGraph call in the first repeat (1.70 s against a mean of 0.13 s in repeats 2-5); at resolutions 1.0 and 1.5 the GPU was faster (1.36x and 1.60x). For data loading, CUDA context initialisation and RMM pool allocation took place before the timer (Methods), so the timed GPU step comprised reading the h5ad file through CPU RAM and transferring the matrix to the device; its excess over the CPU (+0.10, +0.55 and +1.38 s at 10,000, 50,000 and 100,000 cells) grew with dataset size, which is consistent with reading and conversion costs rather than with a fixed overhead. In practice, the GPU advantage grew with dataset size, but even at the smallest size tested (10,000 cells) the GPU pipeline was 12.0-fold faster end to end, partly because CPU differential expression took 54.9% of the CPU time; we did not observe a size at which GPU overhead outweighed its benefit. Dicks et al. note that below about 50,000 cells kernel-launch and host-device transfer overheads can make CPU execution comparable or faster [@Dicks2026]; their benchmark workflow excluded differential expression.

In our multi-GPU configuration the expression matrix stayed on one device, so PCA and neighbour search ran on a single GPU whatever the number of GPUs allocated, and the additional GPUs did not take part in the computation; the 12% shorter runtime with 8 GPUs at 1.3M cells came from CPU-side data loading in jobs that ran concurrently, the 8-GPU jobs on a different node from the 2- and 4-GPU jobs (Results). Multi-GPU scaling was therefore not measured in this study. Multi-GPU workflows built on Dask have been reported with RAPIDS on 8 V100 GPUs for 1.3 million cells [@Nolet2022] and with rapids-singlecell on 8 B300 GPUs for 100 million cells [@Dicks2026].

Because only one GPU computed in our multi-GPU configuration, we expect most of the benefit to be available on a single H100, although we did not run the hybrid pipeline with one GPU at 500k or 1.3M cells. The standard pipeline ran on a single H100 up to 100,000 cells, the largest single-GPU size we measured; the memory-optimised variant was run only with 8 GPUs. If confirmed on a single GPU, this would make the approach usable without a DGX, for example on rented cloud GPUs.

At 10,000 cells, the only size at which we measured concordance, the biological outputs of the GPU and CPU pipelines agreed closely. The perfect concordance on HVG selection (Jaccard = 1.000) and PCA loadings (Spearman rho = 1.000) reflects the deterministic nature of these operations given identical numerical inputs. The adjusted Rand indices for Leiden clustering ranged from 0.908 to 0.963 across resolutions, in a concordance run separate from the timed repeats. Since each pipeline returned identical labels in all five timed repeats at this size, these differences reflect the two implementations and their settings (igraph with two iterations, cuGraph with up to 100) rather than run-to-run stochasticity. From 50,000 cells upwards, however, GPU Leiden labels differed between repeats with a fixed seed in at least one GPU configuration at each size, while CPU labels did not, and other studies report CPU-GPU adjusted Rand indices of about 0.5 for clustering of up to 1.3 million cells [@Nolet2022; @Gardner2025]; whether the two pipelines are interchangeable at atlas scale therefore remains to be shown.

In the memory-optimised pipeline we tested, GPU VRAM did not limit the number of cells; ScaleSC [@Hu2025] and Dicks et al. [@Dicks2026] reach larger datasets with chunked or out-of-core preprocessing, so the limit we observed belongs to the pipeline rather than to GPU analysis in general. At 11.9 million cells, the largest size completed with this pipeline, aggregate GPU VRAM remained flat at 48.8 GiB (7.6% of the 640 GiB total) while the recorded peak CPU RAM reached 535 GiB, 30% of the 1,800 GiB job allocation. The single run at 12.0M cells stopped with a timeout while the Dask cluster was shut down after neighbour search, so it does not show where the memory limit lies; the runs at 13.7M cells were killed by the system (signal 9) without an out-of-memory message, and our between-step sampling of the parent process cannot show whether transient allocations exceeded the SLURM cgroup limit (Table 6). Preprocessing that avoids dense or duplicated host-side intermediates, as in chunked approaches such as ScaleSC [@Hu2025], is the natural route to larger datasets. Our ScaleSC-inspired chunked variant indeed reduced aggregate VRAM by a factor of five (48.8 GiB to 9.6 GiB) and completed 12.0M cells (it was killed at 15.0M), while host RAM reached 862 GiB, which confirms that GPU memory was not the binding resource in this pipeline.

In our timing comparison, pseudo-bulk aggregation was the fastest route to a differential expression result (Table 7). Pseudo-bulk aggregation is recommended because it accounts for variation between biological replicates [@Squair2021], and in our benchmark it was also 44 times faster than the cell-level CPU t-test. Cell-level GPU tests finished 3-7 times sooner than the CPU t-test (Table 7); because the CPU Wilcoxon was not run at this scale, these ratios compare time to result rather than measure a within-method acceleration. On the GPU, our Wilcoxon rank-sum implementation, which computes rank statistics without tie correction or p-values (Methods), finished in 826 s and the t-test in 1,655 s; we did not profile the cause. For multi-donor designs, pseudo-bulk aggregation of raw counts analysed with count-based models such as DESeq2 [@Love2014] or edgeR [@Robinson2010] is recommended [@Squair2021]; our pseudo-bulk timing aggregated log-normalised values and used a Wilcoxon test, so it measures computational cost only.

Beyond scRNA-seq, the extension to spatial transcriptomics demonstrates that GPU acceleration becomes increasingly impactful for computationally intensive spatial statistics. The 3,272x speedup achieved for co-occurrence analysis on Visium HD 8 um data is, to our knowledge, the largest GPU speedup reported for any spatial transcriptomics operation, reflecting the O(n^2) algorithmic complexity of the CPU implementation which the GPU effectively parallelises across thousands of bins and spatial distance intervals simultaneously. Spatial autocorrelation statistics (Moran's I, Geary's C) achieved similarly impressive speedups of 162-170x with near-perfect numerical concordance (rho >= 0.9995), meaning that scientists can obtain identical rankings of spatially variable genes in seconds rather than minutes. The remaining CPU-only operations (spatial neighbours computation via Delaunay triangulation, neighbourhood enrichment, and ligand-receptor analysis) represent clear opportunities for future GPU-native implementations and likely harbour substantial additional speedup potential.

A notable finding from spatial analysis concerns clustering at extreme resolution. The dramatic divergence at Visium HD 2 um (ARI = 0.080) is not specific to GPU versus CPU comparison; rather, it reflects the fundamental sensitivity of stochastic graph-partitioning algorithms to implementation details when the solution landscape contains many near-degenerate partitions. At 389,492 spatial bins with resolution parameter 0.1, local optima abound, and the leidenalg (CPU) and cuGraph (GPU) implementations explore this landscape through different vertex orderings and local heuristics. This observation suggests that users working at ultra-high spatial resolution should not rely on a single run of any Leiden implementation, but instead employ consensus clustering approaches or spatial-aware alternative methods that explicitly account for tissue geometry.

Our study contains several limitations that should be considered when generalising these findings. All scRNA-seq experiments used mouse brain cells from CELLxGENE Census: a random sample for the scaling benchmark and the full 3,436,470-cell selection for the stress test, replicated by concatenation beyond that size, and a 3.4M-cell subset of it (202 donors) for differential expression; performance profiles may differ for other tissues and for datasets with different sparsity patterns or gene counts. Concordance analysis was performed at 10,000 cells; larger datasets may exhibit different adjusted Rand index distributions or reveal additional numerical differences. The CPU baseline was a SLURM allocation of 100 logical CPUs on a node with 224, and we did not measure how Scanpy runtimes scale with the number of threads. In the hybrid runs at 1.3M cells, Scanpy QC took 188.2 s with 32 allocated CPUs and 186.6 s with 100, which suggests that some steps are largely single-threaded; the speedups are therefore relative to this allocation, not per core. The stress test employing the memory-optimised pipeline is mathematically equivalent to but not implementation-identical to the standard rapids-singlecell workflow, introducing potential differences in how the optimization generalises to other analyses. The GPU part of the spatial benchmark ran on an RTX 4090 workstation, while its CPU reference ran on a DGX node; multi-GPU spatial analysis and the full Visium HD 2 um resolution (6.3 million bins) were not benchmarked. This was not a design choice: the cluster nodes we used ran drivers 535.247.01 (1-, 2- and 4-GPU runs) and 535.183.01 (8-GPU runs and stress test), which cap the CUDA runtime at 12.2, and while the scRNA-seq pipeline ran there through forward compatibility, the GPU components of the spatial stack did not; a container rebuilt on RAPIDS 24.06 with CUDA 12.2 passed basic GPU tests on a node with driver 535.183.01 but failed the spatial smoke test at the initialisation of CUDA libraries, and was not pursued (Methods). Driver versions on shared production hardware thus constrain which GPU software stack can be deployed. Scaling analysis was confined to a single DGX H100 node (1-8 GPUs); we did not benchmark multi-node configurations (e.g., 16 GPUs across two nodes interconnected by InfiniBand), and since our multi-GPU configuration did not distribute any step (Results), it gives no indication of how a distributed pipeline would behave across nodes. A further limitation concerns the multi-GPU configuration itself: at 500k and 1.3M cells we ran only the Dask-CUDA hybrid, in which, as implemented, preprocessing ran in Scanpy on the host CPU; rapids-singlecell 0.14.1 provides Dask-based routes for QC, normalisation, log1p, scaling and PCA that we did not use. The share of the timed total spent in CPU preprocessing (data loading, QC, normalisation and HVG selection) in the 8-GPU hybrid runs at 1.3M cells (78.0%, mean of five repeats) is thus a property of our configuration, which ran preprocessing in Scanpy on the CPU, rather than an intrinsic limit of GPU acceleration. A second limitation concerns the memory instrumentation of the stress test itself: CPU memory was sampled between pipeline steps and for the parent process only, so the reported peaks are lower bounds and the attribution in Table 6 is indicative rather than measured. Resolving it would require continuous sampling of the whole process tree, or the peak usage recorded by the scheduler's cgroup, neither of which we collected. Finally, we did not benchmark integration methods (Harmony [@Korsunsky2019], scVI [@Lopez2018]) or multi-sample spatial experimental designs, which represent important directions for ongoing work.

# Conclusions

At 1.3M cells, rapids-singlecell on NVIDIA H100 GPUs reduced a 14.5-hour Scanpy pipeline to 7.3 minutes with 8 GPUs (8.2 minutes with 2), most of the gain coming from Wilcoxon differential expression, which accounted for 93.5% of the CPU time (without it, the speedup was 7.9-9.2-fold); CPU and GPU results agreed closely at 10,000 cells, the only size at which concordance was measured.
In a stress test on replicated copies of a 3.4M-cell dataset, a single DGX H100 node completed 11.9M cells (12.0M with chunked preprocessing) while the recorded GPU memory stayed at 7.6% of the total, so GPU memory did not set the limit.
In the multi-GPU configuration we used, the expression matrix stayed on one GPU and the additional GPUs took no part in the computation, so multi-GPU scaling was not measured.
For differential expression, pseudo-bulk aggregation was the fastest option, 44x faster than the cell-level CPU t-test.
For spatial transcriptomics, GPU acceleration delivers 51.6x end-to-end speedup on Visium HD, with co-occurrence analysis achieving a 3,272x speedup and spatial autocorrelation concordance exceeding 0.9995.
These results provide practical guidance for analysing atlas-scale single-cell and spatial datasets [@Regev2017].

# Conflict of Interest

The authors declare no conflict of interest.

# Acknowledgements

The computational resources for the scRNA-seq benchmarks and for the CPU reference of the spatial benchmarks were provided by the
UPSCALE/CONVECS DGX H100 cluster at the University of Padova. This work was supported in part by the high-performance computing infrastructure developed under the project "CONVECS", funded by the PR Veneto FESR 2021-2027 program, Priority 1 - Specific Objective 1.1 - Action 1.1.2. The authors used a large language model-based assistant to check the analysis code against the text, to recompute reported values from the result files with scripts and to draft revisions of the text; the authors reviewed every change and take full responsibility for the content of this chapter.

# Funding

This study was co-funded by the BIRD 2024/START (SID) programs, Department of Cardio-Thoracic-Vascular Sciences (DCTV), University of Padova (PI: Daniele Sabbatini; 2024DCTV1SIDPROGETTI-00183) and by the Italian Complementary National Plan PNC-I.1 "Research initiatives for innovative technologies and pathways in the health and welfare sector" D.D. 931 of 06/06/2022, "DARE-DigitAl lifelong pRevEntion" initiative, code PNC0000002, CUP: B53C22006440001.

# Availability of Data and Software Code

All code, Dockerfiles, SLURM submission scripts, and benchmark result JSON
files are available at <https://github.com/lucavd/2026.scRNA_DGX>.

# References
