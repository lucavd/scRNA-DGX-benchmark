#!/bin/bash
#SBATCH --job-name=chunked_single
#SBATCH --partition=dgx12cluster
#SBATCH --account=dctv_dgx
#SBATCH --output=/home/u0044/sc-gpu-benchmark/logs/slurm-%x_%j.out
#SBATCH --error=/home/u0044/sc-gpu-benchmark/logs/slurm-%x_%j.err
#SBATCH --export=NONE
#SBATCH --chdir=/home/u0044
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=200
#SBATCH --mem=1800G
#SBATCH --gres=gpu:8
#SBATCH --time=24:00:00
#SBATCH --nodelist=poddgx02
#SBATCH --no-requeue

# ============================================================
# Single-target chunked benchmark. No find-limit loop.
# If OOM-killed, only THIS job dies. No restart.
#
# Usage:
#   TARGET=15000000 sbatch slurm/maxpower_chunked_single.sh
#   TARGET=18000000 sbatch slurm/maxpower_chunked_single.sh
#   TARGET=20000000 sbatch slurm/maxpower_chunked_single.sh
# ============================================================

TARGET=${TARGET:-15000000}

# Load required modules
module load go/1.22.7
module load singularity/4.2.0
module load slurm/slurm/23.02.7

# Detect workdir
if [ -d /mnt/home/u0044/sc-gpu-benchmark ]; then
    WORKDIR=/mnt/home/u0044/sc-gpu-benchmark
elif [ -d /home/u0044/sc-gpu-benchmark ]; then
    WORKDIR=/home/u0044/sc-gpu-benchmark
else
    echo "FAILED: sc-gpu-benchmark not found"; exit 1
fi

CONTAINER=${WORKDIR}/sc-benchmark.sif
SINGULARITY=/cm/shared/apps/singularity/4.2.0/bin/singularity
BIND_ARGS=(-B /home/u0044:/home/u0044)
[ -d /mnt/home/u0044 ] && BIND_ARGS+=(-B /mnt/home/u0044:/mnt/home/u0044)

run_in_container() {
    "${SINGULARITY}" exec --nv "${BIND_ARGS[@]}" "${CONTAINER}" "$@"
}

CONTAINER_PYTHON=$(run_in_container bash -lc 'for py in python python3 /opt/conda/bin/python /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1; then command -v "$py"; exit 0; fi
    if [[ "$py" = /* && -x "$py" ]]; then echo "$py"; exit 0; fi
done; exit 1')

if [ $? -ne 0 ] || [ -z "${CONTAINER_PYTHON}" ]; then
    echo "FAILED: no Python found in container"; exit 1
fi

echo "=================================================================="
echo "CHUNKED SINGLE TARGET: ${TARGET} cells"
echo "=================================================================="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
run_in_container nvidia-smi 2>&1 | head -5
echo ""

DATA_FILE=$(ls "${WORKDIR}/data/brain_full_"*.h5ad 2>/dev/null | head -1)
if [ -z "${DATA_FILE}" ]; then
    echo "ERROR: No brain_full_*.h5ad found."; exit 1
fi

CLUSTERING=${CLUSTERING:-leiden}

run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_maxpower_chunked.py" \
    --data-dir "${WORKDIR}/data" \
    --output-dir "${WORKDIR}/results" \
    --n-gpus 8 \
    --target-cells "${TARGET}" \
    --skip-de \
    --clustering "${CLUSTERING}"

RC=$?
echo ""
echo "Exit code: ${RC}"
echo "End: $(date)"
if [ ${RC} -eq 0 ]; then
    echo ">>> SUCCESS at ${TARGET} cells"
else
    echo ">>> FAILED at ${TARGET} cells (exit ${RC})"
fi
