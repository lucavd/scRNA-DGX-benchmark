DOCKER_USER ?= lucavd
IMAGE_NAME ?= sc-benchmark
TAG ?= latest
FULL_IMAGE = $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)

# Spatial benchmark parameters
SPATIAL_PLATFORM ?= visium
SPATIAL_BIN_SIZE ?= square_008um
SPATIAL_MAX_SPOTS ?=

# Local development
build:
	docker build -t $(FULL_IMAGE) .

run:
	docker run --rm -it --gpus all \
		-v $(PWD):/workspace \
		$(FULL_IMAGE)

run-cpu:
	docker run --rm -it \
		-v $(PWD):/workspace \
		$(FULL_IMAGE)

# Test: verify GPU visibility and key imports
test:
	docker run --rm --gpus all $(FULL_IMAGE) \
		bash -c "nvidia-smi && python -c 'from importlib.metadata import version; import cupy; print(\"scanpy:\", version(\"scanpy\")); print(\"rapids_singlecell:\", version(\"rapids-singlecell\")); print(\"cupy:\", cupy.__version__); print(\"All imports OK\")'"

# Data download (runs inside container, no GPU needed)
download-data:
	docker run --rm \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u scripts/download_data.py --data-dir /workspace/data --max-cells 100000

# Benchmarks
bench-cpu:
	docker run --rm \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u scripts/benchmark_cpu.py \
			--data-dir /workspace/data \
			--output-dir /workspace/results \
			--n-cells 10000

bench-gpu:
	docker run --rm --gpus all \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u scripts/benchmark_gpu.py \
			--data-dir /workspace/data \
			--output-dir /workspace/results \
			--n-cells 10000

concordance:
	docker run --rm \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u scripts/compare_results.py \
			--results-dir /workspace/results \
			--n-cells 10000

# Spatial benchmarks
bench-spatial-cpu:
	docker run --rm \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u SPATIAL/scripts/benchmark_spatial_cpu.py \
			--data-dir /workspace/SPATIAL/data \
			--output-dir /workspace/SPATIAL/results \
			--platform $(SPATIAL_PLATFORM) \
			--bin-size $(SPATIAL_BIN_SIZE) \
			$(if $(SPATIAL_MAX_SPOTS),--max-spots $(SPATIAL_MAX_SPOTS))

bench-spatial-gpu:
	docker run --rm --gpus all \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u SPATIAL/scripts/benchmark_spatial_gpu.py \
			--data-dir /workspace/SPATIAL/data \
			--output-dir /workspace/SPATIAL/results \
			--platform $(SPATIAL_PLATFORM) \
			--bin-size $(SPATIAL_BIN_SIZE) \
			$(if $(SPATIAL_MAX_SPOTS),--max-spots $(SPATIAL_MAX_SPOTS))

spatial-concordance:
	docker run --rm \
		-v $(PWD):/workspace \
		$(FULL_IMAGE) \
		python -u SPATIAL/scripts/compare_spatial_results.py \
			--results-dir /workspace/SPATIAL/results \
			--platform $(SPATIAL_PLATFORM) \
			--bin-size $(SPATIAL_BIN_SIZE)

# Test spatial imports
test-spatial:
	docker run --rm --gpus all $(FULL_IMAGE) \
		bash -c "python -c 'import squidpy; import spatialdata; import spatialdata_io; print(\"squidpy:\", squidpy.__version__); print(\"spatialdata:\", spatialdata.__version__); print(\"All spatial imports OK\")'"

# Docker Hub
push:
	docker push $(FULL_IMAGE)

# Singularity (run on DGX login node)
pull-singularity:
	singularity pull $(IMAGE_NAME).sif docker://$(FULL_IMAGE)
	singularity cache clean

.PHONY: build run run-cpu test test-spatial download-data bench-cpu bench-gpu concordance bench-spatial-cpu bench-spatial-gpu spatial-concordance push pull-singularity
