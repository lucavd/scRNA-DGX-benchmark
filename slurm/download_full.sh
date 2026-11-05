#!/bin/bash
#SBATCH --job-name=download_full
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
#SBATCH --cpus-per-task=8
#SBATCH --mem=512G
#SBATCH --time=04:00:00
#SBATCH --nodelist=poddgx02
# NOTE: No GPU needed — download only

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

echo "=== Download full mouse brain dataset from CELLxGENE Census ==="
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "Workdir: ${WORKDIR}"
echo ""

# Check if already downloaded
if ls "${WORKDIR}/data/brain_full_"*.h5ad 1>/dev/null 2>&1; then
    echo "Full dataset already exists:"
    ls -lh "${WORKDIR}/data/brain_full_"*.h5ad
    echo "Nothing to do."
    exit 0
fi

# Download ALL mouse brain cells (max-cells very high to get everything)
run_in_container "${CONTAINER_PYTHON}" -u "${WORKDIR}/scripts/download_data.py" \
    --data-dir "${WORKDIR}/data" \
    --max-cells 10000000 \
    --skip-subsample

DOWNLOAD_EXIT=$?
echo ""
echo "Download exit code: ${DOWNLOAD_EXIT}"

if [ ${DOWNLOAD_EXIT} -ne 0 ]; then
    echo "FAILED: download failed"
    exit 1
fi

# Rename brain_10000000.h5ad to brain_full_NNNN.h5ad with actual cell count
if [ -f "${WORKDIR}/data/brain_10000000.h5ad" ]; then
    run_in_container "${CONTAINER_PYTHON}" -u -c "
import scanpy as sc, os
path = '${WORKDIR}/data/brain_10000000.h5ad'
adata = sc.read_h5ad(path, backed='r')
n = adata.n_obs
adata.file.close()
dst = '${WORKDIR}/data/brain_full_{}.h5ad'.format(n)
os.rename(path, dst)
print(f'Renamed: brain_10000000.h5ad -> brain_full_{n}.h5ad ({n:,} cells)')
"
fi

echo ""
echo "=== Data directory ==="
ls -lh "${WORKDIR}/data/"*.h5ad 2>/dev/null
echo ""
echo "=== Disk usage ==="
du -sh "${WORKDIR}/"
echo ""
echo "End: $(date)"
