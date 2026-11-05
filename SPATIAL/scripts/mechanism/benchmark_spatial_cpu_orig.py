#!/usr/bin/env python3
"""CPU spatial benchmark: Squidpy spatial analysis pipeline with timing.

Runs a spatial transcriptomics analysis pipeline using Scanpy (expression)
and Squidpy (spatial operations) on CPU, measuring wall-clock time and
peak RAM for each step.

Supports two platforms:
- Visium v1 (~3,000 spots, 55 µm resolution)
- Visium HD (~300k-500k bins, 8 µm resolution)

Usage:
    python SPATIAL/scripts/benchmark_spatial_cpu.py \\
        --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium
    python SPATIAL/scripts/benchmark_spatial_cpu.py \\
        --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium_hd
    python SPATIAL/scripts/benchmark_spatial_cpu.py --help
"""

import argparse
import os
import sys

# ── Threading configuration ──────────────────────────────────────────────
# MUST be set BEFORE importing numpy/scipy/scanpy.
def _configure_threading(n_cpus: int | None = None) -> int:
    """Set all threading env vars before any numerical library is imported."""
    if n_cpus is None:
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
        "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS",
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
import pandas as pd
import psutil
import scanpy as sc
import squidpy as sq

# Fixed random seed
RANDOM_SEED = 42

# Leiden resolution for spatial domain detection
LEIDEN_RESOLUTION = 1.0

# Number of top HVGs to use for spatial autocorrelation
N_TOP_HVGS = 2000


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

    print(f"  {name:30s} | {elapsed:8.2f}s | RAM: {ram_before:.1f} -> {ram_after:.1f} GB")

    return result


def load_visium(data_dir: Path) -> sc.AnnData:
    """Load a standard Visium dataset.

    Args:
        data_dir: Directory containing the visium/ subdirectory.

    Returns:
        AnnData with spatial coordinates in obsm['spatial'].
    """
    visium_dir = data_dir / "visium"
    adata = sq.read.visium(visium_dir)
    adata.var_names_make_unique()
    return adata


def load_visium_hd(data_dir: Path, bin_size: str = "square_008um") -> sc.AnnData:
    """Load a Visium HD dataset at a specific bin size.

    Reads the filtered feature-barcode matrix (h5) and spatial coordinates
    (parquet) directly from the Space Ranger output structure.

    Args:
        data_dir: Directory containing the visium_hd/ subdirectory.
        bin_size: Bin size to load (e.g., "square_002um", "square_008um").

    Returns:
        AnnData with spatial coordinates in obsm['spatial'].
    """
    bin_dir = data_dir / "visium_hd" / "binned_outputs" / bin_size

    # Load count matrix
    h5_path = bin_dir / "filtered_feature_bc_matrix.h5"
    if h5_path.exists():
        adata = sc.read_10x_h5(h5_path)
    else:
        # Fallback to MEX format
        mex_dir = bin_dir / "filtered_feature_bc_matrix"
        adata = sc.read_10x_mtx(mex_dir)

    adata.var_names_make_unique()

    # Load spatial coordinates from parquet
    parquet_path = bin_dir / "spatial" / "tissue_positions.parquet"
    if parquet_path.exists():
        positions = pd.read_parquet(parquet_path)
        # Filter to barcodes in the filtered matrix
        positions = positions.set_index("barcode")
        common = adata.obs_names.intersection(positions.index)
        adata = adata[common].copy()
        positions = positions.loc[common]
        # pxl_row_in_fullres and pxl_col_in_fullres are the spatial coords
        adata.obsm["spatial"] = positions[
            ["pxl_col_in_fullres", "pxl_row_in_fullres"]
        ].values.astype(np.float64)
    else:
        # Try CSV format (older Space Ranger versions)
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
                f"No spatial coordinates found at {bin_dir}/spatial/. "
                f"Expected tissue_positions.parquet or .csv"
            )

    print(f"    Bin size: {bin_size} ({adata.n_obs:,} bins)")
    return adata


