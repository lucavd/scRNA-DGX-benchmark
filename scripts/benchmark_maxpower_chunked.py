#!/usr/bin/env python3
"""Max-power CHUNKED benchmark: push beyond 11.9M cells using chunked preprocessing.

Inspired by ScaleSC (Hu et al. 2025), this script avoids creating the full dense
matrix in CPU RAM.  The key insight: accumulate statistics (mean, variance,
covariance) from sparse cell-batches without ever materialising the dense
n_cells x n_genes matrix.

Differences from benchmark_maxpower.py:
  - HVG selection: accumulates mean/var from sparse batches (no sc.pp.highly_variable_genes)
  - Scale+PCA fused: computes mean/std from sparse, then each GPU batch does
    (X_sparse.toarray() - mean) / std and accumulates covariance (X.T @ X)
  - The dense matrix (n_cells x 2000 x 4B) NEVER exists in full on CPU

Previous limit: 11.9M cells (sc.pp.scale sparse->dense = 45 GB/M cells)
Expected new limit: significantly higher (only batch_size x 2000 = 800 MB at a time)

Usage:
    python scripts/benchmark_maxpower_chunked.py --data-dir data/ --output-dir results/
    python scripts/benchmark_maxpower_chunked.py --data-dir data/ --output-dir results/ --find-limit
    python scripts/benchmark_maxpower_chunked.py --help
"""

import argparse
import gc
import hashlib
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import cupy as cp
import numpy as np
import psutil
import pynvml
import rmm
import scanpy as sc
import scipy.sparse as sp

import rapids_singlecell as rsc


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
LEIDEN_RESOLUTIONS = [0.5, 1.0, 1.5]
CELL_BATCH_SIZE = 100_000  # cells per batch for chunked operations
N_TOP_GENES = 2000
N_PCA_COMPS = 50

OOM_EXIT_CODE = 10
INVALID_BENCHMARK_EXIT_CODE = 20
DASK_RMM_POOL_SIZE = "2GB"
DASK_RMM_MAXIMUM_POOL_SIZE = "70GB"


# ---------------------------------------------------------------------------
# Memory monitoring (same as benchmark_maxpower.py)
# ---------------------------------------------------------------------------

def init_nvml() -> None:
    pynvml.nvmlInit()

def shutdown_nvml() -> None:
    pynvml.nvmlShutdown()

def get_peak_ram_gb() -> float:
    return psutil.Process().memory_info().rss / (1024**3)

def get_vram_used_gb(device_index: int = 0) -> float:
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return info.used / (1024**3)

def get_total_vram_used_gb(n_gpus: int) -> float:
    return sum(get_vram_used_gb(i) for i in range(n_gpus))

