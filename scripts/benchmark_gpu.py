#!/usr/bin/env python3
"""GPU benchmark: run the full rapids-singlecell pipeline and measure performance.

Executes a standard single-cell RNA-seq analysis pipeline using
rapids-singlecell (GPU) and records wall-clock time, peak RAM, and peak VRAM
for each step.

Best-of-breed configuration:
- RMM memory pool: pre-allocates GPU memory so that individual allocations
  avoid the slow cudaMalloc path. Significantly improves performance on
  repeated small allocations (common in single-cell pipelines).
- GPU warmup: a small dummy operation runs before timing to absorb CUDA
  context initialization and JIT compilation overhead.
- Leiden clustering: uses cugraph backend (default in rapids-singlecell),
  the GPU counterpart to igraph on CPU.

Usage:
    python scripts/benchmark_gpu.py --data-dir data/ --output-dir results/ --n-cells 10000
    python scripts/benchmark_gpu.py --help
"""

import argparse
import gc
import hashlib
import json
import os
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from importlib.metadata import version as pkg_version

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
    """Get current GPU VRAM usage in GB.

    Args:
        device_index: GPU device index (default: 0).

    Returns:
        VRAM used in GB.
    """
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return info.used / (1024**3)


def sha256_of_array(arr: np.ndarray) -> str:
    """Compute a SHA256 hash of a numpy array for reproducibility checks."""
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def time_step(
    name: str,
    func: callable,
    timings: dict,
    memory: dict,
    device_index: int = 0,
) -> Any:
    """Time a pipeline step and record RAM + VRAM usage.

    Args:
        name: Name of the step (used as key in timings/memory dicts).
        func: Callable to execute (takes no arguments).
        timings: Dict to store wall-clock time (seconds).
        memory: Dict to store RAM/VRAM snapshots.
        device_index: GPU device index for VRAM monitoring.

    Returns:
        Whatever func() returns.
    """
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()

    ram_before = get_peak_ram_gb()
    vram_before = get_vram_used_gb(device_index)

    # Synchronize GPU before timing
    cp.cuda.Stream.null.synchronize()
    start = time.perf_counter()

    result = func()

    # Synchronize GPU after step to get accurate timing
    cp.cuda.Stream.null.synchronize()
    elapsed = time.perf_counter() - start

    ram_after = get_peak_ram_gb()
    vram_after = get_vram_used_gb(device_index)

    timings[name] = round(elapsed, 4)
    memory[f"{name}_ram_before_gb"] = round(ram_before, 2)
    memory[f"{name}_ram_after_gb"] = round(ram_after, 2)
    memory[f"{name}_vram_before_gb"] = round(vram_before, 2)
    memory[f"{name}_vram_after_gb"] = round(vram_after, 2)

    print(
        f"  {name:25s} | {elapsed:8.2f}s | "
        f"RAM: {ram_before:.1f}->{ram_after:.1f} GB | "
        f"VRAM: {vram_before:.1f}->{vram_after:.1f} GB"
    )

    return result


def get_gpu_info(device_index: int = 0) -> dict:
    """Get GPU device information.

    Args:
        device_index: GPU device index.

    Returns:
        Dict with GPU name, total VRAM, driver version.
    """
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    name = pynvml.nvmlDeviceGetName(handle)
    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    driver = pynvml.nvmlSystemGetDriverVersion()
    return {
        "gpu_name": name if isinstance(name, str) else name.decode(),
        "gpu_vram_total_gb": round(mem_info.total / (1024**3), 1),
        "driver_version": driver if isinstance(driver, str) else driver.decode(),
    }


