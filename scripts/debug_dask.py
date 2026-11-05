#!/usr/bin/env python3
"""Minimal Dask-CUDA debug: inspect CPU/GPU affinity and worker startup."""
import logging
import math
import os
import socket
import time
import traceback


def _format_cpu_list(cpus: list[int]) -> str:
    if not cpus:
        return "none"
    if len(cpus) <= 16:
        return ",".join(str(cpu) for cpu in cpus)
    return f"{cpus[0]}-{cpus[-1]} ({len(cpus)} CPUs)"


def _get_allowed_cpus() -> list[int]:
    if hasattr(os, "sched_getaffinity"):
        return sorted(os.sched_getaffinity(0))
    cpu_count = os.cpu_count() or 0
    return list(range(cpu_count))


def _gpu_cpu_affinity(handle, cpu_count: int) -> list[int]:
    word_count = max(1, math.ceil(max(cpu_count, 1) / 64))
    bitmasks = pynvml.nvmlDeviceGetCpuAffinity(handle, word_count)
    cpus: list[int] = []
    for word_index, bitmask in enumerate(bitmasks):
        value = int(bitmask)
        for bit in range(64):
            if value & (1 << bit):
                cpu = word_index * 64 + bit
                if cpu < cpu_count:
                    cpus.append(cpu)
    return cpus


def _print_environment() -> list[int]:
    print(f"Host: {socket.gethostname()} | PID: {os.getpid()}")
    for key in ("SLURM_PROCID", "SLURM_LOCALID", "SLURM_NTASKS", "SLURM_STEP_NUM_TASKS"):
        print(f"{key}: {os.environ.get(key, 'not set')}")
    print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'not set')}")
    print(f"CUDA_DEVICE_ORDER: {os.environ.get('CUDA_DEVICE_ORDER', 'not set')}")
    for key in (
        "SLURM_CPUS_ON_NODE",
        "SLURM_CPUS_PER_TASK",
        "SLURM_JOB_CPUS_PER_NODE",
        "SLURM_CPU_BIND",
        "SLURM_MEM_PER_NODE",
    ):
        print(f"{key}: {os.environ.get(key, 'not set')}")
    allowed_cpus = _get_allowed_cpus()
    print(f"os.cpu_count(): {os.cpu_count()}")
    print(f"Process allowed CPUs: {_format_cpu_list(allowed_cpus)}")
    return allowed_cpus


def _print_gpu_info(allowed_cpus: list[int]) -> int:
    n_gpus = pynvml.nvmlDeviceGetCount()
    cpu_count = os.cpu_count() or len(allowed_cpus) or 1
    allowed_cpu_set = set(allowed_cpus)
    for i in range(n_gpus):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        affinity_cpus = _gpu_cpu_affinity(handle, cpu_count)
        overlap = sorted(set(affinity_cpus) & allowed_cpu_set)
        print(f"  GPU {i}: {name}, {mem.used/1e9:.1f}/{mem.total/1e9:.1f} GB used")
        print(
            f"    GPU {i} CPU affinity: {_format_cpu_list(affinity_cpus)} | "
            f"overlap with job CPUs: {_format_cpu_list(overlap)}"
        )
    return n_gpus


def _get_scheduler_worker_state(client) -> dict:
    def _inspect_scheduler(dask_scheduler):
        workers = {}
        for addr, worker_state in dask_scheduler.workers.items():
            workers[addr] = {
                "name": str(getattr(worker_state, "name", "?")),
                "status": str(getattr(worker_state, "status", "?")),
            }

        summary = {"workers": workers}
        for attr in ("running", "idle", "saturated"):
            worker_set = getattr(dask_scheduler, attr, None)
            if worker_set is None:
                continue
            summary[f"{attr}_workers"] = sorted(
                str(getattr(worker_state, "address", worker_state))
                for worker_state in worker_set
            )
        return summary

    return client.run_on_scheduler(_inspect_scheduler)


def _try_cluster(label: str, n_gpus: int, **cluster_kwargs) -> bool:
    print(f"\nTrying LocalCUDACluster [{label}] with {n_gpus} GPUs...")
    print(f"Cluster kwargs: {cluster_kwargs}")

    from dask_cuda import LocalCUDACluster
    from dask.distributed import Client

    device_list = ",".join(str(i) for i in range(n_gpus))
    cluster = None
    client = None
    try:
        cluster = LocalCUDACluster(
            CUDA_VISIBLE_DEVICES=device_list,
            n_workers=n_gpus,
            silence_logs=False,
            **cluster_kwargs,
        )
        client = Client(cluster)

        stable_checks = 0
        for t in range(30):
            client_workers = client.scheduler_info()["workers"]
            scheduler_state = _get_scheduler_worker_state(client)
            scheduler_workers = scheduler_state["workers"]
            client_names = sorted(str(worker.get("name", "?")) for worker in client_workers.values())
            scheduler_names = sorted(
                worker["name"] for worker in scheduler_workers.values()
            )
            running_workers = scheduler_state.get("running_workers", [])
            n_workers = len(client_workers)
            if t % 5 == 0 or n_workers == n_gpus:
                print(
                    f"  t={t:2d}s: client={len(client_workers)} workers {client_names} | "
                    f"scheduler={len(scheduler_workers)} workers {scheduler_names} | "
                    f"running={len(running_workers)}"
                )
            if len(client_workers) == n_gpus and len(scheduler_workers) == n_gpus:
                stable_checks += 1
                if stable_checks >= 3:
                    break
            else:
                stable_checks = 0
            time.sleep(1)

        client_workers = client.scheduler_info()["workers"]
        scheduler_state = _get_scheduler_worker_state(client)
        scheduler_workers = scheduler_state["workers"]
        running_workers = scheduler_state.get("running_workers", [])
        print(
            f"\nFinal [{label}]: client={len(client_workers)} / {n_gpus}, "
            f"scheduler={len(scheduler_workers)} / {n_gpus}, "
            f"running={len(running_workers)} / {n_gpus}"
        )
        print("  Client-visible workers:")
        for addr in sorted(client_workers):
            worker = client_workers[addr]
            print(f"    {addr}: name={worker.get('name', '?')}")
        print("  Scheduler workers:")
        for addr in sorted(scheduler_workers):
            worker = scheduler_workers[addr]
            print(
                f"    {addr}: name={worker.get('name', '?')} "
                f"status={worker.get('status', '?')}"
            )
        print(f"  Scheduler running workers: {running_workers}")
        return len(client_workers) == n_gpus and len(scheduler_workers) == n_gpus
    except Exception as exc:
        print(f"\nCluster [{label}] failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return False
    finally:
        if client is not None:
            client.close()
        if cluster is not None:
            cluster.close()
        for i in range(n_gpus):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            print(f"  GPU {i}: {mem.used/1e9:.1f} GB used")


def main():
    os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    logging.basicConfig(level=logging.INFO)

    global pynvml
    import pynvml

    pynvml.nvmlInit()
    try:
        allowed_cpus = _print_environment()
        n_gpus = _print_gpu_info(allowed_cpus)

        variants = [
            (
                "baseline_rmm_pool",
                {
                    "rmm_pool_size": "10GB",
                    "rmm_maximum_pool_size": "70GB",
                },
            ),
            (
                "no_rmm_pool",
                {},
            ),
        ]

        for label, kwargs in variants:
            if _try_cluster(label, n_gpus, **kwargs):
                break
    finally:
        pynvml.nvmlShutdown()

    print("\nDone.")


if __name__ == "__main__":
    main()
