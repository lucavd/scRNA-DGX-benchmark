#!/usr/bin/env python3
"""Factorial benchmark of DE methods at scale (3.4M+ cells).

Tests 8 combinations of {method} × {distribution} × {chunking}:

  1. wilcoxon_cpu        — Wilcoxon on CPU (baseline, slow)
  2. ttest_cpu           — t-test on CPU (fast parametric)
  3. pseudobulk          — Pseudo-bulk aggregation by donor×cluster + Wilcoxon
  4. wilcoxon_scatter    — Wilcoxon scatter by genes across 8 GPUs
  5. wilcoxon_chunk      — Wilcoxon chunk-and-stream on 1 GPU
  6. ttest_scatter       — t-test scatter by genes across 8 GPUs
  7. ttest_chunk         — t-test chunk-and-stream on 1 GPU
  8. ttest_scatter_clean — t-test scatter + GPU cleanup between chunks

All tests use the same data: adata with leiden clusters + raw.X (all genes).
The script expects a pre-processed adata with PCA, neighbors, and leiden
already computed (output of the fullpipe test or benchmark_maxpower.py).

Alternatively, it can run preprocessing from scratch given brain_full_*.h5ad.

Usage:
    python scripts/test_de_benchmark.py --data-dir data/ --target-cells 3400000 --test ttest_cpu
    python scripts/test_de_benchmark.py --data-dir data/ --target-cells 3400000 --test all
    python scripts/test_de_benchmark.py --help
"""

import argparse
import gc
import os
import sys
import time
import warnings
from typing import Any

import numpy as np
import scanpy as sc
import scipy.sparse as sp


RANDOM_SEED = 42
GENE_CHUNK_SIZE = 500  # genes per chunk for chunk-and-stream / scatter
# 500 genes × 3.4M cells × 4B = 6.4 GB — fits on 1 GPU with room for workspace
# Previous value (5000) caused OOM: 3.4M × 5000 × 4B = 68 GB > 80 GB


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_T0 = time.time()


def log(msg: str) -> None:
    """Print a timestamped log message."""
    elapsed = time.time() - _T0
    print(f"[DE +{elapsed:7.1f}s] {msg}", flush=True)


def vram_report(n_gpus: int) -> None:
    """Print VRAM usage for each GPU."""
    import pynvml

    parts = []
    total_used = 0.0
    for i in range(n_gpus):
        h = pynvml.nvmlDeviceGetHandleByIndex(i)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        used_gb = info.used / (1024**3)
        total_gb = info.total / (1024**3)
        total_used += used_gb
        parts.append(f"GPU{i}:{used_gb:.1f}/{total_gb:.0f}GB")
    log(f"VRAM [{total_used:.1f} GB total]: {' | '.join(parts)}")


def ram_report() -> None:
    """Print CPU RAM usage."""
    import psutil

    rss_gb = psutil.Process().memory_info().rss / (1024**3)
    total_gb = psutil.virtual_memory().total / (1024**3)
    log(f"RAM: {rss_gb:.1f} / {total_gb:.0f} GB")


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def prepare_adata(data_dir: str, target_cells: int) -> sc.AnnData:
    """Load, preprocess, run PCA+neighbors+leiden to get cluster labels.

    This replicates the fullpipe preprocessing so that DE tests have
    cluster labels and raw.X available.

    Args:
        data_dir: Directory containing brain_full_*.h5ad.
        target_cells: Number of cells to use.

    Returns:
        AnnData with leiden_1.0 in obs, raw.X with all genes.
    """
    from pathlib import Path
    import cupy as cp

    data_path = Path(data_dir)
    existing = sorted(data_path.glob("brain_full_*.h5ad"))
    if not existing:
        log(f"ERROR: no brain_full_*.h5ad found in {data_dir}")
        sys.exit(1)
    path = existing[0]

    log(f"Loading {path.name}...")
    t0 = time.time()
    adata = sc.read_h5ad(path)
    log(f"Loaded: {adata.n_obs:,} x {adata.n_vars:,} ({time.time()-t0:.0f}s)")

    if target_cells < adata.n_obs:
        log(f"Subsampling to {target_cells:,}...")
        np.random.seed(RANDOM_SEED)
        idx = np.random.choice(adata.n_obs, size=target_cells, replace=False)
        adata = adata[sorted(idx)].copy()

    # QC
    log("QC...")
    adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], log1p=False, inplace=True)
    sc.pp.filter_cells(adata, min_genes=200)
    sc.pp.filter_genes(adata, min_cells=3)
    log(f"After QC: {adata.n_obs:,} x {adata.n_vars:,}")

    # Normalize
    log("Normalizing...")
    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # HVG + raw
    log("HVG selection...")
    sc.pp.highly_variable_genes(adata, n_top_genes=2000)
    adata.raw = adata.copy()
    adata = adata[:, adata.var["highly_variable"]].copy()
    log(f"HVG subset: {adata.n_obs:,} x {adata.n_vars:,}, raw: {adata.raw.n_vars:,} genes")

    # Scale on CPU
    log("Scaling on CPU...")
    if hasattr(adata.X, "toarray"):
        adata.X = adata.X.toarray()
    sc.pp.scale(adata, max_value=10)

    # PCA via scanpy on CPU (fast enough for clustering, avoids GPU setup)
    log("PCA (CPU, 50 components)...")
    sc.pp.pca(adata, n_comps=50, random_state=RANDOM_SEED)

    # Neighbors + Leiden on CPU (we only need cluster labels for DE)
    log("Neighbors + Leiden (CPU)...")
    sc.pp.neighbors(adata, n_neighbors=15, n_pcs=50, random_state=RANDOM_SEED)
    sc.tl.leiden(adata, resolution=1.0, random_state=RANDOM_SEED, key_added="leiden_1.0",
                 flavor="igraph", n_iterations=2, directed=False)

    n_clusters = adata.obs["leiden_1.0"].nunique()
    log(f"Clustering done: {n_clusters} clusters")
    ram_report()

    return adata


