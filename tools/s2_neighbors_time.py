#!/usr/bin/env python3
"""One repetition in a fresh process: time sc.pp.neighbors (k=15, 50 PCs, seed 42)
on the saved PCA, first call (cold, includes JIT) and second call (warm), with
sc.settings.n_jobs = N. Thread variables = 100 before imports, as the benchmark.
Usage: python -B tools/s2_neighbors_time.py --size 10000 --njobs 1 --rep 1 --out DIR"""
import os, sys, argparse
for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"): os.environ[v] = "100"
ap = argparse.ArgumentParser(); ap.add_argument("--size", type=int); ap.add_argument("--njobs", type=int)
ap.add_argument("--rep", type=int); ap.add_argument("--out"); a = ap.parse_args()
import json, time, hashlib, numpy as np, scanpy as sc, anndata as ad, numba
calls = []; orig = numba.set_num_threads
def spy(n): calls.append(int(n)); return orig(n)
numba.set_num_threads = spy
sc.settings.n_jobs = a.njobs
X = np.load(os.path.join(a.out, f"pca_{a.size}.npy"))
start_threads = numba.get_num_threads()
res = {}
for phase in ("cold", "warm"):
    A = ad.AnnData(np.zeros((X.shape[0], 1), dtype=np.float32)); A.obsm["X_pca"] = X.copy()
    calls.clear(); t0 = time.perf_counter()
    sc.pp.neighbors(A, n_neighbors=15, n_pcs=50, random_state=42, use_rep="X_pca")
    t = time.perf_counter() - t0
    idx = A.obsp["distances"].indices
    res[phase] = {"seconds": t, "set_num_threads_calls": list(calls), "threads_after": numba.get_num_threads(),
                  "knn_md5": hashlib.md5(np.ascontiguousarray(idx).tobytes()).hexdigest()}
out = {"size": a.size, "n_jobs": a.njobs, "rep": a.rep, "numba_threads_at_start": start_threads,
       "affinity": len(os.sched_getaffinity(0)), "versions": {"scanpy": sc.__version__, "numba": numba.__version__,
       "pynndescent": __import__("pynndescent").__version__}, **res}
json.dump(out, open(os.path.join(a.out, f"nb_{a.size}_nj{a.njobs}_r{a.rep}.json"), "w"), indent=1)
print(a.size, a.njobs, a.rep, round(res["cold"]["seconds"], 3), round(res["warm"]["seconds"], 3), res["warm"]["set_num_threads_calls"])
