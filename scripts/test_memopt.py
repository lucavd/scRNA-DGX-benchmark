#!/usr/bin/env python3
"""Memory optimization diagnostic tests for max-power benchmark.

Standalone diagnostic script to test different memory strategies for
fitting more cells on 8×H100 GPUs. Run ONE test at a time, check output,
then try the next.

Tests:
  baseline      — current setup (RMM 10GB pool), for comparison
  rmm2gb        — reduce RMM pool from 10GB to 2GB
  cpuscale      — do scale() on CPU, transfer dense matrix to GPU
  scatter       — pre-scatter data across all 8 GPUs via dask array
  fullpipe      — full pipeline: scatter PCA + lean transfer + all steps + DE
  sparsescatter — fused scale+scatter: compute mean/std from sparse on CPU,
                  each GPU densifies+scales its own chunk. Dense matrix NEVER
                  exists on CPU. Maximum RAM savings.

Usage:
    python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test baseline
    python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test rmm2gb
    python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test cpuscale
    python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test scatter
    python scripts/test_memopt.py --help
"""

import argparse
import gc
import os
import sys
import time

import numpy as np
import scanpy as sc


RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print a timestamped log message."""
    elapsed = time.time() - _T0
    print(f"[MEMOPT +{elapsed:7.1f}s] {msg}", flush=True)


def vram_report(n_gpus: int) -> None:
    """Print VRAM usage for each GPU."""
    import pynvml

    parts = []
    total_used = 0.0
    for i in range(n_gpus):
        h = pynvml.nvmlDeviceGetHandleByIndex(i)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        used_gb = info.used / (1024**3)
        total_gb = info.total / (1024**3)
        total_used += used_gb
        parts.append(f"GPU{i}:{used_gb:.1f}/{total_gb:.0f}GB")
    log(f"VRAM [{total_used:.1f} GB total]: {' | '.join(parts)}")


def ram_report() -> None:
    """Print CPU RAM usage."""
    import psutil

    proc = psutil.Process()
    rss_gb = proc.memory_info().rss / (1024**3)
    total_gb = psutil.virtual_memory().total / (1024**3)
    log(f"RAM: {rss_gb:.1f} / {total_gb:.0f} GB")


# ---------------------------------------------------------------------------
# CPU preprocessing (shared across all tests)
# ---------------------------------------------------------------------------

def load_and_preprocess(data_dir: str, target_cells: int) -> sc.AnnData:
    """Load full brain dataset, subsample, QC, normalize, select HVGs.

    Args:
        data_dir: Directory containing brain_full_*.h5ad.
        target_cells: Number of cells to subsample to.

    Returns:
        AnnData with HVG subset (n_cells × 2000), still on CPU.
    """
    from pathlib import Path

    data_path = Path(data_dir)
    existing = sorted(data_path.glob("brain_full_*.h5ad"))
    if not existing:
        log("ERROR: no brain_full_*.h5ad found in " + data_dir)
        sys.exit(1)
    path = existing[0]

    log(f"Loading {path.name}...")
    t0 = time.time()
    adata = sc.read_h5ad(path)
    log(f"Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes ({time.time()-t0:.0f}s)")
    ram_report()

    # Subsample or replicate
    if target_cells < adata.n_obs:
        log(f"Subsampling {adata.n_obs:,} -> {target_cells:,} cells...")
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(adata.n_obs, size=target_cells, replace=False)
        adata = adata[sorted(idx)].copy()
    elif target_cells > adata.n_obs:
        import anndata
        n_orig = adata.n_obs
        n_full_copies = target_cells // n_orig
        remainder = target_cells % n_orig
        log(f"Resizing: {n_orig:,} × {n_full_copies} + {remainder:,} = {target_cells:,} cells...")
        t0 = time.time()
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
        adata = anndata.concat(copies, join="inner", merge="first")
        del copies
        gc.collect()
        log(f"Done: {adata.n_obs:,} x {adata.n_vars:,} ({time.time()-t0:.0f}s)")
        ram_report()

    # QC
    log("QC filtering...")
    adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False, inplace=True)
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    log(f"After QC: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # Normalize
    log("Normalizing...")
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # HVG selection + subset (save raw for DE)
    log("HVG selection (2000 genes)...")
    sc.pp.highly_variable_genes(adata, n_top_genes=2000)
    adata.raw = adata.copy()  # raw = all genes, normalized+log1p (for DE)
    adata = adata[:, adata.var["highly_variable"]].copy()
    log(f"After HVG: {adata.n_obs:,} cells x {adata.n_vars:,} genes")
    log(f"Raw preserved: {adata.raw.n_vars:,} genes")

    matrix_gb = adata.n_obs * adata.n_vars * 4 / (1024**3)
    log(f"Dense matrix would be: {matrix_gb:.1f} GB (float32)")
    ram_report()

    return adata


# ---------------------------------------------------------------------------
# Dask cluster helpers
# ---------------------------------------------------------------------------

def _start_dask(n_gpus: int, rmm_pool: str) -> tuple:
    """Start a Dask CUDA cluster and wait for all workers.

    Args:
        n_gpus: Number of GPUs.
        rmm_pool: Initial RMM pool size per worker (e.g. "2GB", "10GB").

    Returns:
        Tuple of (cluster, client).
    """
    from dask.distributed import Client
    from dask_cuda import LocalCUDACluster

    device_list = ",".join(str(i) for i in range(n_gpus))
    log(f"Starting Dask: {n_gpus} GPUs, rmm_pool={rmm_pool}...")

    cluster = LocalCUDACluster(
        CUDA_VISIBLE_DEVICES=device_list,
        n_workers=n_gpus,
        rmm_pool_size=rmm_pool,
        rmm_maximum_pool_size="70GB",
    )
    client = Client(cluster)

    # Wait for all workers using scheduler-direct check
    def _count_running(dask_scheduler):
        return sum(
            1 for ws in dask_scheduler.workers.values()
            if str(getattr(ws, "status", "")) == "Status.running"
        )

    for _ in range(120):
        n = client.run_on_scheduler(_count_running)
        if n == n_gpus:
            break
        time.sleep(1)

    actual = client.run_on_scheduler(_count_running)
    log(f"Dask workers: {actual}/{n_gpus}")
    if actual != n_gpus:
        log(f"WARNING: only {actual} workers running!")

    return cluster, client


def _stop_dask(cluster, client) -> None:
    """Shut down Dask cluster and clean up."""
    import cupy as cp

    log("Shutting down Dask...")
    if client is not None:
        client.close()
    if cluster is not None:
        cluster.close()
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()


# ---------------------------------------------------------------------------
# Test 1: baseline (current setup)
# Test 2: rmm2gb (reduce RMM pool)
# Test 3: cpuscale (scale on CPU)
# ---------------------------------------------------------------------------

def test_gpu_phase(
    adata: sc.AnnData,
    n_gpus: int,
    rmm_pool: str,
    scale_on_cpu: bool,
    label: str,
) -> bool:
    """Test the GPU-critical path: transfer + scale + PCA + neighbors.

    Args:
        adata: Preprocessed AnnData (HVG subset, on CPU).
        n_gpus: Number of GPUs.
        rmm_pool: RMM pool size string.
        scale_on_cpu: If True, run scale on CPU before GPU transfer.
        label: Test label for logging.

    Returns:
        True if all steps completed without OOM.
    """
    import cupy as cp
    import pynvml
    import rapids_singlecell as rsc

    pynvml.nvmlInit()

    log(f"{'=' * 60}")
    log(f"TEST [{label}]: rmm_pool={rmm_pool}, scale_on_cpu={scale_on_cpu}")
    log(f"Matrix: {adata.n_obs:,} x {adata.n_vars:,}")
    log(f"{'=' * 60}")
    vram_report(n_gpus)

    # Optional: scale on CPU
    if scale_on_cpu:
        log("--- Scale on CPU (sparse -> dense -> scaled) ---")
        t0 = time.time()
        if hasattr(adata.X, "toarray"):
            log("  Converting sparse -> dense...")
            adata.X = adata.X.toarray()
        sc.pp.scale(adata, max_value=10)
        log(f"  CPU scale done in {time.time()-t0:.1f}s")
        log(f"  X: shape={adata.X.shape}, dtype={adata.X.dtype}, "
            f"size={adata.X.nbytes/(1024**3):.1f} GB")
        ram_report()

    # Start Dask cluster
    cluster, client = _start_dask(n_gpus, rmm_pool)
    vram_report(n_gpus)

    try:
        # Transfer to GPU
        log("--- anndata_to_GPU ---")
        t0 = time.time()
        rsc.get.anndata_to_GPU(adata)
        cp.cuda.Stream.null.synchronize()
        log(f"  Transfer done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Scale on GPU (if not done on CPU)
        if not scale_on_cpu:
            log("--- Scale on GPU ---")
            t0 = time.time()
            rsc.pp.scale(adata, max_value=10)
            cp.cuda.Stream.null.synchronize()
            log(f"  GPU scale done in {time.time()-t0:.1f}s")
            cp.get_default_memory_pool().free_all_blocks()
            vram_report(n_gpus)

        # PCA — this is where OOM typically happens
        log("--- PCA (50 components) ---")
        t0 = time.time()
        rsc.pp.pca(adata, n_comps=50, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  PCA done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Neighbors — second multi-GPU step
        log("--- Neighbors (n=15, 50 PCs) ---")
        t0 = time.time()
        rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  Neighbors done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        log(f"SUCCESS [{label}] — all GPU steps completed")
        return True

    except Exception as e:
        log(f"FAILED [{label}]: {type(e).__name__}: {e}")
        vram_report(n_gpus)
        return False

    finally:
        _stop_dask(cluster, client)
        pynvml.nvmlShutdown()


# ---------------------------------------------------------------------------
# Test 4: scatter (pre-distribute data across GPUs)
# ---------------------------------------------------------------------------

def test_scatter(adata: sc.AnnData, n_gpus: int, rmm_pool: str) -> bool:
    """Test pre-scattering data across all GPUs before PCA.

    Instead of putting all data on GPU 0 and letting PCA redistribute,
    we split the matrix on CPU and send each chunk to a different GPU.
    PCA is computed via the covariance method using CuPy directly
    (avoids cuml.dask import issues).

    The covariance method:
      1. Each GPU computes X_i.T @ X_i (2000×2000 matrix — 16 MB)
      2. Sum contributions → full covariance matrix
      3. Eigendecomposition on GPU 0 (tiny: 2000×2000)
      4. Each GPU projects: X_i @ eigenvectors → n_cells/8 × 50

    Memory per GPU: ~chunk_size × 2000 × 4B + workspace ≈ 3-4 GB.

    Args:
        adata: Preprocessed AnnData (HVG subset, on CPU).
        n_gpus: Number of GPUs.
        rmm_pool: RMM pool size string.

    Returns:
        True if all steps completed without OOM.
    """
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()

    log(f"{'=' * 60}")
    log(f"TEST [scatter]: rmm_pool={rmm_pool}, pre-distribute across {n_gpus} GPUs")
    log(f"Matrix: {adata.n_obs:,} x {adata.n_vars:,}")
    log(f"Approach: covariance-method PCA with CuPy (no cuml.dask)")
    log(f"{'=' * 60}")

    # Scale on CPU first (required — scatter needs dense, mean-centered)
    log("--- Scale on CPU ---")
    t0 = time.time()
    if hasattr(adata.X, "toarray"):
        adata.X = adata.X.toarray()
    sc.pp.scale(adata, max_value=10)
    X_np = np.ascontiguousarray(adata.X, dtype=np.float32)
    n_cells, n_genes = X_np.shape
    log(f"  Dense matrix: {X_np.shape}, {X_np.nbytes/(1024**3):.1f} GB ({time.time()-t0:.1f}s)")
    ram_report()

    # Split matrix into chunks on CPU
    chunk_size = n_cells // n_gpus
    remainder = n_cells % n_gpus
    chunks = []
    offset = 0
    for i in range(n_gpus):
        end = offset + chunk_size + (1 if i < remainder else 0)
        chunks.append(X_np[offset:end])
        offset = end
    log(f"  Split into {n_gpus} chunks: {[c.shape[0] for c in chunks]} rows")
    chunk_gb = chunks[0].nbytes / (1024**3)
    log(f"  Per-chunk: {chunk_gb:.2f} GB")

    # Start Dask (only for RMM pool management, not for computation)
    cluster, client = _start_dask(n_gpus, rmm_pool)
    vram_report(n_gpus)

    try:
        # Transfer each chunk to its GPU
        log("--- Transferring chunks to GPUs ---")
        t0 = time.time()
        gpu_chunks = []
        for i, chunk in enumerate(chunks):
            with cp.cuda.Device(i):
                gpu_chunks.append(cp.asarray(chunk))
        cp.cuda.Stream.null.synchronize()
        log(f"  Transfer done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Free CPU numpy arrays
        del X_np, chunks
        gc.collect()
        log("  Freed CPU arrays")
        ram_report()

        # === DISTRIBUTED PCA: COVARIANCE METHOD ===
        n_comps = 50

        # Step 1: Each GPU computes its local X_i.T @ X_i contribution
        log(f"--- PCA Step 1/4: Local covariance (X_i.T @ X_i) on {n_gpus} GPUs ---")
        t0 = time.time()
        local_covs = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                # X_i is (chunk_rows, 2000) → X_i.T @ X_i is (2000, 2000)
                cov_i = X_i.T @ X_i  # float32, 16 MB
                local_covs.append(cov_i)
        cp.cuda.Stream.null.synchronize()
        log(f"  Local covariances computed in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Step 2: Sum covariance contributions on GPU 0
        log("--- PCA Step 2/4: Sum covariances on GPU 0 ---")
        t0 = time.time()
        with cp.cuda.Device(0):
            cov_total = cp.zeros((n_genes, n_genes), dtype=np.float32)
            for i, cov_i in enumerate(local_covs):
                if i == 0:
                    cov_total += cov_i
                else:
                    # Transfer from GPU i to GPU 0
                    cov_total += cp.asarray(cov_i)
            # Normalize: cov = X.T @ X / (n-1)
            cov_total /= (n_cells - 1)
        cp.cuda.Stream.null.synchronize()
        # Free local covariances
        del local_covs
        log(f"  Covariance sum done in {time.time()-t0:.1f}s")
        log(f"  Cov matrix: {cov_total.shape}, {cov_total.nbytes/(1024**2):.1f} MB")
        vram_report(n_gpus)

        # Step 3: Eigendecomposition on GPU 0 (2000×2000 — trivial)
        log(f"--- PCA Step 3/4: Eigendecomposition ({n_genes}×{n_genes}) ---")
        t0 = time.time()
        with cp.cuda.Device(0):
            # eigvalsh returns sorted ascending — take last n_comps
            eigenvalues, eigenvectors = cp.linalg.eigh(cov_total)
            # Reverse to get descending order
            eigenvalues = cp.ascontiguousarray(eigenvalues[::-1][:n_comps])
            eigenvectors = cp.ascontiguousarray(eigenvectors[:, ::-1][:, :n_comps])  # (2000, 50)
            # Explained variance
            total_var = float(cp.trace(cov_total))
            explained_var = eigenvalues / total_var
        cp.cuda.Stream.null.synchronize()
        del cov_total
        log(f"  Eigendecomposition done in {time.time()-t0:.1f}s")
        log(f"  Top 5 explained variance ratios: {cp.asnumpy(explained_var[:5])}")
        log(f"  Total explained variance (50 PCs): {float(explained_var.sum()):.4f}")
        vram_report(n_gpus)

        # Step 4: Project each chunk → PCA coordinates
        log(f"--- PCA Step 4/4: Projection on {n_gpus} GPUs ---")
        t0 = time.time()
        pca_chunks = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                # Copy eigenvectors to this GPU
                V_i = cp.asarray(eigenvectors) if i != 0 else eigenvectors
                # X_i @ V = (chunk_rows, 2000) @ (2000, 50) = (chunk_rows, 50)
                pca_i = X_i @ V_i
                pca_chunks.append(pca_i)
        cp.cuda.Stream.null.synchronize()
        log(f"  Projection done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Gather PCA results to CPU
        log("--- Gathering PCA results to CPU ---")
        t0 = time.time()
        pca_cpu = []
        for i, pca_i in enumerate(pca_chunks):
            with cp.cuda.Device(i):
                pca_cpu.append(cp.asnumpy(pca_i))
        X_pca = np.vstack(pca_cpu)
        del pca_chunks, pca_cpu
        gc.collect()
        log(f"  Gathered in {time.time()-t0:.1f}s, shape={X_pca.shape}")
        log(f"  PCA result: {X_pca.nbytes/(1024**2):.1f} MB")
        ram_report()
        vram_report(n_gpus)

        # Free GPU data chunks
        log("--- Freeing GPU chunks ---")
        del gpu_chunks
        for i in range(n_gpus):
            with cp.cuda.Device(i):
                cp.get_default_memory_pool().free_all_blocks()
        vram_report(n_gpus)

        # Store PCA in adata for downstream steps
        adata.obsm["X_pca"] = X_pca
        adata.uns["pca"] = {
            "variance": cp.asnumpy(eigenvalues),
            "variance_ratio": cp.asnumpy(explained_var),
        }
        log(f"  Stored PCA in adata.obsm['X_pca']")

        # Neighbors on GPU 0 using PCA coordinates (tiny: n_cells × 50)
        log("--- Neighbors (on GPU 0, using 50 PCs) ---")
        t0 = time.time()
        import rapids_singlecell as rsc
        rsc.get.anndata_to_GPU(adata)
        cp.cuda.Stream.null.synchronize()
        log(f"  adata transferred to GPU 0 in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        t0 = time.time()
        rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  Neighbors done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        log("SUCCESS [scatter] — distributed PCA + neighbors completed")
        return True

    except Exception as e:
        log(f"FAILED [scatter]: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        vram_report(n_gpus)
        return False

    finally:
        _stop_dask(cluster, client)
        pynvml.nvmlShutdown()


# ---------------------------------------------------------------------------
# Test 5: fullpipe (full pipeline with memory-efficient GPU usage)
# ---------------------------------------------------------------------------

def test_fullpipe(adata: sc.AnnData, n_gpus: int, rmm_pool: str) -> bool:
    """Test full pipeline with smart GPU memory management.

    Flow:
      A. Scatter PCA across 8 GPUs (proven at 3.4M)
      B. Lean GPU transfer: replace X with empty sparse, transfer only
         X_pca + metadata to GPU 0 — saves ~25 GB
      C. Neighbors + Leiden + UMAP on GPU 0 (~5 GB)
      D. DE testing: try GPU first (load raw.X sparse), fallback to CPU

    Args:
        adata: Preprocessed AnnData (HVG subset + raw, on CPU).
        n_gpus: Number of GPUs.
        rmm_pool: RMM pool size string.

    Returns:
        True if all steps completed.
    """
    import cupy as cp
    import pynvml
    import scipy.sparse as sp
    import warnings

    pynvml.nvmlInit()

    log(f"{'=' * 60}")
    log(f"TEST [fullpipe]: full pipeline with smart GPU memory")
    log(f"Matrix: {adata.n_obs:,} x {adata.n_vars:,}")
    if adata.raw is not None:
        log(f"Raw: {adata.raw.n_vars:,} genes (for DE)")
    log(f"{'=' * 60}")

    # --- Phase A: Scale on CPU + Scatter PCA ---
    log("--- Phase A: Scale + Scatter PCA ---")
    t0_phase = time.time()

    log("  Scaling on CPU...")
    t0 = time.time()
    if hasattr(adata.X, "toarray"):
        adata.X = adata.X.toarray()
    sc.pp.scale(adata, max_value=10)
    log(f"  Scale done in {time.time()-t0:.1f}s")

    # Scatter PCA (reuse logic from test_scatter)
    X_np = np.ascontiguousarray(adata.X, dtype=np.float32)
    n_cells, n_genes = X_np.shape

    chunk_size = n_cells // n_gpus
    remainder = n_cells % n_gpus
    chunks = []
    offset = 0
    for i in range(n_gpus):
        end = offset + chunk_size + (1 if i < remainder else 0)
        chunks.append(X_np[offset:end])
        offset = end
    log(f"  Scatter: {n_gpus} chunks, ~{chunk_size:,} rows, {chunks[0].nbytes/(1024**3):.2f} GB/chunk")

    cluster, client = _start_dask(n_gpus, rmm_pool)
    vram_report(n_gpus)

    try:
        # Transfer chunks to GPUs
        gpu_chunks = []
        for i, chunk in enumerate(chunks):
            with cp.cuda.Device(i):
                gpu_chunks.append(cp.asarray(chunk))
        cp.cuda.Stream.null.synchronize()
        del chunks, X_np
        gc.collect()

        # Covariance PCA
        n_comps = 50
        local_covs = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                local_covs.append(X_i.T @ X_i)
        cp.cuda.Stream.null.synchronize()

        with cp.cuda.Device(0):
            cov_total = cp.zeros((n_genes, n_genes), dtype=np.float32)
            for i, cov_i in enumerate(local_covs):
                cov_total += cov_i if i == 0 else cp.asarray(cov_i)
            cov_total /= (n_cells - 1)
            eigenvalues, eigenvectors = cp.linalg.eigh(cov_total)
            eigenvalues = cp.ascontiguousarray(eigenvalues[::-1][:n_comps])
            eigenvectors = cp.ascontiguousarray(eigenvectors[:, ::-1][:, :n_comps])
            explained_var = eigenvalues / float(cp.trace(cov_total))
        cp.cuda.Stream.null.synchronize()
        del local_covs, cov_total

        pca_chunks = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                V_i = cp.asarray(eigenvectors) if i != 0 else eigenvectors
                pca_chunks.append(X_i @ V_i)
        cp.cuda.Stream.null.synchronize()

        del gpu_chunks
        for i in range(n_gpus):
            with cp.cuda.Device(i):
                cp.get_default_memory_pool().free_all_blocks()

        pca_cpu = []
        for i, pca_i in enumerate(pca_chunks):
            with cp.cuda.Device(i):
                pca_cpu.append(cp.asnumpy(pca_i))
        X_pca = np.vstack(pca_cpu)
        del pca_chunks, pca_cpu

        adata.obsm["X_pca"] = X_pca
        adata.uns["pca"] = {
            "variance": cp.asnumpy(eigenvalues),
            "variance_ratio": cp.asnumpy(explained_var),
        }
        log(f"  PCA done: {X_pca.shape}, explained var = {float(explained_var.sum()):.4f}")
        log(f"  Phase A took {time.time()-t0_phase:.1f}s")
        vram_report(n_gpus)

        # --- Phase B: Lean GPU transfer + Neighbors + Leiden + UMAP ---
        log("--- Phase B: Lean transfer + Neighbors + Leiden + UMAP ---")
        import rapids_singlecell as rsc

        # Replace X with empty sparse — saves ~25 GB on GPU
        log(f"  Replacing adata.X ({adata.X.nbytes/(1024**3):.1f} GB) with empty sparse...")
        adata.X = sp.csr_matrix((adata.n_obs, adata.n_vars), dtype=np.float32)
        log(f"  adata.X is now empty sparse: {adata.X.nnz} non-zeros")

        log("  anndata_to_GPU (lean — no X data)...")
        t0 = time.time()
        rsc.get.anndata_to_GPU(adata)
        cp.cuda.Stream.null.synchronize()
        log(f"  Transfer done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        log("  Neighbors (n=15, 50 PCs)...")
        t0 = time.time()
        rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  Neighbors done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        log("  Leiden (res=1.0)...")
        t0 = time.time()
        rsc.tl.leiden(adata, resolution=1.0, random_state=RANDOM_SEED, key_added="leiden_1.0")
        cp.cuda.Stream.null.synchronize()
        n_clusters = len(np.unique(np.asarray(
            adata.obs["leiden_1.0"].values.get()
            if hasattr(adata.obs["leiden_1.0"].values, "get")
            else adata.obs["leiden_1.0"].values
        )))
        log(f"  Leiden done in {time.time()-t0:.1f}s — {n_clusters} clusters")
        vram_report(n_gpus)

        log("  UMAP...")
        t0 = time.time()
        rsc.tl.umap(adata, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  UMAP done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # --- Phase C: DE testing ---
        log("--- Phase C: Differential Expression ---")

        # C1: Try GPU DE with raw.X
        log("  --- C1: GPU DE (load raw.X sparse to GPU) ---")
        de_gpu_ok = False
        try:
            import cupyx.scipy.sparse as cusp

            # Check raw data
            raw_X = adata.raw.X
            if hasattr(raw_X, "get"):
                raw_nnz = raw_X.nnz
                raw_is_gpu = True
            else:
                raw_nnz = raw_X.nnz if sp.issparse(raw_X) else "dense"
                raw_is_gpu = False
            log(f"  raw.X: {adata.raw.n_vars} genes, nnz={raw_nnz}, on_gpu={raw_is_gpu}")
            log(f"  raw.X type: {type(raw_X)}")
            raw_bytes = raw_X.data.nbytes + raw_X.indices.nbytes + raw_X.indptr.nbytes if sp.issparse(raw_X) else raw_X.nbytes
            log(f"  raw.X size: {raw_bytes/(1024**3):.2f} GB")
            vram_report(n_gpus)

            # Transfer raw.X to GPU
            log("  Transferring raw.X to GPU...")
            t0 = time.time()
            if sp.issparse(raw_X):
                raw_gpu = cusp.csr_matrix(raw_X)
            else:
                raw_gpu = cp.asarray(raw_X)
            # Patch raw to use GPU data
            adata.raw._adata.X = raw_gpu
            cp.cuda.Stream.null.synchronize()
            log(f"  raw.X transferred in {time.time()-t0:.1f}s")
            vram_report(n_gpus)

            log("  Running rsc.tl.rank_genes_groups (GPU, use_raw=True)...")
            t0 = time.time()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
                rsc.tl.rank_genes_groups(
                    adata, groupby="leiden_1.0", method="wilcoxon", use_raw=True,
                )
            cp.cuda.Stream.null.synchronize()
            log(f"  GPU DE done in {time.time()-t0:.1f}s")
            vram_report(n_gpus)
            de_gpu_ok = True
            log("  SUCCESS: GPU DE with raw.X worked!")

        except Exception as e:
            log(f"  GPU DE FAILED: {type(e).__name__}: {e}")
            vram_report(n_gpus)

        # C2: CPU DE (always test for comparison)
        log("  --- C2: CPU DE (scanpy, use_raw=True) ---")
        de_cpu_ok = False
        try:
            log("  Transferring adata back to CPU...")
            t0 = time.time()
            rsc.get.anndata_to_CPU(adata)
            log(f"  Back to CPU in {time.time()-t0:.1f}s")
            ram_report()
            vram_report(n_gpus)

            # Restore raw.X to scipy sparse if it was patched
            raw_X = adata.raw.X
            if hasattr(raw_X, "get"):
                log("  Converting raw.X back to scipy sparse...")
                adata.raw._adata.X = raw_X.get()

            log("  Running sc.tl.rank_genes_groups (CPU, use_raw=True)...")
            t0 = time.time()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
                sc.tl.rank_genes_groups(
                    adata, groupby="leiden_1.0", method="wilcoxon", use_raw=True,
                )
            log(f"  CPU DE done in {time.time()-t0:.1f}s")
            ram_report()
            de_cpu_ok = True
            log("  SUCCESS: CPU DE with raw.X worked!")

        except Exception as e:
            log(f"  CPU DE FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        # Summary
        log("--- SUMMARY ---")
        log(f"  Phase A (scatter PCA):          PASS")
        log(f"  Phase B (lean transfer + pipe):  PASS")
        log(f"  Phase C1 (GPU DE):               {'PASS' if de_gpu_ok else 'FAIL'}")
        log(f"  Phase C2 (CPU DE):               {'PASS' if de_cpu_ok else 'FAIL'}")

        return de_gpu_ok or de_cpu_ok

    except Exception as e:
        log(f"FAILED [fullpipe]: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        vram_report(n_gpus)
        return False

    finally:
        _stop_dask(cluster, client)
        pynvml.nvmlShutdown()


# ---------------------------------------------------------------------------
# Test 6: sparsescatter (fused scale+scatter — no dense on CPU)
# ---------------------------------------------------------------------------

def test_sparsescatter(adata: sc.AnnData, n_gpus: int, rmm_pool: str) -> bool:
    """Fused scale+scatter: dense matrix NEVER exists on CPU.

    Strategy:
      1. Compute per-gene mean and std from the SPARSE matrix on CPU.
         This is O(nnz) memory — no dense copy needed.
      2. Split the sparse matrix by rows (cells) into n_gpus chunks.
      3. Each GPU receives its sparse chunk, densifies it locally (~3 GB),
         and applies (X - mean) / std in-place.
      4. PCA via distributed covariance method (same as scatter test).
      5. Lean transfer for neighbors/leiden/UMAP.

    CPU RAM never holds the dense matrix. At 13.7M × 2000 genes, this
    saves ~103 GB of CPU RAM compared to sc.pp.scale().

    Args:
        adata: Preprocessed AnnData (HVG subset, sparse, on CPU).
        n_gpus: Number of GPUs.
        rmm_pool: RMM pool size string.

    Returns:
        True if all steps completed without OOM.
    """
    import cupy as cp
    import pynvml
    import scipy.sparse as sp

    pynvml.nvmlInit()

    log(f"{'=' * 60}")
    log(f"TEST [sparsescatter]: fused scale+scatter, no dense on CPU")
    log(f"Matrix: {adata.n_obs:,} x {adata.n_vars:,}")
    log(f"{'=' * 60}")

    # Ensure X is sparse
    if not sp.issparse(adata.X):
        log("WARNING: adata.X is already dense — converting to sparse for test")
        adata.X = sp.csr_matrix(adata.X)

    X_sparse = adata.X  # CSR sparse on CPU
    n_cells, n_genes = X_sparse.shape
    log(f"  Sparse X: nnz={X_sparse.nnz:,}, density={X_sparse.nnz/(n_cells*n_genes):.4f}")
    sparse_gb = (X_sparse.data.nbytes + X_sparse.indices.nbytes + X_sparse.indptr.nbytes) / (1024**3)
    log(f"  Sparse size: {sparse_gb:.1f} GB")
    ram_report()

    # Step 1: Compute mean and std per gene from sparse (no dense copy!)
    log("--- Step 1: Compute mean/std from sparse (no dense copy) ---")
    t0 = time.time()
    # mean = sum(X) / n_cells (works on sparse)
    gene_mean = np.asarray(X_sparse.mean(axis=0)).ravel().astype(np.float32)
    # var = E[X²] - (E[X])²
    # X_sparse.power(2) stays sparse (only squares non-zeros)
    gene_sq_mean = np.asarray(X_sparse.power(2).mean(axis=0)).ravel().astype(np.float32)
    gene_var = gene_sq_mean - gene_mean ** 2
    # Clip variance to avoid div by zero, take sqrt
    gene_std = np.sqrt(np.maximum(gene_var, 1e-12)).astype(np.float32)
    log(f"  Mean/std computed in {time.time()-t0:.1f}s (no dense copy created)")
    log(f"  Mean range: [{gene_mean.min():.4f}, {gene_mean.max():.4f}]")
    log(f"  Std range: [{gene_std.min():.4f}, {gene_std.max():.4f}]")
    ram_report()

    # Step 2: Split sparse matrix by rows into chunks
    log(f"--- Step 2: Split sparse into {n_gpus} row chunks ---")
    chunk_size = n_cells // n_gpus
    remainder = n_cells % n_gpus
    chunk_bounds = []
    offset = 0
    for i in range(n_gpus):
        end = offset + chunk_size + (1 if i < remainder else 0)
        chunk_bounds.append((offset, end))
        offset = end
    chunk_rows = [end - start for start, end in chunk_bounds]
    chunk_dense_gb = chunk_rows[0] * n_genes * 4 / (1024**3)
    log(f"  Chunks: {chunk_rows} rows")
    log(f"  Per-chunk dense: {chunk_dense_gb:.2f} GB (exists ONLY on GPU)")
    ram_report()

    # Start Dask (for RMM pools)
    cluster, client = _start_dask(n_gpus, rmm_pool)
    vram_report(n_gpus)

    try:
        # Step 3: Transfer each chunk to GPU, densify, scale — one at a time
        log(f"--- Step 3: Transfer+densify+scale on each GPU ---")
        t0 = time.time()
        gpu_mean = None  # lazy: create on first GPU, copy to others
        gpu_std = None
        gpu_chunks = []

        for i, (start, end) in enumerate(chunk_bounds):
            with cp.cuda.Device(i):
                # Slice sparse rows (CSR row slicing is efficient)
                chunk_sparse = X_sparse[start:end]
                # Densify on GPU
                chunk_gpu = cp.array(chunk_sparse.toarray(), dtype=cp.float32)
                # Scale: (X - mean) / std, clip at max_value=10
                if gpu_mean is None:
                    gpu_mean = cp.asarray(gene_mean)
                    gpu_std = cp.asarray(gene_std)
                mean_i = cp.asarray(gpu_mean) if i != 0 else gpu_mean
                std_i = cp.asarray(gpu_std) if i != 0 else gpu_std
                chunk_gpu -= mean_i
                chunk_gpu /= std_i
                # Clip (same as sc.pp.scale max_value=10)
                cp.clip(chunk_gpu, -10, 10, out=chunk_gpu)
                gpu_chunks.append(chunk_gpu)

        cp.cuda.Stream.null.synchronize()
        log(f"  All chunks transferred+scaled in {time.time()-t0:.1f}s")
        vram_report(n_gpus)
        ram_report()

        # === DISTRIBUTED PCA: COVARIANCE METHOD ===
        n_comps = 50

        # Step 4: Local covariance on each GPU
        log(f"--- Step 4: Local covariance (X_i.T @ X_i) on {n_gpus} GPUs ---")
        t0 = time.time()
        local_covs = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                cov_i = X_i.T @ X_i
                local_covs.append(cov_i)
        cp.cuda.Stream.null.synchronize()
        log(f"  Local covariances in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Step 5: Sum covariances on GPU 0
        log("--- Step 5: Sum + eigendecomposition ---")
        t0 = time.time()
        with cp.cuda.Device(0):
            cov_total = cp.zeros((n_genes, n_genes), dtype=cp.float32)
            for i, cov_i in enumerate(local_covs):
                cov_total += cp.asarray(cov_i) if i != 0 else cov_i
            cov_total /= (n_cells - 1)
            eigenvalues, eigenvectors = cp.linalg.eigh(cov_total)
            eigenvalues = cp.ascontiguousarray(eigenvalues[::-1][:n_comps])
            eigenvectors = cp.ascontiguousarray(eigenvectors[:, ::-1][:, :n_comps])
            total_var = float(cp.trace(cov_total))
            explained_var = eigenvalues / total_var
        cp.cuda.Stream.null.synchronize()
        del local_covs, cov_total
        log(f"  Eigen done in {time.time()-t0:.1f}s")
        log(f"  Explained variance (50 PCs): {float(explained_var.sum()):.4f}")
        vram_report(n_gpus)

        # Step 6: Project each chunk
        log(f"--- Step 6: Projection on {n_gpus} GPUs ---")
        t0 = time.time()
        pca_chunks = []
        for i, X_i in enumerate(gpu_chunks):
            with cp.cuda.Device(i):
                V_i = cp.asarray(eigenvectors) if i != 0 else eigenvectors
                pca_chunks.append(X_i @ V_i)
        cp.cuda.Stream.null.synchronize()
        log(f"  Projection done in {time.time()-t0:.1f}s")

        # Gather PCA to CPU
        log("--- Gathering PCA to CPU ---")
        pca_cpu = []
        for i, pca_i in enumerate(pca_chunks):
            with cp.cuda.Device(i):
                pca_cpu.append(cp.asnumpy(pca_i))
        X_pca = np.vstack(pca_cpu)
        del pca_chunks, pca_cpu
        log(f"  PCA: {X_pca.shape}, {X_pca.nbytes/(1024**2):.1f} MB")

        # Free GPU chunks
        del gpu_chunks
        for i in range(n_gpus):
            with cp.cuda.Device(i):
                cp.get_default_memory_pool().free_all_blocks()
        gc.collect()
        vram_report(n_gpus)
        ram_report()

        # Store PCA
        adata.obsm["X_pca"] = X_pca
        adata.uns["pca"] = {
            "variance": cp.asnumpy(eigenvalues),
            "variance_ratio": cp.asnumpy(explained_var),
        }

        # Lean transfer + neighbors
        log("--- Lean transfer + Neighbors ---")
        import rapids_singlecell as rsc

        adata.X = sp.csr_matrix((adata.n_obs, adata.n_vars), dtype=np.float32)
        rsc.get.anndata_to_GPU(adata)
        t0 = time.time()
        rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  Neighbors done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # Leiden
        log("--- Leiden ---")
        t0 = time.time()
        rsc.tl.leiden(adata, resolution=1.0, random_state=RANDOM_SEED, key_added="leiden_1.0")
        cp.cuda.Stream.null.synchronize()
        log(f"  Leiden done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        # UMAP
        log("--- UMAP ---")
        t0 = time.time()
        rsc.tl.umap(adata, random_state=RANDOM_SEED)
        cp.cuda.Stream.null.synchronize()
        log(f"  UMAP done in {time.time()-t0:.1f}s")
        vram_report(n_gpus)

        log(f"SUCCESS [sparsescatter] — full pipeline, no dense on CPU")
        ram_report()
        return True

    except Exception as e:
        log(f"FAILED [sparsescatter]: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        vram_report(n_gpus)
        return False

    finally:
        _stop_dask(cluster, client)
        pynvml.nvmlShutdown()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Memory optimization diagnostic tests for max-power benchmark.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tests (run one at a time, in order):
  baseline   Current setup: RMM 10GB, scale on GPU
  rmm2gb     Reduce RMM pool to 2GB
  cpuscale   Scale on CPU + RMM 2GB
  scatter    Pre-scatter data across 8 GPUs + distributed PCA
  fullpipe   Full pipeline: scatter PCA + lean transfer + neighbors/leiden/UMAP + DE

Examples:
  python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test baseline
  python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test rmm2gb
  python scripts/test_memopt.py --data-dir data/ --target-cells 2000000 --test scatter
  python scripts/test_memopt.py --data-dir data/ --target-cells 3400000 --test fullpipe
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing brain_full_*.h5ad",
    )
    parser.add_argument(
        "--target-cells", type=int, required=True,
        help="Number of cells to test with",
    )
    parser.add_argument(
        "--n-gpus", type=int, default=8,
        help="Number of GPUs (default: 8)",
    )
    parser.add_argument(
        "--test", type=str, required=True,
        choices=["baseline", "rmm2gb", "cpuscale", "scatter", "fullpipe", "sparsescatter"],
        help="Which optimization test to run",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    global _T0
    _T0 = time.time()

    args = parse_args()
    sc.settings.verbosity = 0

    log(f"Test: {args.test} | Target cells: {args.target_cells:,} | GPUs: {args.n_gpus}")
    matrix_gb = args.target_cells * 2000 * 4 / (1024**3)
    log(f"Estimated dense matrix: {matrix_gb:.1f} GB (float32)")
    log(f"Per-GPU if scattered: {matrix_gb/args.n_gpus:.1f} GB")

    # CPU phase (same for all tests)
    adata = load_and_preprocess(args.data_dir, args.target_cells)

    # GPU phase (varies by test)
    if args.test == "baseline":
        success = test_gpu_phase(adata, args.n_gpus, "10GB", False, "baseline")
    elif args.test == "rmm2gb":
        success = test_gpu_phase(adata, args.n_gpus, "2GB", False, "rmm2gb")
    elif args.test == "cpuscale":
        success = test_gpu_phase(adata, args.n_gpus, "2GB", True, "cpuscale")
    elif args.test == "scatter":
        success = test_scatter(adata, args.n_gpus, "2GB")
    elif args.test == "fullpipe":
        success = test_fullpipe(adata, args.n_gpus, "2GB")
    elif args.test == "sparsescatter":
        success = test_sparsescatter(adata, args.n_gpus, "2GB")
    else:
        log(f"Unknown test: {args.test}")
        sys.exit(1)

    log(f"{'=' * 60}")
    log(f"RESULT: {'PASS' if success else 'FAIL'}")
    log(f"{'=' * 60}")
    sys.exit(0 if success else 1)


# Module-level timestamp for log()
_T0 = time.time()

if __name__ == "__main__":
    main()