# ---------------------------------------------------------------------------
# DE helper: GPU t-test implementation
# ---------------------------------------------------------------------------

def _gpu_ttest_chunk(
    X_chunk: "cp.ndarray | cupyx.scipy.sparse.csr_matrix",
    labels: np.ndarray,
    groups: list[str],
    gene_names: np.ndarray,
) -> dict[str, dict]:
    """Compute t-test for a chunk of genes on GPU.

    For each group vs rest, computes Welch's t-test.

    Args:
        X_chunk: Expression matrix chunk (n_cells × n_genes_chunk) on GPU.
        labels: Cluster labels as integer array (on CPU).
        groups: List of unique group names.
        gene_names: Gene names for this chunk.

    Returns:
        Dict of {group: {"names": [...], "scores": [...], "pvals": [...]}}
    """
    import cupy as cp
    from cupyx.scipy import stats as cstats

    n_cells, n_genes = X_chunk.shape

    # Convert labels to GPU integer array
    # Map string labels to integers for masking
    label_to_int = {g: i for i, g in enumerate(groups)}
    labels_int = np.array([label_to_int[l] for l in labels], dtype=np.int32)
    labels_gpu = cp.asarray(labels_int)

    # Densify if sparse
    if sp.issparse(X_chunk) or hasattr(X_chunk, "toarray"):
        X_dense = X_chunk.toarray() if hasattr(X_chunk, "toarray") else X_chunk
    else:
        X_dense = X_chunk

    # Vectorized t-test: compute mean and var per group using masking
    # This avoids creating X_in/X_out copies for each group
    results = {}
    for gi, group in enumerate(groups):
        mask = labels_gpu == gi
        n_in = int(mask.sum())
        n_out = n_cells - n_in

        if n_in < 2 or n_out < 2:
            continue

        # Compute stats without full copies — use sum-based approach
        X_in_sum = X_dense[mask].sum(axis=0)
        X_in_sq_sum = (X_dense[mask] ** 2).sum(axis=0)
        mean_in = X_in_sum / n_in
        var_in = (X_in_sq_sum / n_in - mean_in ** 2) * n_in / (n_in - 1)

        X_total_sum = X_dense.sum(axis=0)
        X_total_sq_sum = (X_dense ** 2).sum(axis=0)
        X_out_sum = X_total_sum - X_in_sum
        X_out_sq_sum = X_total_sq_sum - X_in_sq_sum
        mean_out = X_out_sum / n_out
        var_out = (X_out_sq_sum / n_out - mean_out ** 2) * n_out / (n_out - 1)

        # Welch's t-test
        se = cp.sqrt(var_in / n_in + var_out / n_out)
        se = cp.maximum(se, 1e-10)  # avoid division by zero
        t_stat = (mean_in - mean_out) / se

        # Log fold change (mean_in - mean_out on log scale)
        logfc = cp.asnumpy(mean_in - mean_out)
        scores = cp.asnumpy(t_stat)

        results[group] = {
            "names": gene_names,
            "scores": scores,
            "logfoldchanges": logfc,
        }

    return results


