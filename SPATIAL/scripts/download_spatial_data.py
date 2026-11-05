#!/usr/bin/env python3
"""Download spatial transcriptomics datasets for GPU vs CPU benchmarking.

Downloads two 10x Genomics datasets:
1. Visium Mouse Brain Sagittal Anterior (~3,000 spots, 55 µm resolution)
2. Visium HD Mouse Brain FFPE, Space Ranger 3.0.0 (393,543 bins at 8 µm, 6,296,688 at 2 µm)

Both datasets are mouse brain tissue, matching the scRNA-seq benchmark.

Usage:
    python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data
    python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data --visium-only
    python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data --verify-only
    python SPATIAL/scripts/download_spatial_data.py --help
"""

import argparse
import hashlib
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


# ── Visium v1 Mouse Brain Sagittal Anterior (Space Ranger 1.1.0) ────────────
VISIUM_SAMPLE = "V1_Mouse_Brain_Sagittal_Anterior"
VISIUM_BASE_URL = (
    "https://cf.10xgenomics.com/samples/spatial-exp/1.1.0"
    f"/{VISIUM_SAMPLE}"
)
VISIUM_FILES = {
    "matrix": (
        f"{VISIUM_SAMPLE}_filtered_feature_bc_matrix.h5",
        f"{VISIUM_BASE_URL}/{VISIUM_SAMPLE}_filtered_feature_bc_matrix.h5",
    ),
    "spatial": (
        f"{VISIUM_SAMPLE}_spatial.tar.gz",
        f"{VISIUM_BASE_URL}/{VISIUM_SAMPLE}_spatial.tar.gz",
    ),
}

# ── Visium HD Mouse Brain FFPE (Space Ranger 3.0.0) ─────────────────────────
# The dataset analysed in the chapter. Until 2026-11-05 this script pointed to
# the 10x developer "Visium_HD_Tiny_3prime_Dataset" (Space Ranger 4.0.1), which
# is NOT the dataset of the benchmark. The four .h5 matrices of
# Visium_HD_Mouse_Brain_binned_outputs.tar.gz were checked byte for byte
# (md5) against the files analysed in SPATIAL/data/visium_hd/ on 2026-11-05
# (step S7 of the LNBI chapter); their md5 are below and are verified after
# extraction.
VISIUM_HD_SAMPLE = "Visium_HD_Mouse_Brain"
VISIUM_HD_BASE_URL = (
    "https://cf.10xgenomics.com/samples/spatial-exp/3.0.0"
    f"/{VISIUM_HD_SAMPLE}"
)
VISIUM_HD_ARCHIVES = [
    f"{VISIUM_HD_SAMPLE}_binned_outputs.tar.gz",  # 4,616,239,264 bytes
    f"{VISIUM_HD_SAMPLE}_spatial.tar.gz",         # 70,978,529 bytes
]
VISIUM_HD_MD5 = {
    "binned_outputs/square_002um/filtered_feature_bc_matrix.h5": "f3095a576f21495dedb349377d4f032d",
    "binned_outputs/square_002um/raw_feature_bc_matrix.h5": "6591190e7de059c0352e876c966fb6e8",
    "binned_outputs/square_008um/filtered_feature_bc_matrix.h5": "70aa0e8613fad7819ab737e298dd5c69",
    "binned_outputs/square_008um/raw_feature_bc_matrix.h5": "1f6150257581b7c99763f689c0364656",
}


def download_file(url: str, dest: Path, description: str = "") -> bool:
    """Download a file using wget with progress bar.

    Args:
        url: URL to download from.
        dest: Destination file path.
        description: Human-readable description for logging.

    Returns:
        True if download succeeded, False otherwise.
    """
    if dest.exists():
        size_mb = dest.stat().st_size / (1024**2)
        print(f"  Already exists: {dest.name} ({size_mb:.1f} MB), skipping")
        return True

    label = description or dest.name
    print(f"  Downloading: {label}")
    print(f"    URL: {url}")
    print(f"    Dest: {dest}")

    try:
        result = subprocess.run(
            ["wget", "-q", "--show-progress", "-O", str(dest), url],
            check=True,
            timeout=3600,  # 1 hour timeout
        )
        size_mb = dest.stat().st_size / (1024**2)
        print(f"    Done: {size_mb:.1f} MB")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    FAILED: wget returned exit code {e.returncode}")
        # Clean up partial download
        if dest.exists():
            dest.unlink()
        return False
    except subprocess.TimeoutExpired:
        print(f"    FAILED: download timed out after 1 hour")
        if dest.exists():
            dest.unlink()
        return False


def extract_tar(archive: Path, dest_dir: Path) -> bool:
    """Extract a tar.gz archive.

    Args:
        archive: Path to the tar.gz file.
        dest_dir: Directory to extract into.

    Returns:
        True if extraction succeeded.
    """
    print(f"  Extracting: {archive.name} → {dest_dir}")
    try:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(path=dest_dir)
        print(f"    Done")
        return True
    except Exception as e:
        print(f"    FAILED: {e}")
        return False


