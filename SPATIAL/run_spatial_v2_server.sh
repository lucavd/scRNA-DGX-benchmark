#!/bin/bash
# LNBI S1: spatial rerun on the RTX 4090 workstation (lesexp-server).
# One docker run per repetition; host state recorded before and after each.
#
#   SPATIAL/run_spatial_v2_server.sh preflight        # is the machine free?
#   SPATIAL/run_spatial_v2_server.sh thermal          # 10-min 128-thread heat test
#   SPATIAL/run_spatial_v2_server.sh mechanism        # numba-thread mechanism check
#   SPATIAL/run_spatial_v2_server.sh gpu              # GPU, 3 platforms x 5 reps
#   SPATIAL/run_spatial_v2_server.sh cpu              # CPU control, 3 platforms x 5 reps
#   SPATIAL/run_spatial_v2_server.sh compare          # concordance (reference and control)
#
# Env: REPO_DATA (dir with visium/ and visium_hd/, read-only), FORCE=1 skips preflight.
set -uo pipefail

MODE=${1:?mode}
WT=$(cd "$(dirname "$0")/.." && pwd)            # worktree root
REPO_DATA=${REPO_DATA:-/mnt/wwn-0x5000039d58caca35/2026.scRNA_DGX/SPATIAL/data}
IMAGE="lucavd/sc-benchmark-spatial:latest"
IMAGE_ID=$(docker image inspect "$IMAGE" --format '{{.Id}}')
GIT_COMMIT=$(git -C "$WT" rev-parse HEAD)
OUT=${OUT:-SPATIAL/results_v2}
WAIT_FREE_MAX_S=${WAIT_FREE_MAX_S:-1200}
N_REPEATS=${N_REPEATS:-5}
LOAD_MAX=${LOAD_MAX:-3.0}
TOP_PCPU_MAX=${TOP_PCPU_MAX:-50}

snapshot() {  # $1 = output file
    {
        echo "utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "loadavg: $(cut -d' ' -f1-3 /proc/loadavg)"
        echo "tctl: $(sensors 2>/dev/null | awk '/Tctl/ {print $2}')"
        echo "gpu: $(nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,clocks.sm --format=csv,noheader 2>/dev/null)"
        echo "top_processes:"
        top -b -n 2 -d 2 -w 200 | awk '/^top -/{n++} n==2' | sed -n '8,22p'
    } > "$1"
}

preflight() {
    local load1 foreign
    load1=$(cut -d' ' -f1 /proc/loadavg)
    foreign=$(top -b -n 2 -d 2 -w 200 | awk '/^top -/{n++} n==2' | sed -n '8,40p' \
        | awk -v m="$TOP_PCPU_MAX" '$9+0 > m && $12 !~ /^(top|dockerd|containerd)/' )
    echo "preflight: load1=$load1 (max $LOAD_MAX), Tctl=$(sensors 2>/dev/null | awk '/Tctl/ {print $2}')"
    if [ -n "$foreign" ]; then echo "preflight: busy processes:"; echo "$foreign"; fi
    if [ "${FORCE:-0}" = "1" ]; then echo "preflight: FORCE=1, not enforced"; return 0; fi
    if awk -v l="$load1" -v m="$LOAD_MAX" 'BEGIN{exit !(l>m)}' || [ -n "$foreign" ]; then
        echo "preflight: MACHINE NOT FREE, aborting"; return 3
    fi
    echo "preflight: machine free"
}

drun() {  # docker run with fresh JIT caches; $1 = container name, rest = command
          # GPU access (--gpus all, NVIDIA container toolkit) only for the GPU runs
    local name=$1; shift
    local gpus=()
    [ "$ROLE" = "server_gpu" ] && gpus=(--gpus all)
    docker run --rm "${gpus[@]}" --name "$name" \
        -e LNBI_GIT_COMMIT="$GIT_COMMIT" -e LNBI_IMAGE_ID="$IMAGE_ID" \
        -e LNBI_HOST_HOSTNAME="$(hostname)" -e LNBI_MACHINE_ROLE="$ROLE" \
        -e NUMBA_CACHE_DIR=/tmp/numba_cache -e CUPY_CACHE_DIR=/tmp/cupy_cache \
        -v "$WT/SPATIAL":/workspace/SPATIAL \
        -v "$REPO_DATA":/workspace/SPATIAL/data:ro \
        "$IMAGE" "$@"
}

if [ -n "${PLATFORMS_OVERRIDE:-}" ]; then read -r -a PLATFORMS <<< "$PLATFORMS_OVERRIDE"
else PLATFORMS=("visium::" "visium_hd:square_008um:" "visium_hd:square_002um:400000"); fi