def _gpu_wilcoxon_chunk(
    X_chunk: "cp.ndarray",
    labels: np.ndarray,
    groups: list[str],
    gene_names: np.ndarray,
) -> dict[str, dict]:
    """Compute Wilcoxon rank-sum test for a chunk of genes on GPU.

    Uses CuPy argsort for ranking.

    Args:
        X_chunk: Dense expression matrix chunk (n_cells × n_genes_chunk) on GPU.
        labels: Cluster labels (on CPU).
        groups: List of unique group names.
        gene_names: Gene names for this chunk.

    Returns:
        Dict of {group: {"names": [...], "scores": [...]}}.
    """
    import cupy as cp

    n_cells, n_genes = X_chunk.shape

    # Densify if needed
    if hasattr(X_chunk, "toarray"):
        X_chunk = X_chunk.toarray()

    # Rank each gene (column) across all cells
    # Free input after argsort to save VRAM (chunk ~6 GB, ranks ~6 GB)
    order = cp.argsort(X_chunk, axis=0)
    del X_chunk
    cp.get_default_memory_pool().free_all_blocks()
    ranks = cp.empty(order.shape, dtype=cp.float32)
    row_idx = cp.arange(n_cells)[:, None]
    ranks[order, cp.arange(n_genes)[None, :]] = row_idx + 1  # 1-based ranks
    del order
    cp.get_default_memory_pool().free_all_blocks()

    label_to_int = {g: i for i, g in enumerate(groups)}
    labels_int = np.array([label_to_int[l] for l in labels], dtype=np.int32)
    labels_gpu = cp.asarray(labels_int)

    results = {}
    for gi, group in enumerate(groups):
        mask = labels_gpu == gi
        n_in = int(mask.sum())
        n_out = n_cells - n_in

        if n_in < 2 or n_out < 2:
            continue

        # Wilcoxon U statistic: sum of ranks in group
        rank_sum = ranks[mask].sum(axis=0)
        # U = R - n_in*(n_in+1)/2
        U = rank_sum - n_in * (n_in + 1) / 2
        # Standardized z-score
        mean_U = n_in * n_out / 2
        std_U = cp.sqrt(n_in * n_out * (n_cells + 1) / 12)
        std_U = cp.maximum(std_U, 1e-10)
        z = (U - mean_U) / std_U

        results[group] = {
            "names": gene_names,
            "scores": cp.asnumpy(z),
        }

    return results


def _merge_de_results(
    chunk_results: list[dict[str, dict]],
) -> dict[str, dict]:
    """Merge DE results from multiple gene chunks.

    Args:
        chunk_results: List of per-chunk result dicts.

    Returns:
        Merged dict with concatenated arrays per group.
    """
    merged = {}
    for chunk in chunk_results:
        for group, data in chunk.items():
            if group not in merged:
                merged[group] = {k: [] for k in data.keys()}
            for k, v in data.items():
                merged[group][k].append(v)

    # Concatenate
    for group in merged:
        for k in merged[group]:
            merged[group][k] = np.concatenate(merged[group][k])

    return merged


# ---------------------------------------------------------------------------
# Test implementations
# ---------------------------------------------------------------------------

def test_wilcoxon_cpu(adata: sc.AnnData) -> dict:
    """Test 1: Wilcoxon on CPU (baseline)."""
    log("=== TEST 1: Wilcoxon CPU (baseline) ===")
    ram_report()

    t0 = time.time()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
        sc.tl.rank_genes_groups(
            adata, groupby="leiden_1.0", method="wilcoxon", use_raw=True,
        )
    elapsed = time.time() - t0

    n_de = len(adata.uns["rank_genes_groups"]["names"])
    log(f"Done in {elapsed:.1f}s — {n_de} genes tested")
    ram_report()

    return {"time": elapsed, "method": "wilcoxon", "backend": "cpu"}


def test_ttest_cpu(adata: sc.AnnData) -> dict:
    """Test 2: t-test on CPU."""
    log("=== TEST 2: t-test CPU ===")
    ram_report()

    t0 = time.time()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
        sc.tl.rank_genes_groups(
            adata, groupby="leiden_1.0", method="t-test", use_raw=True,
        )
    elapsed = time.time() - t0

    n_de = len(adata.uns["rank_genes_groups"]["names"])
    log(f"Done in {elapsed:.1f}s — {n_de} genes tested")
    ram_report()

    return {"time": elapsed, "method": "ttest", "backend": "cpu"}