def extract_zip(archive: Path, dest_dir: Path) -> bool:
    """Extract a zip archive.

    Args:
        archive: Path to the zip file.
        dest_dir: Directory to extract into.

    Returns:
        True if extraction succeeded.
    """
    print(f"  Extracting: {archive.name} → {dest_dir}")
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(path=dest_dir)
        print(f"    Done")
        return True
    except Exception as e:
        print(f"    FAILED: {e}")
        return False


def download_visium(data_dir: Path) -> bool:
    """Download Visium Mouse Brain Sagittal Anterior dataset.

    Creates the directory structure expected by scanpy.read_visium():
        data_dir/visium/
        ├── filtered_feature_bc_matrix.h5
        └── spatial/
            ├── tissue_hires_image.png
            ├── tissue_lowres_image.png
            ├── tissue_positions_list.csv
            └── scalefactors_json.json

    Args:
        data_dir: Base data directory.

    Returns:
        True if all downloads and extractions succeeded.
    """
    visium_dir = data_dir / "visium"
    visium_dir.mkdir(parents=True, exist_ok=True)

    # Check if already complete
    matrix_file = visium_dir / "filtered_feature_bc_matrix.h5"
    spatial_dir = visium_dir / "spatial"
    if matrix_file.exists() and spatial_dir.exists():
        print(f"  Visium data already complete at {visium_dir}")
        return True

    print(f"\n{'─' * 60}")
    print(f"Downloading Visium Mouse Brain Sagittal Anterior")
    print(f"{'─' * 60}")

    # Download filtered feature-barcode matrix
    fname, url = VISIUM_FILES["matrix"]
    matrix_dest = visium_dir / fname
    if not download_file(url, matrix_dest, "filtered feature-barcode matrix"):
        return False

    # Rename to standard name expected by scanpy.read_visium()
    if matrix_dest.exists() and not matrix_file.exists():
        matrix_dest.rename(matrix_file)
        print(f"  Renamed → {matrix_file.name}")

    # Download spatial data (coordinates + images)
    fname, url = VISIUM_FILES["spatial"]
    spatial_archive = visium_dir / fname
    if not download_file(url, spatial_archive, "spatial data (coordinates + images)"):
        return False

    # Extract spatial archive
    if not spatial_dir.exists():
        if not extract_tar(spatial_archive, visium_dir):
            return False

    # Clean up archive
    if spatial_archive.exists() and spatial_dir.exists():
        spatial_archive.unlink()
        print(f"  Cleaned up: {spatial_archive.name}")

    return True


def download_visium_hd(data_dir: Path) -> bool:
    """Download Visium HD Mouse Brain FFPE (Space Ranger 3.0.0), the chapter dataset.

    Downloads the binned outputs (2, 8 and 16 um) and the spatial folder as
    tar.gz archives, extracts them into data_dir/visium_hd/ and checks the md5
    of the four matrices against VISIUM_HD_MD5.

    Args:
        data_dir: Base data directory.

    Returns:
        True if download, extraction and md5 check succeeded.
    """
    visium_hd_dir = data_dir / "visium_hd"
    visium_hd_dir.mkdir(parents=True, exist_ok=True)

    binned_dir = visium_hd_dir / "binned_outputs"
    if binned_dir.exists() and any(binned_dir.iterdir()):
        print(f"  Visium HD data already present at {visium_hd_dir}")
        return check_visium_hd_md5(visium_hd_dir)

    print(f"\n{'─' * 60}")
    print("Downloading Visium HD Mouse Brain FFPE (Space Ranger 3.0.0)")
    print(f"{'─' * 60}")

    for name in VISIUM_HD_ARCHIVES:
        archive_dest = visium_hd_dir / name
        if not download_file(f"{VISIUM_HD_BASE_URL}/{name}", archive_dest, name):
            return False
        print(f"  Extracting {name} ...")
        with tarfile.open(archive_dest, "r:gz") as tf:
            tf.extractall(visium_hd_dir)
        _flatten_extracted_dir(visium_hd_dir)
        archive_dest.unlink()
        print(f"  Cleaned up: {name}")

    if not binned_dir.exists():
        print("\n  ERROR: binned_outputs/ not found after extraction.")
        return False
    return check_visium_hd_md5(visium_hd_dir)


def check_visium_hd_md5(visium_hd_dir: Path) -> bool:
    """Compare the md5 of the four Visium HD matrices with those of the chapter."""
    ok = True
    for rel, expected in VISIUM_HD_MD5.items():
        p = visium_hd_dir / rel
        if not p.exists():
            print(f"  MISSING {rel}")
            ok = False
            continue
        h = hashlib.md5()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        same = h.hexdigest() == expected
        ok = ok and same
        print(f"  {'OK ' if same else 'DIFF'} {rel}")
    return ok


