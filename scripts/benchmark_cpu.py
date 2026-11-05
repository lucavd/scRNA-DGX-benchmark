#!/usr/bin/env python3
"""CPU benchmark: run the full Scanpy pipeline and measure performance.

Executes a standard single-cell RNA-seq analysis pipeline using Scanpy (CPU)
and records wall-clock time and peak RAM for each step.

Best-of-breed configuration:
- Threading: OMP/MKL/OPENBLAS/NUMBA_NUM_THREADS set BEFORE library imports
  so that NumPy, SciPy, and numba pick up the correct thread count.
- Leiden clustering: uses igraph backend (orders of magnitude faster than
  the default leidenalg). This gives the CPU pipeline its best performance,
  making the CPU-vs-GPU comparison fair ("best of breed" on both sides).

Usage:
    python scripts/benchmark_cpu.py --data-dir data/ --output-dir results/ --n-cells 10000
    python scripts/benchmark_cpu.py --help
"""

import argparse
import os
import sys

# ── Threading configuration ──────────────────────────────────────────────
# CRITICAL: these MUST be set BEFORE importing numpy/scipy/scanpy because
# NumPy (via MKL or OpenBLAS) and numba read them at import time.
# Setting them later has NO effect on already-loaded libraries.
def _configure_threading(n_cpus: int | None = None) -> int:
    """Set all threading env vars before any numerical library is imported.

    Args:
        n_cpus: Number of threads. If None, reads --n-cpus from argv or
                falls back to os.cpu_count().

    Returns:
        The effective thread count.
    """
    if n_cpus is None:
        # Peek at argv for --n-cpus before argparse runs
        for i, arg in enumerate(sys.argv):
            if arg == "--n-cpus" and i + 1 < len(sys.argv):
                n_cpus = int(sys.argv[i + 1])
                break
            if arg.startswith("--n-cpus="):
                n_cpus = int(arg.split("=", 1)[1])
                break
        if n_cpus is None:
            n_cpus = os.cpu_count() or 1

    for var in [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMBA_NUM_THREADS",
    ]:
        os.environ[var] = str(n_cpus)
    return n_cpus


_EFFECTIVE_CPUS = _configure_threading()
# ─────────────────────────────────────────────────────────────────────────

import gc
import hashlib
import json
import time
import warnings
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import scanpy as sc


# Fixed random seed
RANDOM_SEED = 42

# Leiden clustering resolutions
LEIDEN_RESOLUTIONS = [0.5, 1.0, 1.5]


def get_peak_ram_gb() -> float:
    """Get current process RSS memory in GB."""
    return psutil.Process().memory_info().rss / (1024**3)


def sha256_of_array(arr: np.ndarray) -> str:
    """Compute a SHA256 hash of a numpy array for reproducibility checks."""
    return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


def time_step(name: str, func: callable, timings: dict, memory: dict) -> Any:
    """Time a pipeline step and record RAM usage.

    Args:
        name: Name of the step (used as key in timings/memory dicts).
        func: Callable to execute (takes no arguments).
        timings: Dict to store wall-clock time (seconds).
        memory: Dict to store RAM snapshots.

    Returns:
        Whatever func() returns.
    """
    gc.collect()
    ram_before = get_peak_ram_gb()
    start = time.perf_counter()

    result = func()

    elapsed = time.perf_counter() - start
    ram_after = get_peak_ram_gb()

    timings[name] = round(elapsed, 4)
    memory[f"{name}_ram_before_gb"] = round(ram_before, 2)
    memory[f"{name}_ram_after_gb"] = round(ram_after, 2)

    print(f"  {name:25s} | {elapsed:8.2f}s | RAM: {ram_before:.1f} -> {ram_after:.1f} GB")

    return result


def _get_numpy_blas_backend() -> str:
    """Detect the BLAS backend used by NumPy (MKL, OpenBLAS, etc.)."""
    try:
        cfg = np.show_config(mode="dicts")
        return cfg.get("Build Dependencies", {}).get("blas", {}).get("name", "unknown")
    except (TypeError, AttributeError):
        # numpy < 1.24 doesn't support mode="dicts"
        return "unknown (numpy < 1.24)"


