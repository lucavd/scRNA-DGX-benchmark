#!/usr/bin/env python3
"""S1 anomaly check: does the GPU co-occurrence at Visium HD 8 um break where pair
counts exceed the int32 range? Counts bin pairs within each Squidpy distance
threshold (same thresholds as sq.gr.co_occurrence, interval=50) with a KD-tree,
and prints the rapids-singlecell co_occurrence source lines that declare counters.
"""
import inspect
import json
import sys

import numpy as np
import pandas as pd
import scanpy as sc
from scipy.spatial import cKDTree

sys.path.insert(0, "SPATIAL/scripts")
import benchmark_spatial_cpu as b  # noqa: E402  (same loader as the benchmark)

adata = b.load_visium_hd(__import__("pathlib").Path("SPATIAL/data"), "square_008um")
sc.pp.filter_cells(adata, min_genes=1)
xy = adata.obsm["spatial"]
from squidpy.gr._ppatterns import _find_min_max  # noqa: E402
tmin, tmax = _find_min_max(xy)
thr = np.linspace(tmin, tmax, num=50)
tree = cKDTree(xy)
cum = tree.count_neighbors(tree, thr)  # ordered pairs incl. self, cumulative
import rapids_singlecell.squidpy_gpu._co_oc as co  # noqa: E402
src = inspect.getsource(co)
lines = [l.strip() for l in src.splitlines() if any(k in l for k in ("int32", "uint32", "int64", "dtype", "atomicAdd", "unsigned"))]
out = {"n_obs": int(adata.n_obs), "thresholds": thr.tolist(), "ordered_pairs_within": [int(x) for x in cum],
       "int32_max": 2**31 - 1, "uint32_max": 2**32 - 1,
       "first_threshold_index_over_int32": int(np.argmax(cum > 2**31 - 1)) if (cum > 2**31 - 1).any() else None,
       "first_threshold_index_over_uint32": int(np.argmax(cum > 2**32 - 1)) if (cum > 2**32 - 1).any() else None,
       "rsc_source_file": co.__file__, "rsc_counter_lines": lines[:60]}
print(json.dumps(out, indent=1))
