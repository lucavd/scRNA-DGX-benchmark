#!/usr/bin/env python3
"""Mechanism check for the CPU slowdown after repetition 1 (LNBI S1, brief item 6).

Runs the ORIGINAL March CPU script (benchmark_spatial_cpu_orig.py, identical to
SPATIAL/scripts/benchmark_spatial_cpu.py at main) on Visium v1 with two
repetitions in the same process, and records numba.get_num_threads() before and
after every Squidpy/Scanpy call that can touch numba. Timings are not used.

Usage (inside the container):
    python mechanism_numba_threads.py --data-dir D --output-dir O --n-cpus N
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--data-dir", required=True)
ap.add_argument("--output-dir", required=True)
ap.add_argument("--n-cpus", type=int, required=True)
a = ap.parse_args()
out = Path(a.output_dir)
out.mkdir(parents=True, exist_ok=True)

# The original script configures thread env vars from sys.argv at import time.
sys.argv = [
    "benchmark_spatial_cpu_orig.py", "--data-dir", a.data_dir,
    "--output-dir", str(out / "orig_outputs"), "--platform", "visium",
    "--n-repeats", "2", "--n-cpus", str(a.n_cpus),
]
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("orig", here / "benchmark_spatial_cpu_orig.py")
orig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orig)

import numba  # noqa: E402

log = []
state = {"repeat": 0}


def wrap(owner, attr, label):
    fn = getattr(owner, attr)

    def wrapped(*args, **kwargs):
        before = numba.get_num_threads()
        res = fn(*args, **kwargs)
        after = numba.get_num_threads()
        log.append({"repeat": state["repeat"], "call": label,
                    "numba_threads_before": before, "numba_threads_after": after})
        print(f"  [mechanism] repeat {state['repeat']} {label}: numba threads {before} -> {after}")
        return res

    setattr(owner, attr, wrapped)


wrap(orig.sc.pp, "neighbors", "sc.pp.neighbors")
wrap(orig.sc.tl, "umap", "sc.tl.umap")
wrap(orig.sq.gr, "spatial_neighbors", "sq.gr.spatial_neighbors")
wrap(orig.sq.gr, "spatial_autocorr", "sq.gr.spatial_autocorr")
wrap(orig.sq.gr, "co_occurrence", "sq.gr.co_occurrence")
wrap(orig.sq.gr, "nhood_enrichment", "sq.gr.nhood_enrichment")
wrap(orig.sq.gr, "ligrec", "sq.gr.ligrec")

_run = orig.run_pipeline


def run_counted(*args, **kwargs):
    state["repeat"] += 1
    log.append({"repeat": state["repeat"], "call": "repeat_start",
                "numba_threads_before": numba.get_num_threads(),
                "numba_threads_after": numba.get_num_threads()})
    return _run(*args, **kwargs)


orig.run_pipeline = run_counted
orig.main()

drop = [r for r in log if r["call"] != "repeat_start"
        and r["numba_threads_after"] < r["numba_threads_before"]]
summary = {
    "n_cpus_requested": a.n_cpus,
    "numba_config_num_threads": int(numba.config.NUMBA_NUM_THREADS),
    "calls": log,
    "calls_that_lowered_threads": drop,
    "threads_at_start_of_repeat_2": next(
        (r["numba_threads_before"] for r in log
         if r["repeat"] == 2 and r["call"] == "repeat_start"), None),
    "mechanism_confirmed": any(r["call"] == "sq.gr.nhood_enrichment" for r in drop),
}
(out / "mechanism_numba_threads.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "calls"}, indent=2))
