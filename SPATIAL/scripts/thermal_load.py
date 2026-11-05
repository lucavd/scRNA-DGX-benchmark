#!/usr/bin/env python3
"""Sustained all-core numba load for the thermal test (LNBI S1). Not a benchmark."""
import argparse
import os
import time

ap = argparse.ArgumentParser()
ap.add_argument("--n-threads", type=int, required=True)
ap.add_argument("--seconds", type=int, default=600)
a = ap.parse_args()
os.environ["NUMBA_NUM_THREADS"] = str(a.n_threads)

import numba  # noqa: E402
import numpy as np  # noqa: E402


@numba.njit(parallel=True, fastmath=False)
def burn(x, it):
    out = np.empty_like(x)
    for i in numba.prange(x.shape[0]):
        v = x[i]
        for _ in range(it):
            v = np.sin(v) * 1.0000001 + np.cos(v) * 0.9999999
        out[i] = v
    return out


numba.set_num_threads(a.n_threads)
x = np.random.default_rng(1).random(a.n_threads * 64)
t_end = time.time() + a.seconds
n = 0
while time.time() < t_end:
    t0 = time.perf_counter()
    burn(x, 200_000)
    n += 1
    print(f"batch {n} {time.time():.2f} {time.perf_counter() - t0:.4f} threads={numba.get_num_threads()}", flush=True)