wait_free() {  # poll the preflight every 20 s (load average decays after our own runs)
    local waited=0
    until preflight > /tmp/lnbi_s1_preflight.txt 2>&1; do
        if [ "$waited" -ge "$WAIT_FREE_MAX_S" ]; then cat /tmp/lnbi_s1_preflight.txt; echo "wait_free: gave up after ${waited}s"; return 3; fi
        sleep 20; waited=$((waited + 20))
    done
    echo "wait_free: free after ${waited}s ($(head -n 1 /tmp/lnbi_s1_preflight.txt))"
}

plat_args() {  # "platform:bin:max" -> CLI args and file prefix
    IFS=: read -r P B M <<< "$1"
    ARGS=(--platform "$P"); TAG="$P"
    [ -n "$B" ] && { ARGS+=(--bin-size "$B"); TAG="${P}_${B}"; }
    [ -n "$M" ] && ARGS+=(--max-spots "$M")
}

run_reps() {  # $1 = cpu|gpu, $2 = outdir
    local dev=$1 od=$2
    mkdir -p "$WT/$od/host_snapshots"
    for spec in "${PLATFORMS[@]}"; do
        plat_args "$spec"
        LABELS="${LABELS_DIR:-$OUT/dgx_cpu}/spatial_cpu_${TAG}_r1_clusters.csv"
        if [ ! -f "$WT/$LABELS" ]; then echo "missing reference labels $LABELS"; return 4; fi
        for r in $(seq 1 "$N_REPEATS"); do
            local stem="spatial_${dev}_${TAG}_r${r}"
            if [ -f "$WT/$od/${stem}_results.json" ]; then echo "$stem exists, skipped"; continue; fi
            wait_free || return 3
            snapshot "$WT/$od/host_snapshots/${stem}_start.txt"
            local extra=()
            [ "$dev" = "cpu" ] && extra=(--n-cpus 128)
            local t0=$(date +%s)
            drun "lnbi_s1_${dev}_${TAG}_r${r}" python -u SPATIAL/scripts/benchmark_spatial_${dev}.py \
                --data-dir SPATIAL/data --output-dir "$od" "${ARGS[@]}" \
                --repeat-id "$r" --labels-from "$LABELS" "${extra[@]}" \
                > "$WT/$od/host_snapshots/${stem}.log" 2>&1
            local rc=$?
            snapshot "$WT/$od/host_snapshots/${stem}_end.txt"
            echo "$stem rc=$rc wall=$(( $(date +%s) - t0 ))s"
            if [ $rc -ne 0 ]; then return $rc; fi
        done
    done
    return 0
}

case "$MODE" in
    preflight) preflight ;;
    thermal)
        ROLE=server_thermal_test; wait_free || exit 3
        mkdir -p "$WT/$OUT/thermal"
        ( for i in $(seq 1 150); do
              echo "$(date -u +%s) $(sensors | awk '/Tctl/ {gsub(/[+°C]/,"",$2); print $2}') $(awk '/MHz/ {s+=$4; n++} END {printf "%.0f", s/n}' /proc/cpuinfo) $(cut -d' ' -f1 /proc/loadavg)"
              sleep 5
          done > "$WT/$OUT/thermal/thermal_samples.txt" ) &
        SAMPLER=$!
        drun lnbi_s1_thermal python -u SPATIAL/scripts/thermal_load.py --n-threads 128 --seconds 600 \
            > "$WT/$OUT/thermal/thermal_load.log" 2>&1
        wait $SAMPLER
        echo "thermal done" ;;
    mechanism)
        ROLE=server_mechanism_check
        drun lnbi_s1_mechanism python -u SPATIAL/scripts/mechanism/mechanism_numba_threads.py \
            --data-dir SPATIAL/data --output-dir "$OUT/mechanism" --n-cpus "${MECH_CPUS:-16}" \
            > "$WT/$OUT/mechanism_server.log" 2>&1; echo "mechanism rc=$?" ;;
    gpu) ROLE=server_gpu; run_reps gpu "$OUT/server_gpu" ;;
    cpu) ROLE=server_cpu_control; run_reps cpu "$OUT/server_cpu" ;;
    compare)
        ROLE=compare
        for spec in "${PLATFORMS[@]}"; do
            plat_args "$spec"; BA=(); [ -n "$B" ] && BA=(--bin-size "$B")
            drun lnbi_s1_cmp_ref python -u SPATIAL/scripts/compare_spatial_results.py \
                --results-dir "$OUT/server_gpu" --cpu-results-dir "$OUT/dgx_cpu" \
                --output-dir "$OUT/concordance_reference" --platform "$P" "${BA[@]}" --n-repeats "$N_REPEATS"
            drun lnbi_s1_cmp_ctl python -u SPATIAL/scripts/compare_spatial_results.py \
                --results-dir "$OUT/server_gpu" --cpu-results-dir "$OUT/server_cpu" \
                --output-dir "$OUT/concordance_server_control" --platform "$P" "${BA[@]}" --n-repeats "$N_REPEATS"
        done ;;
    *) echo "unknown mode $MODE"; exit 2 ;;
esac