def test_wilcoxon_scatter(adata: sc.AnnData, n_gpus: int) -> dict:
    """Test 3: Wilcoxon scatter by genes across N GPUs."""
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()
    log(f"=== TEST 3: Wilcoxon scatter ({n_gpus} GPUs) ===")

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)
    gene_names = np.array(adata.raw.var_names)
    labels = np.array(adata.obs["leiden_1.0"].values, dtype=str)
    groups = sorted(np.unique(labels), key=lambda x: int(x))
    n_genes = raw_X.shape[1]

    log(f"raw.X: {raw_X.shape}, nnz={raw_X.nnz:,}")
    log(f"Groups: {len(groups)} clusters")

    # Convert to CSC for efficient column slicing
    log("Converting raw.X to CSC for column slicing...")
    t0 = time.time()
    raw_csc = raw_X.tocsc()
    log(f"CSC conversion: {time.time()-t0:.1f}s")

    # Create gene chunks — distribute across GPUs
    gene_chunks = []
    for start in range(0, n_genes, GENE_CHUNK_SIZE):
        end = min(start + GENE_CHUNK_SIZE, n_genes)
        gene_chunks.append((start, end))

    log(f"Gene chunks: {len(gene_chunks)} chunks of ~{GENE_CHUNK_SIZE} genes")
    vram_report(n_gpus)

    t0 = time.time()
    all_results = []

    # Process chunks round-robin across GPUs
    for ci, (start, end) in enumerate(gene_chunks):
        gpu_id = ci % n_gpus
        chunk_genes = gene_names[start:end]

        # Slice columns and densify
        X_slice = raw_csc[:, start:end].toarray().astype(np.float32)

        with cp.cuda.Device(gpu_id):
            X_gpu = cp.asarray(X_slice)
            result = _gpu_wilcoxon_chunk(X_gpu, labels, groups, chunk_genes)
            all_results.append(result)
            del X_gpu
            cp.get_default_memory_pool().free_all_blocks()

        if (ci + 1) % n_gpus == 0 or ci == len(gene_chunks) - 1:
            log(f"  Chunks {ci+1}/{len(gene_chunks)} done")

    elapsed = time.time() - t0
    merged = _merge_de_results(all_results)

    log(f"Done in {elapsed:.1f}s — {n_genes} genes across {n_gpus} GPUs")
    vram_report(n_gpus)
    pynvml.nvmlShutdown()

    return {"time": elapsed, "method": "wilcoxon", "backend": f"scatter_{n_gpus}gpu"}


def test_wilcoxon_chunk(adata: sc.AnnData) -> dict:
    """Test 4: Wilcoxon chunk-and-stream on 1 GPU."""
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()
    log("=== TEST 4: Wilcoxon chunk-and-stream (1 GPU) ===")

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)
    gene_names = np.array(adata.raw.var_names)
    labels = np.array(adata.obs["leiden_1.0"].values, dtype=str)
    groups = sorted(np.unique(labels), key=lambda x: int(x))
    n_genes = raw_X.shape[1]

    log("Converting to CSC...")
    t0_csc = time.time()
    raw_csc = raw_X.tocsc()
    log(f"CSC conversion: {time.time()-t0_csc:.1f}s")

    gene_chunks = []
    for start in range(0, n_genes, GENE_CHUNK_SIZE):
        end = min(start + GENE_CHUNK_SIZE, n_genes)
        gene_chunks.append((start, end))

    log(f"Gene chunks: {len(gene_chunks)} of ~{GENE_CHUNK_SIZE}")
    vram_report(1)

    t0 = time.time()
    all_results = []

    with cp.cuda.Device(0):
        for ci, (start, end) in enumerate(gene_chunks):
            chunk_genes = gene_names[start:end]
            X_slice = raw_csc[:, start:end].toarray().astype(np.float32)
            X_gpu = cp.asarray(X_slice)

            result = _gpu_wilcoxon_chunk(X_gpu, labels, groups, chunk_genes)
            all_results.append(result)

            del X_gpu
            cp.get_default_memory_pool().free_all_blocks()

            if (ci + 1) % 3 == 0 or ci == len(gene_chunks) - 1:
                log(f"  Chunk {ci+1}/{len(gene_chunks)}")
                vram_report(1)

    elapsed = time.time() - t0
    merged = _merge_de_results(all_results)

    log(f"Done in {elapsed:.1f}s — {n_genes} genes on 1 GPU")
    pynvml.nvmlShutdown()

    return {"time": elapsed, "method": "wilcoxon", "backend": "chunk_1gpu"}


