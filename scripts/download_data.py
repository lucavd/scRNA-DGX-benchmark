#!/usr/bin/env python3
"""Download and subsample single-cell RNA-seq datasets for benchmarking.

Downloads mouse brain cells from CZ CELLxGENE Census, then creates
reproducible subsamples at different cell counts for benchmarking.

Usage:
    python scripts/download_data.py --data-dir data/
    python scripts/download_data.py --data-dir /mnt/home/u0044/sc-gpu-benchmark/data
    python scripts/download_data.py --help
"""

import argparse
import gc
import sys
import time
from pathlib import Path

import numpy as np

# Fixed random seed for reproducibility
RANDOM_SEED = 42

# Subsample sizes to create
SUBSAMPLE_SIZES = [10_000, 50_000, 100_000, 500_000]

# Maximum number of cells to download from Census.
# The full Census has ~3.6M mouse brain cells; we cap at 1.3M to match
# the original 10x Genomics benchmark dataset size.
MAX_CELLS = 1_300_000

# Census version for reproducibility (pinned to a specific release)
CENSUS_VERSION = "2025-11-08"


def download_from_census(data_dir: Path, max_cells: int) -> Path:
    """Download mouse brain cells from CZ CELLxGENE Census.

    Downloads primary mouse brain single-cell data, limited to 10x assays
    for consistency. Pins the Census version for reproducibility.

    Args:
        data_dir: Directory to save the downloaded h5ad file.
        max_cells: Maximum number of cells to download.

    Returns:
        Path to the saved h5ad file.
    """
    import cellxgene_census

    out_path = data_dir / f"brain_{max_cells}.h5ad"
    if out_path.exists():
        size_gb = out_path.stat().st_size / (1024**3)
        print(f"  Already exists: {out_path} ({size_gb:.2f} GB), skipping")
        return out_path

    obs_filter = (
        "tissue_general == 'brain' "
        "and is_primary_data == True "
        "and assay in ['10x 3\\' v3', '10x 3\\' v2', '10x 3\\' v1']"
    )
    obs_columns = [
        "cell_type", "assay", "tissue", "disease", "dataset_id", "donor_id",
    ]

    print(f"  Opening Census (version: {CENSUS_VERSION})...")
    start_time = time.time()

    with cellxgene_census.open_soma(census_version=CENSUS_VERSION) as census:
        # Step 1: Get only cell metadata (tiny — just a dataframe, no expression)
        print(f"  Step 1/2: Fetching cell metadata (lightweight)...")
        obs_df = cellxgene_census.get_obs(
            census,
            organism="Mus musculus",
            value_filter=obs_filter,
            column_names=["soma_joinid"] + obs_columns,
        )
        print(f"  Found {len(obs_df):,} matching cells")

        # Step 2: Pick random subset of cell IDs, then download only those
        np.random.seed(RANDOM_SEED)
        n_to_sample = min(max_cells, len(obs_df))
        selected_idx = np.random.choice(len(obs_df), size=n_to_sample, replace=False)
        selected_ids = obs_df.iloc[sorted(selected_idx)]["soma_joinid"].tolist()
        del obs_df
        gc.collect()

        print(f"  Step 2/2: Downloading expression data for {n_to_sample:,} cells...")
        adata = cellxgene_census.get_anndata(
            census=census,
            organism="Mus musculus",
            obs_coords=selected_ids,
            obs_column_names=obs_columns,
        )

    elapsed = time.time() - start_time
    print(f"  Downloaded: {adata.n_obs:,} cells x {adata.n_vars:,} genes in {elapsed:.0f}s")

    print(f"  Saving to: {out_path}")
    adata.write_h5ad(out_path)
    size_gb = out_path.stat().st_size / (1024**3)
    print(f"  Saved: {size_gb:.2f} GB")

    return out_path


def create_subsamples(source_path: Path, data_dir: Path) -> None:
    """Create reproducible subsamples from the full dataset.

    Args:
        source_path: Path to the full h5ad file.
        data_dir: Directory to save subsampled files.
    """
    import scanpy as sc

    print(f"\nLoading full dataset: {source_path}")
    adata = sc.read_h5ad(source_path)
    print(f"  Full dataset: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    for n_cells in SUBSAMPLE_SIZES:
        out_path = data_dir / f"brain_{n_cells}.h5ad"
        if out_path.exists():
            print(f"\n  Subsample {n_cells:,} already exists, skipping")
            continue

        if n_cells > adata.n_obs:
            print(f"\n  Skipping {n_cells:,}: exceeds available cells ({adata.n_obs:,})")
            continue

        print(f"\n  Creating subsample: {n_cells:,} cells")
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(adata.n_obs, size=n_cells, replace=False)
        subset = adata[sorted(idx)].copy()

        print(f"  Saving to: {out_path}")
        subset.write_h5ad(out_path)
        size_mb = out_path.stat().st_size / (1024**2)
        print(f"  Saved: {subset.n_obs:,} cells x {subset.n_vars:,} genes ({size_mb:.1f} MB)")

        del subset
        gc.collect()


def verify_datasets(data_dir: Path) -> None:
    """Print summary of all datasets in the data directory.

    Args:
        data_dir: Directory containing h5ad files.
    """
    import scanpy as sc

    print("\n" + "=" * 70)
    print("DATASET VERIFICATION")
    print("=" * 70)

    h5ad_files = sorted(data_dir.glob("*.h5ad"))
    if not h5ad_files:
        print("  No .h5ad files found!")
        return

    for filepath in h5ad_files:
        size_mb = filepath.stat().st_size / (1024**2)
        try:
            adata = sc.read_h5ad(filepath, backed="r")
            print(
                f"  {filepath.name:40s} | "
                f"{adata.n_obs:>10,} cells | "
                f"{adata.n_vars:>8,} genes | "
                f"{size_mb:>8.1f} MB"
            )
            adata.file.close()
        except Exception as e:
            print(f"  {filepath.name:40s} | ERROR: {e}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download and subsample scRNA-seq datasets for benchmarking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/download_data.py --data-dir data/
  python scripts/download_data.py --data-dir data/ --max-cells 500000
  python scripts/download_data.py --data-dir data/ --skip-subsample
  python scripts/download_data.py --data-dir data/ --verify-only
        """,
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Directory to store downloaded datasets",
    )
    parser.add_argument(
        "--max-cells",
        type=int,
        default=MAX_CELLS,
        help=f"Max cells to download from Census (default: {MAX_CELLS:,})",
    )
    parser.add_argument(
        "--skip-subsample",
        action="store_true",
        help="Skip subsampling step (download only)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing datasets, no downloads",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Data directory: {data_dir.resolve()}")

    if args.verify_only:
        verify_datasets(data_dir)
        return

    # Download from CELLxGENE Census
    print(f"\n{'=' * 70}")
    print(f"Downloading mouse brain cells from CZ CELLxGENE Census")
    print(f"Target: {args.max_cells:,} cells (10x assays only)")
    print(f"Census version: {CENSUS_VERSION}")
    print(f"{'=' * 70}")

    source_path = download_from_census(data_dir, args.max_cells)

    # Create subsamples
    if not args.skip_subsample:
        create_subsamples(source_path, data_dir)

    # Verify everything
    verify_datasets(data_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()