def init_rmm_pool(device_index: int = 0) -> dict:
    """Initialize RMM memory pool for optimal GPU allocation performance.

    Without a pool, every GPU allocation goes through cudaMalloc which is slow.
    The pool pre-allocates memory so subsequent allocations are near-instant.

    RMM 26.02+ defaults: initial_pool_size = 50% VRAM, maximum = 100% VRAM.
    CuPy allocator is registered automatically by rmm.reinitialize().

    Args:
        device_index: GPU device index.

    Returns:
        Dict with pool configuration details.
    """
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    total_vram = pynvml.nvmlDeviceGetMemoryInfo(handle).total

    # Use RMM defaults (50% initial, 100% max) — safe and optimal
    rmm.reinitialize(
        pool_allocator=True,
        devices=device_index,
    )

    pool_config = {
        "pool_allocator": True,
        "total_vram_gb": round(total_vram / (1024**3), 1),
        "initial_pool": "50% (RMM default)",
        "maximum_pool": "100% (RMM default)",
    }
    print(f"  RMM pool enabled: {pool_config['total_vram_gb']} GB total VRAM")
    return pool_config


def gpu_warmup() -> None:
    """Run a small dummy operation to warm up the CUDA context.

    The first GPU operation always includes overhead from CUDA context
    initialization and JIT compilation. Running a warmup avoids charging
    this one-time cost to the first benchmark step.
    """
    print("  GPU warmup (CUDA context + JIT)...", end=" ", flush=True)
    # Small matmul to trigger kernel compilation
    a = cp.random.random((100, 100), dtype=cp.float32)
    _ = cp.dot(a, a)
    cp.cuda.Stream.null.synchronize()
    del a, _
    cp.get_default_memory_pool().free_all_blocks()
    print("done")


