#!/bin/bash
#SBATCH --job-name=maxpower_chunked
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
#SBATCH --cpus-per-task=200
#SBATCH --mem=1800G
#SBATCH --gres=gpu:8
#SBATCH --time=7-00:00:00
#SBATCH --nodelist=poddgx02

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

echo "=================================================================="
echo "CHUNKED MAX-POWER BENCHMARK — push beyond 11.9M cells"
echo "=================================================================="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Workdir: ${WORKDIR}"
run_in_container nvidia-smi
echo ""

# Verify data exists
DATA_FILE=$(ls "${WORKDIR}/data/brain_full_"*.h5ad 2>/dev/null | head -1)
if [ -z "${DATA_FILE}" ]; then
    echo "ERROR: No brain_full_*.h5ad found. Run download_full.sh first."
    exit 1
fi
echo "Data file: ${DATA_FILE}"
echo "File size: $(ls -lh "${DATA_FILE}" | awk '{print $5}')"
echo ""

# Build find-limit command
FIND_LIMIT_ARGS=(--find-limit)
if [ -n "${FINE_LOW}" ] && [ -n "${FINE_HIGH}" ]; then
    FIND_LIMIT_ARGS+=(--fine-low "${FINE_LOW}" --fine-high "${FINE_HIGH}")
    echo "Fine search bounds: ${FINE_LOW} — ${FINE_HIGH}"
fi

# Support --clustering (default: leiden)
CLUSTERING=${CLUSTERING:-leiden}
echo "Clustering: ${CLUSTERING}"
echo ""

# Run chunked find-limit
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/benchmark_maxpower_chunked.py" \
    --data-dir "${WORKDIR}/data" \
    --output-dir "${WORKDIR}/results" \
    --n-gpus 8 \
    --clustering "${CLUSTERING}" \
    "${FIND_LIMIT_ARGS[@]}"

echo ""
echo "=== Results ==="
ls -lh "${WORKDIR}/results/maxpower_chunked_"* 2>/dev/null
echo ""
echo "End: $(date)"
