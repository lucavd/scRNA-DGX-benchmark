#!/usr/bin/env python3
"""S1 co-occurrence check (PI decision D-13): GPU co-occurrence alone, same groups
as the CPU reference, one repetition per process. Run with the original image
(rapids-singlecell 0.14.1) and with the derived image (0.15.1).

Same preconditions as benchmark_spatial_gpu.py: RMM pool, GPU warmup, loading,
GPU QC filtering, then the groups from --labels-from and the timed
rsc.gr.co_occurrence on the CPU-resident AnnData. Compares the result with the
CPU reference matrix (--cpu-ref).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark_spatial_gpu as g  # noqa: E402
import spatial_run_meta as srm  # noqa: E402
import numpy as np  # noqa: E402
import cupy as cp  # noqa: E402
import rapids_singlecell as rsc  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data-dir", required=True)
ap.add_argument("--platform", required=True, choices=["visium", "visium_hd"])
ap.add_argument("--bin-size", default="square_008um")
ap.add_argument("--labels-from", required=True)
ap.add_argument("--cpu-ref", required=True)
ap.add_argument("--output-dir", required=True)
ap.add_argument("--repeat-id", type=int, required=True)
a = ap.parse_args()
out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)
g.sc.settings.verbosity = 0
g.init_nvml()
host_start = srm.host_snapshot()
rmm_cfg = g.init_rmm_pool(0)
gpu_info = g.get_gpu_info(0)
g.gpu_warmup()
data_dir = Path(a.data_dir)
adata = g.load_visium(data_dir) if a.platform == "visium" else g.load_visium_hd(data_dir, a.bin_size)
g.rsc.get.anndata_to_GPU(adata)
min_genes = 1 if a.platform == "visium_hd" else 200
rsc.pp.filter_cells(adata, min_genes=min_genes)
rsc.pp.filter_genes(adata, min_cells=3)
rsc.get.anndata_to_CPU(adata)
groups, ginfo = srm.load_groups(a.labels_from, adata.obs_names)
adata.obs["spatial_groups"] = groups
timings, memory = {}, {}
g.time_step("co_occurrence", lambda: rsc.gr.co_occurrence(adata, cluster_key="spatial_groups"), timings, memory, 0)
occ = np.asarray(adata.uns["spatial_groups_co_occurrence"]["occ"])
ref = np.load(a.cpu_ref)
tag = f"{a.platform}" + ("" if a.platform == "visium" else f"_{a.bin_size}")
np.save(out / f"cooc_gpu_{tag}_r{a.repeat_id}.npy", occ)
same_shape = occ.shape == ref.shape
eq = [bool(np.allclose(occ[:, :, k], ref[:, :, k], atol=1e-3, rtol=0)) for k in range(ref.shape[2])] if same_shape else []
res = {
    "platform": tag, "repeat_id": a.repeat_id, "timestamp": datetime.now(timezone.utc).isoformat(),
    "rapids_singlecell": None,
    "timings": timings, "memory": memory, "groups": ginfo, "gpu_info": gpu_info, "rmm": rmm_cfg,
    "system": srm.system_info(None), "host_start": host_start, "host_end": srm.host_snapshot(),
    "comparison_with_cpu": {
        "same_shape": same_shape, "shape_gpu": list(occ.shape), "shape_cpu": list(ref.shape),
        "max_abs_diff": float(np.nanmax(np.abs(occ - ref))) if same_shape else None,
        "spearman_rho": float(spearmanr(occ.ravel(), ref.ravel())[0]) if same_shape else None,
        "n_intervals": int(ref.shape[2]), "n_intervals_equal_atol_1e-3": int(sum(eq)),
        "first_unequal_interval": (eq.index(False) if False in eq else None),
    },
}
for name in ("rapids-singlecell", "rapids-singlecell-cu12"):
    try:
        res["rapids_singlecell"] = {"dist": name, "version": pkg_version(name)}
        break
    except Exception:
        continue
(out / f"cooc_gpu_{tag}_r{a.repeat_id}.json").write_text(json.dumps(res, indent=2, default=str))
print(json.dumps({"t": timings["co_occurrence"], **res["comparison_with_cpu"], "rsc": res["rapids_singlecell"]}))
g.shutdown_nvml()