def run_pipeline(adata_path: Path, n_cpus: int) -> dict:
    """Run the full Scanpy CPU pipeline with timing.

    Args:
        adata_path: Path to the input h5ad file.
        n_cpus: Number of CPU threads to use.

    Returns:
        Dict with timings, memory, and results summary.
    """
    # Threading is already configured at module level via _configure_threading()
    # (must happen before numpy/scipy import to take effect)

    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    print(f"\n{'=' * 70}")
    print(f"CPU BENCHMARK — {adata_path.name} — {n_cpus} threads")
    print(f"{'=' * 70}")
    print(f"  {'Step':25s} | {'Time':>8s} | {'Memory':>20s}")
    print(f"  {'-'*25}-+-{'-'*8}-+-{'-'*20}")

    # 1. Data loading
    adata = time_step(
        "data_loading",
        lambda: sc.read_h5ad(adata_path),
        timings, memory,
    )
    print(f"    Loaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # 2. QC & filtering
    def qc_filter():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
            sc.pp.calculate_qc_metrics(
                adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
            )
            adata.obs = adata.obs.copy()
            adata.var = adata.var.copy()
            sc.pp.filter_cells(adata, min_genes=200)
            sc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory)
    n_cells_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_cells_after_qc:,} cells x {n_genes_after_qc:,} genes")

    # 3. Normalization
    def normalize():
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory)

    # 4. HVG selection
    def hvg_selection():
        sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat_v3")

    # seurat_v3 needs raw counts — store them first, then normalize
    # Actually, seurat_v3 needs raw counts. We already normalized.
    # Use "seurat" flavor instead which works on log-normalized data.
    def hvg_selection():
        sc.pp.highly_variable_genes(adata, n_top_genes=2000)

    time_step("hvg_selection", hvg_selection, timings, memory)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    # Subset to HVGs for downstream analysis
    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()

    # 5. Scale + PCA
    # scale() densifies the sparse matrix — this is intentional and needed
    # for max_value clipping. On 1.3M cells this uses ~20 GB extra RAM.
    def run_pca():
        adata.X = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
        sc.pp.scale(adata, max_value=10)
        sc.tl.pca(adata, n_comps=50, random_state=RANDOM_SEED)

    time_step("pca", run_pca, timings, memory)

    # 6. Neighbor graph
    time_step(
        "neighbors",
        lambda: sc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED),
        timings, memory,
    )

    # 7. Clustering (multiple resolutions)
    # Best-of-breed: use igraph backend which is orders of magnitude faster
    # than the default leidenalg. This gives the CPU pipeline its optimal
    # performance for a fair comparison against GPU (cugraph).
    cluster_results = {}
    for res in LEIDEN_RESOLUTIONS:
        key = f"leiden_{res}"
        time_step(
            key,
            lambda r=res: sc.tl.leiden(
                adata, resolution=r, random_state=RANDOM_SEED,
                key_added=f"leiden_{r}", flavor="igraph",
                n_iterations=2,  # required by igraph flavor
            ),
            timings, memory,
        )
        labels = adata.obs[f"leiden_{res}"].values
        n_clusters = len(np.unique(labels))
        cluster_results[key] = {
            "n_clusters": n_clusters,
            "labels_hash": sha256_of_array(labels.astype(str)),
        }
        print(f"    {key}: {n_clusters} clusters")

    # 8. UMAP
    time_step(
        "umap",
        lambda: sc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory,
    )

    # 9. Differential expression (using leiden_1.0 as the grouping)
    def run_de():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            sc.tl.rank_genes_groups(
                adata,
                groupby="leiden_1.0",
                method="wilcoxon",
                use_raw=True,
            )

    time_step("de_testing", run_de, timings, memory)

    # Calculate total time
    timings["total"] = round(sum(timings.values()), 4)

    # Peak RAM
    peak_ram = max(
        v for k, v in memory.items() if k.endswith("_ram_after_gb")
    )

    print(f"\n  {'TOTAL':25s} | {timings['total']:8.2f}s | Peak RAM: {peak_ram:.1f} GB")

    # Build output dict
    result = {
        "metadata": {
            "pipeline": "cpu_scanpy",
            "n_cells_input": int(adata_path.stem.split("_")[-1]),
            "n_cpus": n_cpus,
            "n_gpus": 0,
            "random_seed": RANDOM_SEED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "software_versions": {
                "scanpy": pkg_version("scanpy"),
                "python": f"{os.sys.version}",
                "numpy": np.__version__,
                "leidenalg": pkg_version("leidenalg"),
                "igraph": pkg_version("igraph"),
            },
            "configuration": {
                "leiden_backend": "igraph",
                "threading_vars": {
                    "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
                    "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
                    "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
                    "NUMBA_NUM_THREADS": os.environ.get("NUMBA_NUM_THREADS"),
                },
                "numpy_blas_backend": _get_numpy_blas_backend(),
            },
            "input_file": str(adata_path),
        },
        "timings": timings,
        "memory": {
            "peak_ram_gb": round(peak_ram, 2),
            "peak_vram_gb": 0.0,
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
        adata: AnnData object after pipeline.
        hvg_list: List of highly variable gene names.
        output_dir: Directory to save results.
        repeat_id: Repeat number for this run.
    """
    n_cells = result["metadata"]["n_cells_input"]
    prefix = f"cpu_{n_cells}_r{repeat_id}"

    # JSON results
    json_path = output_dir / f"{prefix}_results.json"
    result["metadata"]["repeat_id"] = repeat_id
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {json_path}")

    # Cluster labels CSV
    import pandas as pd

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

    # DE results CSV (top 100 genes per cluster for leiden_1.0)
    de_df = sc.get.rank_genes_groups_df(adata, group=None)
    de_path = output_dir / f"{prefix}_de.csv"
    de_df.to_csv(de_path, index=False)
    print(f"  DE results saved: {de_path}")

    # UMAP coordinates CSV
    umap_df = pd.DataFrame(
        adata.obsm["X_umap"],
        columns=["UMAP1", "UMAP2"],
        index=adata.obs_names,
    )
    umap_path = output_dir / f"{prefix}_umap.csv"
    umap_df.to_csv(umap_path)
    print(f"  UMAP saved: {umap_path}")

    # PCA loadings CSV (first 10 components)
    pca_loadings = pd.DataFrame(
        adata.varm["PCs"][:, :10],
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
        # Extract k-nearest neighbor indices per cell from sparse distance matrix
        n_cells_graph = dist_matrix.shape[0]
        knn_indices = []
        for i in range(n_cells_graph):
            row = dist_matrix.getrow(i)
            neighbors_idx = sorted(row.indices)
            knn_indices.append(neighbors_idx)
        # Save as npz for efficiency
        knn_path = output_dir / f"{prefix}_knn.npz"
        np.savez_compressed(knn_path, *[np.array(row) for row in knn_indices])
        print(f"  kNN indices saved: {knn_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Scanpy CPU benchmark pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/benchmark_cpu.py --data-dir data/ --output-dir results/ --n-cells 10000
  python scripts/benchmark_cpu.py --data-dir data/ --output-dir results/ --n-cells 10000 --n-repeats 5
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
        "--n-cpus", type=int, default=os.cpu_count(),
        help=f"Number of CPU threads (default: {os.cpu_count()})",
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

    # Set scanpy verbosity
    sc.settings.verbosity = 0

    for repeat in range(1, args.n_repeats + 1):
        print(f"\n{'#' * 70}")
        print(f"# REPEAT {repeat}/{args.n_repeats}")
        print(f"{'#' * 70}")

        result, adata, hvg_list = run_pipeline(input_file, args.n_cpus)
        save_results(result, adata, hvg_list, output_dir, repeat)

        # Free memory between repeats
        del adata, hvg_list
        gc.collect()

    print(f"\nAll {args.n_repeats} repeat(s) completed!")


if __name__ == "__main__":
    main()
