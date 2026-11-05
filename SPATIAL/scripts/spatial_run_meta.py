"""Run provenance for the spatial benchmark rerun (LNBI chapter, step S1).

Imported by benchmark_spatial_cpu.py and benchmark_spatial_gpu.py. Every
function here runs OUTSIDE the timed region of a pipeline step.
"""

from __future__ import annotations

import glob
import hashlib
import os
import platform as _platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _read(path: str) -> str | None:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def cpu_temperature_c() -> dict:
    """CPU temperature from hwmon: AMD k10temp Tctl or Intel coretemp package max."""
    out: dict = {}
    for d in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = _read(f"{d}/name")
        if name == "k10temp":
            for inp in sorted(glob.glob(f"{d}/temp*_input")):
                label = _read(inp.replace("_input", "_label")) or Path(inp).stem
                if label == "Tctl":
                    out["Tctl"] = int(_read(inp)) / 1000.0
        elif name == "coretemp":
            vals = []
            for inp in sorted(glob.glob(f"{d}/temp*_input")):
                label = _read(inp.replace("_input", "_label")) or ""
                if label.startswith("Package id"):
                    vals.append(int(_read(inp)) / 1000.0)
            if vals:
                out.setdefault("package_max", [])
                out["package_max"].append(max(vals))
    if "package_max" in out:
        out["package_max"] = max(out["package_max"])
    return out


def host_snapshot() -> dict:
    """Load average and CPU temperature at this instant (host-wide values)."""
    la = (_read("/proc/loadavg") or "").split()
    return {
        "utc": datetime.now(timezone.utc).isoformat(),
        "loadavg_1_5_15": [float(x) for x in la[:3]] if len(la) >= 3 else None,
        "cpu_temp_c": cpu_temperature_c(),
    }


def thread_snapshot() -> dict:
    """numba threads and threadpoolctl view (threads per native library)."""
    snap: dict = {}
    try:
        import numba

        snap["numba_num_threads"] = int(numba.get_num_threads())
        snap["numba_config_num_threads"] = int(numba.config.NUMBA_NUM_THREADS)
    except Exception as exc:  # pragma: no cover
        snap["numba_error"] = repr(exc)
    try:
        from threadpoolctl import threadpool_info

        snap["threadpools"] = [
            {
                "user_api": p.get("user_api"),
                "internal_api": p.get("internal_api"),
                "prefix": p.get("prefix"),
                "num_threads": p.get("num_threads"),
            }
            for p in threadpool_info()
        ]
    except Exception as exc:  # pragma: no cover
        snap["threadpoolctl_error"] = repr(exc)
    return snap


def system_info(requested_cpus: int | None) -> dict:
    """Machine, container and code provenance for the result JSON."""
    model = None
    cpuinfo = _read("/proc/cpuinfo") or ""
    for line in cpuinfo.splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break
    try:
        affinity = sorted(os.sched_getaffinity(0))
    except AttributeError:  # pragma: no cover
        affinity = []
    gpu = None
    try:
        import pynvml

        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(h)
        drv = pynvml.nvmlSystemGetDriverVersion()
        gpu = {
            "gpu_name": name if isinstance(name, str) else name.decode(),
            "driver_version": drv if isinstance(drv, str) else drv.decode(),
        }
    except Exception as exc:
        gpu = {"unavailable": type(exc).__name__}
    env_keys = [
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMBA_NUM_THREADS", "SLURM_JOB_ID", "SLURM_STEP_ID",
        "SLURM_CPUS_PER_TASK", "SLURM_JOB_NODELIST",
        "LNBI_GIT_COMMIT", "LNBI_IMAGE_ID", "LNBI_RUN_ID", "LNBI_MACHINE_ROLE",
    ]
    return {
        "hostname": os.environ.get("LNBI_HOST_HOSTNAME") or socket.gethostname(),
        "container_hostname": socket.gethostname(),
        "os_cpu_count": os.cpu_count(),
        "affinity_n_cpus": len(affinity),
        "affinity_cpus": affinity,
        "requested_cpus": requested_cpus,
        "cpu_model": model,
        "kernel": _platform.release(),
        "gpu": gpu,
        "env": {k: os.environ.get(k) for k in env_keys},
        "git_commit": os.environ.get("LNBI_GIT_COMMIT"),
        "image_id": os.environ.get("LNBI_IMAGE_ID"),
    }


def md5_of_file(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_groups(path: str | Path, obs_names: pd.Index) -> tuple[pd.Categorical, dict]:
    """Read group labels (barcode index, one label column) aligned to obs_names.

    Fails if any observation of the current AnnData has no label: CPU and GPU
    must run the spatial steps on exactly the same groups.
    """
    df = pd.read_csv(path, index_col=0)
    col = df.columns[0]
    lab = df[col].astype(str)
    missing = obs_names.difference(lab.index)
    if len(missing) > 0:
        raise ValueError(
            f"{len(missing)} of {len(obs_names)} observations have no label in {path}"
        )
    vals = lab.loc[obs_names].to_numpy()
    uniq = pd.unique(lab.to_numpy())
    try:
        cats = sorted(uniq, key=lambda x: int(x))
    except ValueError:
        cats = sorted(uniq)
    used = pd.unique(vals)
    cats_used = [c for c in cats if c in set(used)]
    groups = pd.Categorical(vals, categories=cats_used)
    info = {
        "labels_file": str(path),
        "labels_md5": md5_of_file(path),
        "labels_column": col,
        "n_labels_in_file": int(len(lab)),
        "n_obs_labelled": int(len(obs_names)),
        "n_groups_used": int(len(cats_used)),
    }
    return groups, info


class StepRecorder:
    """Thread and host state at the start and end of each timed step."""

    def __init__(self) -> None:
        self.steps: dict = {}

    def before(self, name: str) -> None:
        self.steps[name] = {"start": {**thread_snapshot(), **host_snapshot()}}

    def after(self, name: str) -> None:
        self.steps.setdefault(name, {})["end"] = {
            "numba_num_threads": thread_snapshot().get("numba_num_threads"),
            **host_snapshot(),
        }
