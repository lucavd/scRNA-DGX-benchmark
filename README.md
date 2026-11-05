# scRNA-DGX-benchmark

Release v1.0.0, archived on Zenodo: <https://doi.org/10.5281/zenodo.23984290>.

GPU-accelerated single-cell and spatial transcriptomics benchmark: rapids-singlecell on NVIDIA H100 GPUs against Scanpy on 100 logical CPUs of a DGX H100 node (scRNA-seq), and an RTX 4090 against the same CPU reference (spatial). This is the cleaned, archived release of the working repository <https://github.com/lucavd/2026.scRNA_DGX>. The chapter extending the CIBB 2026 short paper in Springer LNBI and its Supplementary Material are in `manuscript/` (`full_paper_LNBI.md`, `supplementary_LNBI.md`; LaTeX and PDF in `manuscript/lncs_latex/`).

Key findings, as reported in the LNBI chapter (every value is re-read from the result files by the scripts in `tools/`):

- scRNA-seq, 1.3 million mouse brain cells: the GPU pipeline took 435.2 s against 52,056.2 s on 100 logical CPUs (119.6-fold with eight GPUs allocated, 105.5-fold with two). Wilcoxon DE accounted for 93.5% of the CPU time; without it the speedup was 7.9-9.2-fold. Additional GPUs did no computation in this configuration.
- Concordance at 10,000 cells: HVG selection identical (Jaccard = 1.000), Leiden ARI 0.908-0.963.
- A memory-optimised pipeline completed 11.9 million cells, built from copies of a 3,436,470-cell dataset.
- Spatial, one RTX 4090 against 100 CPUs of a DGX H100 node: 1.4-fold on Visium v1, 6.9-fold on Visium HD 8 um (without co-occurrence) and 10.4-fold on a random 400k-bin subsample of Visium HD 2 um. GPU co-occurrence in rapids-singlecell 0.14.1 was wrong at 41 of 49 distances through 32-bit integer overflow; version 0.15.1 matched the CPU at all 49.
- The spatial figures of the short paper (March 2026 runs) are superseded by the new CPU reference of the chapter (`SPATIAL/results_v2/`).

## Repository structure

```
.
|-- Dockerfile, Makefile, constraints.txt, requirements-squidpy.txt   # container and pinned packages
|-- scripts/          # scRNA-seq benchmarks, data download, figure scripts
|-- slurm/            # SLURM submission scripts used on the DGX H100 cluster
|-- SPATIAL/          # spatial benchmark: scripts, Dockerfiles, March 2026 results, results_v2 (chapter reference)
|-- results/          # scRNA-seq benchmark JSON outputs
|-- results_v2/       # receipts of the checks of each revision step (S2-S7)
|-- figures/          # vector PDF figures, PNG previews, LEGENDS.md (file -> figure number)
|-- manuscript/       # chapter and Supplementary Material (Markdown, LaTeX llncs 2.26, PDF), bibliography,
|                     # second internal review (revisione_n2/, in Italian): ledger, receipts, scripts
|-- tools/            # deterministic checks that re-read every number of the text from the result files
|-- manifests/        # md5 manifest of the raw results
|-- docs/, reports/   # step-by-step provenance of the revision (decisions, expectations, reports; in Italian)
`-- CITATION.cff
```

## Requirements

- NVIDIA GPU with CUDA 12 support (tested on RTX 4090 locally and H100 SXM on the DGX).
- NVIDIA driver version that supports the CUDA 12.8 runtime (native or via forward-compatibility). The DGX cluster used for the paper runs driver 535.183.01, which is compatible via CUDA forward-compatibility for scRNA-seq workloads.
- Docker with the NVIDIA Container Toolkit (`nvidia-docker`) for GPU passthrough.
- Disk: ~50 GB for the container image plus datasets.
- RAM: 16 GB minimum to run on the 10k-cell tier; 64 GB+ recommended for 100k+.

## Quickstart with Docker

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/lucavd/scRNA-DGX-benchmark.git
   cd scRNA-DGX-benchmark
   ```

2. Build the image (or pull the pre-built one from Docker Hub):

   ```bash
   make build
   # or:
   docker pull lucavd/sc-benchmark:latest
   ```

3. Smoke-test that Docker sees the GPU and all libraries import:

   ```bash
   make test
   ```

   Expected output: `nvidia-smi` table plus library version strings (scanpy, rapids-singlecell, cupy).

4. Run the full benchmark pipeline on a small dataset (10k cells). The commands below use the Makefile targets; each one runs the corresponding Python script inside the container with the correct bind mounts.

   ```bash
   make download-data        # fetches the 1.3M mouse-brain dataset and subsamples
   make bench-cpu            # CPU baseline (Scanpy)
   make bench-gpu            # single-GPU GPU pipeline (rapids-singlecell)
   make concordance          # CPU vs GPU biological agreement
   ```

   All results land in `results/` as JSON.

### Opening an interactive shell inside the container

```bash
make run        # interactive shell with GPU access
make run-cpu    # interactive shell, CPU only
```

The current working directory is bind-mounted at `/workspace` inside the container.

## Running specific benchmarks

### scRNA-seq

CPU baseline and GPU single-device, 10k cells (default):

```bash
make bench-cpu
make bench-gpu
```

Larger scale (set `N_CELLS` to 10000, 50000, 100000, 500000, or 1300000):

```bash
docker run --rm --gpus all -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/benchmark_gpu.py \
        --data-dir /workspace/data \
        --output-dir /workspace/results \
        --n-cells 100000
```

Multi-GPU (requires 2, 4, or 8 devices):

