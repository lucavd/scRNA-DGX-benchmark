#!/bin/bash
#SBATCH --job-name=download_data
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
#SBATCH --cpus-per-task=4
#SBATCH --mem=512G
#SBATCH --time=04:00:00

# Download full 1.3M mouse brain dataset + create subsamples
# Must run BEFORE cpu_benchmark.sh and gpu_*.sh

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

echo "=== DATA DOWNLOAD START ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Python: ${CONTAINER_PYTHON}"
echo ""

# Download full 1.3M cells + create all subsamples (10k, 50k, 100k, 500k)
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/download_data.py" \
    --data-dir "${WORKDIR}/data" \
    --max-cells 1300000

if [ $? -ne 0 ]; then
    echo "FAILED: download step"
    exit 1
fi

echo ""
echo "=== Disk usage ==="
du -sh "${WORKDIR}/data/"
ls -lh "${WORKDIR}/data/"*.h5ad

echo ""
echo "=== DATA DOWNLOAD COMPLETE ==="
echo "Date: $(date)"