def _flatten_extracted_dir(target_dir: Path) -> None:
    """If extraction created a single subdirectory, move its contents up.

    10x archives sometimes contain a top-level directory like
    'Visium_HD_Mouse_Brain/' that wraps the actual output files.
    This function detects that case and flattens the structure.

    Args:
        target_dir: Directory to check and flatten.
    """
    subdirs = [d for d in target_dir.iterdir() if d.is_dir()]
    # If there's exactly one subdirectory and it contains the expected files
    # (binned_outputs, spatial, etc.), move everything up
    if len(subdirs) == 1:
        inner = subdirs[0]
        inner_contents = list(inner.iterdir())
        # Check if the inner dir has the expected Visium HD structure
        inner_names = {c.name for c in inner_contents}
        if "binned_outputs" in inner_names or "spatial" in inner_names:
            print(f"  Flattening: moving contents of {inner.name}/ up")
            for item in inner_contents:
                dest = target_dir / item.name
                if not dest.exists():
                    item.rename(dest)
            # Remove the now-empty inner directory
            if not any(inner.iterdir()):
                inner.rmdir()


def verify_visium(data_dir: Path) -> None:
    """Verify Visium dataset and print summary.

    Args:
        data_dir: Base data directory.
    """
    import scanpy as sc

    visium_dir = data_dir / "visium"
    if not visium_dir.exists():
        print("  Visium: NOT FOUND")
        return

    try:
        adata = sc.read_visium(visium_dir)
        print(f"  Visium: {adata.n_obs:,} spots × {adata.n_vars:,} genes")
        print(f"    Spatial coords: {adata.obsm['spatial'].shape}")
        spatial_keys = list(adata.uns.get("spatial", {}).keys())
        if spatial_keys:
            lib_id = spatial_keys[0]
            images = adata.uns["spatial"][lib_id].get("images", {})
            print(f"    Images: {list(images.keys())}")
    except Exception as e:
        print(f"  Visium: ERROR: {e}")


def verify_visium_hd(data_dir: Path) -> None:
    """Verify Visium HD dataset and print summary.

    Args:
        data_dir: Base data directory.
    """
    visium_hd_dir = data_dir / "visium_hd"
    if not visium_hd_dir.exists():
        print("  Visium HD: NOT FOUND")
        return

    binned_dir = visium_hd_dir / "binned_outputs"
    if not binned_dir.exists():
        print("  Visium HD: binned_outputs/ NOT FOUND")
        return

    # List available bin sizes
    bin_sizes = sorted([d.name for d in binned_dir.iterdir() if d.is_dir()])
    print(f"  Visium HD: binned_outputs/ found")
    print(f"    Available bin sizes: {bin_sizes}")

    # Try loading the 8 µm bins with spatialdata-io
    for bin_size in bin_sizes:
        bin_dir = binned_dir / bin_size
        h5_file = bin_dir / "filtered_feature_bc_matrix.h5"
        if h5_file.exists():
            size_mb = h5_file.stat().st_size / (1024**2)
            print(f"    {bin_size}: matrix found ({size_mb:.1f} MB)")
        else:
            # Check for MEX format (matrix.mtx.gz)
            mex_dir = bin_dir / "filtered_feature_bc_matrix"
            if mex_dir.exists():
                print(f"    {bin_size}: MEX format found")
            else:
                print(f"    {bin_size}: no count matrix found")
    print("    md5 of the matrices against the chapter dataset:")
    check_visium_hd_md5(visium_hd_dir)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download spatial transcriptomics datasets for benchmarking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data
  python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data --visium-only
  python SPATIAL/scripts/download_spatial_data.py --data-dir SPATIAL/data --verify-only
        """,
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Directory to store spatial datasets",
    )
    parser.add_argument(
        "--visium-only",
        action="store_true",
        help="Download only the Visium v1 dataset (skip Visium HD)",
    )
    parser.add_argument(
        "--visium-hd-only",
        action="store_true",
        help="Download only the Visium HD dataset (skip Visium v1)",
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
        print(f"\n{'=' * 60}")
        print("DATASET VERIFICATION")
        print(f"{'=' * 60}")
        verify_visium(data_dir)
        verify_visium_hd(data_dir)
        return

    # Download datasets
    results = {}

    if not args.visium_hd_only:
        results["visium"] = download_visium(data_dir)

    if not args.visium_only:
        results["visium_hd"] = download_visium_hd(data_dir)

    # Verify
    print(f"\n{'=' * 60}")
    print("DATASET VERIFICATION")
    print(f"{'=' * 60}")
    verify_visium(data_dir)
    verify_visium_hd(data_dir)

    # Summary
    print(f"\n{'=' * 60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'=' * 60}")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {name:20s} {status}")

    if not all(results.values()):
        print("\nSome downloads failed. Check the errors above.")
        sys.exit(1)

    print("\nDone!")


if __name__ == "__main__":
    main()
