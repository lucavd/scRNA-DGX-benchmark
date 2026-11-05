#!/bin/bash
#SBATCH --job-name=lnbi_s1_spatial_cpu
#SBATCH --partition=dgx12cluster
#SBATCH --account=dctv_dgx
#SBATCH --nodelist=poddgx02
#SBATCH --exclusive
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --mem=0
#SBATCH --time=16:00:00
#SBATCH --export=NONE
#SBATCH --chdir=/home/u0044/lnbi_spatial_v2
#SBATCH --output=/home/u0044/lnbi_spatial_v2/logs/%x_%j.out
#SBATCH --error=/home/u0044/lnbi_spatial_v2/logs/%x_%j.err
# LNBI S1: CPU reference of the spatial benchmark on the DGX node poddgx02,
# reserved exclusively; each repetition is a separate process in a 100-CPU
# job step (same CPU request as the scRNA CPU reference).
set -uo pipefail
# --export=NONE leaves no SLURM tools on PATH: load them as the scRNA scripts do
set +u
source /etc/profile >/dev/null 2>&1 || true
module load slurm/slurm/23.02.7 >/dev/null 2>&1 || true
set -u
command -v srun >/dev/null || { echo "srun not found"; exit 7; }
W=/home/u0044/lnbi_spatial_v2
SIF=$W/image/sc-benchmark-spatial.sif
APPT=$(command -v apptainer || command -v singularity || echo /cm/shared/apps/singularity/4.2.0/bin/singularity)
OUT=${OUT:-$W/results_v2/dgx_cpu}
MECH_OUT=${MECH_OUT:-$W/results_v2/mechanism_dgx}
SNAP=$OUT/host_snapshots
N_REPEATS=${N_REPEATS:-5}
N_CPUS=100
PLATFORMS=${PLATFORMS:-"visium:: visium_hd:square_008um: visium_hd:square_002um:400000"}
mkdir -p "$OUT" "$SNAP"
GIT_COMMIT=$(cat $W/scripts/GIT_COMMIT)
IMAGE_ID=$(cat $W/image/IMAGE_ID)

# Stage the input data on the node-local disk (/ = local RAID; /home is NFS;
# /dev/shm is not visible inside the apptainer step)
SHM=/tmp/lnbi_s1_${SLURM_JOB_ID}
mkdir -p "$SHM" && cp -a "$W/data" "$SHM/" || exit 5
( cd "$SHM" && md5sum -c --quiet "$W/logs/data_md5_dgx.txt" ) || { echo "data md5 mismatch"; exit 6; }
trap 'rm -rf "$SHM"' EXIT

snapshot() {
    {
        echo "utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "host: $(hostname)  job: $SLURM_JOB_ID"
        echo "loadavg: $(cut -d' ' -f1-3 /proc/loadavg)"
        echo "coretemp_package_max: $(for d in /sys/class/hwmon/hwmon*; do [ "$(cat $d/name)" = coretemp ] && for f in $d/temp*_label; do grep -q Package $f && cat ${f%_label}_input; done; done | sort -n | tail -n 1)"
        echo "node_jobs: $(squeue -h -w poddgx02 -o '%i:%u:%T' | tr '\n' ' ')"
        echo "top_processes:"
        ps -eo pid,user,pcpu,etime,comm --sort=-pcpu | head -n 15
    } > "$1"
}

echo "start $(date -Iseconds) node=$(hostname) job=$SLURM_JOB_ID apptainer=$APPT"
for spec in $PLATFORMS; do
    IFS=: read -r P B M <<< "$spec"
    ARGS=(--platform "$P"); TAG="$P"
    [ -n "$B" ] && { ARGS+=(--bin-size "$B"); TAG="${P}_${B}"; }
    [ -n "$M" ] && ARGS+=(--max-spots "$M")
    for r in $(seq 1 "$N_REPEATS"); do
        stem="spatial_cpu_${TAG}_r${r}"
        LAB=()
        # repetition 1 defines the groups; 2..N read them from its clusters file
        [ "$r" -gt 1 ] && LAB=(--labels-from "$OUT/spatial_cpu_${TAG}_r1_clusters.csv")
        # fresh JIT cache and fresh home (OmniPath config/cache for ligrec) per repetition,
        # as in a new docker container on the workstation
        rm -rf "$SHM/jit_cache" "$SHM/home" && mkdir -p "$SHM/jit_cache" "$SHM/home"
        snapshot "$SNAP/${stem}_start.txt"
        t0=$(date +%s)
        srun --ntasks=1 --cpus-per-task=$N_CPUS --cpu-bind=cores --exact \
            "$APPT" exec --home "$SHM/home" -B "$W:$W" -B "$SHM:$SHM" \
            --env LNBI_GIT_COMMIT="$GIT_COMMIT",LNBI_IMAGE_ID="$IMAGE_ID",LNBI_HOST_HOSTNAME="$(hostname)",LNBI_MACHINE_ROLE=dgx_cpu_reference,NUMBA_CACHE_DIR="$SHM/jit_cache",MPLCONFIGDIR="$SHM/mpl" \
            "$SIF" python -u "$W/scripts/benchmark_spatial_cpu.py" \
            --data-dir "$SHM/data" --output-dir "$OUT" "${ARGS[@]}" \
            --n-cpus $N_CPUS --repeat-id "$r" "${LAB[@]}" > "$SNAP/${stem}.log" 2>&1
        rc=$?
        snapshot "$SNAP/${stem}_end.txt"
        echo "$stem rc=$rc wall=$(( $(date +%s) - t0 ))s"
        [ $rc -ne 0 ] && exit $rc
    done
done
# Mechanism check (original March script, 2 repetitions in one process)
mkdir -p "$SHM/jit_cache_mech" "$SHM/home_mech" "$MECH_OUT"
srun --ntasks=1 --cpus-per-task=$N_CPUS --cpu-bind=cores --exact \
    "$APPT" exec --home "$SHM/home_mech" -B "$W:$W" -B "$SHM:$SHM" --env MPLCONFIGDIR="$SHM/mpl",NUMBA_CACHE_DIR="$SHM/jit_cache_mech" "$SIF" \
    python -u "$W/scripts/mechanism/mechanism_numba_threads.py" \
    --data-dir "$SHM/data" --output-dir "$MECH_OUT" --n-cpus $N_CPUS \
    > "$MECH_OUT.log" 2>&1
echo "mechanism rc=$?"
echo "end $(date -Iseconds)"
