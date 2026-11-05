#!/bin/bash
#SBATCH --job-name=smoke_test
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
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00

# Smoke test: download 10k cells, run CPU + GPU benchmarks, compare results

# Load required modules
module load go/1.22.7
module load singularity/4.2.0
module load slurm/slurm/23.02.7

if [ -d /mnt/home/u0044/sc-gpu-benchmark ]; then
    WORKDIR=/mnt/home/u0044/sc-gpu-benchmark
elif [ -d /home/u0044/sc-gpu-benchmark ]; then
    WORKDIR=/home/u0044/sc-gpu-benchmark
else
    echo "FAILED: sc-gpu-benchmark not found under /mnt/home/u0044 or /home/u0044"
    exit 1
fi

CONTAINER=${WORKDIR}/sc-benchmark.sif
SINGULARITY=/cm/shared/apps/singularity/4.2.0/bin/singularity
BIND_ARGS=(-B /home/u0044:/home/u0044)

if [ -d /mnt/home/u0044 ]; then
    BIND_ARGS+=(-B /mnt/home/u0044:/mnt/home/u0044)
fi

run_in_container() {
    "${SINGULARITY}" exec --nv "${BIND_ARGS[@]}" "${CONTAINER}" "$@"
}

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
    echo "FAILED: no Python interpreter found inside container"
    exit 1
fi

echo "=== SMOKE TEST START ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Container Python: ${CONTAINER_PYTHON}"
echo ""

# Step 1: Check GPU visibility
echo "=== Step 1: GPU check ==="
run_in_container nvidia-smi

if [ $? -ne 0 ]; then
    echo "FAILED: GPU visibility"
    exit 1
fi

run_in_container "${CONTAINER_PYTHON}" -c 'import cupy; print("CuPy OK, GPU:", cupy.cuda.runtime.getDeviceCount())'

if [ $? -ne 0 ]; then
    echo "FAILED: GPU Python import"
    exit 1
fi
echo ""

# Step 2: Download 10k cells
echo "=== Step 2: Download data (10k cells) ==="
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/download_data.py" \
    --data-dir "${WORKDIR}/data" \
    --max-cells 10000

if [ $? -ne 0 ]; then
    echo "FAILED: Download step"
    exit 1
fi
echo ""

# Step 3: CPU benchmark (10k cells)
echo "=== Step 3: CPU benchmark ==="
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_cpu.py" \
    --data-dir "${WORKDIR}/data" \
    --output-dir "${WORKDIR}/results" \
    --n-cells 10000

if [ $? -ne 0 ]; then
    echo "FAILED: CPU benchmark step"
    exit 1
fi
echo ""

# Step 4: GPU benchmark (10k cells)
echo "=== Step 4: GPU benchmark ==="
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_gpu.py" \
    --data-dir "${WORKDIR}/data" \
    --output-dir "${WORKDIR}/results" \
    --n-cells 10000

if [ $? -ne 0 ]; then
    echo "FAILED: GPU benchmark step"
    exit 1
fi
echo ""

# Step 5: Concordance comparison
echo "=== Step 5: Concordance ==="
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/compare_results.py" \
    --results-dir "${WORKDIR}/results" \
    --n-cells 10000

if [ $? -ne 0 ]; then
    echo "FAILED: Concordance step"
    exit 1
fi

echo ""
echo "=== SMOKE TEST COMPLETE ==="
echo "Date: $(date)"
