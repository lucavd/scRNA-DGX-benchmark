#!/usr/bin/env python3
"""Multi-GPU benchmark: rapids-singlecell pipeline with Dask-CUDA scaling.

Runs the single-cell pipeline across multiple GPUs using dask_cuda.
Not all steps benefit from multi-GPU — the script honestly measures which
steps scale and which run on a single GPU.

Multi-GPU steps (via dask-cuml): PCA, neighbors
Single-GPU steps: QC, normalization, HVG, scale, leiden, UMAP, DE

Usage:
    python scripts/benchmark_multigpu.py --data-dir data/ --output-dir results/ --n-cells 500000 --n-gpus 2
    python scripts/benchmark_multigpu.py --help
"""

import argparse
import gc
import hashlib
import json
import os
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
    """Compute a SHA256 hash of a numpy array for reproducibility checks."""
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def time_step(
    name: str,
    func: callable,
    timings: dict,
    memory: dict,
    n_gpus: int,
) -> Any:
    """Time a pipeline step and record RAM + VRAM usage across all GPUs.

    Args:
        name: Name of the step.
        func: Callable to execute.
        timings: Dict to store wall-clock time.
        memory: Dict to store RAM/VRAM snapshots.
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
        n_gpus: Number of GPUs to use.

    Returns:
        Tuple of (cluster, client).
    """
    from dask_cuda import LocalCUDACluster
    from dask.distributed import Client

    device_list = ",".join(str(i) for i in range(n_gpus))

    cuda_env = os.environ.get("CUDA_VISIBLE_DEVICES", "not set")
    print(f"  CUDA_VISIBLE_DEVICES env: {cuda_env}")
    print(f"  Setting up Dask CUDA cluster with {n_gpus} GPUs ({device_list})...")
    cluster = LocalCUDACluster(
        CUDA_VISIBLE_DEVICES=device_list,
        n_workers=n_gpus,
        rmm_pool_size="10GB",
        rmm_maximum_pool_size="70GB",
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


def run_pipeline(
    adata_path: Path,
    n_gpus: int,
) -> tuple:
    """Run the rapids-singlecell pipeline with multi-GPU support.

    The pipeline uses dask_cuda for steps that support multi-GPU (PCA,
    neighbors) and falls back to single-GPU for other steps.

    IMPORTANT: The Dask cluster is started ONLY for multi-GPU steps (PCA,
    neighbors) to avoid CUDA memory conflicts between Dask workers' RMM
    pools and direct CuPy operations on GPU 0.

    Args:
        adata_path: Path to the input h5ad file.
        n_gpus: Number of GPUs to use.

    Returns:
        Tuple of (result dict, adata on CPU, hvg_list).
    """
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    print(f"\n{'=' * 80}")
    print(f"MULTI-GPU BENCHMARK — {adata_path.name} — {n_gpus} GPUs")
    print(f"{'=' * 80}")

    dask_setup_info = {
        "n_workers": n_gpus,
        "rmm_pool_size": "10GB",
        "rmm_maximum_pool_size": "70GB",
    }

    print(
        f"  {'Step':25s} | {'Time':>8s} | {'RAM':>20s} | {'VRAM (total)':>20s}"
    )
    print(f"  {'-'*25}-+-{'-'*8}-+-{'-'*20}-+-{'-'*20}")

    # === PHASE 1: CPU steps (QC, normalize, HVG) ===
    # The full matrix (e.g. 500k×27k genes) is too large for a single GPU.
    # We do preprocessing on CPU with scanpy, then transfer the small
    # HVG-subset matrix (e.g. 500k×2000) to GPU.

    # 1. Data loading (CPU only)
    def load_data():
        return sc.read_h5ad(adata_path)

    adata = time_step("data_loading", load_data, timings, memory, n_gpus)
    print(f"    Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # 2. QC & filtering (CPU — scanpy)
    def qc_filter():
        adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False, inplace=True)
        sc.pp.filter_cells(adata, min_genes=200)
        sc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory, n_gpus)
    n_cells_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_cells_after_qc:,} cells x {n_genes_after_qc:,} genes")

    # 3. Normalization (CPU — scanpy)
    def normalize():
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory, n_gpus)

    # 4. HVG selection (CPU — scanpy)
    def hvg_selection():
        sc.pp.highly_variable_genes(adata, n_top_genes=2000)

    time_step("hvg_selection", hvg_selection, timings, memory, n_gpus)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    # Subset to HVGs (still on CPU)
    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()
    print(f"    After HVG subset: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # === PHASE 2: Transfer to GPU + GPU steps ===
    # Now the matrix is small (n_cells × 2000), fits easily on GPU.

    # Warm up GPU 0
    gpu_warmup(1)

    # Transfer to GPU (no RMM pool needed — one-shot bulk allocation)
    def transfer_to_gpu():
        rsc.get.anndata_to_GPU(adata)

    time_step("gpu_transfer", transfer_to_gpu, timings, memory, n_gpus)

    # 5. Scale (single GPU)
    def run_scale():
        rsc.pp.scale(adata, max_value=10)

    time_step("scale", run_scale, timings, memory, n_gpus)

    # Free CuPy cache before Dask workers allocate their RMM pools
    cp.get_default_memory_pool().free_all_blocks()
    print(
        "  GPU VRAM after scale: "
        + ", ".join(f"GPU {i}: {get_vram_used_gb(i):.1f} GB" for i in range(n_gpus)),
    )

    # Start Dask cluster for multi-GPU steps
    print(f"\n  Starting Dask CUDA cluster for multi-GPU steps...")
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

        def run_pca():
            rsc.pp.pca(adata, n_comps=50, random_state=RANDOM_SEED)

        time_step("pca", run_pca, timings, memory, n_gpus)

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

    # Re-initialize RMM for remaining single-GPU steps
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()
    rmm.reinitialize(pool_allocator=True, devices=0)

    # 8. Clustering (single GPU — cugraph)
    cluster_results = {}
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

    # 9. UMAP (single GPU)
    time_step(
        "umap",
        lambda: rsc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory, n_gpus,
    )

    # 10. Differential expression
    def run_de():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            rsc.tl.rank_genes_groups(
                adata, groupby="leiden_1.0", method="wilcoxon", use_raw=True,
            )

    time_step("de_testing", run_de, timings, memory, n_gpus)

    # Transfer back to CPU
    print("\n  Transferring data back to CPU...")
    rsc.get.anndata_to_CPU(adata)

    # Calculate total time
    timings["total"] = round(sum(timings.values()), 4)

    # Peak RAM and VRAM
    peak_ram = max(v for k, v in memory.items() if k.endswith("_ram_after_gb"))
    peak_vram = max(v for k, v in memory.items() if k.endswith("_vram_after_gb"))

    print(
        f"\n  {'TOTAL':25s} | {timings['total']:8.2f}s | "
        f"Peak RAM: {peak_ram:.1f} GB | Peak VRAM(total): {peak_vram:.1f} GB"
    )

    # Get GPU info
    gpu_info = get_gpu_info(n_gpus)

    result = {
        "metadata": {
            "pipeline": f"gpu_rapids_{n_gpus}gpu",
            "n_cells_input": int(adata_path.stem.split("_")[-1]),
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
                "leiden_backend": "cugraph",
                "cpu_steps": [
                    "data_loading", "qc_filtering", "normalization",
                    "hvg_selection",
                ],
                "multi_gpu_steps": ["pca", "neighbors"],
                "single_gpu_steps": [
                    "gpu_transfer", "scale", "leiden", "umap", "de_testing",
                ],
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
    """Save benchmark results to JSON and supplementary CSVs."""
    n_cells = result["metadata"]["n_cells_input"]
    n_gpus = result["metadata"]["n_gpus"]
    prefix = f"gpu{n_gpus}_{n_cells}_r{repeat_id}"

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
    if hasattr(umap_data, "get"):
        umap_data = umap_data.get()
    umap_df = pd.DataFrame(
        umap_data, columns=["UMAP1", "UMAP2"], index=adata.obs_names,
    )
    umap_path = output_dir / f"{prefix}_umap.csv"
    umap_df.to_csv(umap_path)
    print(f"  UMAP saved: {umap_path}")

    # PCA loadings CSV (first 10 components)
    pca_data = adata.varm["PCs"][:, :10]
    if hasattr(pca_data, "get"):
        pca_data = pca_data.get()
    pca_loadings = pd.DataFrame(
        pca_data, index=adata.var_names,
        columns=[f"PC{i+1}" for i in range(10)],
    )
    pca_path = output_dir / f"{prefix}_pca_loadings.csv"
    pca_loadings.to_csv(pca_path)
    print(f"  PCA loadings saved: {pca_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run multi-GPU rapids-singlecell benchmark pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/benchmark_multigpu.py --data-dir data/ --output-dir results/ --n-cells 500000 --n-gpus 2
  python scripts/benchmark_multigpu.py --data-dir data/ --output-dir results/ --n-cells 1300000 --n-gpus 8 --n-repeats 5
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
        "--n-cells", type=int, required=True,
        help="Number of cells to benchmark (must match a file in data-dir)",
    )
    parser.add_argument(
        "--n-gpus", type=int, required=True,
        help="Number of GPUs to use (2, 4, or 8)",
    )
    parser.add_argument(
        "--n-repeats", type=int, default=1,
        help="Number of repeat runs (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_file = data_dir / f"brain_{args.n_cells}.h5ad"
    if not input_file.exists():
        print(f"ERROR: File not found: {input_file}")
        print(f"Available files: {list(data_dir.glob('*.h5ad'))}")
        raise SystemExit(1)

    # Initialize NVML
    init_nvml()

    # Print GPU info
    gpu_info = get_gpu_info(args.n_gpus)
    for gpu in gpu_info["gpus"]:
        print(f"  GPU {gpu['device_index']}: {gpu['gpu_name']} ({gpu['gpu_vram_total_gb']} GB)")
    print(f"  Driver: {gpu_info['driver_version']}")

    sc.settings.verbosity = 0

    for repeat in range(1, args.n_repeats + 1):
        print(f"\n{'#' * 70}")
        print(f"# REPEAT {repeat}/{args.n_repeats} — {args.n_gpus} GPUs")
        print(f"{'#' * 70}")

        result, adata, hvg_list = run_pipeline(input_file, args.n_gpus)
        save_results(result, adata, hvg_list, output_dir, repeat)

        del adata, hvg_list
        gc.collect()
        cp.get_default_memory_pool().free_all_blocks()

    shutdown_nvml()
    print(f"\nAll {args.n_repeats} repeat(s) completed!")


if __name__ == "__main__":
    main()
