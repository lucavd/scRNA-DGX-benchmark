# Dockerfile for scRNA-seq GPU vs CPU benchmark
# Base: NVIDIA RAPIDS with CUDA 12, Python 3.12
FROM nvcr.io/nvidia/rapidsai/base:26.02-cuda12-py3.12

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (run as root for apt)
USER root
RUN mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages via pip
# Split into two steps:
# 1) rapids-singlecell without deps (cuml/cupy already in RAPIDS base)
# 2) Everything else
RUN pip install --no-cache-dir --no-deps rapids-singlecell && \
    pip install --no-cache-dir \
    scanpy \
    anndata \
    scvi-tools \
    cellxgene-census \
    tiledbsoma \
    scikit-learn \
    scipy \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    psutil \
    nvidia-ml-py \
    h5py \
    leidenalg \
    igraph \
    && pip cache purge \
    && chmod -R o+rX /opt/conda

# Set working directory
WORKDIR /workspace

# Default command: open a shell
CMD ["/bin/bash"]