def run_pipeline(adata_path: Path, device_index: int = 0) -> dict:
    """Run the full rapids-singlecell GPU pipeline with timing.

    Args:
        adata_path: Path to the input h5ad file.
        device_index: GPU device index to use.

    Returns:
        Tuple of (result dict, adata on CPU, hvg_list).
    """
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    print(f"\n{'=' * 80}")
    print(f"GPU BENCHMARK — {adata_path.name} — GPU {device_index}")
    print(f"{'=' * 80}")

    # Initialize RMM pool and warm up GPU before any timed operations
    rmm_config = init_rmm_pool(device_index)
    gpu_warmup()

    print(
        f"  {'Step':25s} | {'Time':>8s} | {'RAM':>20s} | {'VRAM':>20s}"
    )
    print(f"  {'-'*25}-+-{'-'*8}-+-{'-'*20}-+-{'-'*20}")

    # 1. Data loading (read on CPU first, then transfer to GPU)
    def load_and_transfer():
        adata = sc.read_h5ad(adata_path)
        rsc.get.anndata_to_GPU(adata)
        return adata

    adata = time_step(
        "data_loading", load_and_transfer, timings, memory, device_index,
    )
    print(f"    Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # 2. QC & filtering
    def qc_filter():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
            rsc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False)
            adata.obs = adata.obs.copy()
            adata.var = adata.var.copy()
            rsc.pp.filter_cells(adata, min_genes=200)
            rsc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory, device_index)
    n_cells_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_cells_after_qc:,} cells x {n_genes_after_qc:,} genes")

    # 3. Normalization
    def normalize():
        rsc.pp.normalize_total(adata, target_sum=1e4)
        rsc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory, device_index)

    # 4. HVG selection
    def hvg_selection():
        # Use default flavor (seurat) which works on log-normalized data
        rsc.pp.highly_variable_genes(adata, n_top_genes=2000)

    time_step("hvg_selection", hvg_selection, timings, memory, device_index)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    # Store raw and subset to HVGs
    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()

    # 5. PCA
    def run_pca():
        rsc.pp.scale(adata, max_value=10)
        rsc.pp.pca(adata, n_comps=50, random_state=RANDOM_SEED)

    time_step("pca", run_pca, timings, memory, device_index)

    # 6. Neighbor graph
    time_step(
        "neighbors",
        lambda: rsc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED),
        timings, memory, device_index,
    )

    # 7. Clustering (multiple resolutions)
    cluster_results = {}
    for res in LEIDEN_RESOLUTIONS:
        key = f"leiden_{res}"
        time_step(
            key,
            lambda r=res: rsc.tl.leiden(
                adata, resolution=r, random_state=RANDOM_SEED, key_added=f"leiden_{r}",
            ),
            timings, memory, device_index,
        )
        labels = adata.obs[f"leiden_{res}"].values
        # Labels may be cupy array or categorical — convert to numpy
        if hasattr(labels, "get"):
            labels = labels.get()
        n_clusters = len(np.unique(np.asarray(labels)))
        cluster_results[key] = {
            "n_clusters": n_clusters,
            "labels_hash": sha256_of_array(np.asarray(labels, dtype=str)),
        }
        print(f"    {key}: {n_clusters} clusters")

    # 8. UMAP
    time_step(
        "umap",
        lambda: rsc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory, device_index,
    )

    # 9. Differential expression (using leiden_1.0 as the grouping)
    def run_de():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            rsc.tl.rank_genes_groups(
                adata,
                groupby="leiden_1.0",
                method="wilcoxon",
                use_raw=True,
            )

    time_step("de_testing", run_de, timings, memory, device_index)

    # Transfer back to CPU for saving results
    print("\n  Transferring data back to CPU...")
    rsc.get.anndata_to_CPU(adata)

    # Calculate total time
    timings["total"] = round(sum(timings.values()), 4)

    # Peak RAM and VRAM
    peak_ram = max(v for k, v in memory.items() if k.endswith("_ram_after_gb"))
    peak_vram = max(v for k, v in memory.items() if k.endswith("_vram_after_gb"))

    print(
        f"\n  {'TOTAL':25s} | {timings['total']:8.2f}s | "
        f"Peak RAM: {peak_ram:.1f} GB | Peak VRAM: {peak_vram:.1f} GB"
    )

    # Get GPU info
    gpu_info = get_gpu_info(device_index)

    # Build output dict
    result = {
        "metadata": {
            "pipeline": "gpu_rapids",
            "n_cells_input": int(adata_path.stem.split("_")[-1]),
            "n_cpus": os.cpu_count(),
            "n_gpus": 1,
            "gpu_device_index": device_index,
            "random_seed": RANDOM_SEED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "software_versions": {
                "scanpy": pkg_version("scanpy"),
                "rapids_singlecell": pkg_version("rapids_singlecell"),
                "cupy": cp.__version__,
                "rmm": pkg_version("rmm"),
                "python": f"{os.sys.version}",
                "numpy": np.__version__,
            },
            "configuration": {
                "rmm_pool": rmm_config,
                "gpu_warmup": True,
                "leiden_backend": "cugraph",
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
            **{f"n_clusters_{res}": cluster_results[f"leiden_{res}"]["n_clusters"]
               for res in LEIDEN_RESOLUTIONS},
            **{f"cluster_labels_hash_{res}": cluster_results[f"leiden_{res}"]["labels_hash"]
               for res in LEIDEN_RESOLUTIONS},
        },
    }

    return result, adata, hvg_list


def save_results(
    result: dict,
    adata: sc.AnnData,
    hvg_list: list,
    output_dir: Path,
    repeat_id: int,
) -> None:
    """Save benchmark results to JSON and supplementary CSVs.

    Args:
        result: Benchmark result dict.
        adata: AnnData object after pipeline (on CPU).
        hvg_list: List of highly variable gene names.
        output_dir: Directory to save results.
        repeat_id: Repeat number for this run.
    """
    n_cells = result["metadata"]["n_cells_input"]
    prefix = f"gpu_{n_cells}_r{repeat_id}"

    # JSON results
    json_path = output_dir / f"{prefix}_results.json"
    result["metadata"]["repeat_id"] = repeat_id
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {json_path}")

    import pandas as pd

    # Cluster labels CSV
    cluster_df = pd.DataFrame(index=adata.obs_names)
    for res in LEIDEN_RESOLUTIONS:
        cluster_df[f"leiden_{res}"] = adata.obs[f"leiden_{res}"].values
    cluster_path = output_dir / f"{prefix}_clusters.csv"
    cluster_df.to_csv(cluster_path)
    print(f"  Clusters saved: {cluster_path}")

    # HVG list CSV
    hvg_path = output_dir / f"{prefix}_hvgs.csv"
    pd.DataFrame({"gene": hvg_list}).to_csv(hvg_path, index=False)
    print(f"  HVGs saved: {hvg_path}")

    # DE results CSV
    de_df = sc.get.rank_genes_groups_df(adata, group=None)
    de_path = output_dir / f"{prefix}_de.csv"
    de_df.to_csv(de_path, index=False)
    print(f"  DE results saved: {de_path}")

    # UMAP coordinates CSV
    umap_data = adata.obsm["X_umap"]
    # Convert from cupy if needed
    if hasattr(umap_data, "get"):
        umap_data = umap_data.get()
    umap_df = pd.DataFrame(
        umap_data,
        columns=["UMAP1", "UMAP2"],
        index=adata.obs_names,
    )
    umap_path = output_dir / f"{prefix}_umap.csv"
    umap_df.to_csv(umap_path)
    print(f"  UMAP saved: {umap_path}")

    # PCA loadings CSV (first 10 components)
    pca_data = adata.varm["PCs"][:, :10]
    if hasattr(pca_data, "get"):
        pca_data = pca_data.get()
    pca_loadings = pd.DataFrame(
        pca_data,
        index=adata.var_names,
        columns=[f"PC{i+1}" for i in range(10)],
    )
    pca_path = output_dir / f"{prefix}_pca_loadings.csv"
    pca_loadings.to_csv(pca_path)
    print(f"  PCA loadings saved: {pca_path}")

    # kNN indices (from the neighbor graph distances matrix)
    from scipy.sparse import issparse

    dist_matrix = adata.obsp["distances"]
    if issparse(dist_matrix):
        n_cells_graph = dist_matrix.shape[0]
        knn_indices = []
        for i in range(n_cells_graph):
            row = dist_matrix.getrow(i)
            neighbors_idx = sorted(row.indices)
            knn_indices.append(neighbors_idx)
        knn_path = output_dir / f"{prefix}_knn.npz"
        np.savez_compressed(knn_path, *[np.array(row) for row in knn_indices])
        print(f"  kNN indices saved: {knn_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run rapids-singlecell GPU benchmark pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/benchmark_gpu.py --data-dir data/ --output-dir results/ --n-cells 10000
  python scripts/benchmark_gpu.py --data-dir data/ --output-dir results/ --n-cells 10000 --n-repeats 5
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing h5ad data files",
    )
    parser.add_argument(
        "--output-dir", type=str, required=True,
        help="Directory to save benchmark results",
    )
    parser.add_argument(
        "--n-cells", type=int, default=10000,
        help="Number of cells to benchmark (must match a file in data-dir)",
    )
    parser.add_argument(
        "--n-repeats", type=int, default=1,
        help="Number of repeat runs (default: 1)",
    )
    parser.add_argument(
        "--gpu-id", type=int, default=0,
        help="GPU device index to use (default: 0)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find input file
    input_file = data_dir / f"brain_{args.n_cells}.h5ad"
    if not input_file.exists():
        print(f"ERROR: File not found: {input_file}")
        print(f"Available files: {list(data_dir.glob('*.h5ad'))}")
        raise SystemExit(1)

    # Initialize NVML for GPU monitoring
    init_nvml()

    # Print GPU info
    gpu_info = get_gpu_info(args.gpu_id)
    print(f"\nGPU: {gpu_info['gpu_name']} ({gpu_info['gpu_vram_total_gb']} GB)")
    print(f"Driver: {gpu_info['driver_version']}")

    # Set scanpy verbosity
    sc.settings.verbosity = 0

    # Set CUDA device
    cp.cuda.Device(args.gpu_id).use()

    for repeat in range(1, args.n_repeats + 1):
        print(f"\n{'#' * 70}")
        print(f"# REPEAT {repeat}/{args.n_repeats}")
        print(f"{'#' * 70}")

        result, adata, hvg_list = run_pipeline(input_file, args.gpu_id)
        save_results(result, adata, hvg_list, output_dir, repeat)

        # Free memory between repeats
        del adata, hvg_list
        gc.collect()
        cp.get_default_memory_pool().free_all_blocks()

    shutdown_nvml()
    print(f"\nAll {args.n_repeats} repeat(s) completed!")


if __name__ == "__main__":
    main()
