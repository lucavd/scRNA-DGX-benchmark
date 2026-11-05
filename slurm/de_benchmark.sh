#!/bin/bash
#SBATCH --job-name=de_bench
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
#SBATCH --time=2-00:00:00
#SBATCH --nodelist=poddgx02

# Usage:
#   First run: preprocess + save (one job only)
#   sbatch --export=DE_TEST=preprocess,TARGET_CELLS=3400000 slurm/de_benchmark.sh
#
#   Then run tests loading preprocessed data (fast, no repeated preprocessing):
#   sbatch --export=DE_TEST=ttest_cpu,TARGET_CELLS=3400000 slurm/de_benchmark.sh
#   sbatch --export=DE_TEST=all,TARGET_CELLS=3400000 slurm/de_benchmark.sh

# Load required modules
module load go/1.22.7
module load singularity/4.2.0
module load slurm/slurm/23.02.7

# Validate inputs
if [ -z "${DE_TEST}" ] || [ -z "${TARGET_CELLS}" ]; then
    echo "ERROR: DE_TEST and TARGET_CELLS must be set."
    echo "Usage: sbatch --export=DE_TEST=ttest_cpu,TARGET_CELLS=3400000 slurm/de_benchmark.sh"
    exit 1
fi

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

echo "=================================================================="
echo "DE BENCHMARK: ${DE_TEST} — ${TARGET_CELLS} cells"
echo "=================================================================="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
echo ""

PREPROCESSED_PATH="${WORKDIR}/data/de_preprocessed_${TARGET_CELLS}.h5ad"

# Special mode: preprocess only (run once, then all tests load from file)
if [ "${DE_TEST}" = "preprocess" ]; then
    echo "Preprocessing + saving to ${PREPROCESSED_PATH}"
    run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/test_de_benchmark.py" \
        --data-dir "${WORKDIR}/data" \
        --target-cells "${TARGET_CELLS}" \
        --n-gpus 8 \
        --test ttest_cpu \
        --save-preprocessed "${PREPROCESSED_PATH}"
    EXIT_CODE=$?
    echo ""
    echo "Exit code: ${EXIT_CODE}"
    echo "End: $(date)"
    exit ${EXIT_CODE}
fi

# If preprocessed file exists, use it (skip 3h preprocessing)
EXTRA_ARGS=""
if [ -f "${PREPROCESSED_PATH}" ]; then
    echo "Found preprocessed: ${PREPROCESSED_PATH}"
    EXTRA_ARGS="--preprocessed ${PREPROCESSED_PATH}"
fi

# Run DE benchmark
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/test_de_benchmark.py" \
    --data-dir "${WORKDIR}/data" \
    --target-cells "${TARGET_CELLS}" \
    --n-gpus 8 \
    --test "${DE_TEST}" \
    ${EXTRA_ARGS}

EXIT_CODE=$?
echo ""
echo "Exit code: ${EXIT_CODE}"
echo "End: $(date)"