```bash
docker run --rm --gpus all -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/benchmark_multigpu.py \
        --data-dir /workspace/data \
        --output-dir /workspace/results \
        --n-cells 500000 \
        --n-gpus 4
```

### Differential expression

The factorial DE benchmark (7 configurations, 3.4M cells):

```bash
docker run --rm --gpus all -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/test_de_benchmark.py \
        --data-dir /workspace/data \
        --output-dir /workspace/results
```

### Maximum-capacity stress test

Binary search for the largest processable cell count:

```bash
docker run --rm --gpus all -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/benchmark_maxpower.py \
        --data-dir /workspace/data \
        --output-dir /workspace/results \
        --find-limit
```

Chunked variant (Step 10c, ScaleSC-inspired):

```bash
docker run --rm --gpus all -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/benchmark_maxpower_chunked.py \
        --data-dir /workspace/data \
        --output-dir /workspace/results \
        --target-cells 12000000
```

### Spatial transcriptomics

Visium v1, Visium HD 8 um, and Visium HD 2 um benchmarks (Makefile targets):

```bash
# Visium v1 (classical)
make bench-spatial-cpu SPATIAL_PLATFORM=visium SPATIAL_BIN_SIZE=
make bench-spatial-gpu SPATIAL_PLATFORM=visium SPATIAL_BIN_SIZE=

# Visium HD 8 um
make bench-spatial-cpu SPATIAL_PLATFORM=visium_hd SPATIAL_BIN_SIZE=square_008um
make bench-spatial-gpu SPATIAL_PLATFORM=visium_hd SPATIAL_BIN_SIZE=square_008um

# Visium HD 2 um (subsample if VRAM is limited)
make bench-spatial-cpu SPATIAL_PLATFORM=visium_hd SPATIAL_BIN_SIZE=square_002um SPATIAL_MAX_SPOTS=400000
make bench-spatial-gpu SPATIAL_PLATFORM=visium_hd SPATIAL_BIN_SIZE=square_002um SPATIAL_MAX_SPOTS=400000

make spatial-concordance SPATIAL_PLATFORM=visium_hd SPATIAL_BIN_SIZE=square_008um
```

See `SPATIAL/SPATIAL.md` for the spatial-pipeline specifics.

### Figures

After the JSON outputs are produced in `results/`, regenerate all figures used in the manuscript:

```bash
docker run --rm -v $(pwd):/workspace lucavd/sc-benchmark:latest \
    python -u scripts/generate_figures.py \
        --results-dir /workspace/results \
        --figures-dir /workspace/figures
```

## Running on the DGX H100 cluster (SLURM)

The cluster does not allow user-installable software; benchmarks run inside a Singularity container converted from the same Docker image.

1. On the login node, pull and convert the image:

   ```bash
   cd /mnt/home/$USER
   singularity pull sc-benchmark.sif docker://lucavd/sc-benchmark:latest
   singularity cache clean
   ```

2. Submit the SLURM job scripts in `slurm/` (edit paths and account as needed):

   ```bash
   sbatch slurm/cpu_benchmark.sh     # 100-core CPU run
   sbatch slurm/gpu_1.sh             # 1 GPU
   sbatch slurm/gpu_4.sh             # 4 GPUs
   sbatch slurm/gpu_8.sh             # 8 GPUs
   sbatch slurm/maxpower.sh          # stress test
   sbatch slurm/de_benchmark.sh      # DE factorial
   ```

Each SLURM script bind-mounts `/mnt/home/$USER` into the container so that `data/` and `results/` are visible.

## Reproducibility

- All stochastic steps use seed `42`: `numpy.random.choice` for subsampling, `sc.pp.pca` / `rsc.pp.pca`, `sc.tl.leiden` / `rsc.tl.leiden`, `sc.tl.umap` / `rsc.tl.umap`.
- Container and package versions are pinned by the `Dockerfile` (`nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12`) and `constraints.txt`.
- Key versions: Scanpy 1.12, rapids-singlecell 0.14.1, CuPy 13.6.0, RMM 26.2.0, NumPy 2.2.6, Python 3.12.
- GPU floating-point arithmetic is non-deterministic (non-associative parallel reductions); bit-identical outputs are not expected. The concordance metrics in `results/concordance_*.json` quantify the resulting numerical drift.

## How the numbers of the chapter are checked

- `tools/s7_md2lncs.py` generates the LaTeX sources in `manuscript/lncs_latex/` from the Markdown; `tools/s7_check.py` checks that the numbers and citations of the `.tex` are those of the `.md`, in the same order.
- `tools/s3_check.py` (with `manuscript/revisione_n2/S3/valori_R*.py`), `tools/s4_check.py` and `tools/s5_check.py` recompute from the result files the values written in the text and drawn in the figures; `tools/s7_provenance.py` assigns a source to every number of the chapter and of the Supplementary Material.
- `tools/check_manifest.py` compares the raw results with `manifests/raw_results_md5_2026-11-03.tsv`.
- Per-cell outputs (cluster labels, DE tables, k-NN indices) and SLURM logs are not included because of their size. The input data are public: CZ CELLxGENE Census release 2025-11-08 (`scripts/download_data.py`), 10x Genomics Visium v1 Mouse Brain Sagittal Anterior and Visium HD Mouse Brain FFPE, Space Ranger 3.0.0 (`SPATIAL/scripts/download_spatial_data.py`, which checks the md5 of the Visium HD matrices).

## Citation

Please cite the LNBI chapter once published and this archive: <https://doi.org/10.5281/zenodo.23984290> (see `CITATION.cff`). Bibliography entries for all tools and datasets used are in `manuscript/bibliography/cibb2026_references.bib`.

## License

See `LICENSE.md`.