def sha256_of_array(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def time_step(name: str, func, timings: dict, memory: dict, n_gpus: int) -> Any:
    """Time a pipeline step and record RAM + VRAM usage."""
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()

    ram_before = get_peak_ram_gb()
    vram_before = get_total_vram_used_gb(n_gpus)
    cp.cuda.Stream.null.synchronize()
    start = time.perf_counter()

    result = func()

    cp.cuda.Stream.null.synchronize()
    elapsed = time.perf_counter() - start

    ram_after = get_peak_ram_gb()
    vram_after = get_total_vram_used_gb(n_gpus)

    timings[name] = round(elapsed, 4)
    memory[f"{name}_ram_before_gb"] = round(ram_before, 2)
    memory[f"{name}_ram_after_gb"] = round(ram_after, 2)
    memory[f"{name}_vram_before_gb"] = round(vram_before, 2)
    memory[f"{name}_vram_after_gb"] = round(vram_after, 2)

    print(
        f"  {name:30s} | {elapsed:8.2f}s | "
        f"RAM: {ram_before:.1f}->{ram_after:.1f} GB | "
        f"VRAM(total): {vram_before:.1f}->{vram_after:.1f} GB"
    )
    return result


def get_gpu_info(n_gpus: int) -> dict:
    gpus = []
    for i in range(n_gpus):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpus.append({
            "device_index": i,
            "gpu_name": name if isinstance(name, str) else name.decode(),
            "gpu_vram_total_gb": round(mem_info.total / (1024**3), 1),
        })
    driver = pynvml.nvmlSystemGetDriverVersion()
    return {
        "gpus": gpus,
        "driver_version": driver if isinstance(driver, str) else driver.decode(),
    }


# ---------------------------------------------------------------------------
# Dask cluster (same as benchmark_maxpower.py)
# ---------------------------------------------------------------------------

def _get_running_scheduler_workers(client) -> dict[str, str]:
    def _inspect_scheduler(dask_scheduler):
        return {
            str(addr): str(getattr(worker_state, "name", "?"))
            for addr, worker_state in dask_scheduler.workers.items()
            if str(getattr(worker_state, "status", "")) == "Status.running"
        }
    return client.run_on_scheduler(_inspect_scheduler)


def setup_dask_cluster(n_gpus: int) -> tuple:
    from dask_cuda import LocalCUDACluster
    from dask.distributed import Client

    device_list = ",".join(str(i) for i in range(n_gpus))
    print(f"  Setting up Dask CUDA cluster with {n_gpus} GPUs ({device_list})...")

    cluster = LocalCUDACluster(
        CUDA_VISIBLE_DEVICES=device_list,
        n_workers=n_gpus,
        rmm_pool_size=DASK_RMM_POOL_SIZE,
        rmm_maximum_pool_size=DASK_RMM_MAXIMUM_POOL_SIZE,
    )
    client = None
    try:
        client = Client(cluster)
        deadline = time.monotonic() + 120
        stable_checks = 0
        n_workers = 0
        while time.monotonic() < deadline:
            workers = _get_running_scheduler_workers(client)
            n_workers = len(workers)
            if n_workers == n_gpus:
                stable_checks += 1
                if stable_checks >= 3:
                    break
            else:
                stable_checks = 0
            time.sleep(1)
        print(f"  Workers ready: {n_workers}")
        if n_workers != n_gpus:
            raise RuntimeError(
                f"Dask CUDA cluster started with {n_workers} workers, expected {n_gpus}"
            )
        return cluster, client
    except Exception as e:
        if client is not None:
            client.close()
        cluster.close()
        raise


def gpu_warmup(n_gpus: int) -> None:
    print(f"  GPU warmup ({n_gpus} GPUs)...", end=" ", flush=True)
    for i in range(n_gpus):
        with cp.cuda.Device(i):
            a = cp.random.random((100, 100), dtype=cp.float32)
            _ = cp.dot(a, a)
            cp.cuda.Stream.null.synchronize()
            del a, _
    cp.cuda.Device(0).use()
    cp.get_default_memory_pool().free_all_blocks()
    print("done")


# ---------------------------------------------------------------------------
# Chunked HVG selection (Seurat v1 on log-normalised data)
# ---------------------------------------------------------------------------

def chunked_hvg_selection(
    X_sparse: sp.csr_matrix,
    gene_names: np.ndarray,
    n_top_genes: int = 2000,
    batch_size: int = CELL_BATCH_SIZE,
) -> np.ndarray:
    """Select highly variable genes by accumulating mean/var from sparse batches.

    Replicates Scanpy's `flavor='seurat'` HVG selection (on log-normalised data):
    1. Compute per-gene mean and variance across ALL cells (streaming)
    2. Bin genes by mean expression into 20 bins
    3. Within each bin, compute z-normalised variance
    4. Select top n_top_genes by normalised variance

    The sparse matrix is NEVER converted to dense in full.

    Args:
        X_sparse: CSR sparse matrix (n_cells x n_genes), log-normalised.
        gene_names: Array of gene names.
        n_top_genes: Number of HVGs to select.
        batch_size: Cells per batch.

    Returns:
        Boolean mask of length n_genes (True = highly variable).
    """
    n_cells, n_genes = X_sparse.shape
    print(f"    Chunked HVG: {n_cells:,} cells x {n_genes:,} genes, batch={batch_size:,}")

    # Pass 1: accumulate sum and sum-of-squares per gene
    gene_sum = np.zeros(n_genes, dtype=np.float64)
    gene_sq_sum = np.zeros(n_genes, dtype=np.float64)

    n_batches = (n_cells + batch_size - 1) // batch_size
    for i in range(n_batches):
        start = i * batch_size
        end = min(start + batch_size, n_cells)
        # Slice rows from sparse — this is cheap (CSR row slicing is O(nnz_batch))
        batch = X_sparse[start:end]
        # Accumulate: .A1 flattens sparse .sum() to 1D array
        gene_sum += np.asarray(batch.sum(axis=0)).ravel()
        # For variance: sum of squares. For sparse, (batch.multiply(batch)).sum()
        # is efficient — only touches non-zero elements.
        gene_sq_sum += np.asarray(batch.multiply(batch).sum(axis=0)).ravel()

    gene_mean = gene_sum / n_cells
    # Var = E[X^2] - (E[X])^2, with Bessel correction
    gene_var = (gene_sq_sum / n_cells - gene_mean ** 2) * (n_cells / (n_cells - 1))

    # Clip variance floor to avoid log(0)
    gene_var = np.maximum(gene_var, 1e-12)

    # Seurat v1 dispersion: bin genes by mean, z-normalise variance within bins
    # Replicate scanpy's _highly_variable_genes_seurat_v1 logic
    gene_mean_log = np.log1p(gene_mean)  # scanpy uses log1p of mean for binning

    # 20 bins (scanpy default)
    n_bins = 20
    # Use percentile-based bins to handle skewed distributions
    bin_edges = np.percentile(gene_mean_log[gene_mean_log > 0], np.linspace(0, 100, n_bins + 1))
    # Ensure unique edges
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        # Fallback: all genes in one bin
        bin_edges = np.array([gene_mean_log.min(), gene_mean_log.max() + 1])

    gene_disp = gene_var / (gene_mean + 1e-12)  # dispersion = var / mean
    gene_disp_log = np.log(gene_disp + 1e-12)

    # Assign bins
    gene_bins = np.digitize(gene_mean_log, bin_edges) - 1
    gene_bins = np.clip(gene_bins, 0, len(bin_edges) - 2)

    # Z-normalise dispersion within each bin
    gene_disp_norm = np.zeros(n_genes, dtype=np.float64)
    for b in range(gene_bins.max() + 1):
        mask = gene_bins == b
        if mask.sum() < 2:
            continue
        d = gene_disp_log[mask]
        gene_disp_norm[mask] = (d - d.mean()) / (d.std() + 1e-12)

    # Select top n_top_genes by normalised dispersion
    # Exclude genes with zero mean (no expression)
    gene_disp_norm[gene_mean == 0] = -np.inf
    top_indices = np.argsort(gene_disp_norm)[::-1][:n_top_genes]
    hvg_mask = np.zeros(n_genes, dtype=bool)
    hvg_mask[top_indices] = True

    n_selected = hvg_mask.sum()
    print(f"    Selected {n_selected} HVGs (chunked Seurat v1)")

    return hvg_mask


# ---------------------------------------------------------------------------
# Chunked fused scale + covariance PCA (multi-GPU)
# ---------------------------------------------------------------------------

def chunked_scale_covariance_pca(
    X_sparse: sp.csr_matrix,
    hvg_indices: np.ndarray,
    n_gpus: int,
    n_comps: int = 50,
    batch_size: int = CELL_BATCH_SIZE,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fused scale + PCA without ever creating the full dense matrix.

    Two-pass algorithm:
      Pass 1: compute per-gene mean and std from sparse data (streaming)
      Pass 2: for each cell-batch, extract HVG columns, densify (small: batch x 2000),
              scale using precomputed mean/std, accumulate X.T @ X on GPU

    Then eigendecompose the 2000x2000 covariance on GPU and project in batches.

    Memory: only batch_size x n_hvgs x 4B dense at a time (~800 MB for 100k x 2000).
    The full n_cells x n_hvgs dense matrix NEVER exists.

    Args:
        X_sparse: CSR sparse matrix (n_cells x n_genes), log-normalised.
        hvg_indices: Column indices of selected HVGs.
        n_gpus: Number of GPUs for parallel projection.
        n_comps: PCA components.
        batch_size: Cells per batch.

    Returns:
        (X_pca, eigenvalues, variance_ratio) — all on CPU as numpy arrays.
    """
    n_cells = X_sparse.shape[0]
    n_hvgs = len(hvg_indices)

    # Extract HVG columns WITHOUT creating a full CSC copy.
    # scipy's CSR[:, cols] internally converts the entire matrix to CSC (~400 GB).
    # Instead, extract in row batches: each batch is small (100k x 44k),
    # so the temporary CSC per batch is only ~3 GB, not 400 GB.
    print(f"    Extracting {n_hvgs} HVG columns via row-batch slicing (no full CSC)...")
    t0 = time.perf_counter()
    if not sp.isspmatrix_csr(X_sparse):
        X_sparse = sp.csr_matrix(X_sparse)
    extract_batch = batch_size  # reuse the same batch size (100k cells)
    hvg_chunks = []
    for start in range(0, n_cells, extract_batch):
        end = min(start + extract_batch, n_cells)
        # Row slice on CSR is O(1); column slice on small matrix is cheap
        row_chunk = X_sparse[start:end]          # CSR row slice: fast, no copy
        hvg_chunk = row_chunk[:, hvg_indices]     # col slice on 100k x 44k: tiny CSC
        hvg_chunks.append(sp.csr_matrix(hvg_chunk))
        if start % (extract_batch * 20) == 0 and start > 0:
            print(f"      Batch {start // extract_batch}/{n_cells // extract_batch} "
                  f"(RAM: {get_peak_ram_gb():.1f} GB)")
    X_hvg_sparse = sp.vstack(hvg_chunks, format="csr")
    del hvg_chunks
    gc.collect()
    print(f"    HVG extraction: {time.perf_counter() - t0:.1f}s, "
          f"shape={X_hvg_sparse.shape}, "
          f"nnz={X_hvg_sparse.nnz:,}, "
          f"sparse size={X_hvg_sparse.data.nbytes / (1024**3):.2f} GB")

    # --- Pass 1: compute mean and std from sparse batches ---
    print(f"    Pass 1: computing per-gene mean/std from sparse batches...")
    t0 = time.perf_counter()
    gene_sum = np.zeros(n_hvgs, dtype=np.float64)
    gene_sq_sum = np.zeros(n_hvgs, dtype=np.float64)

    n_batches = (n_cells + batch_size - 1) // batch_size
    for i in range(n_batches):
        start = i * batch_size
        end = min(start + batch_size, n_cells)
        batch = X_hvg_sparse[start:end]
        gene_sum += np.asarray(batch.sum(axis=0)).ravel()
        gene_sq_sum += np.asarray(batch.multiply(batch).sum(axis=0)).ravel()

    gene_mean = (gene_sum / n_cells).astype(np.float32)
    gene_var = ((gene_sq_sum / n_cells - (gene_sum / n_cells) ** 2)
                * (n_cells / (n_cells - 1))).astype(np.float32)
    gene_std = np.sqrt(np.maximum(gene_var, 1e-12))

    print(f"    Pass 1 done: {time.perf_counter() - t0:.1f}s")

    # --- Pass 2: accumulate covariance on GPU ---
    # Distribute covariance accumulation across GPUs for speed.
    # Each GPU gets a subset of cell-batches and accumulates its local X.T @ X.
    print(f"    Pass 2: accumulating covariance across {n_gpus} GPUs...")
    t0 = time.perf_counter()

    # Prepare GPU-side mean/std for scaling
    gpu_mean = {}
    gpu_std = {}
    for g in range(n_gpus):
        with cp.cuda.Device(g):
            gpu_mean[g] = cp.asarray(gene_mean)
            gpu_std[g] = cp.asarray(gene_std)

    # Distribute batches round-robin across GPUs
    # Each GPU accumulates a local covariance matrix
    local_covs = {}
    for g in range(n_gpus):
        with cp.cuda.Device(g):
            local_covs[g] = cp.zeros((n_hvgs, n_hvgs), dtype=cp.float32)

    max_value = 10.0  # scanpy scale max_value
    for i in range(n_batches):
        gpu_id = i % n_gpus
        start = i * batch_size
        end = min(start + batch_size, n_cells)
        # Densify only this batch (100k x 2000 = 800 MB)
        batch_dense = X_hvg_sparse[start:end].toarray().astype(np.float32)
        with cp.cuda.Device(gpu_id):
            X_gpu = cp.asarray(batch_dense)
            # Scale: (X - mean) / std, clip to [-max_value, max_value]
            X_gpu = (X_gpu - gpu_mean[gpu_id]) / gpu_std[gpu_id]
            cp.clip(X_gpu, -max_value, max_value, out=X_gpu)
            # Accumulate covariance
            local_covs[gpu_id] += X_gpu.T @ X_gpu
            del X_gpu
        del batch_dense

        if (i + 1) % 20 == 0 or i == n_batches - 1:
            print(f"      Batch {i+1}/{n_batches} "
                  f"(RAM: {get_peak_ram_gb():.1f} GB)")

    # Sum all local covariances on GPU 0
    with cp.cuda.Device(0):
        cov_total = local_covs[0]
        for g in range(1, n_gpus):
            cov_total += cp.asarray(local_covs[g])
        cov_total /= (n_cells - 1)
    cp.cuda.Stream.null.synchronize()

    # Clean up GPU mean/std/local_covs
    del local_covs, gpu_mean, gpu_std
    for g in range(n_gpus):
        with cp.cuda.Device(g):
            cp.get_default_memory_pool().free_all_blocks()

    print(f"    Pass 2 covariance done: {time.perf_counter() - t0:.1f}s")

    # --- Eigendecomposition on GPU 0 ---
    print(f"    Eigendecomposition ({n_hvgs}x{n_hvgs})...")
    t0 = time.perf_counter()
    with cp.cuda.Device(0):
        eigenvalues, eigenvectors = cp.linalg.eigh(cov_total)
        eigenvalues = cp.ascontiguousarray(eigenvalues[::-1][:n_comps])
        eigenvectors = cp.ascontiguousarray(eigenvectors[:, ::-1][:, :n_comps])
        total_var = float(cp.trace(cov_total))
        variance_ratio = eigenvalues / total_var
    cp.cuda.Stream.null.synchronize()
    del cov_total
    print(f"    Eigendecomposition: {time.perf_counter() - t0:.1f}s, "
          f"explained var: {float(variance_ratio.sum()):.4f}")

    # --- Pass 3: project each batch to PCA space ---
    # Distribute projection across GPUs for speed.
    print(f"    Pass 3: projecting {n_cells:,} cells to {n_comps} PCs...")
    t0 = time.perf_counter()

    # Copy eigenvectors to all GPUs
    gpu_V = {}
    for g in range(n_gpus):
        with cp.cuda.Device(g):
            gpu_V[g] = cp.asarray(eigenvectors) if g != 0 else eigenvectors

    X_pca = np.empty((n_cells, n_comps), dtype=np.float32)

    for i in range(n_batches):
        gpu_id = i % n_gpus
        start = i * batch_size
        end = min(start + batch_size, n_cells)
        batch_dense = X_hvg_sparse[start:end].toarray().astype(np.float32)
        with cp.cuda.Device(gpu_id):
            X_gpu = cp.asarray(batch_dense)
            X_gpu = (X_gpu - cp.asarray(gene_mean)) / cp.asarray(gene_std)
            cp.clip(X_gpu, -max_value, max_value, out=X_gpu)
            pca_chunk = X_gpu @ gpu_V[gpu_id]
            X_pca[start:end] = cp.asnumpy(pca_chunk)
            del X_gpu, pca_chunk

    del gpu_V
    for g in range(n_gpus):
        with cp.cuda.Device(g):
            cp.get_default_memory_pool().free_all_blocks()

    print(f"    Pass 3 projection: {time.perf_counter() - t0:.1f}s, "
          f"X_pca shape: {X_pca.shape}")

    eigenvalues_cpu = cp.asnumpy(eigenvalues)
    variance_ratio_cpu = cp.asnumpy(variance_ratio)

    return X_pca, eigenvalues_cpu, variance_ratio_cpu


# ---------------------------------------------------------------------------
# Dataset resize (same as benchmark_maxpower.py)
# ---------------------------------------------------------------------------

def resize_dataset(adata: sc.AnnData, target_cells: int) -> sc.AnnData:
    """Resize an AnnData to target_cells by replicating + subsampling."""
    import anndata
    n_orig = adata.n_obs

    if target_cells == n_orig:
        return adata
    if target_cells < n_orig:
        print(f"  Subsampling {n_orig:,} -> {target_cells:,} cells...")
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(n_orig, size=target_cells, replace=False)
        return adata[sorted(idx)].copy()

    n_full_copies = target_cells // n_orig
    remainder = target_cells % n_orig
    print(f"  Resizing: {n_orig:,} x {n_full_copies} + {remainder:,} = {target_cells:,} cells...")
    start = time.time()

    copies = []
    for i in range(n_full_copies):
        copy = adata.copy()
        copy.obs_names = [f"{name}_rep{i}" for name in copy.obs_names]
        copies.append(copy)

    if remainder > 0:
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(n_orig, size=remainder, replace=False)
        partial = adata[sorted(idx)].copy()
        partial.obs_names = [f"{name}_rep{n_full_copies}" for name in partial.obs_names]
        copies.append(partial)

    result = anndata.concat(copies, join="inner", merge="first")
    elapsed = time.time() - start
    print(f"  Done: {result.n_obs:,} cells x {result.n_vars:,} genes ({elapsed:.1f}s)")
    del copies
    gc.collect()
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    adata_path: Path,
    n_gpus: int,
    target_cells: int = 0,
    skip_de: bool = False,
    clustering: str = "leiden",
) -> tuple:
    """Run the chunked max-power pipeline.

    Key difference from standard maxpower: preprocessing is fully chunked.
    The dense matrix (n_cells x 2000) NEVER exists in full on CPU.

    Pipeline:
      1. Data loading (CPU)
      2. QC filtering (CPU, sparse)
      3. Normalisation (CPU, sparse — in-place on sparse matrix)
      4. HVG selection (CPU, chunked from sparse batches)
      5. Scale + PCA fused (multi-GPU, chunked covariance from sparse batches)
      6. Lean GPU transfer (only X_pca to GPU 0)
      7. Neighbours (GPU 0)
      8. Leiden / KMeans (GPU 0)
      9. UMAP (GPU 0)
     10. DE (CPU, optional)
    """
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    print(f"\n{'=' * 80}")
    print(f"CHUNKED MAX-POWER BENCHMARK — target {target_cells:,} cells — {n_gpus} GPUs")
    print(f"  Batch size: {CELL_BATCH_SIZE:,} cells")
    print(f"  Dense matrix is NEVER created in full")
    print(f"{'=' * 80}")

    print(
        f"  {'Step':30s} | {'Time':>8s} | {'RAM':>20s} | {'VRAM (total)':>20s}"
    )
    print(f"  {'-' * 30}-+-{'-' * 8}-+-{'-' * 20}-+-{'-' * 20}")

    # --- Step 1: Data loading ---
    def load_data():
        return sc.read_h5ad(adata_path)

    adata = time_step("data_loading", load_data, timings, memory, n_gpus)
    print(f"    Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # Resize if needed
    if target_cells > 0 and target_cells != adata.n_obs:
        adata = resize_dataset(adata, target_cells)

    # --- Step 2: QC filtering ---
    def qc_filter():
        adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False, inplace=True)
        sc.pp.filter_cells(adata, min_genes=200)
        sc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory, n_gpus)
    n_cells_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_cells_after_qc:,} cells x {n_genes_after_qc:,} genes")

    # --- Step 3: Normalisation (sparse, in-place) ---
    def normalize():
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory, n_gpus)

    # Save raw for DE later (sparse, before HVG subset).
    # NOTE: adata.raw = adata.copy() would duplicate the entire ~420 GB sparse
    # matrix. Instead, use adata.raw = adata which only creates a lightweight
    # AnnData view that shares the underlying sparse arrays (no RAM increase).
    adata.raw = adata

    # --- Step 4: HVG selection (CHUNKED — no dense matrix) ---
    def hvg_select():
        X_sparse = adata.X
        if not sp.issparse(X_sparse):
            raise ValueError("Expected sparse matrix after normalisation")
        hvg_mask = chunked_hvg_selection(
            X_sparse, adata.var_names.values, n_top_genes=N_TOP_GENES,
        )
        adata.var["highly_variable"] = hvg_mask

    time_step("hvg_selection_chunked", hvg_select, timings, memory, n_gpus)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    hvg_indices = np.where(adata.var["highly_variable"].values)[0]
    print(f"    HVGs selected: {n_hvgs}")

    # --- Step 5: Fused scale + PCA (CHUNKED, multi-GPU) ---
    # This is the KEY optimisation: we never create the full dense matrix.
    # Instead we accumulate covariance from sparse batches on GPUs.

    gpu_warmup(n_gpus)

    def fused_scale_pca():
        X_pca, eigenvalues, variance_ratio = chunked_scale_covariance_pca(
            adata.X,  # sparse, full gene set
            hvg_indices,
            n_gpus=n_gpus,
            n_comps=N_PCA_COMPS,
        )
        # Store PCA results in adata (scanpy-compatible)
        adata.obsm["X_pca"] = X_pca
        adata.uns["pca"] = {
            "variance": eigenvalues,
            "variance_ratio": variance_ratio,
            "params": {
                "n_comps": N_PCA_COMPS,
                "method": "chunked_covariance_distributed",
                "n_gpus": n_gpus,
                "random_state": RANDOM_SEED,
                "batch_size": CELL_BATCH_SIZE,
            },
        }

    time_step("fused_scale_pca", fused_scale_pca, timings, memory, n_gpus)

    # Subset adata to HVGs for anndata_to_GPU structure.
    # MEMORY-CRITICAL: delete the large sparse X before subsetting to avoid
    # holding two copies (~420 GB each) simultaneously.
    n_obs = adata.n_obs
    hvg_var = adata.var[adata.var["highly_variable"]].copy()
    X_pca = adata.obsm["X_pca"]
    pca_uns = adata.uns.get("pca", {})
    obs_df = adata.obs.copy()

    # Drop the heavy adata object (releases ~420 GB sparse matrix)
    del adata
    gc.collect()
    ram_after_del = get_peak_ram_gb()
    print(f"    Released original adata (RAM after: {ram_after_del:.1f} GB)")

    # Reconstruct lightweight adata with empty X + PCA coords
    adata = sc.AnnData(
        X=sp.csr_matrix((n_obs, len(hvg_var)), dtype=np.float32),
        obs=obs_df,
        var=hvg_var,
    )
    adata.obsm["X_pca"] = X_pca
    adata.uns["pca"] = pca_uns
    print(f"    After HVG subset + lean X: {adata.n_obs:,} cells x {adata.n_vars:,} genes")
    print(f"    X_pca: {adata.obsm['X_pca'].shape} ({adata.obsm['X_pca'].nbytes / (1024**2):.0f} MB)")

    # --- Step 6: GPU transfer (lean — only X_pca) ---
    def transfer_to_gpu():
        rsc.get.anndata_to_GPU(adata)

    time_step("gpu_transfer", transfer_to_gpu, timings, memory, n_gpus)

    # --- Step 7: Neighbours on GPU 0 ---
    time_step(
        "neighbors",
        lambda: rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED),
        timings, memory, n_gpus,
    )

    # --- Step 8: Clustering ---
    cluster_results = {}
    if clustering == "kmeans":
        from cuml import KMeans as cuKMeans
        kmeans_k_map = {0.5: 50, 1.0: 100, 1.5: 200}
        for res in LEIDEN_RESOLUTIONS:
            k = kmeans_k_map[res]
            key = f"kmeans_{res}"
            def _run(n_clusters=k, r=res):
                km = cuKMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, max_iter=300)
                X_pca = adata.obsm["X_pca"]
                if not hasattr(X_pca, "__cuda_array_interface__"):
                    X_pca = cp.asarray(X_pca)
                labels = km.fit_predict(X_pca)
                if hasattr(labels, "get"):
                    labels = labels.get()
                adata.obs[f"kmeans_{r}"] = labels.astype(str)
            time_step(key, _run, timings, memory, n_gpus)
            labels = np.asarray(adata.obs[f"kmeans_{res}"].values)
            if hasattr(labels, "get"):
                labels = labels.get()
            cluster_results[key] = {
                "n_clusters": len(np.unique(labels)),
                "labels_hash": sha256_of_array(np.asarray(labels, dtype=str)),
            }
            print(f"    {key}: {cluster_results[key]['n_clusters']} clusters")
    else:
        for res in LEIDEN_RESOLUTIONS:
            key = f"leiden_{res}"
            time_step(
                key,
                lambda r=res: rsc.tl.leiden(
                    adata, resolution=r, random_state=RANDOM_SEED, key_added=f"leiden_{r}",
                ),
                timings, memory, n_gpus,
            )
            labels = np.asarray(adata.obs[f"leiden_{res}"].values)
            if hasattr(labels, "get"):
                labels = labels.get()
            cluster_results[key] = {
                "n_clusters": len(np.unique(labels)),
                "labels_hash": sha256_of_array(np.asarray(labels, dtype=str)),
            }
            print(f"    {key}: {cluster_results[key]['n_clusters']} clusters")

    # --- Step 9: UMAP ---
    time_step(
        "umap",
        lambda: rsc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory, n_gpus,
    )

    # Transfer back to CPU
    print("\n  Transferring data back to CPU...")
    rsc.get.anndata_to_CPU(adata)

    # --- Step 10: DE (optional) ---
    if skip_de:
        print("  DE skipped (--skip-de)")
        timings["de_testing"] = 0.0
    else:
        def run_de():
            groupby = "leiden_1.0" if clustering == "leiden" else "kmeans_1.0"
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
                sc.tl.rank_genes_groups(
                    adata, groupby=groupby, method="wilcoxon", use_raw=True,
                )
        time_step("de_testing", run_de, timings, memory, n_gpus)

    # --- Summary ---
    timings["total"] = round(sum(timings.values()), 4)
    peak_ram = max(v for k, v in memory.items() if k.endswith("_ram_after_gb"))
    peak_vram = max(v for k, v in memory.items() if k.endswith("_vram_after_gb"))

    print(
        f"\n  {'TOTAL':30s} | {timings['total']:8.2f}s | "
        f"Peak RAM: {peak_ram:.1f} GB | Peak VRAM(total): {peak_vram:.1f} GB"
    )

    ram_total = 2048
    vram_total = 80 * n_gpus
    print(f"\n  Resource utilization:")
    print(f"    RAM:  {peak_ram:.0f} / {ram_total} GB ({peak_ram/ram_total*100:.1f}%)")
    print(f"    VRAM: {peak_vram:.0f} / {vram_total} GB ({peak_vram/vram_total*100:.1f}%)")

    gpu_info = get_gpu_info(n_gpus)
    n_cells_effective = target_cells if target_cells > 0 else adata.n_obs

    result = {
        "metadata": {
            "pipeline": f"maxpower_chunked_{n_gpus}gpu",
            "n_cells_input": n_cells_effective,
            "n_cpus": os.cpu_count(),
            "n_gpus": n_gpus,
            "random_seed": RANDOM_SEED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "software_versions": {
                "scanpy": pkg_version("scanpy"),
                "rapids_singlecell": pkg_version("rapids_singlecell"),
                "cupy": cp.__version__,
                "rmm": pkg_version("rmm"),
                "dask": pkg_version("dask"),
                "dask_cuda": pkg_version("dask_cuda"),
                "python": f"{sys.version}",
                "numpy": np.__version__,
            },
            "configuration": {
                "cell_batch_size": CELL_BATCH_SIZE,
                "n_top_genes": N_TOP_GENES,
                "n_pca_comps": N_PCA_COMPS,
                "chunked_hvg": True,
                "fused_scale_pca": True,
                "clustering_algorithm": clustering,
                "pca_method": "chunked_covariance_distributed",
                "dense_matrix_created": False,
            },
            "gpu_info": gpu_info,
            "input_file": str(adata_path),
        },
        "timings": timings,
        "memory": {
            "peak_ram_gb": round(peak_ram, 2),
            "peak_vram_gb": round(peak_vram, 2),
            "detailed": memory,
        },
        "results_summary": {
            "n_cells_after_qc": n_cells_after_qc,
            "n_genes_after_qc": n_genes_after_qc,
            "n_hvgs": n_hvgs,
            "hvg_list_hash": hvg_hash,
            **{f"n_clusters_{res}": list(cluster_results.values())[i]["n_clusters"]
               for i, res in enumerate(LEIDEN_RESOLUTIONS)},
            **{f"cluster_labels_hash_{res}": list(cluster_results.values())[i]["labels_hash"]
               for i, res in enumerate(LEIDEN_RESOLUTIONS)},
        },
        "resource_utilization": {
            "ram_used_gb": round(peak_ram, 1),
            "ram_total_gb": ram_total,
            "ram_pct": round(peak_ram / ram_total * 100, 1),
            "vram_used_gb": round(peak_vram, 1),
            "vram_total_gb": vram_total,
            "vram_pct": round(peak_vram / vram_total * 100, 1),
        },
    }

    return result, adata, hvg_list


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chunked max-power benchmark: push beyond 11.9M cells.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run at 15M cells
  python scripts/benchmark_maxpower_chunked.py --data-dir data/ --output-dir results/ --target-cells 15000000

  # Binary search for the new limit
  python scripts/benchmark_maxpower_chunked.py --data-dir data/ --output-dir results/ --find-limit

  # Skip coarse search, refine between known bounds
  python scripts/benchmark_maxpower_chunked.py --data-dir data/ --output-dir results/ --find-limit --fine-low 20000000 --fine-high 25000000
        """,
    )
    parser.add_argument("--data-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--n-gpus", type=int, default=8)
    parser.add_argument("--target-cells", type=int, default=0)
    parser.add_argument("--find-limit", action="store_true",
                        help="Binary search for max cells before OOM.")
    parser.add_argument("--fine-low", type=int, default=0)
    parser.add_argument("--fine-high", type=int, default=0)
    parser.add_argument("--coarse-start", type=int, default=0,
                        help="Resume coarse search from this cell count (skip lower targets).")
    parser.add_argument("--skip-de", action="store_true")
    parser.add_argument("--clustering", type=str, default="leiden",
                        choices=["leiden", "kmeans"])
    return parser.parse_args()


def run_single(
    adata_path: Path, n_gpus: int, target_cells: int, output_dir: Path,
    skip_de: bool = False, clustering: str = "leiden",
) -> dict | None:
    try:
        result, adata, hvg_list = run_pipeline(
            adata_path, n_gpus, target_cells, skip_de, clustering,
        )
    except (MemoryError, cp.cuda.memory.OutOfMemoryError) as e:
        print(f"\n  OOM ERROR at {target_cells:,} cells: {e}")
        gc.collect()
        cp.get_default_memory_pool().free_all_blocks()
        return None
    except RuntimeError as e:
        message = str(e).lower()
        if any(t in message for t in (
            "out_of_memory", "cudaerrormemoryallocation", "std::bad_alloc",
            "rmm::bad_alloc", "failed to allocate",
        )):
            print(f"\n  OOM ERROR at {target_cells:,} cells: {e}")
            gc.collect()
            cp.get_default_memory_pool().free_all_blocks()
            return None
        raise

    n_cells = result["metadata"]["n_cells_input"]
    prefix = f"maxpower_chunked_{n_cells}_{n_gpus}gpu"
    json_path = output_dir / f"{prefix}_results.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {json_path}")

    t = result["timings"]
    r = result["resource_utilization"]
    print(f"\n{'=' * 80}")
    print(f"CHUNKED MAX-POWER SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Cells processed:  {result['results_summary']['n_cells_after_qc']:,}")
    print(f"  GPUs used:        {n_gpus}x H100 80GB")
    print(f"  Total time:       {t['total']:.1f}s ({t['total']/60:.1f} min)")
    print(f"  RAM used:         {r['ram_used_gb']:.0f} / {r['ram_total_gb']} GB ({r['ram_pct']:.1f}%)")
    print(f"  VRAM used:        {r['vram_used_gb']:.0f} / {r['vram_total_gb']} GB ({r['vram_pct']:.1f}%)")
    print(f"  Throughput:       {result['results_summary']['n_cells_after_qc'] / t['total']:,.0f} cells/s")

    del adata, hvg_list
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()
    return result


