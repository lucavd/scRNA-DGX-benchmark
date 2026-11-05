#!/usr/bin/env python3
"""GPU spatial benchmark: rapids-singlecell spatial analysis pipeline with timing.

Runs a spatial transcriptomics analysis pipeline using rapids-singlecell (GPU)
for expression analysis and GPU-accelerated spatial operations, with Squidpy
as fallback for steps without GPU support.

GPU-accelerated spatial steps:
- spatial_autocorr (Moran's I, Geary's C) -- rsc.gr.spatial_autocorr
- co_occurrence -- rsc.gr.co_occurrence

CPU-only spatial steps (no GPU equivalent):
- spatial_neighbors -- sq.gr.spatial_neighbors
- nhood_enrichment -- sq.gr.nhood_enrichment

Supports two platforms:
- Visium v1 (~3,000 spots, 55 um resolution)
- Visium HD (~300k-500k bins, 8 um resolution)

Usage:
    python SPATIAL/scripts/benchmark_spatial_gpu.py \\
        --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium
    python SPATIAL/scripts/benchmark_spatial_gpu.py --help
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
import pandas as pd
import psutil
import pynvml
import rmm
import scanpy as sc
import squidpy as sq

import rapids_singlecell as rsc

import spatial_run_meta as srm

# Thread/host recorder for the current repetition (set in run_pipeline)
_REC: srm.StepRecorder | None = None


# Fixed random seed
RANDOM_SEED = 42

# Leiden resolution for spatial domain detection
LEIDEN_RESOLUTION = 1.0

# Number of top HVGs
N_TOP_HVGS = 2000


# -- GPU monitoring helpers ---------------------------------------------------

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
        name: Name of the step.
        func: Callable to execute.
        timings: Dict to store wall-clock time (seconds).
        memory: Dict to store RAM/VRAM snapshots.
        device_index: GPU device index for VRAM monitoring.

    Returns:
        Whatever func() returns.
    """
    if _REC is not None:
        _REC.before(name)
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()

    ram_before = get_peak_ram_gb()
    vram_before = get_vram_used_gb(device_index)

    cp.cuda.Stream.null.synchronize()
    start = time.perf_counter()

    result = func()

    cp.cuda.Stream.null.synchronize()
    elapsed = time.perf_counter() - start

    ram_after = get_peak_ram_gb()
    vram_after = get_vram_used_gb(device_index)
    if _REC is not None:
        _REC.after(name)

    timings[name] = round(elapsed, 4)
    memory[f"{name}_ram_before_gb"] = round(ram_before, 2)
    memory[f"{name}_ram_after_gb"] = round(ram_after, 2)
    memory[f"{name}_vram_before_gb"] = round(vram_before, 2)
    memory[f"{name}_vram_after_gb"] = round(vram_after, 2)

    print(
        f"  {name:30s} | {elapsed:8.2f}s | "
        f"RAM: {ram_before:.1f}->{ram_after:.1f} GB | "
        f"VRAM: {vram_before:.1f}->{vram_after:.1f} GB"
    )

    return result


