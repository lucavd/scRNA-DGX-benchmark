#!/usr/bin/env python3
"""Max-power benchmark: process ALL available mouse brain cells on 8× H100 GPUs.

Downloads the complete mouse brain dataset from CZ CELLxGENE Census (~3.6M cells)
and runs the full hybrid CPU+GPU pipeline on 8 GPUs.  This demonstrates the
maximum throughput of a single DGX H100 node for scRNA-seq analysis.

The script expects the data file to already exist (download separately via
download_data.py --max-cells 0), OR it can download it on-the-fly if
--download is specified.

Usage:
    python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/
    python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/ --download
    python scripts/benchmark_maxpower.py --help
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

import rapids_singlecell as rsc


# Fixed random seed
RANDOM_SEED = 42

# Leiden clustering resolutions
LEIDEN_RESOLUTIONS = [0.5, 1.0, 1.5]

OOM_EXIT_CODE = 10
INVALID_BENCHMARK_EXIT_CODE = 20
DASK_RMM_POOL_SIZE = "2GB"
DASK_RMM_MAXIMUM_POOL_SIZE = "70GB"

# Census configuration
CENSUS_VERSION = "2025-11-08"
CENSUS_FILTER = (
    "tissue_general == 'brain' "
    "and is_primary_data == True "
    "and assay in ['10x 3\\' v3', '10x 3\\' v2', '10x 3\\' v1']"
)
CENSUS_OBS_COLUMNS = [
    "cell_type", "assay", "tissue", "disease", "dataset_id", "donor_id",
]


# ---------------------------------------------------------------------------
# Memory monitoring helpers
# ---------------------------------------------------------------------------

def init_nvml() -> None:
    """Initialize NVML for GPU memory monitoring."""
    pynvml.nvmlInit()


def shutdown_nvml() -> None:
    """Shutdown NVML."""
    pynvml.nvmlShutdown()


def get_peak_ram_gb() -> float:
    """Get current process RSS memory in GB."""
    return psutil.Process().memory_info().rss / (1024**3)


def get_vram_used_gb(device_index: int = 0) -> float:
    """Get current GPU VRAM usage in GB."""
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return info.used / (1024**3)


def get_total_vram_used_gb(n_gpus: int) -> float:
    """Get total VRAM usage across all GPUs in GB."""
    total = 0.0
    for i in range(n_gpus):
        total += get_vram_used_gb(i)
    return total


def sha256_of_array(arr: np.ndarray) -> str:
    """Compute a short SHA256 hash of a numpy array."""
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def time_step(
    name: str,
    func: callable,
    timings: dict,
    memory: dict,
    n_gpus: int,
) -> Any:
    """Time a pipeline step and record RAM + VRAM usage.

    Args:
        name: Step name.
        func: Callable to execute.
        timings: Dict for wall-clock times.
        memory: Dict for RAM/VRAM snapshots.
        n_gpus: Number of GPUs to monitor.

    Returns:
        Whatever func() returns.
    """
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
        f"  {name:25s} | {elapsed:8.2f}s | "
        f"RAM: {ram_before:.1f}->{ram_after:.1f} GB | "
        f"VRAM(total): {vram_before:.1f}->{vram_after:.1f} GB"
    )

    return result


def get_gpu_info(n_gpus: int) -> dict:
    """Get GPU device information for all GPUs."""
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
# Data download
# ---------------------------------------------------------------------------

def download_full_brain(data_dir: Path) -> Path:
    """Download ALL mouse brain cells from CELLxGENE Census.

    Unlike the standard download which caps at 1.3M cells, this downloads
    every available cell matching our filter.

    Args:
        data_dir: Directory to save the h5ad file.

    Returns:
        Path to the saved h5ad file.
    """
    import cellxgene_census

    # Check if any brain_full file already exists
    existing = list(data_dir.glob("brain_full_*.h5ad"))
    if existing:
        path = existing[0]
        size_gb = path.stat().st_size / (1024**3)
        print(f"  Full dataset already exists: {path} ({size_gb:.2f} GB)")
        return path

    print(f"  Opening Census (version: {CENSUS_VERSION})...")
    start = time.time()

    with cellxgene_census.open_soma(census_version=CENSUS_VERSION) as census:
        # Step 1: Get metadata to know total count
        print("  Step 1/2: Fetching cell metadata...")
        obs_df = cellxgene_census.get_obs(
            census,
            organism="Mus musculus",
            value_filter=CENSUS_FILTER,
            column_names=["soma_joinid"] + CENSUS_OBS_COLUMNS,
        )
        total_cells = len(obs_df)
        print(f"  Found {total_cells:,} matching cells — downloading ALL")

        selected_ids = obs_df["soma_joinid"].tolist()
        del obs_df
        gc.collect()

        # Step 2: Download expression data for all cells
        print(f"  Step 2/2: Downloading expression data for {total_cells:,} cells...")
        adata = cellxgene_census.get_anndata(
            census=census,
            organism="Mus musculus",
            obs_coords=selected_ids,
            obs_column_names=CENSUS_OBS_COLUMNS,
        )

    elapsed = time.time() - start
    print(f"  Downloaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes in {elapsed:.0f}s")

    # Save with actual cell count in filename
    out_path = data_dir / f"brain_full_{adata.n_obs}.h5ad"
    print(f"  Saving to: {out_path}")
    adata.write_h5ad(out_path)
    size_gb = out_path.stat().st_size / (1024**3)
    print(f"  Saved: {size_gb:.2f} GB")

    del adata
    gc.collect()

    return out_path


# ---------------------------------------------------------------------------
# Dask cluster setup
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
    """Set up a Dask CUDA cluster with N GPUs.

    Args:
        n_gpus: Number of GPUs.

    Returns:
        Tuple of (cluster, client).
    """
    from dask_cuda import LocalCUDACluster
    from dask.distributed import Client

    device_list = ",".join(str(i) for i in range(n_gpus))

    # Log CUDA device visibility for debugging
    cuda_env = os.environ.get("CUDA_VISIBLE_DEVICES", "not set")
    print(f"  CUDA_VISIBLE_DEVICES env: {cuda_env}")
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
        worker_addresses = []
        n_workers = 0
        while time.monotonic() < deadline:
            workers = _get_running_scheduler_workers(client)
            worker_addresses = sorted(workers)
            n_workers = len(worker_addresses)
            if n_workers == n_gpus:
                stable_checks += 1
                if stable_checks >= 3:
                    break
            else:
                stable_checks = 0
            time.sleep(1)
        print(f"  Dask dashboard: {client.dashboard_link}")
        print(f"  Workers: {n_workers}")
        print(f"  Worker addresses: {worker_addresses}")
        if n_workers != n_gpus:
            raise RuntimeError(
                f"Dask CUDA cluster started with {n_workers} workers, expected {n_gpus}",
            )
        return cluster, client
    except Exception as e:
        worker_addresses = []
        if client is not None:
            try:
                worker_addresses = sorted(_get_running_scheduler_workers(client))
            except Exception:
                worker_addresses = []
            client.close()
        print(
            "  GPU VRAM during Dask startup failure: "
            + ", ".join(f"GPU {i}: {get_vram_used_gb(i):.1f} GB" for i in range(n_gpus)),
        )
        cluster.close()
        raise RuntimeError(
            f"Dask CUDA cluster did not reach {n_gpus} workers; got {len(worker_addresses)} "
            f"workers: {worker_addresses}",
        ) from e


def gpu_warmup(n_gpus: int) -> None:
    """Warm up all GPUs with small dummy operations."""
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
# Distributed covariance PCA
# ---------------------------------------------------------------------------

def _distributed_covariance_pca(
    adata: sc.AnnData,
    n_gpus: int,
    n_comps: int = 50,
) -> None:
    """Compute PCA via covariance method distributed across all GPUs.

    Instead of putting the entire dense matrix on GPU 0 (which OOMs at ~2M+
    cells), this distributes data chunks across all GPUs.  Each GPU computes
    its local covariance contribution (X_i.T @ X_i), the contributions are
    summed on GPU 0, eigendecomposed, and each GPU projects its chunk.

    Mathematically equivalent to standard PCA: eigh(X.T @ X / (n-1)).

    Memory per GPU: ~(n_cells/n_gpus × n_genes × 4B) + workspace.
    For 3.4M cells × 2000 genes on 8 GPUs: ~3.2 GB per GPU.

    Args:
        adata: AnnData with dense scaled .X on CPU (float32).
        n_gpus: Number of GPUs to distribute across.
        n_comps: Number of PCA components (default: 50).
    """
    X_np = np.ascontiguousarray(adata.X, dtype=np.float32)
    n_cells, n_genes = X_np.shape

    # Split into chunks — one per GPU
    chunk_size = n_cells // n_gpus
    remainder = n_cells % n_gpus
    chunks = []
    offset = 0
    for i in range(n_gpus):
        end = offset + chunk_size + (1 if i < remainder else 0)
        chunks.append(X_np[offset:end])
        offset = end

    print(f"    Scatter: {n_gpus} chunks, ~{chunk_size:,} rows each, "
          f"{chunks[0].nbytes / (1024**3):.2f} GB/chunk")

    # Transfer each chunk to its own GPU
    gpu_chunks = []
    for i, chunk in enumerate(chunks):
        with cp.cuda.Device(i):
            gpu_chunks.append(cp.asarray(chunk))
    cp.cuda.Stream.null.synchronize()

    del chunks
    gc.collect()

    # Step 1: Each GPU computes local X_i.T @ X_i (2000×2000 = 16 MB)
    local_covs = []
    for i, X_i in enumerate(gpu_chunks):
        with cp.cuda.Device(i):
            local_covs.append(X_i.T @ X_i)
    cp.cuda.Stream.null.synchronize()

    # Step 2: Sum covariance contributions on GPU 0
    with cp.cuda.Device(0):
        cov_total = cp.zeros((n_genes, n_genes), dtype=np.float32)
        for i, cov_i in enumerate(local_covs):
            if i == 0:
                cov_total += cov_i
            else:
                cov_total += cp.asarray(cov_i)
        cov_total /= (n_cells - 1)
    cp.cuda.Stream.null.synchronize()
    del local_covs

    # Step 3: Eigendecomposition on GPU 0 (2000×2000 — trivial)
    with cp.cuda.Device(0):
        eigenvalues, eigenvectors = cp.linalg.eigh(cov_total)
        # eigh returns ascending — reverse for descending
        eigenvalues = cp.ascontiguousarray(eigenvalues[::-1][:n_comps])
        eigenvectors = cp.ascontiguousarray(eigenvectors[:, ::-1][:, :n_comps])
        total_var = float(cp.trace(cov_total))
        explained_var = eigenvalues / total_var
    cp.cuda.Stream.null.synchronize()
    del cov_total

    print(f"    Explained variance ({n_comps} PCs): {float(explained_var.sum()):.4f}")

    # Step 4: Project each chunk on its GPU
    pca_chunks = []
    for i, X_i in enumerate(gpu_chunks):
        with cp.cuda.Device(i):
            V_i = cp.asarray(eigenvectors) if i != 0 else eigenvectors
            pca_chunks.append(X_i @ V_i)
    cp.cuda.Stream.null.synchronize()

    # Free GPU data chunks
    del gpu_chunks
    for i in range(n_gpus):
        with cp.cuda.Device(i):
            cp.get_default_memory_pool().free_all_blocks()

    # Gather PCA results to CPU
    pca_cpu = []
    for i, pca_i in enumerate(pca_chunks):
        with cp.cuda.Device(i):
            pca_cpu.append(cp.asnumpy(pca_i))
    X_pca = np.vstack(pca_cpu)
    del pca_chunks, pca_cpu

    # Store in adata (scanpy-compatible format)
    adata.obsm["X_pca"] = X_pca
    adata.uns["pca"] = {
        "variance": cp.asnumpy(eigenvalues),
        "variance_ratio": cp.asnumpy(explained_var),
        "params": {
            "n_comps": n_comps,
            "method": "covariance_distributed",
            "n_gpus": n_gpus,
            "random_state": RANDOM_SEED,
        },
    }

    print(f"    PCA stored: {X_pca.shape} ({X_pca.nbytes / (1024**2):.0f} MB)")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def resize_dataset(adata: sc.AnnData, target_cells: int) -> sc.AnnData:
    """Resize an AnnData to exactly target_cells by replicating + subsampling.

    If target_cells <= adata.n_obs, subsamples.
    If target_cells > adata.n_obs, replicates the dataset enough times and
    then subsamples down to the exact target.

    Each replica gets a unique suffix on obs_names to avoid duplicates.

    Args:
        adata: Source AnnData object.
        target_cells: Exact number of cells desired.

    Returns:
        AnnData with exactly target_cells cells.
    """
    import anndata

    n_orig = adata.n_obs

    if target_cells == n_orig:
        return adata

    if target_cells < n_orig:
        print(f"  Subsampling {n_orig:,} -> {target_cells:,} cells...")
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(n_orig, size=target_cells, replace=False)
        return adata[sorted(idx)].copy()

    # Need to replicate: figure out how many full copies + remainder
    n_full_copies = target_cells // n_orig
    remainder = target_cells % n_orig

    print(f"  Resizing: {n_orig:,} × {n_full_copies} + {remainder:,} = {target_cells:,} cells...")
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


def run_pipeline(
    adata_path: Path, n_gpus: int, target_cells: int = 0, skip_de: bool = False,
    clustering: str = "leiden",
) -> tuple:
    """Run the full hybrid CPU+GPU pipeline on all available GPUs.

    Phase 1 (CPU): data loading, QC, normalization, HVG selection, scale
    Phase 2 (GPU): PCA (scatter across all GPUs), lean transfer, neighbors,
                    leiden, UMAP
    Phase 3 (CPU): DE with Wilcoxon on all genes (unless --skip-de)

    Args:
        adata_path: Path to the input h5ad file.
        n_gpus: Number of GPUs to use.
        target_cells: If > 0, resize dataset to this many cells (replicate/subsample).
        skip_de: If True, skip differential expression testing.

    Returns:
        Tuple of (result dict, adata on CPU, hvg_list).
    """
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    # Read actual cell count from filename (brain_full_NNNNN.h5ad or brain_NNNNN.h5ad)
    stem = adata_path.stem
    n_cells_file = int(stem.split("_")[-1])

    print(f"\n{'=' * 80}")
    if target_cells > 0 and target_cells != n_cells_file:
        print(f"MAX-POWER BENCHMARK — target {target_cells:,} cells (from {n_cells_file:,}) — {n_gpus} GPUs")
    else:
        print(f"MAX-POWER BENCHMARK — {n_cells_file:,} cells — {n_gpus} GPUs")
    print(f"{'=' * 80}")

    dask_setup_info = {
        "n_workers": n_gpus,
        "rmm_pool_size": DASK_RMM_POOL_SIZE,
        "rmm_maximum_pool_size": DASK_RMM_MAXIMUM_POOL_SIZE,
    }

    print(
        f"  {'Step':25s} | {'Time':>8s} | {'RAM':>20s} | {'VRAM (total)':>20s}"
    )
    print(f"  {'-' * 25}-+-{'-' * 8}-+-{'-' * 20}-+-{'-' * 20}")

    # === PHASE 1: CPU (scanpy) ===

    def load_data():
        return sc.read_h5ad(adata_path)

    adata = time_step("data_loading", load_data, timings, memory, n_gpus)
    print(f"    Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # Resize dataset if requested
    if target_cells > 0 and target_cells != adata.n_obs:
        adata = resize_dataset(adata, target_cells)

    def qc_filter():
        adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False, inplace=True)
        sc.pp.filter_cells(adata, min_genes=200)
        sc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory, n_gpus)
    n_cells_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_cells_after_qc:,} cells x {n_genes_after_qc:,} genes")

    def normalize():
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory, n_gpus)

    def hvg_selection():
        sc.pp.highly_variable_genes(adata, n_top_genes=2000)

    time_step("hvg_selection", hvg_selection, timings, memory, n_gpus)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()
    print(f"    After HVG subset: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # === PHASE 2: GPU ===
    # Strategy: scale on CPU (2 TB RAM), distribute data across all GPUs for
    # PCA (covariance method), then transfer to GPU 0 for neighbors/clustering.
    # This avoids the GPU 0 bottleneck where scale+PCA exceeded 80 GB VRAM.

    # Scale on CPU — converts sparse → dense (25 GB for 3.4M cells is trivial
    # on 2 TB RAM; on GPU 0 it caused OOM at 3.4M).
    def cpu_scale():
        if hasattr(adata.X, "toarray"):
            adata.X = adata.X.toarray()
        sc.pp.scale(adata, max_value=10)

    time_step("scale", cpu_scale, timings, memory, n_gpus)

    # Start Dask CUDA cluster
    print(f"\n  Starting Dask CUDA cluster for multi-GPU PCA...")
    cluster_obj = None
    client = None
    try:
        cluster_obj, client = setup_dask_cluster(n_gpus)
        workers = _get_running_scheduler_workers(client)
        dask_setup_info["actual_n_workers"] = len(workers)
        dask_setup_info["worker_addresses"] = sorted(workers)
        print(
            "  GPU VRAM after Dask startup: "
            + ", ".join(f"GPU {i}: {get_vram_used_gb(i):.1f} GB" for i in range(n_gpus)),
        )

        # Distributed PCA: scatter data across all GPUs, covariance method
        def scatter_pca():
            _distributed_covariance_pca(adata, n_gpus, n_comps=50)

        time_step("pca", scatter_pca, timings, memory, n_gpus)

        # Lean GPU transfer: replace scaled X with empty sparse matrix.
        # After PCA, adata.X (25 GB dense) is no longer needed — neighbors
        # only uses X_pca (0.6 GB in obsm). This drops GPU 0 from ~29 GB
        # to ~4 GB, dramatically increasing the cell count limit.
        import scipy.sparse as sp
        print(f"    Dropping adata.X ({adata.X.nbytes/(1024**3):.1f} GB) — not needed after PCA")
        adata.X = sp.csr_matrix((adata.n_obs, adata.n_vars), dtype=np.float32)

        def transfer_to_gpu():
            rsc.get.anndata_to_GPU(adata)

        time_step("gpu_transfer", transfer_to_gpu, timings, memory, n_gpus)

        # Neighbors on GPU 0 — uses only PCA coordinates (n_cells × 50)
        time_step(
            "neighbors",
            lambda: rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED),
            timings, memory, n_gpus,
        )
    finally:
        if client is not None or cluster_obj is not None:
            print("\n  Shutting down Dask cluster...")
        if client is not None:
            client.close()
        if cluster_obj is not None:
            cluster_obj.close()

    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()
    rmm.reinitialize(pool_allocator=True, devices=0)

    # Single-GPU steps: clustering
    cluster_results = {}
    if clustering == "kmeans":
        # GPU-native KMeans via cuML — scales beyond leiden's memory limit
        from cuml import KMeans as cuKMeans

        # Map leiden resolutions to approximate k values
        # (more resolution → more clusters)
        kmeans_k_map = {0.5: 50, 1.0: 100, 1.5: 200}
        for res in LEIDEN_RESOLUTIONS:
            k = kmeans_k_map[res]
            key = f"kmeans_{res}"

            def _run_kmeans(n_clusters=k, r=res):
                km = cuKMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, max_iter=300)
                X_pca = adata.obsm["X_pca"]
                if not hasattr(X_pca, "__cuda_array_interface__"):
                    X_pca = cp.asarray(X_pca)
                labels = km.fit_predict(X_pca)
                if hasattr(labels, "get"):
                    labels = labels.get()
                adata.obs[f"kmeans_{r}"] = labels.astype(str)

            time_step(key, _run_kmeans, timings, memory, n_gpus)
            labels = adata.obs[f"kmeans_{res}"].values
            if hasattr(labels, "get"):
                labels = labels.get()
            n_clusters = len(np.unique(np.asarray(labels)))
            cluster_results[key] = {
                "n_clusters": n_clusters,
                "labels_hash": sha256_of_array(np.asarray(labels, dtype=str)),
            }
            print(f"    {key}: {n_clusters} clusters (k={kmeans_k_map[res]})")
    else:
        # Default: Leiden via cugraph (GPU) — OOMs above ~12M cells
        for res in LEIDEN_RESOLUTIONS:
            key = f"leiden_{res}"
            time_step(
                key,
                lambda r=res: rsc.tl.leiden(
                    adata, resolution=r, random_state=RANDOM_SEED, key_added=f"leiden_{r}",
                ),
                timings, memory, n_gpus,
            )
            labels = adata.obs[f"leiden_{res}"].values
            if hasattr(labels, "get"):
                labels = labels.get()
            n_clusters = len(np.unique(np.asarray(labels)))
            cluster_results[key] = {
                "n_clusters": n_clusters,
                "labels_hash": sha256_of_array(np.asarray(labels, dtype=str)),
            }
            print(f"    {key}: {n_clusters} clusters")

    time_step(
        "umap",
        lambda: rsc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory, n_gpus,
    )

    # Transfer back to CPU
    print("\n  Transferring data back to CPU...")
    rsc.get.anndata_to_CPU(adata)

    # DE: run on CPU with all genes (raw.X is 121 GB sparse at 3.4M cells —
    # too large for a single GPU). Skip in binary search mode (--skip-de).
    if skip_de:
        print("  DE skipped (--skip-de)")
        timings["de_testing"] = 0.0
    else:
        def run_de():
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
                sc.tl.rank_genes_groups(
                    adata, groupby="leiden_1.0", method="wilcoxon", use_raw=True,
                )

        time_step("de_testing", run_de, timings, memory, n_gpus)

    # Total
    timings["total"] = round(sum(timings.values()), 4)

    peak_ram = max(v for k, v in memory.items() if k.endswith("_ram_after_gb"))
    peak_vram = max(v for k, v in memory.items() if k.endswith("_vram_after_gb"))

    print(
        f"\n  {'TOTAL':25s} | {timings['total']:8.2f}s | "
        f"Peak RAM: {peak_ram:.1f} GB | Peak VRAM(total): {peak_vram:.1f} GB"
    )

    # Summary
    ram_total = 2048  # DGX H100 total RAM
    vram_per_gpu = 80
    vram_total = vram_per_gpu * n_gpus
    print(f"\n  Resource utilization:")
    print(f"    RAM:  {peak_ram:.0f} / {ram_total} GB ({peak_ram/ram_total*100:.1f}%)")
    print(f"    VRAM: {peak_vram:.0f} / {vram_total} GB ({peak_vram/vram_total*100:.1f}%)")

    gpu_info = get_gpu_info(n_gpus)

    n_cells_effective = target_cells if target_cells > 0 else n_cells_file

    result = {
        "metadata": {
            "pipeline": f"maxpower_{n_gpus}gpu",
            "n_cells_input": n_cells_effective,
            "n_cells_source_file": n_cells_file,
            "target_cells": target_cells,
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
                "python": f"{os.sys.version}",
                "numpy": np.__version__,
            },
            "configuration": {
                "dask_cluster": dask_setup_info,
                "gpu_warmup": True,
                "clustering_algorithm": clustering,
                "leiden_backend": "cugraph" if clustering == "leiden" else None,
                "cpu_steps": [
                    "data_loading", "qc_filtering", "normalization",
                    "hvg_selection", "scale",
                ],
                "multi_gpu_steps": ["pca"],
                "single_gpu_steps": [
                    "gpu_transfer", "neighbors", "leiden", "umap", "de_testing",
                ],
                "pca_method": "covariance_distributed",
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
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Max-power benchmark: all mouse brain cells on 8 H100 GPUs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/
  python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/ --download
  python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/ --n-gpus 4
  python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/ --target-cells 7200000
  python scripts/benchmark_maxpower.py --data-dir data/ --output-dir results/ --find-limit
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing (or to download to) h5ad data files",
    )
    parser.add_argument(
        "--output-dir", type=str, required=True,
        help="Directory to save benchmark results",
    )
    parser.add_argument(
        "--n-gpus", type=int, default=8,
        help="Number of GPUs (default: 8 = full DGX node)",
    )
    parser.add_argument(
        "--target-cells", type=int, default=0,
        help="Resize dataset to this many cells (replicate if needed). 0 = use as-is.",
    )
    parser.add_argument(
        "--find-limit", action="store_true",
        help="Binary search for max cells before OOM. Runs multiple passes automatically.",
    )
    parser.add_argument(
        "--fine-low", type=int, default=0,
        help="Skip coarse search; start fine binary search from this lower bound (success)",
    )
    parser.add_argument(
        "--fine-high", type=int, default=0,
        help="Skip coarse search; start fine binary search from this upper bound (fail)",
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Download the full dataset from CELLxGENE Census if not present",
    )
    parser.add_argument(
        "--skip-de", action="store_true",
        help="Skip differential expression (for binary search — DE is slow on CPU at >3M cells)",
    )
    parser.add_argument(
        "--clustering", type=str, default="leiden", choices=["leiden", "kmeans"],
        help="Clustering algorithm: leiden (default, OOM at >12M) or kmeans (GPU-native, scalable)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    n_gpus = args.n_gpus

    # Find or download the full brain dataset
    existing = list(data_dir.glob("brain_full_*.h5ad"))
    if existing:
        adata_path = existing[0]
        print(f"Found full dataset: {adata_path}")
    elif args.download:
        print("Downloading full mouse brain dataset from CELLxGENE Census...")
        adata_path = download_full_brain(data_dir)
    else:
        print("ERROR: No brain_full_*.h5ad file found in data directory.")
        print("  Run with --download to fetch it from CELLxGENE Census,")
        print("  or run download_data.py separately first.")
        raise SystemExit(1)

    if args.find_limit:
        # In find-limit mode the parent process must NOT touch GPUs at all.
        # Each attempt runs in a clean subprocess with its own CUDA context.
        print(f"\nSystem RAM: {psutil.virtual_memory().total / (1024**3):.0f} GB")
        run_find_limit(adata_path, n_gpus, output_dir, args.fine_low, args.fine_high, args.clustering)
    else:
        # Single-run mode: initialize GPU and run directly
        init_nvml()
        try:
            gpu_info = get_gpu_info(n_gpus)
            print(f"\nDGX Configuration:")
            for gpu in gpu_info["gpus"]:
                print(f"  GPU {gpu['device_index']}: {gpu['gpu_name']} ({gpu['gpu_vram_total_gb']} GB)")
            print(f"  Driver: {gpu_info['driver_version']}")
            print(f"  Total VRAM: {sum(g['gpu_vram_total_gb'] for g in gpu_info['gpus']):.0f} GB")
            print(f"  System RAM: {psutil.virtual_memory().total / (1024**3):.0f} GB")

            sc.settings.verbosity = 0

            result = run_single(adata_path, n_gpus, args.target_cells, output_dir, args.skip_de, args.clustering)
            if result is None:
                raise SystemExit(OOM_EXIT_CODE)
        except RuntimeError as e:
            message = str(e).lower()
            if any(token in message for token in (
                "did not reach",
                "expected 8",
                "expected workers",
                "cluster started with",
            )):
                print(
                    "\nINVALID BENCHMARK RUN: max-power requires all requested "
                    f"{n_gpus} Dask workers to be active. {e}",
                )
                raise SystemExit(INVALID_BENCHMARK_EXIT_CODE) from e
            raise
        finally:
            shutdown_nvml()

    print("\nDone!")


def run_single(
    adata_path: Path, n_gpus: int, target_cells: int, output_dir: Path,
    skip_de: bool = False, clustering: str = "leiden",
) -> dict | None:
    """Run a single benchmark and save results.

    Returns:
        Result dict if successful, None if OOM.
    """
    try:
        result, adata, hvg_list = run_pipeline(adata_path, n_gpus, target_cells, skip_de, clustering)
    except (MemoryError, cp.cuda.memory.OutOfMemoryError) as e:
        print(f"\n  OOM ERROR at {target_cells:,} cells: {e}")
        gc.collect()
        cp.get_default_memory_pool().free_all_blocks()
        return None
    except RuntimeError as e:
        message = str(e).lower()
        if any(token in message for token in (
            "out_of_memory",
            "cudaerrormemoryallocation",
            "std::bad_alloc",
            "rmm::bad_alloc",
            "failed to allocate",
        )):
            print(f"\n  OOM ERROR at {target_cells:,} cells: {e}")
            gc.collect()
            cp.get_default_memory_pool().free_all_blocks()
            return None
        raise

    # Save results
    n_cells = result["metadata"]["n_cells_input"]
    prefix = f"maxpower_{n_cells}_{n_gpus}gpu"

    json_path = output_dir / f"{prefix}_results.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {json_path}")

    # Print final summary
    t = result["timings"]
    r = result["resource_utilization"]
    print(f"\n{'=' * 80}")
    print(f"MAX-POWER SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Cells processed:  {result['results_summary']['n_cells_after_qc']:,}")
    print(f"  GPUs used:        {n_gpus}× H100 80GB")
    print(f"  Total time:       {t['total']:.1f}s ({t['total']/60:.1f} min)")
    print(f"  RAM used:         {r['ram_used_gb']:.0f} / {r['ram_total_gb']} GB ({r['ram_pct']:.1f}%)")
    print(f"  VRAM used:        {r['vram_used_gb']:.0f} / {r['vram_total_gb']} GB ({r['vram_pct']:.1f}%)")
    print(f"  Throughput:       {result['results_summary']['n_cells_after_qc'] / t['total']:,.0f} cells/second")
    clust_key = "n_clusters_1.0"
    clust_algo = clustering
    print(f"  Clusters found:   {result['results_summary'][clust_key]} ({clust_algo} res=1.0)")

    del adata, hvg_list
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()

    return result


def _run_in_subprocess(
    script_path: str,
    data_dir: str,
    output_dir: str,
    n_gpus: int,
    target_cells: int,
    clustering: str = "leiden",
) -> bool:
    """Run a single benchmark attempt in an isolated subprocess.

    This ensures complete GPU memory cleanup between attempts — the subprocess
    exits, all CUDA contexts are destroyed, and the next attempt starts fresh.

    Args:
        script_path: Path to this script (benchmark_maxpower.py).
        data_dir: Data directory.
        output_dir: Output directory.
        n_gpus: Number of GPUs.
        target_cells: Target cell count.

    Returns:
        True if the run succeeded, False if it OOM'd or crashed.
    """
    import subprocess as _sp

    cmd = [
        sys.executable, "-u", script_path,
        "--data-dir", data_dir,
        "--output-dir", output_dir,
        "--n-gpus", str(n_gpus),
        "--target-cells", str(target_cells),
        "--skip-de",  # DE is too slow for binary search; run separately
        "--clustering", clustering,
    ]

    print(f"  Launching subprocess: target={target_cells:,} cells, {n_gpus} GPUs")
    result = _sp.run(cmd, timeout=86400)  # 24h timeout per attempt
    if result.returncode == 0:
        return True
    if result.returncode == OOM_EXIT_CODE:
        return False
    if result.returncode == INVALID_BENCHMARK_EXIT_CODE:
        raise RuntimeError(
            "Benchmark subprocess failed because the 8-GPU Dask cluster did not "
            f"start completely for target={target_cells:,} cells. This run is "
            "invalid and find-limit must stop.",
        )
    raise RuntimeError(
        f"Benchmark subprocess failed with exit code {result.returncode} "
        f"for target={target_cells:,} cells",
    )


def run_find_limit(
    adata_path: Path, n_gpus: int, output_dir: Path,
    fine_low: int = 0, fine_high: int = 0, clustering: str = "leiden",
) -> None:
    """Binary search for the maximum number of cells before OOM.

    Each attempt runs in an isolated subprocess so GPU memory is fully released
    between iterations (no VRAM leak accumulation).

    Strategy:
      1. Coarse phase: try N, 2N, 3N, ... to find where it fails
      2. Fine phase: binary search between last-success and first-fail with 100k steps

    If fine_low and fine_high are both > 0, skip coarse and go directly to fine.
    """
    # Find the script path for subprocess invocation
    script_path = str(Path(__file__).resolve())

    stem = adata_path.stem
    n_source = int(stem.split("_")[-1])

    print(f"\n{'=' * 80}")
    print(f"FIND-LIMIT MODE: subprocess isolation for clean GPU memory")
    print(f"Source dataset: {n_source:,} cells")
    print(f"{'=' * 80}")

    last_success = 0
    first_fail = 0

    # Skip coarse phase if bounds are provided
    if fine_low > 0 and fine_high > 0:
        last_success = fine_low
        first_fail = fine_high
        print(f"\n--- Skipping coarse search (provided bounds: {fine_low:,}–{fine_high:,}) ---")
    else:
        # Phase 1: coarse search — big jumps to find the crash zone
        coarse_targets = [n_source]
        step = n_source
        while coarse_targets[-1] + step <= 50_000_000:
            coarse_targets.append(coarse_targets[-1] + step)

        print(f"\n--- Phase 1: Coarse search (step ~{n_source:,}) ---")
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
            print(f"\n  All targets succeeded up to {coarse_targets[-1]:,} cells!")
            print(f"  The DGX can handle at least {coarse_targets[-1]:,} cells.")
            return

    # Phase 2: fine search — binary search with 100k steps
    print(f"\n--- Phase 2: Fine search between {last_success:,} and {first_fail:,} ---")
    fine_step = 100_000
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
            print(f"  >>> SUCCESS at {mid:,}")
        else:
            high = mid
            print(f"  >>> FAILED at {mid:,}")

    print(f"\n{'=' * 80}")
    print(f"LIMIT FOUND")
    print(f"{'=' * 80}")
    print(f"  Maximum cells:  {low:,}")
    print(f"  First OOM at:   {high:,}")
    print(f"  Clustering:     {clustering}")
    print(f"  Configuration:  {n_gpus}× NVIDIA H100 80GB, ~1800 GB RAM")
    print(f"  Source dataset: {n_source:,} cells (replicated to reach limit)")
    print(f"  PCA method:     covariance_distributed (scatter across {n_gpus} GPUs)")

    # Save summary to JSON
    summary = {
        "max_cells": low,
        "first_oom_at": high,
        "n_gpus": n_gpus,
        "clustering": clustering,
        "source_cells": n_source,
        "pca_method": "covariance_distributed",
        "rmm_pool_size": DASK_RMM_POOL_SIZE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    suffix = f"_{clustering}" if clustering != "leiden" else ""
    summary_path = output_dir / f"maxpower_limit_{n_gpus}gpu{suffix}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved:  {summary_path}")


if __name__ == "__main__":
    main()