def test_ttest_scatter(adata: sc.AnnData, n_gpus: int) -> dict:
    """Test 5: t-test scatter by genes across N GPUs."""
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()
    log(f"=== TEST 5: t-test scatter ({n_gpus} GPUs) ===")

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)
    gene_names = np.array(adata.raw.var_names)
    labels = np.array(adata.obs["leiden_1.0"].values, dtype=str)
    groups = sorted(np.unique(labels), key=lambda x: int(x))
    n_genes = raw_X.shape[1]

    log("Converting to CSC...")
    raw_csc = raw_X.tocsc()

    gene_chunks = []
    for start in range(0, n_genes, GENE_CHUNK_SIZE):
        end = min(start + GENE_CHUNK_SIZE, n_genes)
        gene_chunks.append((start, end))

    log(f"Gene chunks: {len(gene_chunks)} of ~{GENE_CHUNK_SIZE}")
    vram_report(n_gpus)

    t0 = time.time()
    all_results = []

    for ci, (start, end) in enumerate(gene_chunks):
        gpu_id = ci % n_gpus
        chunk_genes = gene_names[start:end]
        X_slice = raw_csc[:, start:end].toarray().astype(np.float32)

        with cp.cuda.Device(gpu_id):
            X_gpu = cp.asarray(X_slice)
            result = _gpu_ttest_chunk(X_gpu, labels, groups, chunk_genes)
            all_results.append(result)
            del X_gpu
            cp.get_default_memory_pool().free_all_blocks()

        if (ci + 1) % n_gpus == 0 or ci == len(gene_chunks) - 1:
            log(f"  Chunks {ci+1}/{len(gene_chunks)} done")

    elapsed = time.time() - t0
    merged = _merge_de_results(all_results)

    log(f"Done in {elapsed:.1f}s — {n_genes} genes across {n_gpus} GPUs")
    vram_report(n_gpus)
    pynvml.nvmlShutdown()

    return {"time": elapsed, "method": "ttest", "backend": f"scatter_{n_gpus}gpu"}


def test_ttest_chunk(adata: sc.AnnData) -> dict:
    """Test 6: t-test chunk-and-stream on 1 GPU."""
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()
    log("=== TEST 6: t-test chunk-and-stream (1 GPU) ===")

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)
    gene_names = np.array(adata.raw.var_names)
    labels = np.array(adata.obs["leiden_1.0"].values, dtype=str)
    groups = sorted(np.unique(labels), key=lambda x: int(x))
    n_genes = raw_X.shape[1]

    log("Converting to CSC...")
    raw_csc = raw_X.tocsc()

    gene_chunks = []
    for start in range(0, n_genes, GENE_CHUNK_SIZE):
        end = min(start + GENE_CHUNK_SIZE, n_genes)
        gene_chunks.append((start, end))

    log(f"Gene chunks: {len(gene_chunks)} of ~{GENE_CHUNK_SIZE}")
    vram_report(1)

    t0 = time.time()
    all_results = []

    with cp.cuda.Device(0):
        for ci, (start, end) in enumerate(gene_chunks):
            chunk_genes = gene_names[start:end]
            X_slice = raw_csc[:, start:end].toarray().astype(np.float32)
            X_gpu = cp.asarray(X_slice)

            result = _gpu_ttest_chunk(X_gpu, labels, groups, chunk_genes)
            all_results.append(result)

            del X_gpu
            cp.get_default_memory_pool().free_all_blocks()

            if (ci + 1) % 3 == 0 or ci == len(gene_chunks) - 1:
                log(f"  Chunk {ci+1}/{len(gene_chunks)}")

    elapsed = time.time() - t0
    merged = _merge_de_results(all_results)

    log(f"Done in {elapsed:.1f}s — {n_genes} genes on 1 GPU")
    vram_report(1)
    pynvml.nvmlShutdown()

    return {"time": elapsed, "method": "ttest", "backend": "chunk_1gpu"}