def _run_in_subprocess(
    script_path: str, data_dir: str, output_dir: str,
    n_gpus: int, target_cells: int, clustering: str = "leiden",
) -> bool:
    import subprocess as _sp
    cmd = [
        sys.executable, "-u", script_path,
        "--data-dir", data_dir,
        "--output-dir", output_dir,
        "--n-gpus", str(n_gpus),
        "--target-cells", str(target_cells),
        "--skip-de",
        "--clustering", clustering,
    ]
    print(f"  Launching subprocess: target={target_cells:,} cells, {n_gpus} GPUs")
    try:
        result = _sp.run(cmd, timeout=86400)
    except _sp.TimeoutExpired:
        print(f"  >>> TIMEOUT at {target_cells:,} cells (24h limit)")
        return False
    rc = result.returncode
    if rc == 0:
        return True
    if rc == OOM_EXIT_CODE:
        return False
    # Signal 9 (SIGKILL) = OOM killer; signal 7 (SIGBUS) = memory mapping failure
    # Negative return codes mean killed by signal: rc = -signal_number
    if rc < 0:
        sig = -rc
        print(f"  >>> Killed by signal {sig} (likely OOM killer) at {target_cells:,} cells")
        return False
    if rc == INVALID_BENCHMARK_EXIT_CODE:
        raise RuntimeError(f"Dask cluster failed for target={target_cells:,}")
    # Any other non-zero exit: treat as failure, don't crash the search
    print(f"  >>> Subprocess failed (exit {rc}) at {target_cells:,} cells — treating as OOM")
    return False


