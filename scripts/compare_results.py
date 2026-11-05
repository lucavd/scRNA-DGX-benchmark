#!/usr/bin/env python3
"""Compare CPU vs GPU benchmark results for concordance analysis.

Computes ARI, NMI, HVG Jaccard, PCA loading correlations, DE log-fold-change
correlations, and UMAP Procrustes distance between CPU and GPU pipeline outputs.

Usage:
    python scripts/compare_results.py --results-dir results/ --n-cells 10000
    python scripts/compare_results.py --help
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


# Leiden resolutions to compare
LEIDEN_RESOLUTIONS = [0.5, 1.0, 1.5]


def load_pair(results_dir: Path, n_cells: int, repeat: int) -> dict:
    """Load CPU and GPU result files for a given cell count and repeat.

    Args:
        results_dir: Directory containing result files.
        n_cells: Number of input cells.
        repeat: Repeat ID.

    Returns:
        Dict with cpu/gpu sub-dicts containing DataFrames and JSON metadata.
    """
    data = {}
    for pipeline in ["cpu", "gpu"]:
        prefix = f"{pipeline}_{n_cells}_r{repeat}"
        data[pipeline] = {
            "json": json.loads((results_dir / f"{prefix}_results.json").read_text()),
            "clusters": pd.read_csv(results_dir / f"{prefix}_clusters.csv", index_col=0),
            "hvgs": pd.read_csv(results_dir / f"{prefix}_hvgs.csv"),
            "de": pd.read_csv(results_dir / f"{prefix}_de.csv"),
            "umap": pd.read_csv(results_dir / f"{prefix}_umap.csv", index_col=0),
            "pca": pd.read_csv(results_dir / f"{prefix}_pca_loadings.csv", index_col=0),
        }
        # Load kNN indices if available
        knn_path = results_dir / f"{prefix}_knn.npz"
        if knn_path.exists():
            knn_npz = np.load(knn_path)
            data[pipeline]["knn"] = [knn_npz[k] for k in knn_npz.files]
        else:
            data[pipeline]["knn"] = None
    return data


def compare_clusters(cpu_clusters: pd.DataFrame, gpu_clusters: pd.DataFrame) -> dict:
    """Compute ARI and NMI between CPU and GPU cluster assignments.

    Args:
        cpu_clusters: DataFrame with cluster labels from CPU pipeline.
        gpu_clusters: DataFrame with cluster labels from GPU pipeline.

    Returns:
        Dict with ARI and NMI per resolution.
    """
    # Align indices (cells must match)
    common = cpu_clusters.index.intersection(gpu_clusters.index)
    cpu_aligned = cpu_clusters.loc[common]
    gpu_aligned = gpu_clusters.loc[common]

    results = {}
    for res in LEIDEN_RESOLUTIONS:
        col = f"leiden_{res}"
        cpu_labels = cpu_aligned[col].astype(str).values
        gpu_labels = gpu_aligned[col].astype(str).values

        ari = adjusted_rand_score(cpu_labels, gpu_labels)
        nmi = normalized_mutual_info_score(cpu_labels, gpu_labels)

        results[col] = {
            "ari": round(ari, 6),
            "nmi": round(nmi, 6),
            "n_clusters_cpu": len(np.unique(cpu_labels)),
            "n_clusters_gpu": len(np.unique(gpu_labels)),
            "n_cells_compared": len(common),
        }
        print(f"  {col}: ARI={ari:.4f}, NMI={nmi:.4f} "
              f"(CPU: {results[col]['n_clusters_cpu']} clusters, "
              f"GPU: {results[col]['n_clusters_gpu']} clusters)")

    return results


def compare_hvgs(cpu_hvgs: pd.DataFrame, gpu_hvgs: pd.DataFrame) -> dict:
    """Compute Jaccard index of HVG sets.

    Args:
        cpu_hvgs: DataFrame with gene column from CPU.
        gpu_hvgs: DataFrame with gene column from GPU.

    Returns:
        Dict with Jaccard index and overlap counts.
    """
    cpu_set = set(cpu_hvgs["gene"].values)
    gpu_set = set(gpu_hvgs["gene"].values)

    intersection = cpu_set & gpu_set
    union = cpu_set | gpu_set
    jaccard = len(intersection) / len(union) if union else 0.0

    result = {
        "jaccard": round(jaccard, 6),
        "n_cpu": len(cpu_set),
        "n_gpu": len(gpu_set),
        "n_intersection": len(intersection),
        "n_union": len(union),
    }
    print(f"  HVG Jaccard: {jaccard:.4f} "
          f"({len(intersection)}/{len(union)} overlap)")
    return result


def compare_pca(cpu_pca: pd.DataFrame, gpu_pca: pd.DataFrame) -> dict:
    """Compute Spearman correlation of PCA loadings (first 10 PCs).

    PCA components can have arbitrary sign flips, so we compare
    the absolute value of the correlation.

    Args:
        cpu_pca: DataFrame with PCA loadings from CPU.
        gpu_pca: DataFrame with PCA loadings from GPU.

    Returns:
        Dict with per-PC Spearman correlations.
    """
    # Align gene indices
    common_genes = cpu_pca.index.intersection(gpu_pca.index)
    cpu_aligned = cpu_pca.loc[common_genes]
    gpu_aligned = gpu_pca.loc[common_genes]

    correlations = {}
    for col in cpu_aligned.columns:
        rho, pval = spearmanr(cpu_aligned[col].values, gpu_aligned[col].values)
        correlations[col] = {
            "spearman_rho": round(rho, 6),
            "abs_spearman_rho": round(abs(rho), 6),
            "pvalue": float(f"{pval:.2e}"),
        }

    mean_abs_rho = np.mean([v["abs_spearman_rho"] for v in correlations.values()])
    print(f"  PCA loadings: mean |Spearman rho| = {mean_abs_rho:.4f} "
          f"(across {len(correlations)} PCs)")

    return {
        "per_pc": correlations,
        "mean_abs_spearman_rho": round(mean_abs_rho, 6),
        "n_genes_compared": len(common_genes),
    }


def match_clusters(
    cpu_clusters: pd.DataFrame,
    gpu_clusters: pd.DataFrame,
    resolution: str = "leiden_1.0",
) -> dict:
    """Find optimal cluster matching between CPU and GPU using Hungarian algorithm.

    Builds a contingency matrix (rows=CPU clusters, cols=GPU clusters) where
    each cell is the number of shared cells. Then finds the assignment that
    maximises total overlap.

    Args:
        cpu_clusters: Cluster labels from CPU.
        gpu_clusters: Cluster labels from GPU.
        resolution: Which leiden column to use.

    Returns:
        Dict mapping CPU cluster label -> GPU cluster label.
    """
    common = cpu_clusters.index.intersection(gpu_clusters.index)
    cpu_labels = cpu_clusters.loc[common, resolution].astype(str).values
    gpu_labels = gpu_clusters.loc[common, resolution].astype(str).values

    cpu_unique = sorted(set(cpu_labels), key=lambda x: int(x) if x.isdigit() else x)
    gpu_unique = sorted(set(gpu_labels), key=lambda x: int(x) if x.isdigit() else x)

    # Build contingency matrix (n_cpu_clusters x n_gpu_clusters)
    contingency = np.zeros((len(cpu_unique), len(gpu_unique)), dtype=int)
    cpu_idx_map = {c: i for i, c in enumerate(cpu_unique)}
    gpu_idx_map = {g: i for i, g in enumerate(gpu_unique)}

    for c, g in zip(cpu_labels, gpu_labels):
        contingency[cpu_idx_map[c], gpu_idx_map[g]] += 1

    # Hungarian algorithm (minimises cost, so we negate the overlap)
    row_ind, col_ind = linear_sum_assignment(-contingency)

    matching = {}
    for r, c in zip(row_ind, col_ind):
        overlap = contingency[r, c]
        cpu_size = contingency[r, :].sum()
        matching[cpu_unique[r]] = {
            "gpu_cluster": gpu_unique[c],
            "overlap": int(overlap),
            "cpu_cluster_size": int(cpu_size),
            "overlap_fraction": round(overlap / cpu_size, 4) if cpu_size > 0 else 0.0,
        }

    return matching


def compare_de(
    cpu_de: pd.DataFrame,
    gpu_de: pd.DataFrame,
    cluster_matching: dict,
) -> dict:
    """Compare DE log-fold-changes using matched clusters.

    Uses the Hungarian-matched cluster pairs so that CPU cluster X is
    compared to the GPU cluster that shares the most cells with X.

    Args:
        cpu_de: DataFrame with DE results from CPU.
        gpu_de: DataFrame with DE results from GPU.
        cluster_matching: Dict from match_clusters() mapping CPU -> GPU cluster.

    Returns:
        Dict with per-matched-pair and overall Spearman correlations.
    """
    per_pair = {}
    all_rhos = []

    for cpu_group, match_info in sorted(
        cluster_matching.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]
    ):
        gpu_group = match_info["gpu_cluster"]

        cpu_g = cpu_de[cpu_de["group"].astype(str) == cpu_group].set_index("names")
        gpu_g = gpu_de[gpu_de["group"].astype(str) == gpu_group].set_index("names")

        # Top 100 genes from CPU, intersect with GPU
        top_cpu = cpu_g.head(100).index
        common_genes = top_cpu.intersection(gpu_g.index)

        if len(common_genes) < 5:
            continue

        cpu_lfc = cpu_g.loc[common_genes, "logfoldchanges"].values
        gpu_lfc = gpu_g.loc[common_genes, "logfoldchanges"].values

        rho, pval = spearmanr(cpu_lfc, gpu_lfc)
        pair_key = f"cpu{cpu_group}_gpu{gpu_group}"
        per_pair[pair_key] = {
            "spearman_rho": round(rho, 6),
            "pvalue": float(f"{pval:.2e}"),
            "n_genes_compared": len(common_genes),
            "overlap_fraction": match_info["overlap_fraction"],
        }
        all_rhos.append(rho)
        print(f"    CPU {cpu_group:>3s} <-> GPU {gpu_group:>3s} "
              f"(overlap {match_info['overlap_fraction']:.0%}): "
              f"rho={rho:.4f}")

    mean_rho = np.mean(all_rhos) if all_rhos else 0.0
    print(f"\n  DE mean Spearman rho = {mean_rho:.4f} "
          f"(across {len(per_pair)} matched pairs)")

    return {
        "per_pair": per_pair,
        "mean_spearman_rho": round(mean_rho, 6),
        "n_pairs_compared": len(per_pair),
        "cluster_matching": cluster_matching,
    }


def compare_knn(cpu_knn: list, gpu_knn: list) -> dict:
    """Compute per-cell Jaccard overlap of k-nearest neighbor sets.

    For each cell, computes |CPU_neighbors ∩ GPU_neighbors| / |CPU_neighbors ∪ GPU_neighbors|.
    This directly measures whether the two pipelines agree on neighborhood structure,
    which is what drives clustering and DE.

    Args:
        cpu_knn: List of arrays, each containing neighbor indices for one cell.
        gpu_knn: List of arrays, each containing neighbor indices for one cell.

    Returns:
        Dict with mean/median/min Jaccard and distribution summary.
    """
    n_cells = min(len(cpu_knn), len(gpu_knn))
    jaccards = []

    for i in range(n_cells):
        cpu_set = set(cpu_knn[i])
        gpu_set = set(gpu_knn[i])
        if not cpu_set and not gpu_set:
            jaccards.append(1.0)
            continue
        intersection = len(cpu_set & gpu_set)
        union = len(cpu_set | gpu_set)
        jaccards.append(intersection / union if union > 0 else 0.0)

    jaccards = np.array(jaccards)

    result = {
        "mean_jaccard": round(float(np.mean(jaccards)), 6),
        "median_jaccard": round(float(np.median(jaccards)), 6),
        "min_jaccard": round(float(np.min(jaccards)), 6),
        "max_jaccard": round(float(np.max(jaccards)), 6),
        "std_jaccard": round(float(np.std(jaccards)), 6),
        "fraction_perfect": round(float(np.mean(jaccards == 1.0)), 4),
        "n_cells": n_cells,
    }

    print(f"  kNN Jaccard: mean={result['mean_jaccard']:.4f}, "
          f"median={result['median_jaccard']:.4f}, "
          f"min={result['min_jaccard']:.4f}")
    print(f"  Cells with identical neighbors: "
          f"{result['fraction_perfect']:.1%} ({int(result['fraction_perfect'] * n_cells)}/{n_cells})")

    return result


def compare_timings(cpu_json: dict, gpu_json: dict) -> dict:
    """Compute speedup factors (CPU time / GPU time) per step.

    Args:
        cpu_json: CPU benchmark results JSON.
        gpu_json: GPU benchmark results JSON.

    Returns:
        Dict with speedup per step.
    """
    cpu_t = cpu_json["timings"]
    gpu_t = gpu_json["timings"]

    speedups = {}
    for step in cpu_t:
        if step in gpu_t and gpu_t[step] > 0:
            speedup = cpu_t[step] / gpu_t[step]
            speedups[step] = {
                "cpu_seconds": cpu_t[step],
                "gpu_seconds": gpu_t[step],
                "speedup": round(speedup, 2),
            }

    print("\n  Speedup (CPU time / GPU time):")
    for step, vals in speedups.items():
        arrow = "faster" if vals["speedup"] > 1 else "SLOWER"
        print(f"    {step:25s}: {vals['speedup']:6.2f}x ({arrow})")

    return speedups


def run_comparison(results_dir: Path, n_cells: int, repeat: int) -> dict:
    """Run all concordance comparisons for a CPU/GPU pair.

    Args:
        results_dir: Directory with result files.
        n_cells: Number of input cells.
        repeat: Repeat ID.

    Returns:
        Full comparison results dict.
    """
    print(f"\n{'=' * 70}")
    print(f"CONCORDANCE ANALYSIS — {n_cells:,} cells — repeat {repeat}")
    print(f"{'=' * 70}")

    data = load_pair(results_dir, n_cells, repeat)

    print("\n--- Cluster concordance ---")
    cluster_concordance = compare_clusters(
        data["cpu"]["clusters"], data["gpu"]["clusters"],
    )

    print("\n--- HVG overlap ---")
    hvg_concordance = compare_hvgs(
        data["cpu"]["hvgs"], data["gpu"]["hvgs"],
    )

    print("\n--- PCA loadings ---")
    pca_concordance = compare_pca(
        data["cpu"]["pca"], data["gpu"]["pca"],
    )

    print("\n--- Cluster matching (Hungarian algorithm) ---")
    cluster_matching = match_clusters(
        data["cpu"]["clusters"], data["gpu"]["clusters"], "leiden_1.0",
    )
    matched = sum(1 for v in cluster_matching.values() if v["overlap_fraction"] > 0.5)
    print(f"  {matched}/{len(cluster_matching)} clusters matched with >50% overlap")

    print("\n--- DE log-fold-changes (matched clusters) ---")
    de_concordance = compare_de(
        data["cpu"]["de"], data["gpu"]["de"], cluster_matching,
    )

    print("\n--- kNN neighbor overlap ---")
    if data["cpu"]["knn"] is not None and data["gpu"]["knn"] is not None:
        knn_concordance = compare_knn(data["cpu"]["knn"], data["gpu"]["knn"])
    else:
        print("  SKIPPED: kNN files not found. Re-run benchmarks to generate them.")
        knn_concordance = {"skipped": True}

    print("\n--- Performance ---")
    speedups = compare_timings(
        data["cpu"]["json"], data["gpu"]["json"],
    )

    return {
        "metadata": {
            "n_cells": n_cells,
            "repeat": repeat,
            "cpu_timestamp": data["cpu"]["json"]["metadata"]["timestamp"],
            "gpu_timestamp": data["gpu"]["json"]["metadata"]["timestamp"],
        },
        "cluster_concordance": cluster_concordance,
        "hvg_concordance": hvg_concordance,
        "pca_concordance": pca_concordance,
        "de_concordance": de_concordance,
        "knn_concordance": knn_concordance,
        "speedups": speedups,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare CPU vs GPU benchmark results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/compare_results.py --results-dir results/ --n-cells 10000
  python scripts/compare_results.py --results-dir results/ --n-cells 10000 --repeat 1
        """,
    )
    parser.add_argument(
        "--results-dir", type=str, required=True,
        help="Directory containing benchmark result files",
    )
    parser.add_argument(
        "--n-cells", type=int, default=10000,
        help="Number of cells to compare (default: 10000)",
    )
    parser.add_argument(
        "--repeat", type=int, default=1,
        help="Repeat ID to compare (default: 1)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    results_dir = Path(args.results_dir)

    # Verify files exist
    for pipeline in ["cpu", "gpu"]:
        prefix = f"{pipeline}_{args.n_cells}_r{args.repeat}"
        json_file = results_dir / f"{prefix}_results.json"
        if not json_file.exists():
            print(f"ERROR: Missing {json_file}")
            print("Run both CPU and GPU benchmarks first.")
            raise SystemExit(1)

    comparison = run_comparison(results_dir, args.n_cells, args.repeat)

    # Save results
    output_file = results_dir / f"concordance_{args.n_cells}_r{args.repeat}.json"
    with open(output_file, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n  Concordance results saved: {output_file}")


if __name__ == "__main__":
    main()