def test_pseudobulk(adata: sc.AnnData) -> dict:
    """Test 8: Pseudo-bulk DE with Wilcoxon on aggregated counts.

    Aggregates raw counts by (donor_id × cluster), creating pseudo-bulk
    samples. Then runs Wilcoxon between clusters on the aggregated matrix.

    This is the statistically correct approach for multi-donor scRNA-seq:
    - Treats each donor as the experimental unit (avoids pseudoreplication)
    - Works on count-level data (sum of raw counts per donor×cluster)
    - Dramatically reduces matrix size (millions of cells → hundreds of samples)

    Note: a full implementation would use DESeq2/edgeR (negative binomial GLMs)
    on the raw counts. Here we use scanpy's Wilcoxon on the log-normalized
    pseudo-bulk matrix for fair comparison with the other tests. The key
    insight is the aggregation step, not the test itself.
    """
    log("=== TEST 8: Pseudo-bulk DE ===")
    ram_report()

    # Check if donor_id exists
    if "donor_id" not in adata.obs.columns:
        # Fall back: create synthetic donor_id from obs_names prefix
        log("  WARNING: donor_id not found, creating synthetic donor groups")
        np.random.seed(RANDOM_SEED)
        adata.obs["donor_id"] = np.random.choice(
            [f"donor_{i}" for i in range(20)], size=adata.n_obs,
        )

    donors = adata.obs["donor_id"].unique()
    clusters = sorted(adata.obs["leiden_1.0"].unique(), key=lambda x: int(x))
    log(f"  Donors: {len(donors)}, Clusters: {len(clusters)}")

    # Aggregate: sum raw counts per (donor × cluster)
    log("  Aggregating to pseudo-bulk (donor × cluster)...")
    t0_agg = time.time()

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)

    # Build pseudo-bulk matrix
    pb_data = []
    pb_labels = []
    pb_donors = []

    for cluster in clusters:
        cluster_mask = np.array(adata.obs["leiden_1.0"] == cluster)
        for donor in donors:
            donor_mask = np.array(adata.obs["donor_id"] == donor)
            combined = cluster_mask & donor_mask
            n_cells_group = combined.sum()
            if n_cells_group < 5:  # skip groups with too few cells
                continue

            # Sum raw counts for this donor×cluster
            group_sum = np.asarray(raw_X[combined].sum(axis=0)).flatten()
            pb_data.append(group_sum)
            pb_labels.append(cluster)
            pb_donors.append(donor)

    agg_time = time.time() - t0_agg
    log(f"  Aggregation: {len(pb_data)} pseudo-bulk samples in {agg_time:.1f}s")

    if len(pb_data) < 10:
        log("  ERROR: too few pseudo-bulk samples")
        return {"time": -1, "method": "pseudobulk", "backend": "cpu", "error": "too few samples"}

    # Create pseudo-bulk AnnData
    pb_matrix = np.vstack(pb_data).astype(np.float32)
    pb_adata = sc.AnnData(
        X=pb_matrix,
        var=adata.raw.var.copy(),
        obs={
            "leiden_1.0": pb_labels,
            "donor_id": pb_donors,
        },
    )
    log(f"  Pseudo-bulk matrix: {pb_adata.shape}")
    log(f"  Samples per cluster: min={min(pb_labels.count(c) for c in clusters if pb_labels.count(c) > 0)}, "
        f"max={max(pb_labels.count(c) for c in clusters)}")

    # Filter clusters with < 2 pseudo-bulk samples (can't run Wilcoxon on n=1)
    cluster_counts = pb_adata.obs["leiden_1.0"].value_counts()
    valid_clusters = cluster_counts[cluster_counts >= 2].index.tolist()
    dropped = len(clusters) - len(valid_clusters)
    if dropped > 0:
        log(f"  Dropping {dropped} clusters with <2 pseudo-bulk samples")
        pb_adata = pb_adata[pb_adata.obs["leiden_1.0"].isin(valid_clusters)].copy()
    log(f"  Pseudo-bulk after filter: {pb_adata.shape}, {len(valid_clusters)} clusters")

    # Normalize + log transform the pseudo-bulk
    sc.pp.normalize_total(pb_adata, target_sum=1e6)  # CPM for pseudo-bulk
    sc.pp.log1p(pb_adata)

    # DE on pseudo-bulk (tiny matrix — instant)
    log("  Running Wilcoxon on pseudo-bulk...")
    t0_de = time.time()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="DataFrame is highly fragmented")
        warnings.filterwarnings("ignore", category=UserWarning)
        sc.tl.rank_genes_groups(
            pb_adata, groupby="leiden_1.0", method="wilcoxon",
        )
    de_time = time.time() - t0_de

    total_time = agg_time + de_time
    n_genes_tested = len(pb_adata.uns["rank_genes_groups"]["names"])
    log(f"  DE done in {de_time:.1f}s — {n_genes_tested} genes tested")
    log(f"  Total (agg + DE): {total_time:.1f}s")
    ram_report()

    return {
        "time": total_time,
        "time_aggregation": agg_time,
        "time_de": de_time,
        "method": "pseudobulk_wilcoxon",
        "backend": "cpu",
        "n_pseudobulk_samples": len(pb_data),
        "n_donors": len(donors),
        "n_clusters": len(clusters),
    }


