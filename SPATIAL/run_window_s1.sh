#!/bin/bash
# LNBI S1: the whole free-server window in one command (run from the worktree root).
#   bash SPATIAL/run_window_s1.sh
# Order: thermal test -> criterion -> GPU 3x5 -> CPU control 3x5 -> concordance.
# Each repetition waits until the preflight passes (load1 <= 3, no foreign process > 50%).
set -uo pipefail
cd "$(dirname "$0")/.."
S=SPATIAL/run_spatial_v2_server.sh
R=SPATIAL/results_v2
mkdir -p $R
echo "window start $(date -Iseconds)"
if [ ! -f $R/thermal/thermal_eval.json ]; then
    bash $S thermal || { echo "thermal: machine not free"; exit 3; }
    python3 SPATIAL/scripts/s1_thermal_eval.py $R/thermal > $R/thermal/thermal_eval.json
    rc=$?; cat $R/thermal/thermal_eval.json
    [ $rc -ne 0 ] && { echo "THERMAL CRITERION FAILED: stop, the PI decides the thread count"; exit 10; }
fi
# Groups: wait until the DGX reference has finished repetition 1 of every platform,
# then copy the DGX results produced so far (labels included) into the worktree.
DGX="ssh -o BatchMode=yes -o IdentitiesOnly=yes -i $HOME/.ssh/id_ed25519_dgx u0044@logindgx.hpc.ict.unipd.it"
DW=/home/u0044/lnbi_spatial_v2/results_v2/dgx_cpu
for i in $(seq 1 240); do
    $DGX "test -f $DW/spatial_cpu_visium_hd_square_002um_r1_results.json" && break
    [ $i -eq 1 ] && echo "waiting for DGX repetition 1 of HD 2 um $(date -Iseconds)"
    sleep 60
done
mkdir -p $R/dgx_cpu
rsync -a -e "$DGX" ":$DW/" $R/dgx_cpu/ || { echo "rsync of DGX results failed"; exit 6; }
for t in visium visium_hd_square_008um visium_hd_square_002um; do
    [ -f $R/dgx_cpu/spatial_cpu_${t}_r1_clusters.csv ] || { echo "labels for $t missing"; exit 6; }
done
echo "gpu start $(date -Iseconds)";  bash $S gpu || { echo "gpu failed rc=$?"; exit 4; }
echo "cpu start $(date -Iseconds)";  bash $S cpu || { echo "cpu failed rc=$?"; exit 5; }
echo "compare start $(date -Iseconds)"; bash $S compare > $R/compare.log 2>&1; echo "compare rc=$?"
echo "window end $(date -Iseconds)"
