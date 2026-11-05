#!/usr/bin/env python3
"""Compare CPU vs GPU spatial benchmark results for concordance analysis.

Computes spatial-specific concordance metrics between CPU (Squidpy) and
GPU (rapids-singlecell) pipeline outputs:
- Moran's I correlation (Spearman, per gene)
- Geary's C correlation (Spearman, per gene)
- SVG overlap (Jaccard of top-N spatially variable genes)
- Co-occurrence matrix correlation
- Cluster ARI/NMI (expression-based Leiden)
- Neighborhood enrichment z-score correlation

Usage:
    python SPATIAL/scripts/compare_spatial_results.py \\
        --results-dir SPATIAL/results --platform visium
    python SPATIAL/scripts/compare_spatial_results.py --help
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


# Optional separate directory for the CPU files (CPU reference on another machine)
CPU_RESULTS_DIR: Path | None = None


def load_pair(
    results_dir: Path, platform: str, repeat: int,
    bin_size: str | None = None,
) -> dict:
    """Load CPU and GPU spatial result files for a given platform and repeat.

    Args:
        results_dir: Directory containing result files.
        platform: "visium" or "visium_hd".
        repeat: Repeat ID.
        bin_size: Bin size for Visium HD (e.g., "square_008um").

    Returns:
        Dict with cpu/gpu sub-dicts containing DataFrames and metadata.
    """
    data = {}
    for pipeline in ["cpu", "gpu"]:
        pdir = CPU_RESULTS_DIR if (pipeline == "cpu" and CPU_RESULTS_DIR is not None) else results_dir
        if platform == "visium_hd" and bin_size:
            prefix = f"spatial_{pipeline}_{platform}_{bin_size}_r{repeat}"
        else:
            prefix = f"spatial_{pipeline}_{platform}_r{repeat}"

        entry = {
            "json": json.loads(
                (pdir / f"{prefix}_results.json").read_text()
            ),
            "clusters": pd.read_csv(
                pdir / f"{prefix}_clusters.csv", index_col=0
            ),
        }

        # Moran's I
        moran_path = pdir / f"{prefix}_moranI.csv"
        if moran_path.exists():
            entry["moranI"] = pd.read_csv(moran_path, index_col=0)
        else:
            entry["moranI"] = None

        # Geary's C
        geary_path = pdir / f"{prefix}_gearyC.csv"
        if geary_path.exists():
            entry["gearyC"] = pd.read_csv(geary_path, index_col=0)
        else:
            entry["gearyC"] = None

        # Co-occurrence
        co_occ_path = pdir / f"{prefix}_co_occurrence.npy"
        if co_occ_path.exists():
            entry["co_occurrence"] = np.load(co_occ_path)
        else:
            entry["co_occurrence"] = None

        # Neighborhood enrichment
        nhood_path = pdir / f"{prefix}_nhood_enrichment.npy"
        if nhood_path.exists():
            entry["nhood_enrichment"] = np.load(nhood_path)
        else:
            entry["nhood_enrichment"] = None

        data[pipeline] = entry

    return data


def compare_autocorr(
    cpu_df: pd.DataFrame | None,
    gpu_df: pd.DataFrame | None,
    mode: str,
) -> dict:
    """Compare spatial autocorrelation results between CPU and GPU.

    Args:
        cpu_df: CPU autocorrelation results (genes × stats).
        gpu_df: GPU autocorrelation results (genes × stats).
        mode: "moran" or "geary".

    Returns:
        Dict with correlation and SVG overlap metrics.
    """
    if cpu_df is None or gpu_df is None:
        return {"status": "missing_data"}

    # Align genes
    common_genes = cpu_df.index.intersection(gpu_df.index)
    if len(common_genes) == 0:
        return {"status": "no_common_genes"}

    cpu_aligned = cpu_df.loc[common_genes]
    gpu_aligned = gpu_df.loc[common_genes]

    # The statistic column name depends on mode
    stat_col = "I" if mode == "moran" else "C"

    result = {
        "n_common_genes": len(common_genes),
    }

    # Spearman correlation of the statistic (Moran's I or Geary's C)
    if stat_col in cpu_aligned.columns and stat_col in gpu_aligned.columns:
        cpu_vals = cpu_aligned[stat_col].values
        gpu_vals = gpu_aligned[stat_col].values

        # Remove NaN/inf
        mask = np.isfinite(cpu_vals) & np.isfinite(gpu_vals)
        if mask.sum() > 2:
            rho, pval = spearmanr(cpu_vals[mask], gpu_vals[mask])
            result[f"{stat_col}_spearman_rho"] = round(float(rho), 6)
            result[f"{stat_col}_spearman_pval"] = float(pval)

            # Pearson correlation too
            pearson = np.corrcoef(cpu_vals[mask], gpu_vals[mask])[0, 1]
            result[f"{stat_col}_pearson_r"] = round(float(pearson), 6)

    # SVG overlap: Jaccard of top-N genes ranked by the statistic
    for top_n in [50, 100, 200]:
        if stat_col in cpu_aligned.columns and stat_col in gpu_aligned.columns:
            if mode == "moran":
                # Higher Moran's I = more spatially autocorrelated
                cpu_top = set(cpu_aligned.nlargest(top_n, stat_col).index)
                gpu_top = set(gpu_aligned.nlargest(top_n, stat_col).index)
            else:
                # Lower Geary's C = more spatially autocorrelated
                cpu_top = set(cpu_aligned.nsmallest(top_n, stat_col).index)
                gpu_top = set(gpu_aligned.nsmallest(top_n, stat_col).index)

            intersection = len(cpu_top & gpu_top)
            union = len(cpu_top | gpu_top)
            jaccard = intersection / union if union > 0 else 0.0
            result[f"svg_jaccard_top{top_n}"] = round(jaccard, 4)

    # Compare significant SVGs (FDR < 0.05)
    fdr_col = "pval_norm_fdr_bh"
    if fdr_col in cpu_aligned.columns and fdr_col in gpu_aligned.columns:
        cpu_sig = set(cpu_aligned[cpu_aligned[fdr_col] < 0.05].index)
        gpu_sig = set(gpu_aligned[gpu_aligned[fdr_col] < 0.05].index)

        if len(cpu_sig | gpu_sig) > 0:
            jaccard_sig = len(cpu_sig & gpu_sig) / len(cpu_sig | gpu_sig)
            result["svg_jaccard_fdr005"] = round(jaccard_sig, 4)
            result["n_svg_cpu"] = len(cpu_sig)
            result["n_svg_gpu"] = len(gpu_sig)
            result["n_svg_shared"] = len(cpu_sig & gpu_sig)

    return result


def compare_clusters(
    cpu_clusters: pd.DataFrame,
    gpu_clusters: pd.DataFrame,
) -> dict:
    """Compute ARI and NMI between CPU and GPU Leiden cluster assignments.

    Args:
        cpu_clusters: CPU cluster labels.
        gpu_clusters: GPU cluster labels.

    Returns:
        Dict with ARI and NMI.
    """
    # Align indices
    common = cpu_clusters.index.intersection(gpu_clusters.index)
    if len(common) == 0:
        return {"status": "no_common_spots"}

    col = "leiden_1.0"
    cpu_labels = cpu_clusters.loc[common, col].astype(str).values
    gpu_labels = gpu_clusters.loc[common, col].astype(str).values

    ari = adjusted_rand_score(cpu_labels, gpu_labels)
    nmi = normalized_mutual_info_score(cpu_labels, gpu_labels)

    return {
        "n_common_spots": len(common),
        "ari": round(float(ari), 4),
        "nmi": round(float(nmi), 4),
        "n_clusters_cpu": len(np.unique(cpu_labels)),
        "n_clusters_gpu": len(np.unique(gpu_labels)),
    }


def compare_co_occurrence(
    cpu_co_occ: np.ndarray | None,
    gpu_co_occ: np.ndarray | None,
) -> dict:
    """Compare co-occurrence matrices between CPU and GPU.

    Args:
        cpu_co_occ: CPU co-occurrence array.
        gpu_co_occ: GPU co-occurrence array.

    Returns:
        Dict with correlation metrics.
    """
    if cpu_co_occ is None or gpu_co_occ is None:
        return {"status": "missing_data"}

    if cpu_co_occ.shape != gpu_co_occ.shape:
        return {
            "status": "shape_mismatch",
            "cpu_shape": list(cpu_co_occ.shape),
            "gpu_shape": list(gpu_co_occ.shape),
        }

    # Flatten and compute correlation
    cpu_flat = cpu_co_occ.flatten()
    gpu_flat = gpu_co_occ.flatten()

    mask = np.isfinite(cpu_flat) & np.isfinite(gpu_flat)
    if mask.sum() < 3:
        return {"status": "insufficient_valid_values"}

    rho, pval = spearmanr(cpu_flat[mask], gpu_flat[mask])
    pearson = np.corrcoef(cpu_flat[mask], gpu_flat[mask])[0, 1]

    # Max absolute difference
    max_diff = float(np.max(np.abs(cpu_flat[mask] - gpu_flat[mask])))

    return {
        "spearman_rho": round(float(rho), 6),
        "pearson_r": round(float(pearson), 6),
        "max_abs_diff": round(max_diff, 6),
        "n_values": int(mask.sum()),
    }


def compare_nhood_enrichment(
    cpu_nhood: np.ndarray | None,
    gpu_nhood: np.ndarray | None,
) -> dict:
    """Compare neighborhood enrichment z-scores between CPU and GPU.

    Args:
        cpu_nhood: CPU nhood enrichment z-score matrix.
        gpu_nhood: GPU nhood enrichment z-score matrix.

    Returns:
        Dict with correlation metrics.
    """
    if cpu_nhood is None or gpu_nhood is None:
        return {"status": "missing_data"}

    if cpu_nhood.shape != gpu_nhood.shape:
        return {
            "status": "shape_mismatch",
            "cpu_shape": list(cpu_nhood.shape),
            "gpu_shape": list(gpu_nhood.shape),
        }

    cpu_flat = cpu_nhood.flatten()
    gpu_flat = gpu_nhood.flatten()

    mask = np.isfinite(cpu_flat) & np.isfinite(gpu_flat)
    if mask.sum() < 3:
        return {"status": "insufficient_valid_values"}

    rho, pval = spearmanr(cpu_flat[mask], gpu_flat[mask])
    pearson = np.corrcoef(cpu_flat[mask], gpu_flat[mask])[0, 1]

    return {
        "spearman_rho": round(float(rho), 6),
        "pearson_r": round(float(pearson), 6),
        "n_values": int(mask.sum()),
    }


def compare_timing(cpu_json: dict, gpu_json: dict) -> dict:
    """Compare timing between CPU and GPU pipelines.

    Args:
        cpu_json: CPU results JSON.
        gpu_json: GPU results JSON.

    Returns:
        Dict with speedup per step and overall.
    """
    cpu_timings = cpu_json["timings"]
    gpu_timings = gpu_json["timings"]

    speedups = {}
    for step in cpu_timings:
        if step == "total":
            continue
        cpu_time = cpu_timings.get(step, -1)
        gpu_time = gpu_timings.get(step, -1)

        if cpu_time > 0 and gpu_time > 0:
            speedups[step] = {
                "cpu_seconds": cpu_time,
                "gpu_seconds": gpu_time,
                "speedup": round(cpu_time / gpu_time, 2),
            }

    # Overall speedup
    if cpu_timings.get("total", 0) > 0 and gpu_timings.get("total", 0) > 0:
        speedups["total"] = {
            "cpu_seconds": cpu_timings["total"],
            "gpu_seconds": gpu_timings["total"],
            "speedup": round(cpu_timings["total"] / gpu_timings["total"], 2),
        }

    return speedups


def run_comparison(
    results_dir: Path, platform: str, repeat: int,
    bin_size: str | None = None,
) -> dict:
    """Run all concordance comparisons for a single repeat.

    Args:
        results_dir: Directory with result files.
        platform: "visium" or "visium_hd".
        repeat: Repeat ID.
        bin_size: Bin size for Visium HD.

    Returns:
        Comprehensive concordance results dict.
    """
    label = f"{platform} ({bin_size})" if bin_size else platform
    print(f"\n{'=' * 60}")
    print(f"SPATIAL CONCORDANCE — {label} — repeat {repeat}")
    print(f"{'=' * 60}")

    data = load_pair(results_dir, platform, repeat, bin_size=bin_size)

    results = {
        "platform": platform,
        "repeat_id": repeat,
    }

    # 1. Moran's I concordance
    print("\n  Moran's I concordance:")
    moran_result = compare_autocorr(
        data["cpu"]["moranI"], data["gpu"]["moranI"], "moran"
    )
    results["moranI"] = moran_result
    if "I_spearman_rho" in moran_result:
        print(f"    Spearman ρ: {moran_result['I_spearman_rho']:.4f}")
        print(f"    Pearson r:  {moran_result['I_pearson_r']:.4f}")
    for k, v in moran_result.items():
        if k.startswith("svg_jaccard"):
            print(f"    {k}: {v:.4f}")

    # 2. Geary's C concordance
    print("\n  Geary's C concordance:")
    geary_result = compare_autocorr(
        data["cpu"]["gearyC"], data["gpu"]["gearyC"], "geary"
    )
    results["gearyC"] = geary_result
    if "C_spearman_rho" in geary_result:
        print(f"    Spearman ρ: {geary_result['C_spearman_rho']:.4f}")
        print(f"    Pearson r:  {geary_result['C_pearson_r']:.4f}")
    for k, v in geary_result.items():
        if k.startswith("svg_jaccard"):
            print(f"    {k}: {v:.4f}")

    # 3. Cluster concordance (expression-based Leiden)
    print("\n  Cluster concordance (Leiden 1.0):")
    cluster_result = compare_clusters(
        data["cpu"]["clusters"], data["gpu"]["clusters"],
    )
    results["clusters"] = cluster_result
    if "ari" in cluster_result:
        print(f"    ARI: {cluster_result['ari']:.4f}")
        print(f"    NMI: {cluster_result['nmi']:.4f}")
        print(
            f"    Clusters: CPU={cluster_result['n_clusters_cpu']}, "
            f"GPU={cluster_result['n_clusters_gpu']}"
        )

    # 4. Co-occurrence concordance
    print("\n  Co-occurrence concordance:")
    co_occ_result = compare_co_occurrence(
        data["cpu"]["co_occurrence"], data["gpu"]["co_occurrence"],
    )
    results["co_occurrence"] = co_occ_result
    if "spearman_rho" in co_occ_result:
        print(f"    Spearman ρ: {co_occ_result['spearman_rho']:.4f}")
        print(f"    Max abs diff: {co_occ_result['max_abs_diff']:.6f}")

    # 5. Neighborhood enrichment concordance
    print("\n  Neighborhood enrichment concordance:")
    nhood_result = compare_nhood_enrichment(
        data["cpu"]["nhood_enrichment"], data["gpu"]["nhood_enrichment"],
    )
    results["nhood_enrichment"] = nhood_result
    if "spearman_rho" in nhood_result:
        print(f"    Spearman ρ: {nhood_result['spearman_rho']:.4f}")

    # 6. Timing comparison
    print("\n  Timing comparison (CPU → GPU speedup):")
    timing_result = compare_timing(data["cpu"]["json"], data["gpu"]["json"])
    results["timing"] = timing_result
    for step, info in timing_result.items():
        cpu_t = info["cpu_seconds"]
        gpu_t = info["gpu_seconds"]
        spd = info["speedup"]
        label = "faster" if spd > 1 else "slower"
        print(f"    {step:30s} | CPU: {cpu_t:7.2f}s | GPU: {gpu_t:7.2f}s | {spd:5.2f}× {label}")

    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare CPU vs GPU spatial benchmark results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python SPATIAL/scripts/compare_spatial_results.py \\
      --results-dir SPATIAL/results --platform visium
  python SPATIAL/scripts/compare_spatial_results.py \\
      --results-dir SPATIAL/results --platform visium_hd --n-repeats 5
        """,
    )
    parser.add_argument(
        "--results-dir", type=str, required=True,
        help="Directory containing spatial benchmark results",
    )
    parser.add_argument(
        "--platform", type=str, required=True,
        choices=["visium", "visium_hd"],
        help="Spatial platform to compare",
    )
    parser.add_argument(
        "--bin-size", type=str, default=None,
        choices=["square_002um", "square_008um", "square_016um"],
        help="Bin size for Visium HD (required for visium_hd platform)",
    )
    parser.add_argument(
        "--n-repeats", type=int, default=1,
        help="Number of repeats to compare (default: 1)",
    )
    parser.add_argument(
        "--cpu-results-dir", type=str, default=None,
        help="Directory with the CPU files, if different from --results-dir",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Where to write the concordance JSON (default: --results-dir)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    global CPU_RESULTS_DIR
    args = parse_args()
    results_dir = Path(args.results_dir)
    if args.cpu_results_dir is not None:
        CPU_RESULTS_DIR = Path(args.cpu_results_dir)

    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}")
        raise SystemExit(1)

    all_results = []
    for repeat in range(1, args.n_repeats + 1):
        try:
            result = run_comparison(results_dir, args.platform, repeat, bin_size=args.bin_size)
            all_results.append(result)
        except FileNotFoundError as e:
            print(f"\n  Repeat {repeat}: SKIPPED — {e}")

    if not all_results:
        print("\nERROR: No results to compare.")
        raise SystemExit(1)

    # Save concordance results
    suffix = f"_{args.bin_size}" if args.bin_size else ""
    out_dir = Path(args.output_dir) if args.output_dir else results_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"spatial_concordance_{args.platform}{suffix}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n\nConcordance results saved: {output_path}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for r in all_results:
        print(f"\n  Repeat {r['repeat_id']}:")
        if "I_spearman_rho" in r.get("moranI", {}):
            print(f"    Moran's I ρ:    {r['moranI']['I_spearman_rho']:.4f}")
        if "C_spearman_rho" in r.get("gearyC", {}):
            print(f"    Geary's C ρ:    {r['gearyC']['C_spearman_rho']:.4f}")
        if "ari" in r.get("clusters", {}):
            print(f"    Cluster ARI:    {r['clusters']['ari']:.4f}")
            print(f"    Cluster NMI:    {r['clusters']['nmi']:.4f}")
        if "spearman_rho" in r.get("co_occurrence", {}):
            print(f"    Co-occ ρ:       {r['co_occurrence']['spearman_rho']:.4f}")
        if "spearman_rho" in r.get("nhood_enrichment", {}):
            print(f"    Nhood enrich ρ: {r['nhood_enrichment']['spearman_rho']:.4f}")
        if "total" in r.get("timing", {}):
            print(f"    Total speedup:  {r['timing']['total']['speedup']:.2f}×")

    print("\nDone!")


if __name__ == "__main__":
    main()
