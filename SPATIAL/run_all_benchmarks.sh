#!/bin/bash
# Run all spatial benchmarks locally: 3 platforms × CPU/GPU × 5 repeats + concordance
# Estimated total time: ~2.5 hours
set -e

IMAGE="lucavd/sc-benchmark-spatial:latest"
DOCKER_RUN="docker run --rm --gpus all -v $(pwd)/SPATIAL:/workspace/SPATIAL ${IMAGE}"
SCRIPTS="SPATIAL/scripts"
DATA="SPATIAL/data"
OUT="SPATIAL/results"

echo "========================================"
echo "SPATIAL BENCHMARK — FULL RUN (5 repeats)"
echo "Started: $(date)"
echo "========================================"

# --- 1. Visium v1 CPU (3k spots, ~3 min) ---
echo ""
echo ">>> [1/9] CPU Visium v1 — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_cpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium --n-repeats 5

# --- 2. Visium v1 GPU (3k spots, ~3 min) ---
echo ""
echo ">>> [2/9] GPU Visium v1 — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_gpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium --n-repeats 5

# --- 3. Concordance Visium v1 ---
echo ""
echo ">>> [3/9] Concordance Visium v1"
${DOCKER_RUN} python ${SCRIPTS}/compare_spatial_results.py \
    --results-dir ${OUT} --platform visium --n-repeats 5

# --- 4. Visium HD 8um CPU (393k spots, ~50 min) ---
echo ""
echo ">>> [4/9] CPU Visium HD 8um — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_cpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium_hd --bin-size square_008um --n-repeats 5

# --- 5. Visium HD 8um GPU (393k spots, ~25 min) ---
echo ""
echo ">>> [5/9] GPU Visium HD 8um — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_gpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium_hd --bin-size square_008um --n-repeats 5

# --- 6. Concordance Visium HD 8um ---
echo ""
echo ">>> [6/9] Concordance Visium HD 8um"
${DOCKER_RUN} python ${SCRIPTS}/compare_spatial_results.py \
    --results-dir ${OUT} --platform visium_hd --bin-size square_008um --n-repeats 5

# --- 7. Visium HD 2um CPU (400k cap, ~50 min) ---
echo ""
echo ">>> [7/9] CPU Visium HD 2um (max 400k spots) — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_cpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium_hd --bin-size square_002um --max-spots 400000 --n-repeats 5

# --- 8. Visium HD 2um GPU (400k cap, ~15 min) ---
echo ""
echo ">>> [8/9] GPU Visium HD 2um (max 400k spots) — 5 repeats"
${DOCKER_RUN} python ${SCRIPTS}/benchmark_spatial_gpu.py \
    --data-dir ${DATA} --output-dir ${OUT} \
    --platform visium_hd --bin-size square_002um --max-spots 400000 --n-repeats 5

# --- 9. Concordance Visium HD 2um ---
echo ""
echo ">>> [9/9] Concordance Visium HD 2um"
${DOCKER_RUN} python ${SCRIPTS}/compare_spatial_results.py \
    --results-dir ${OUT} --platform visium_hd --bin-size square_002um --n-repeats 5

echo ""
echo "========================================"
echo "ALL DONE — $(date)"
echo "========================================"