def get_gpu_info(device_index: int = 0) -> dict:
    """Get GPU device information."""
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

    Args:
        device_index: GPU device index.

    Returns:
        Dict with pool configuration details.
    """
    handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
    total_vram = pynvml.nvmlDeviceGetMemoryInfo(handle).total

    # Use RMM pool allocator: pre-allocates memory so allocations are fast.
    # Default: 50% initial, 100% max.
    rmm.reinitialize(pool_allocator=True)

    pool_config = {
        "pool_allocator": True,
        "total_vram_gb": round(total_vram / (1024**3), 1),
    }
    print(f"  RMM pool initialized: {pool_config['total_vram_gb']} GB total VRAM")
    return pool_config


def gpu_warmup() -> None:
    """Run a small dummy operation to warm up the CUDA context."""
    print("  GPU warmup (CUDA context + JIT)...", end=" ", flush=True)
    a = cp.ones((100, 100), dtype=cp.float32)
    _ = cp.dot(a, a)
    cp.cuda.Stream.null.synchronize()
    del a, _
    cp.get_default_memory_pool().free_all_blocks()
    print("done")


# -- Data loading -------------------------------------------------------------

def load_visium(data_dir: Path) -> sc.AnnData:
    """Load a standard Visium dataset."""
    visium_dir = data_dir / "visium"
    adata = sq.read.visium(visium_dir)
    adata.var_names_make_unique()
    return adata


def load_visium_hd(data_dir: Path, bin_size: str = "square_008um") -> sc.AnnData:
    """Load a Visium HD dataset at a specific bin size.

    Reads the filtered feature-barcode matrix (h5) and spatial coordinates
    (parquet) directly from the Space Ranger output structure.
    """
    bin_dir = data_dir / "visium_hd" / "binned_outputs" / bin_size

    # Load count matrix
    h5_path = bin_dir / "filtered_feature_bc_matrix.h5"
    if h5_path.exists():
        adata = sc.read_10x_h5(h5_path)
    else:
        mex_dir = bin_dir / "filtered_feature_bc_matrix"
        adata = sc.read_10x_mtx(mex_dir)

    adata.var_names_make_unique()

    # Load spatial coordinates from parquet
    parquet_path = bin_dir / "spatial" / "tissue_positions.parquet"
    if parquet_path.exists():
        positions = pd.read_parquet(parquet_path)
        positions = positions.set_index("barcode")
        common = adata.obs_names.intersection(positions.index)
        adata = adata[common].copy()
        positions = positions.loc[common]
        adata.obsm["spatial"] = positions[
            ["pxl_col_in_fullres", "pxl_row_in_fullres"]
        ].values.astype(np.float64)
    else:
        csv_path = bin_dir / "spatial" / "tissue_positions.csv"
        if csv_path.exists():
            positions = pd.read_csv(csv_path, header=None)
            positions.columns = [
                "barcode", "in_tissue", "array_row", "array_col",
                "pxl_row_in_fullres", "pxl_col_in_fullres",
            ]
            positions = positions.set_index("barcode")
            common = adata.obs_names.intersection(positions.index)
            adata = adata[common].copy()
            positions = positions.loc[common]
            adata.obsm["spatial"] = positions[
                ["pxl_col_in_fullres", "pxl_row_in_fullres"]
            ].values.astype(np.float64)
        else:
            raise FileNotFoundError(
                f"No spatial coordinates found at {bin_dir}/spatial/"
            )

    print(f"    Bin size: {bin_size} ({adata.n_obs:,} bins)")
    return adata


# -- Main pipeline ------------------------------------------------------------

def run_pipeline(
    data_dir: Path,
    platform: str,
    device_index: int = 0,
    bin_size: str = "square_008um",
    max_spots: int | None = None,
    labels_from: str | None = None,
) -> tuple[dict, sc.AnnData]:
    """Run the GPU spatial pipeline with timing.

    Phase A: Expression analysis on GPU (rapids-singlecell)
    Phase B: Spatial analysis -- GPU where available, CPU fallback otherwise

    Args:
        data_dir: Base data directory.
        platform: "visium" or "visium_hd".
        device_index: GPU device index.
        bin_size: Bin size for Visium HD.
        max_spots: If set, subsample to this many spots after loading.

    Returns:
        Tuple of (result dict, processed AnnData on CPU).
    """
    global _REC
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}
    _REC = srm.StepRecorder()
    host_start = srm.host_snapshot()
    threads_start = srm.thread_snapshot()

    label = f"{platform}" if platform == "visium" else f"{platform} ({bin_size})"
    print(f"\n{'=' * 80}")
    print(f"SPATIAL GPU BENCHMARK -- {label} -- GPU {device_index}")
    print(f"{'=' * 80}")

    # Initialize RMM + warmup
    rmm_config = init_rmm_pool(device_index)
    gpu_info = get_gpu_info(device_index)
    gpu_warmup()

    print(
        f"  {'Step':30s} | {'Time':>8s} | "
        f"{'RAM':>20s} | {'VRAM':>20s}"
    )
    print(f"  {'-'*30}-+-{'-'*8}-+-{'-'*20}-+-{'-'*20}")

    # -- Phase A: Expression analysis on GPU ----------------------------------

    # 1. Data loading (CPU read -> GPU transfer)
    if platform == "visium":
        load_fn = lambda: load_visium(data_dir)
    elif platform == "visium_hd":
        load_fn = lambda: load_visium_hd(data_dir, bin_size=bin_size)
    else:
        raise ValueError(f"Unknown platform: {platform}")

    def load_and_transfer():
        adata = load_fn()
        rsc.get.anndata_to_GPU(adata)
        return adata

    adata = time_step(
        "data_loading", load_and_transfer, timings, memory, device_index,
    )

    n_spots_input = adata.n_obs
    n_genes_input = adata.n_vars
    print(f"    Loaded: {n_spots_input:,} spots x {n_genes_input:,} genes")

    # Optional subsampling (preserves spatial coordinates)
    if max_spots is not None and adata.n_obs > max_spots:
        rsc.get.anndata_to_CPU(adata)
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(adata.n_obs, size=max_spots, replace=False)
        adata = adata[sorted(idx)].copy()
        rsc.get.anndata_to_GPU(adata)
        print(f"    Subsampled: {adata.n_obs:,} spots (from {n_spots_input:,})")

    # 2. QC & filtering
    def qc_filter():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
            rsc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False)
            adata.obs = adata.obs.copy()
            adata.var = adata.var.copy()
            min_genes = 1 if platform == "visium_hd" else 200
            rsc.pp.filter_cells(adata, min_genes=min_genes)
            rsc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory, device_index)
    n_spots_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_spots_after_qc:,} spots x {n_genes_after_qc:,} genes")

    # 3. Normalization
    def normalize():
        rsc.pp.normalize_total(adata, target_sum=1e4)
        rsc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory, device_index)

    # 4. HVG selection
    def hvg_selection():
        n_hvg = min(N_TOP_HVGS, adata.n_vars)
        rsc.pp.highly_variable_genes(adata, n_top_genes=n_hvg)

    time_step("hvg_selection", hvg_selection, timings, memory, device_index)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    # Store raw and subset to HVGs
    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()

    # 5. Scale + PCA
    def run_pca():
        rsc.pp.scale(adata, max_value=10)
        rsc.pp.pca(adata, n_comps=50, random_state=RANDOM_SEED)

    time_step("pca", run_pca, timings, memory, device_index)

    # 6-8. Expression graph + clustering + embedding
    n_after_qc = adata.n_obs
    if n_after_qc > 100_000:
        leiden_res = 0.1
    else:
        leiden_res = LEIDEN_RESOLUTION

    time_step(
        "expression_neighbors",
        lambda: rsc.pp.neighbors(
            adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED,
        ),
        timings, memory, device_index,
    )

    time_step(
        "leiden",
        lambda: rsc.tl.leiden(
            adata, resolution=leiden_res, random_state=RANDOM_SEED,
            key_added="leiden_1.0",
        ),
        timings, memory, device_index,
    )

    time_step(
        "umap",
        lambda: rsc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory, device_index,
    )

    labels = adata.obs["leiden_1.0"].values
    if hasattr(labels, "get"):
        labels = labels.get()
    n_clusters = len(np.unique(np.asarray(labels)))
    print(f"    Leiden clusters: {n_clusters} (resolution={leiden_res})")

    # Groups for co-occurrence, nhood enrichment and ligrec (not timed).
    # With --labels-from, CPU and GPU use the same groups read from file;
    # Leiden above is still run and timed as before.
    if labels_from is not None:
        groups, groups_info = srm.load_groups(labels_from, adata.obs_names)
        adata.obs["spatial_groups"] = groups
        group_key = "spatial_groups"
    else:
        group_key = "leiden_1.0"
        groups_info = {"labels_file": None, "n_groups_used": n_clusters}
    n_groups = int(groups_info["n_groups_used"])
    groups_info["group_key"] = group_key
    print(f"    Groups for spatial steps: {n_groups} (key={group_key})")

    # -- Phase B: Spatial-specific analysis -----------------------------------

    print(f"\n  {'--- SPATIAL STEPS ---':^70}")

    # Transfer back to CPU for spatial operations that need it
    rsc.get.anndata_to_CPU(adata)

    # 9. Spatial neighbors (CPU only -- no GPU equivalent in rsc)
    time_step(
        "spatial_neighbors",
        lambda: sq.gr.spatial_neighbors(adata, coord_type="generic", delaunay=True),
        timings, memory, device_index,
    )

    # Transfer back to GPU for GPU spatial operations
    rsc.get.anndata_to_GPU(adata)

    # Warmup for spatial_autocorr: the first call includes JIT compilation
    # overhead for GPU spatial kernels.
    print("  spatial_autocorr warmup (JIT)...", end=" ", flush=True)
    import scipy.sparse as sp
    _warmup_adata = adata[:10, :5].copy()
    _n = _warmup_adata.n_obs
    _warmup_adata.obsp["spatial_connectivities"] = sp.eye(_n, format="csr")
    _warmup_adata.obsp["spatial_distances"] = sp.eye(_n, format="csr")
    try:
        rsc.gr.spatial_autocorr(_warmup_adata, mode="moran")
    except Exception:
        pass  # warmup failure is non-critical
    del _warmup_adata
    cp.cuda.Stream.null.synchronize()
    print("done")

    # 10. Spatial autocorrelation -- Moran's I (GPU)
    time_step(
        "spatial_autocorr_moran",
        lambda: rsc.gr.spatial_autocorr(adata, mode="moran"),
        timings, memory, device_index,
    )

    moranI = adata.uns.get("moranI", pd.DataFrame())
    n_svgs_moran = int((moranI["pval_norm_fdr_bh"] < 0.05).sum()) if len(moranI) > 0 else 0
    print(f"    SVGs (Moran's I, FDR < 0.05): {n_svgs_moran}")

    # 11. Spatial autocorrelation -- Geary's C (GPU)
    time_step(
        "spatial_autocorr_geary",
        lambda: rsc.gr.spatial_autocorr(adata, mode="geary"),
        timings, memory, device_index,
    )

    gearyC = adata.uns.get("gearyC", pd.DataFrame())
    n_svgs_geary = int((gearyC["pval_norm_fdr_bh"] < 0.05).sum()) if len(gearyC) > 0 else 0
    print(f"    SVGs (Geary's C, FDR < 0.05): {n_svgs_geary}")

    # 12. Co-occurrence (GPU) -- skip if too many clusters (O(k^2) memory)
    rsc.get.anndata_to_CPU(adata)
    if n_groups <= 500:
        time_step(
            "co_occurrence",
            lambda: rsc.gr.co_occurrence(adata, cluster_key=group_key),
            timings, memory, device_index,
        )
    else:
        print(f"  co_occurrence: SKIPPED -- {n_groups} groups (>500)")
        timings["co_occurrence"] = -1

    # 13. Neighborhood enrichment (CPU only) -- skip if too many clusters
    if n_groups <= 500:
        time_step(
            "nhood_enrichment",
            lambda: sq.gr.nhood_enrichment(adata, cluster_key=group_key),
            timings, memory, device_index,
        )
    else:
        print(f"  nhood_enrichment: SKIPPED -- {n_groups} groups (>500)")
        timings["nhood_enrichment"] = -1

    # 14. Ligand-receptor interaction (CPU -- Squidpy)
    # Skip at large scale (>100k spots) -- very slow and not informative
    if n_after_qc <= 100_000 and n_groups <= 500:
        try:
            time_step(
                "ligrec",
                lambda: sq.gr.ligrec(
                    adata,
                    cluster_key=group_key,
                    use_raw=False,
                    n_perms=100,
                    transmitter_params={"categories": "ligand"},
                    receiver_params={"categories": "receptor"},
                ),
                timings, memory, device_index,
            )
        except Exception as e:
            print(f"  ligrec: SKIPPED -- {e}")
            timings["ligrec"] = -1
    else:
        print(f"  ligrec: SKIPPED -- large scale ({n_after_qc:,} spots)")
        timings["ligrec"] = -1

    # -- Transfer to CPU for output -------------------------------------------

    rsc.get.anndata_to_CPU(adata)

    # -- Summary --------------------------------------------------------------

    timings["total"] = round(
        sum(v for v in timings.values() if v > 0), 4
    )

    peak_ram = max(
        v for k, v in memory.items() if k.endswith("_ram_after_gb")
    )
    peak_vram = max(
        v for k, v in memory.items() if k.endswith("_vram_after_gb")
    )

    print(
        f"\n  {'TOTAL':30s} | {timings['total']:8.2f}s | "
        f"Peak RAM: {peak_ram:.1f} GB | Peak VRAM: {peak_vram:.1f} GB"
    )

    result = {
        "metadata": {
            "pipeline": "spatial_gpu_rsc",
            "platform": platform,
            "bin_size": bin_size if platform == "visium_hd" else None,
            "n_spots_input": n_spots_input,
            "n_genes_input": n_genes_input,
            "n_cpus": os.cpu_count() or 1,
            "n_gpus": 1,
            "random_seed": RANDOM_SEED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gpu_info": gpu_info,
            "rmm_config": rmm_config,
            "software_versions": {
                "scanpy": pkg_version("scanpy"),
                "squidpy": pkg_version("squidpy"),
                "rapids_singlecell": pkg_version("rapids-singlecell"),
                "cupy": cp.__version__,
                "python": sys.version,
                "numpy": np.__version__,
                "numba": pkg_version("numba"),
                "threadpoolctl": pkg_version("threadpoolctl"),
            },
            "system": srm.system_info(None),
            "threads_at_start": threads_start,
            "host_start": host_start,
            "host_end": srm.host_snapshot(),
            "steps_runtime": _REC.steps,
            "groups": groups_info,
            "spatial_gpu_coverage": {
                "expression_steps": "gpu (rsc)",
                "spatial_neighbors": "cpu_only (squidpy)",
                "spatial_autocorr": "gpu (rsc.gr.spatial_autocorr)",
                "co_occurrence": "gpu (rsc.gr.co_occurrence)",
                "nhood_enrichment": "cpu_only (squidpy)",
                "ligrec": "cpu_only (squidpy)",
            },
        },
        "timings": timings,
        "memory": {
            "peak_ram_gb": round(peak_ram, 2),
            "peak_vram_gb": round(peak_vram, 2),
            "detailed": memory,
        },
        "results_summary": {
            "n_spots_after_qc": n_spots_after_qc,
            "n_genes_after_qc": n_genes_after_qc,
            "n_hvgs": n_hvgs,
            "hvg_list_hash": hvg_hash,
            "n_clusters": n_clusters,
            "n_groups_spatial_steps": n_groups,
            "n_svgs_moran_fdr005": n_svgs_moran,
            "n_svgs_geary_fdr005": n_svgs_geary,
        },
    }

    return result, adata


def save_results(
    result: dict,
    adata: sc.AnnData,
    output_dir: Path,
    repeat_id: int,
) -> None:
    """Save benchmark results to JSON and supplementary CSVs."""
    platform = result["metadata"]["platform"]
    bin_size = result["metadata"].get("bin_size")
    if bin_size:
        prefix = f"spatial_gpu_{platform}_{bin_size}_r{repeat_id}"
    else:
        prefix = f"spatial_gpu_{platform}_r{repeat_id}"

    # JSON results
    json_path = output_dir / f"{prefix}_results.json"
    result["metadata"]["repeat_id"] = repeat_id
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {json_path}")

    # Moran's I results CSV
    moranI = adata.uns.get("moranI", pd.DataFrame())
    if len(moranI) > 0:
        moran_path = output_dir / f"{prefix}_moranI.csv"
        moranI.to_csv(moran_path)
        print(f"  Moran's I saved: {moran_path}")

    # Geary's C results CSV
    gearyC = adata.uns.get("gearyC", pd.DataFrame())
    if len(gearyC) > 0:
        geary_path = output_dir / f"{prefix}_gearyC.csv"
        gearyC.to_csv(geary_path)
        print(f"  Geary's C saved: {geary_path}")

    # Cluster labels CSV
    cluster_path = output_dir / f"{prefix}_clusters.csv"
    adata.obs[["leiden_1.0"]].to_csv(cluster_path)
    print(f"  Clusters saved: {cluster_path}")

    group_key = result["metadata"].get("groups", {}).get("group_key", "leiden_1.0")

    # Groups used by the spatial steps are the labels file restricted to
    # these observations; its md5 is in result["metadata"]["groups"].

    # Co-occurrence results
    if f"{group_key}_co_occurrence" in adata.uns:
        co_occ = adata.uns[f"{group_key}_co_occurrence"]
        if isinstance(co_occ, dict) and "occ" in co_occ:
            co_occ_path = output_dir / f"{prefix}_co_occurrence.npy"
            np.save(co_occ_path, co_occ["occ"])
            print(f"  Co-occurrence saved: {co_occ_path}")

    # Neighborhood enrichment results
    if f"{group_key}_nhood_enrichment" in adata.uns:
        nhood = adata.uns[f"{group_key}_nhood_enrichment"]
        if isinstance(nhood, dict) and "zscore" in nhood:
            nhood_path = output_dir / f"{prefix}_nhood_enrichment.npy"
            np.save(nhood_path, nhood["zscore"])
            print(f"  Nhood enrichment saved: {nhood_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run GPU spatial benchmark pipeline (rapids-singlecell + Squidpy).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python SPATIAL/scripts/benchmark_spatial_gpu.py \\
      --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium
  python SPATIAL/scripts/benchmark_spatial_gpu.py \\
      --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium_hd
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing spatial datasets",
    )
    parser.add_argument(
        "--output-dir", type=str, required=True,
        help="Directory to save benchmark results",
    )
    parser.add_argument(
        "--platform", type=str, required=True,
        choices=["visium", "visium_hd"],
        help="Spatial platform to benchmark",
    )
    parser.add_argument(
        "--bin-size", type=str, default="square_008um",
        choices=["square_002um", "square_008um", "square_016um"],
        help="Bin size for Visium HD (default: square_008um)",
    )
    parser.add_argument(
        "--max-spots", type=int, default=None,
        help="Subsample to this many spots after loading (default: no subsampling)",
    )
    parser.add_argument(
        "--n-repeats", type=int, default=1,
        help="Number of repeat runs (default: 1)",
    )
    parser.add_argument(
        "--repeat-id", type=int, default=None,
        help="Run exactly one repetition with this id (one process per repetition)",
    )
    parser.add_argument(
        "--labels-from", type=str, default=None,
        help="CSV (barcode index, one label column) with the groups used by "
             "co-occurrence, nhood enrichment and ligrec",
    )
    parser.add_argument(
        "--device", type=int, default=0,
        help="GPU device index (default: 0)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify data exists
    if args.platform == "visium":
        check_path = data_dir / "visium" / "filtered_feature_bc_matrix.h5"
    elif args.platform == "visium_hd":
        check_path = data_dir / "visium_hd" / "binned_outputs" / args.bin_size
    else:
        raise ValueError(f"Unknown platform: {args.platform}")

    if not check_path.exists():
        print(f"ERROR: Data not found: {check_path}")
        print("Run download_spatial_data.py first.")
        raise SystemExit(1)

    # Suppress scanpy verbosity
    sc.settings.verbosity = 0

    # Initialize NVML
    init_nvml()

    if args.repeat_id is not None:
        repeats = [args.repeat_id]
    else:
        repeats = list(range(1, args.n_repeats + 1))

    try:
        for repeat in repeats:
            print(f"\n{'#' * 70}")
            print(f"# REPEAT {repeat} (process-local index {repeats.index(repeat) + 1}/{len(repeats)})")
            print(f"{'#' * 70}")

            result, adata = run_pipeline(
                data_dir, args.platform, args.device,
                bin_size=args.bin_size, max_spots=args.max_spots,
                labels_from=args.labels_from,
            )
            result["metadata"]["repeats_in_this_process"] = len(repeats)
            save_results(result, adata, output_dir, repeat)

            del adata
            gc.collect()
            cp.get_default_memory_pool().free_all_blocks()
    finally:
        shutdown_nvml()

    print(f"\nAll {len(repeats)} repeat(s) completed!")


if __name__ == "__main__":
    main()
