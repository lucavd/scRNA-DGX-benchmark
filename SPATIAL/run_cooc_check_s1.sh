#!/bin/bash
# LNBI S1, D-13: GPU co-occurrence check, one repetition per docker run.
#   bash SPATIAL/run_cooc_check_s1.sh
set -uo pipefail
WT=$(cd "$(dirname "$0")/.." && pwd)
REPO_DATA=${REPO_DATA:-/mnt/wwn-0x5000039d58caca35/2026.scRNA_DGX/SPATIAL/data}
R=SPATIAL/results_v2
O=$R/cooc_check
N=${N_REPEATS:-5}
GIT_COMMIT=$(git -C "$WT" rev-parse HEAD)
preflight() {
    local load1 foreign
    load1=$(cut -d' ' -f1 /proc/loadavg)
    foreign=$(top -b -n 2 -d 2 -w 200 | awk '/^top -/{n++} n==2' | sed -n '8,40p' \
        | awk '$9+0 > 50 && $12 !~ /^(top|dockerd|containerd)/')
    awk -v l="$load1" 'BEGIN{exit !(l>3.0)}' && return 1
    [ -n "$foreign" ] && return 1
    return 0
}
wait_free() { local w=0; until preflight; do [ $w -ge 1200 ] && { echo "not free after ${w}s"; return 3; }; sleep 20; w=$((w+20)); done; echo "free after ${w}s, load1=$(cut -d' ' -f1 /proc/loadavg), Tctl=$(sensors | awk '/Tctl/ {print $2}')"; }
snapshot() { { echo "utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "loadavg: $(cut -d' ' -f1-3 /proc/loadavg)"; echo "tctl: $(sensors 2>/dev/null | awk '/Tctl/ {print $2}')"; echo "gpu: $(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader)"; echo "top_processes:"; top -b -n 2 -d 2 -w 200 | awk '/^top -/{n++} n==2' | sed -n '8,22p'; } > "$1"; }
run() {  # $1 image tag dir, $2 image, $3 platform spec
    local tagdir=$1 image=$2 spec=$3 P B ARGS TAG
    IFS=: read -r P B <<< "$spec"; ARGS=(--platform "$P"); TAG=$P
    [ -n "$B" ] && { ARGS+=(--bin-size "$B"); TAG="${P}_${B}"; }
    mkdir -p "$WT/$O/$tagdir/host_snapshots"
    for r in $(seq 1 "$N"); do
        local stem="cooc_gpu_${TAG}_r${r}"
        [ -f "$WT/$O/$tagdir/${stem}.json" ] && { echo "$tagdir $stem exists"; continue; }
        wait_free || return 3
        snapshot "$WT/$O/$tagdir/host_snapshots/${stem}_start.txt"
        docker run --rm --gpus all -e NUMBA_CACHE_DIR=/tmp/nc -e CUPY_CACHE_DIR=/tmp/cc \
            -e LNBI_GIT_COMMIT="$GIT_COMMIT" -e LNBI_HOST_HOSTNAME="$(hostname)" -e LNBI_MACHINE_ROLE="cooc_check_$tagdir" \
            -e LNBI_IMAGE_ID="$(docker image inspect "$image" --format '{{.Id}}')" \
            -v "$WT/SPATIAL":/workspace/SPATIAL -v "$REPO_DATA":/workspace/SPATIAL/data:ro "$image" \
            python -u SPATIAL/scripts/s1_cooc_check.py --data-dir SPATIAL/data "${ARGS[@]}" \
            --labels-from "$R/dgx_cpu/spatial_cpu_${TAG}_r1_clusters.csv" \
            --cpu-ref "$R/dgx_cpu/spatial_cpu_${TAG}_r1_co_occurrence.npy" \
            --output-dir "$O/$tagdir" --repeat-id "$r" > "$WT/$O/$tagdir/host_snapshots/${stem}.log" 2>&1
        local rc=$?
        snapshot "$WT/$O/$tagdir/host_snapshots/${stem}_end.txt"
        echo "$tagdir $stem rc=$rc $(tail -n 1 "$WT/$O/$tagdir/host_snapshots/${stem}.log" | cut -c1-200)"
        if [ $rc -ne 0 ]; then return $rc; fi
    done
    return 0
}
echo "start $(date -Iseconds)"
run rsc0151 lnbi/sc-benchmark-spatial:rsc0151 "visium_hd:square_008um" || exit $?
run rsc0141 lucavd/sc-benchmark-spatial:latest "visium_hd:square_008um" || exit $?
run rsc0151 lnbi/sc-benchmark-spatial:rsc0151 "visium:" || exit $?
echo "end $(date -Iseconds)"