def test_ttest_scatter_clean(adata: sc.AnnData, n_gpus: int) -> dict:
    """Test 7: t-test scatter + aggressive GPU cleanup between rounds.

    Like test 5, but explicitly frees ALL GPU memory pools between
    each round of chunks across GPUs.
    """
    import cupy as cp
    import pynvml

    pynvml.nvmlInit()
    log(f"=== TEST 7: t-test scatter + cleanup ({n_gpus} GPUs) ===")

    raw_X = adata.raw.X
    if not sp.issparse(raw_X):
        raw_X = sp.csr_matrix(raw_X)
    gene_names = np.array(adata.raw.var_names)
    labels = np.array(adata.obs["leiden_1.0"].values, dtype=str)
    groups = sorted(np.unique(labels), key=lambda x: int(x))
    n_genes = raw_X.shape[1]

    log("Converting to CSC...")
    raw_csc = raw_X.tocsc()

    gene_chunks = []
    for start in range(0, n_genes, GENE_CHUNK_SIZE):
        end = min(start + GENE_CHUNK_SIZE, n_genes)
        gene_chunks.append((start, end))

    log(f"Gene chunks: {len(gene_chunks)} of ~{GENE_CHUNK_SIZE}")
    vram_report(n_gpus)

    t0 = time.time()
    all_results = []

    # Process in rounds of n_gpus chunks
    for round_start in range(0, len(gene_chunks), n_gpus):
        round_end = min(round_start + n_gpus, len(gene_chunks))
        round_chunks = gene_chunks[round_start:round_end]

        # Process this round across GPUs
        for gi, (start, end) in enumerate(round_chunks):
            gpu_id = gi
            chunk_genes = gene_names[start:end]
            X_slice = raw_csc[:, start:end].toarray().astype(np.float32)

            with cp.cuda.Device(gpu_id):
                X_gpu = cp.asarray(X_slice)
                result = _gpu_ttest_chunk(X_gpu, labels, groups, chunk_genes)
                all_results.append(result)
                del X_gpu

        # Aggressive cleanup after each round
        for i in range(n_gpus):
            with cp.cuda.Device(i):
                cp.get_default_memory_pool().free_all_blocks()
        gc.collect()

        log(f"  Round {round_start//n_gpus + 1}/{(len(gene_chunks) + n_gpus - 1)//n_gpus} done")

    elapsed = time.time() - t0
    merged = _merge_de_results(all_results)

    log(f"Done in {elapsed:.1f}s — {n_genes} genes, {n_gpus} GPUs, with cleanup")
    vram_report(n_gpus)
    pynvml.nvmlShutdown()

    return {"time": elapsed, "method": "ttest", "backend": f"scatter_clean_{n_gpus}gpu"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ALL_TESTS = [
    "wilcoxon_cpu",
    "ttest_cpu",
    "pseudobulk",
    "wilcoxon_scatter",
    "wilcoxon_chunk",
    "ttest_scatter",
    "ttest_chunk",
    "ttest_scatter_clean",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Factorial benchmark of DE methods at scale.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Tests (run one at a time, or 'all'):
  {chr(10).join(f'  {i+1}. {t}' for i, t in enumerate(ALL_TESTS))}

Examples:
  python scripts/test_de_benchmark.py --data-dir data/ --target-cells 3400000 --test ttest_cpu
  python scripts/test_de_benchmark.py --data-dir data/ --target-cells 3400000 --test all
        """,
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Directory containing brain_full_*.h5ad",
    )
    parser.add_argument(
        "--target-cells", type=int, required=True,
        help="Number of cells to test with",
    )
    parser.add_argument(
        "--n-gpus", type=int, default=8,
        help="Number of GPUs for scatter tests (default: 8)",
    )
    parser.add_argument(
        "--test", type=str, required=True,
        choices=ALL_TESTS + ["all"],
        help="Which test to run (or 'all' for all tests sequentially)",
    )
    parser.add_argument(
        "--gene-chunk-size", type=int, default=GENE_CHUNK_SIZE,
        help=f"Genes per chunk for scatter/chunk tests (default: {GENE_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--preprocessed", type=str, default=None,
        help="Path to preprocessed h5ad (skip preprocessing). "
             "Use --save-preprocessed to create it first.",
    )
    parser.add_argument(
        "--save-preprocessed", type=str, default=None,
        help="After preprocessing, save adata to this path and continue.",
    )
    return parser.parse_args()


def run_test(test_name: str, adata: sc.AnnData, n_gpus: int) -> dict:
    """Run a single DE test.

    Args:
        test_name: Name of the test.
        adata: Preprocessed AnnData with clusters + raw.
        n_gpus: Number of GPUs.

    Returns:
        Result dict with timing info.
    """
    test_funcs = {
        "wilcoxon_cpu": lambda: test_wilcoxon_cpu(adata),
        "ttest_cpu": lambda: test_ttest_cpu(adata),
        "pseudobulk": lambda: test_pseudobulk(adata),
        "wilcoxon_scatter": lambda: test_wilcoxon_scatter(adata, n_gpus),
        "wilcoxon_chunk": lambda: test_wilcoxon_chunk(adata),
        "ttest_scatter": lambda: test_ttest_scatter(adata, n_gpus),
        "ttest_chunk": lambda: test_ttest_chunk(adata),
        "ttest_scatter_clean": lambda: test_ttest_scatter_clean(adata, n_gpus),
    }

    if test_name not in test_funcs:
        log(f"Unknown test: {test_name}")
        return {"error": f"unknown test {test_name}"}

    try:
        return test_funcs[test_name]()
    except Exception as e:
        log(f"FAILED [{test_name}]: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "time": -1}


def main() -> None:
    """Main entry point."""
    global _T0, GENE_CHUNK_SIZE
    _T0 = time.time()

    args = parse_args()
    GENE_CHUNK_SIZE = args.gene_chunk_size
    sc.settings.verbosity = 0

    log(f"DE Benchmark | Cells: {args.target_cells:,} | GPUs: {args.n_gpus}")
    log(f"Gene chunk size: {GENE_CHUNK_SIZE}")

    # Load preprocessed or preprocess from scratch
    if args.preprocessed:
        log(f"Loading preprocessed adata from {args.preprocessed}...")
        t0 = time.time()
        adata = sc.read_h5ad(args.preprocessed)
        log(f"Loaded in {time.time()-t0:.0f}s: {adata.n_obs:,} x {adata.n_vars:,}, "
            f"raw: {adata.raw.n_vars:,} genes, "
            f"clusters: {adata.obs['leiden_1.0'].nunique()}")
        ram_report()
    else:
        adata = prepare_adata(args.data_dir, args.target_cells)

        if args.save_preprocessed:
            log(f"Saving preprocessed adata to {args.save_preprocessed}...")
            t0 = time.time()
            adata.write_h5ad(args.save_preprocessed)
            log(f"Saved in {time.time()-t0:.0f}s")

    # Raw data info
    raw_X = adata.raw.X
    if sp.issparse(raw_X):
        raw_bytes = raw_X.data.nbytes + raw_X.indices.nbytes + raw_X.indptr.nbytes
        log(f"raw.X: {raw_X.shape}, nnz={raw_X.nnz:,}, {raw_bytes/(1024**3):.1f} GB sparse")
    else:
        log(f"raw.X: {raw_X.shape}, {raw_X.nbytes/(1024**3):.1f} GB dense")

    # Run tests
    tests_to_run = ALL_TESTS if args.test == "all" else [args.test]
    results = {}

    for test_name in tests_to_run:
        log(f"\n{'='*60}")
        result = run_test(test_name, adata, args.n_gpus)
        results[test_name] = result
        log(f"{'='*60}\n")

        # Clean up between tests
        gc.collect()

    # Summary table
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"{'Test':<25s} | {'Time':>10s} | {'Method':>10s} | {'Backend':>20s}")
    log(f"{'-'*25}-+-{'-'*10}-+-{'-'*10}-+-{'-'*20}")
    for name, res in results.items():
        t = res.get("time", -1)
        t_str = f"{t:.1f}s" if t >= 0 else "FAIL"
        method = res.get("method", "?")
        backend = res.get("backend", "?")
        log(f"{name:<25s} | {t_str:>10s} | {method:>10s} | {backend:>20s}")

    # Save results
    import json
    from pathlib import Path

    # Save results — one file per test to avoid overwriting
    out_dir = Path(args.data_dir).parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    test_label = args.test  # e.g. "ttest_cpu" or "all"
    out_path = out_dir / f"de_benchmark_{test_label}.json"
    with open(out_path, "w") as f:
        json.dump({
            "n_cells": adata.n_obs,
            "n_genes_raw": adata.raw.n_vars,
            "n_clusters": adata.obs["leiden_1.0"].nunique(),
            "gene_chunk_size": GENE_CHUNK_SIZE,
            "n_gpus": args.n_gpus,
            "results": {k: {kk: vv for kk, vv in v.items() if kk != "error"} for k, v in results.items()},
        }, f, indent=2, default=str)
    log(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
