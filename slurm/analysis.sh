#!/bin/bash
#SBATCH --job-name=concordance
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
#SBATCH --time=02:00:00
# NOTE: NO GPU needed — analysis is CPU-only

# Concordance analysis: compare CPU vs GPU results for all dataset sizes

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
    "${SINGULARITY}" exec "${BIND_ARGS[@]}" "${CONTAINER}" "$@"
}

CONTAINER_PYTHON=$(run_in_container bash -lc 'for py in python python3 /opt/conda/bin/python /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1; then command -v "$py"; exit 0; fi
    if [[ "$py" = /* && -x "$py" ]]; then echo "$py"; exit 0; fi
done; exit 1')

if [ $? -ne 0 ] || [ -z "${CONTAINER_PYTHON}" ]; then
    echo "FAILED: no Python found in container"
    exit 1
fi

echo "=== CONCORDANCE ANALYSIS START ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo ""

SIZES=(10000 50000 100000 500000 1300000)
FAILED=0

for SIZE in "${SIZES[@]}"; do
    # Check if both CPU and GPU results exist for this size
    CPU_FILE="${WORKDIR}/results/cpu_${SIZE}_r1_results.json"
    GPU_FILE="${WORKDIR}/results/gpu_${SIZE}_r1_results.json"

    if [ ! -f "${CPU_FILE}" ] || [ ! -f "${GPU_FILE}" ]; then
        echo "Skipping ${SIZE} cells: missing CPU or GPU results"
        continue
    fi

    echo "================================================================"
    echo "=== Concordance: ${SIZE} cells ==="
    echo "================================================================"

    run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/compare_results.py" \
        --results-dir "${WORKDIR}/results" \
        --n-cells "${SIZE}"

    EXIT_CODE=$?
    [ ${EXIT_CODE} -ne 0 ] && FAILED=$((FAILED + 1))
done

echo ""
echo "=== CONCORDANCE ANALYSIS COMPLETE ==="
echo "Date: $(date)"
echo "Failures: ${FAILED}"
exit ${FAILED}