def run_pipeline(
    data_dir: Path,
    platform: str,
    n_cpus: int,
    bin_size: str = "square_008um",
    max_spots: int | None = None,
) -> tuple[dict, sc.AnnData]:
    """Run the full Scanpy + Squidpy CPU pipeline with timing.

    The pipeline has two phases:
    A) Expression analysis (shared with scRNA-seq benchmark)
    B) Spatial-specific analysis (Squidpy)

    Args:
        data_dir: Base data directory.
        platform: "visium" or "visium_hd".
        n_cpus: Number of CPU threads.
        bin_size: Bin size for Visium HD (e.g., "square_002um", "square_008um").
        max_spots: If set, subsample to this many spots after loading.

    Returns:
        Tuple of (result dict, processed AnnData).
    """
    timings: dict[str, float] = {}
    memory: dict[str, float] = {}

    label = f"{platform}" if platform == "visium" else f"{platform} ({bin_size})"
    print(f"\n{'=' * 70}")
    print(f"SPATIAL CPU BENCHMARK — {label} — {n_cpus} threads")
    print(f"{'=' * 70}")
    print(f"  {'Step':30s} | {'Time':>8s} | {'Memory':>20s}")
    print(f"  {'-'*30}-+-{'-'*8}-+-{'-'*20}")

    # ── Phase A: Expression analysis ─────────────────────────────────────

    # 1. Data loading
    if platform == "visium":
        adata = time_step(
            "data_loading",
            lambda: load_visium(data_dir),
            timings, memory,
        )
    elif platform == "visium_hd":
        adata = time_step(
            "data_loading",
            lambda: load_visium_hd(data_dir, bin_size=bin_size),
            timings, memory,
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")

    n_spots_input = adata.n_obs
    n_genes_input = adata.n_vars
    print(f"    Loaded: {n_spots_input:,} spots × {n_genes_input:,} genes")
    print(f"    Spatial coords: {adata.obsm['spatial'].shape}")

    # Optional subsampling (preserves spatial coordinates)
    if max_spots is not None and adata.n_obs > max_spots:
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(adata.n_obs, size=max_spots, replace=False)
        adata = adata[sorted(idx)].copy()
        print(f"    Subsampled: {adata.n_obs:,} spots (from {n_spots_input:,})")

    # 2. QC & filtering
    def qc_filter():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
            # Spatial data: use MT genes for QC (same as scRNA-seq)
            adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
            sc.pp.calculate_qc_metrics(
                adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
            )
            adata.obs = adata.obs.copy()
            adata.var = adata.var.copy()
            # Visium HD 2µm bins have very few genes per bin (median ~9),
            # so min_genes=200 would filter nearly everything.
            # Use min_genes=1 for HD (Space Ranger already filtered on-tissue).
            min_genes = 1 if platform == "visium_hd" else 200
            sc.pp.filter_cells(adata, min_genes=min_genes)
            sc.pp.filter_genes(adata, min_cells=3)

    time_step("qc_filtering", qc_filter, timings, memory)
    n_spots_after_qc = adata.n_obs
    n_genes_after_qc = adata.n_vars
    print(f"    After QC: {n_spots_after_qc:,} spots × {n_genes_after_qc:,} genes")

    # 3. Normalization
    def normalize():
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

    time_step("normalization", normalize, timings, memory)

    # 4. HVG selection
    def hvg_selection():
        n_hvg = min(N_TOP_HVGS, adata.n_vars)
        sc.pp.highly_variable_genes(adata, n_top_genes=n_hvg)

    time_step("hvg_selection", hvg_selection, timings, memory)

    hvg_list = adata.var_names[adata.var["highly_variable"]].tolist()
    n_hvgs = len(hvg_list)
    hvg_hash = sha256_of_array(np.array(hvg_list, dtype=str))
    print(f"    HVGs selected: {n_hvgs}")

    # Store raw counts for DE later
    adata.raw = adata.copy()

    # Subset to HVGs
    adata = adata[:, adata.var["highly_variable"]].copy()

    # 5. Scale + PCA
    def run_pca():
        adata.X = adata.X.toarray() if hasattr(adata.X, "toarray") else adata.X
        sc.pp.scale(adata, max_value=10)
        sc.tl.pca(adata, n_comps=50, random_state=RANDOM_SEED)

    time_step("pca", run_pca, timings, memory)

    # 6. Expression neighbor graph
    time_step(
        "expression_neighbors",
        lambda: sc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED),
        timings, memory,
    )

    # 7. Leiden clustering (expression-based)
    # Adapt resolution: at large scale (>100k), resolution=1.0 produces
    # tens of thousands of clusters, making downstream steps (co_occurrence,
    # nhood_enrichment, ligrec) impossible. Use lower resolution.
    n_after_qc = adata.n_obs
    if n_after_qc > 100_000:
        leiden_res = 0.1
    else:
        leiden_res = LEIDEN_RESOLUTION

    time_step(
        "leiden",
        lambda: sc.tl.leiden(
            adata, resolution=leiden_res, random_state=RANDOM_SEED,
            key_added="leiden_1.0", flavor="igraph", n_iterations=2,
        ),
        timings, memory,
    )

    n_clusters = len(adata.obs["leiden_1.0"].unique())
    print(f"    Leiden clusters: {n_clusters} (resolution={leiden_res})")

    # 8. UMAP
    time_step(
        "umap",
        lambda: sc.tl.umap(adata, random_state=RANDOM_SEED),
        timings, memory,
    )

    # ── Phase B: Spatial-specific analysis ───────────────────────────────

    print(f"\n  {'─── SPATIAL STEPS ───':^60}")

    # 9. Spatial neighbors (coordinate-based graph)
    time_step(
        "spatial_neighbors",
        lambda: sq.gr.spatial_neighbors(adata, coord_type="generic", delaunay=True),
        timings, memory,
    )

    # 10. Spatial autocorrelation — Moran's I
    # Run on HVGs only (already subsetted)
    time_step(
        "spatial_autocorr_moran",
        lambda: sq.gr.spatial_autocorr(adata, mode="moran"),
        timings, memory,
    )

    # Extract SVG results (spatially variable genes)
    moranI = adata.uns.get("moranI", pd.DataFrame())
    n_svgs_moran = int((moranI["pval_norm_fdr_bh"] < 0.05).sum()) if len(moranI) > 0 else 0
    print(f"    SVGs (Moran's I, FDR < 0.05): {n_svgs_moran}")

    # 11. Spatial autocorrelation — Geary's C
    time_step(
        "spatial_autocorr_geary",
        lambda: sq.gr.spatial_autocorr(adata, mode="geary"),
        timings, memory,
    )

    gearyC = adata.uns.get("gearyC", pd.DataFrame())
    n_svgs_geary = int((gearyC["pval_norm_fdr_bh"] < 0.05).sum()) if len(gearyC) > 0 else 0
    print(f"    SVGs (Geary's C, FDR < 0.05): {n_svgs_geary}")

    # 12. Co-occurrence (skip if too many clusters — O(k²) memory)
    if n_clusters <= 500:
        time_step(
            "co_occurrence",
            lambda: sq.gr.co_occurrence(adata, cluster_key="leiden_1.0"),
            timings, memory,
        )
    else:
        print(f"  co_occurrence: SKIPPED — {n_clusters} clusters (>500)")
        timings["co_occurrence"] = -1

    # 13. Neighborhood enrichment (skip if too many clusters — O(k²) memory)
    if n_clusters <= 500:
        time_step(
            "nhood_enrichment",
            lambda: sq.gr.nhood_enrichment(adata, cluster_key="leiden_1.0"),
            timings, memory,
        )
    else:
        print(f"  nhood_enrichment: SKIPPED — {n_clusters} clusters (>500)")
        timings["nhood_enrichment"] = -1

    # 14. Ligand-receptor interaction analysis
    # Skip at large scale (>100k spots) — very slow and not informative
    if n_after_qc <= 100_000 and n_clusters <= 500:
        try:
            time_step(
                "ligrec",
                lambda: sq.gr.ligrec(
                    adata,
                    cluster_key="leiden_1.0",
                    use_raw=False,
                    n_perms=100,  # reduced for speed; 1000 for production
                    transmitter_params={"categories": "ligand"},
                    receiver_params={"categories": "receptor"},
                ),
                timings, memory,
            )
        except Exception as e:
            print(f"  ligrec: SKIPPED — {e}")
            timings["ligrec"] = -1
    else:
        print(f"  ligrec: SKIPPED — large scale ({n_after_qc:,} spots)")
        timings["ligrec"] = -1

    # ── Summary ──────────────────────────────────────────────────────────

    timings["total"] = round(
        sum(v for v in timings.values() if v > 0), 4
    )

    peak_ram = max(
        v for k, v in memory.items() if k.endswith("_ram_after_gb")
    )

    print(f"\n  {'TOTAL':30s} | {timings['total']:8.2f}s | Peak RAM: {peak_ram:.1f} GB")

    # Build result dict
    result = {
        "metadata": {
            "pipeline": "spatial_cpu_squidpy",
            "platform": platform,
            "bin_size": bin_size if platform == "visium_hd" else None,
            "n_spots_input": n_spots_input,
            "n_genes_input": n_genes_input,
            "n_cpus": n_cpus,
            "n_gpus": 0,
            "random_seed": RANDOM_SEED,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "software_versions": {
                "scanpy": pkg_version("scanpy"),
                "squidpy": pkg_version("squidpy"),
                "python": sys.version,
                "numpy": np.__version__,
            },
        },
        "timings": timings,
        "memory": {
            "peak_ram_gb": round(peak_ram, 2),
            "peak_vram_gb": 0.0,
            "detailed": memory,
        },
        "results_summary": {
            "n_spots_after_qc": n_spots_after_qc,
            "n_genes_after_qc": n_genes_after_qc,
            "n_hvgs": n_hvgs,
            "hvg_list_hash": hvg_hash,
            "n_clusters": n_clusters,
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
    """Save benchmark results to JSON and supplementary CSVs.

    Args:
        result: Benchmark result dict.
        adata: AnnData after pipeline.
        output_dir: Directory for results.
        repeat_id: Repeat number.
    """
    platform = result["metadata"]["platform"]
    bin_size = result["metadata"].get("bin_size")
    if bin_size:
        prefix = f"spatial_cpu_{platform}_{bin_size}_r{repeat_id}"
    else:
        prefix = f"spatial_cpu_{platform}_r{repeat_id}"

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

    # Co-occurrence results
    if "leiden_1.0_co_occurrence" in adata.uns:
        co_occ = adata.uns["leiden_1.0_co_occurrence"]
        if isinstance(co_occ, dict) and "occ" in co_occ:
            co_occ_path = output_dir / f"{prefix}_co_occurrence.npy"
            np.save(co_occ_path, co_occ["occ"])
            print(f"  Co-occurrence saved: {co_occ_path}")

    # Neighborhood enrichment results
    if "leiden_1.0_nhood_enrichment" in adata.uns:
        nhood = adata.uns["leiden_1.0_nhood_enrichment"]
        if isinstance(nhood, dict) and "zscore" in nhood:
            nhood_path = output_dir / f"{prefix}_nhood_enrichment.npy"
            np.save(nhood_path, nhood["zscore"])
            print(f"  Nhood enrichment saved: {nhood_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Squidpy CPU spatial benchmark pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python SPATIAL/scripts/benchmark_spatial_cpu.py \\
      --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium
  python SPATIAL/scripts/benchmark_spatial_cpu.py \\
      --data-dir SPATIAL/data --output-dir SPATIAL/results --platform visium_hd
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing spatial datasets (visium/ and visium_hd/ subdirs)",
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

    for repeat in range(1, args.n_repeats + 1):
        print(f"\n{'#' * 70}")
        print(f"# REPEAT {repeat}/{args.n_repeats}")
        print(f"{'#' * 70}")

        result, adata = run_pipeline(
            data_dir, args.platform, args.n_cpus,
            bin_size=args.bin_size, max_spots=args.max_spots,
        )
        save_results(result, adata, output_dir, repeat)

        del adata
        gc.collect()

    print(f"\nAll {args.n_repeats} repeat(s) completed!")


if __name__ == "__main__":
    main()
