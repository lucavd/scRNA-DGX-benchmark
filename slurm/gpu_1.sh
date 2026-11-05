#!/bin/bash
#SBATCH --job-name=gpu_bench_1
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
#SBATCH --cpus-per-task=16
#SBATCH --mem=256G
#SBATCH --gres=gpu:1
#SBATCH --time=168:00:00

# Single-GPU benchmark: all dataset sizes × 5 repeats

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

# Find python inside container
CONTAINER_PYTHON=$(run_in_container bash -lc 'for py in python python3 /opt/conda/bin/python /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1; then
        command -v "$py"
        exit 0
    fi
    if [[ "$py" = /* && -x "$py" ]]; then
        echo "$py"
        exit 0
    fi
done
exit 1')

if [ $? -ne 0 ] || [ -z "${CONTAINER_PYTHON}" ]; then
    echo "FAILED: no Python found in container"
    exit 1
fi

echo "=== GPU BENCHMARK (1 GPU) START ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
echo ""

# Check GPU
run_in_container nvidia-smi
echo ""

# Dataset sizes to benchmark (smallest → largest)
# NOTE: 500k and 1.3M may OOM on single H100 (80GB VRAM).
# The script will log the error and continue to the next size.
SIZES=(10000 50000 100000 500000 1300000)
N_REPEATS=5

FAILED=0

for SIZE in "${SIZES[@]}"; do
    INPUT_FILE="${WORKDIR}/data/brain_${SIZE}.h5ad"
    if [ ! -f "${INPUT_FILE}" ]; then
        echo "WARNING: ${INPUT_FILE} not found, skipping ${SIZE} cells"
        continue
    fi

    echo ""
    echo "================================================================"
    echo "=== GPU benchmark: ${SIZE} cells, 1 GPU, ${N_REPEATS} repeats ==="
    echo "=== Start: $(date) ==="
    echo "================================================================"

    run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_gpu.py" \
        --data-dir "${WORKDIR}/data" \
        --output-dir "${WORKDIR}/results" \
        --n-cells "${SIZE}" \
        --n-repeats "${N_REPEATS}" \
        --gpu-id 0

    EXIT_CODE=$?
    echo "=== ${SIZE} cells finished at $(date) with exit code ${EXIT_CODE} ==="

    if [ ${EXIT_CODE} -ne 0 ]; then
        echo "ERROR: GPU benchmark failed for ${SIZE} cells"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=== Disk usage ==="
du -sh "${WORKDIR}/results/"
ls -lh "${WORKDIR}/results/gpu_"*.json 2>/dev/null

echo ""
echo "=== GPU BENCHMARK (1 GPU) COMPLETE ==="
echo "Date: $(date)"
echo "Failures: ${FAILED}"

exit ${FAILED}
