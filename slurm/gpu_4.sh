#!/bin/bash
#SBATCH --job-name=gpu_bench_4
#SBATCH --partition=dgx12cluster
#SBATCH --account=dctv_dgx
#SBATCH --output=/home/u0044/sc-gpu-benchmark/logs/slurm-%x_%j.out
#SBATCH --error=/home/u0044/sc-gpu-benchmark/logs/slurm-%x_%j.err
#SBATCH --export=NONE
#SBATCH --chdir=/home/u0044
#SBATCH --mail-user=luca.vedovelli@unipd.it
#SBATCH --mail-type=ALL
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=56
#SBATCH --mem=1024G
#SBATCH --gres=gpu:4
#SBATCH --time=168:00:00

# Multi-GPU benchmark: 4 GPUs × (500k, 1.3M) × 5 repeats

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
    echo "FAILED: sc-gpu-benchmark not found"
    exit 1
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
    echo "FAILED: no Python found in container"
    exit 1
fi

N_GPUS=4
SIZES=(10000 50000 100000 500000 1300000)
N_REPEATS=5

echo "=== GPU BENCHMARK (${N_GPUS} GPUs) START ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
run_in_container nvidia-smi
echo ""

FAILED=0

for SIZE in "${SIZES[@]}"; do
    INPUT_FILE="${WORKDIR}/data/brain_${SIZE}.h5ad"
    if [ ! -f "${INPUT_FILE}" ]; then
        echo "WARNING: ${INPUT_FILE} not found, skipping"
        continue
    fi

    echo "================================================================"
    echo "=== ${N_GPUS}-GPU benchmark: ${SIZE} cells, ${N_REPEATS} repeats ==="
    echo "=== Start: $(date) ==="
    echo "================================================================"

    run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_multigpu.py" \
        --data-dir "${WORKDIR}/data" \
        --output-dir "${WORKDIR}/results" \
        --n-cells "${SIZE}" \
        --n-gpus "${N_GPUS}" \
        --n-repeats "${N_REPEATS}"

    EXIT_CODE=$?
    echo "=== ${SIZE} cells finished at $(date) with exit code ${EXIT_CODE} ==="
    [ ${EXIT_CODE} -ne 0 ] && FAILED=$((FAILED + 1))
done

echo ""
echo "=== GPU BENCHMARK (${N_GPUS} GPUs) COMPLETE ==="
echo "Date: $(date)"
echo "Failures: ${FAILED}"
exit ${FAILED}