def run_find_limit(
    adata_path: Path, n_gpus: int, output_dir: Path,
    fine_low: int = 0, fine_high: int = 0, coarse_start: int = 0,
    clustering: str = "leiden",
) -> None:
    script_path = str(Path(__file__).resolve())
    stem = adata_path.stem
    n_source = int(stem.split("_")[-1])

    print(f"\n{'=' * 80}")
    print(f"CHUNKED FIND-LIMIT MODE — subprocess isolation")
    print(f"Source dataset: {n_source:,} cells")
    print(f"Previous limit (standard pipeline): 11,900,000 cells")
    print(f"{'=' * 80}")

    last_success = 0
    first_fail = 0

    if fine_low > 0 and fine_high > 0:
        last_success = fine_low
        first_fail = fine_high
        print(f"\n--- Skipping coarse search (bounds: {fine_low:,}–{fine_high:,}) ---")
    else:
        # Coarse search: start at 12M (previous limit), step by ~3.4M
        coarse_targets = list(range(12_000_000, 50_000_000, n_source))
        if coarse_start > 0:
            coarse_targets = [t for t in coarse_targets if t >= coarse_start]
            last_success = max(t for t in range(12_000_000, coarse_start, n_source))
            print(f"\n--- Phase 1: Coarse search (RESUME from {coarse_start:,}, "
                  f"previous success at {last_success:,}) ---")
        else:
            print(f"\n--- Phase 1: Coarse search (start at 12M, step ~{n_source:,}) ---")
        for target in coarse_targets:
            print(f"\n>>> Trying {target:,} cells...")
            success = _run_in_subprocess(
                script_path, str(adata_path.parent), str(output_dir),
                n_gpus, target, clustering,
            )
            if success:
                last_success = target
                print(f"  >>> SUCCESS at {target:,} cells")
            else:
                first_fail = target
                print(f"  >>> FAILED at {target:,} cells")
                break
        else:
            print(f"\n  All targets succeeded up to {coarse_targets[-1]:,}!")
            return

    # Fine search
    print(f"\n--- Phase 2: Fine search between {last_success:,} and {first_fail:,} ---")
    fine_step = 500_000
    low = last_success
    high = first_fail

    while high - low > fine_step:
        mid = ((low + high) // 2 // fine_step) * fine_step
        if mid == low:
            mid = low + fine_step
        print(f"\n>>> Binary search: trying {mid:,} cells (range: {low:,}–{high:,})...")
        success = _run_in_subprocess(
            script_path, str(adata_path.parent), str(output_dir),
            n_gpus, mid, clustering,
        )
        if success:
            low = mid
        else:
            high = mid

    print(f"\n{'=' * 80}")
    print(f"CHUNKED LIMIT FOUND")
    print(f"{'=' * 80}")
    print(f"  Maximum cells:  {low:,}")
    print(f"  First OOM at:   {high:,}")
    print(f"  Previous limit: 11,900,000 (standard pipeline)")
    print(f"  Improvement:    {low / 11_900_000:.1f}x")

    summary = {
        "max_cells": low,
        "first_oom_at": high,
        "previous_limit": 11_900_000,
        "improvement_factor": round(low / 11_900_000, 2),
        "n_gpus": n_gpus,
        "clustering": clustering,
        "pipeline": "chunked",
        "batch_size": CELL_BATCH_SIZE,
        "dense_matrix_created": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / f"maxpower_chunked_limit_{n_gpus}gpu.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved:  {summary_path}")


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    n_gpus = args.n_gpus

    existing = list(data_dir.glob("brain_full_*.h5ad"))
    if existing:
        adata_path = existing[0]
        print(f"Found full dataset: {adata_path}")
    else:
        print("ERROR: No brain_full_*.h5ad file found. Run download_full.sh first.")
        raise SystemExit(1)

    if args.find_limit:
        print(f"\nSystem RAM: {psutil.virtual_memory().total / (1024**3):.0f} GB")
        run_find_limit(adata_path, n_gpus, output_dir, args.fine_low, args.fine_high,
                       args.coarse_start, args.clustering)
    else:
        init_nvml()
        try:
            gpu_info = get_gpu_info(n_gpus)
            print(f"\nDGX Configuration:")
            for gpu in gpu_info["gpus"]:
                print(f"  GPU {gpu['device_index']}: {gpu['gpu_name']} ({gpu['gpu_vram_total_gb']} GB)")
            print(f"  System RAM: {psutil.virtual_memory().total / (1024**3):.0f} GB")

            sc.settings.verbosity = 0
            result = run_single(
                adata_path, n_gpus, args.target_cells, output_dir,
                args.skip_de, args.clustering,
            )
            if result is None:
                raise SystemExit(OOM_EXIT_CODE)
        finally:
            shutdown_nvml()

    print("\nDone!")


if __name__ == "__main__":
    main()
