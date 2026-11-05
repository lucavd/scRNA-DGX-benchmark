#!/usr/bin/env python3
"""Prepare the PCA input of the neighbour step exactly as scripts/benchmark_cpu.py
(QC, normalize_total 1e4, log1p, HVG default flavor 2000, subset, dense scale
max_value 10, PCA 50 comps seed 42) and save X_pca. Not timed.
Usage: python -B tools/s2_neighbors_prep.py --size 10000 --out results_v2/S2/neighbors [--data-dir data]"""
import os, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--size", type=int); ap.add_argument("--out"); ap.add_argument("--data-dir", default="data"); a = ap.parse_args()
import json, hashlib, warnings, numpy as np, scanpy as sc
ad = sc.read_h5ad(os.path.join(a.data_dir, f"brain_{a.size}.h5ad"))
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ad.var["mt"] = ad.var_names.str.startswith(("MT-", "mt-"))
    sc.pp.calculate_qc_metrics(ad, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)
    ad.obs = ad.obs.copy(); ad.var = ad.var.copy()
    sc.pp.filter_cells(ad, min_genes=200); sc.pp.filter_genes(ad, min_cells=3)
nq, gq = int(ad.n_obs), int(ad.n_vars)
sc.pp.normalize_total(ad, target_sum=1e4); sc.pp.log1p(ad)
sc.pp.highly_variable_genes(ad, n_top_genes=2000)
ad = ad[:, ad.var["highly_variable"]].copy()
ad.X = ad.X.toarray() if hasattr(ad.X, "toarray") else ad.X
sc.pp.scale(ad, max_value=10); sc.tl.pca(ad, n_comps=50, random_state=42)
os.makedirs(a.out, exist_ok=True)
p = os.path.join(a.out, f"pca_{a.size}.npy"); np.save(p, ad.obsm["X_pca"].astype(np.float32))
json.dump({"size": a.size, "n_cells_after_qc": nq, "n_genes_after_qc": gq, "pca_shape": list(ad.obsm["X_pca"].shape),
           "pca_md5": hashlib.md5(open(p, "rb").read()).hexdigest(), "scanpy": sc.__version__},
          open(os.path.join(a.out, f"prep_{a.size}.json"), "w"), indent=1)
print(nq, gq)
