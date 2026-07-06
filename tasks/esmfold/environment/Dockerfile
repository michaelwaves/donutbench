FROM nvidia/cuda:11.7.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda

WORKDIR /app/esmfold

# ESMFold's dependency stack (openfold in particular) is pinned to an old,
# narrow combination of Python/CUDA/PyTorch versions. Python 3.9 is the
# newest version the upstream README supports for the `[esmfold]` extra.
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    curl \
    git \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-venv \
    python3.9-dev \
    python3.9-distutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3.9 -m venv /app/esmfold/.venv && \
    /app/esmfold/.venv/bin/python -m ensurepip --upgrade

ENV PATH=/app/esmfold/.venv/bin:$PATH

RUN pip install --no-cache-dir --upgrade pip setuptools wheel ninja

# PyTorch 1.12, CUDA 11.6 build: the combination documented in the ESM repo's
# esmfold conda environment (environment.yml), and required for openfold's
# custom CUDA kernel (attn_core_inplace_cuda) to compile and load correctly.
RUN pip install --no-cache-dir \
    torch==1.12.1+cu116 \
    --extra-index-url https://download.pytorch.org/whl/cu116

# Pin the handful of `[esmfold]` extras whose newest releases have dropped
# prebuilt wheels for Python 3.9 (dm-tree in particular would otherwise
# fall back to a from-source Bazel build, which this image cannot perform).
# Versions match the ESM repo's documented esmfold conda environment.
#
# pytorch-lightning==1.5.10's published metadata has a malformed dependency
# specifier ("torch (>=1.7.*)") that pip >=24.1 hard-rejects as invalid
# (pip's own error points at this exact fix). This isn't just a one-time
# resolution problem: pip >=24.1 refuses to even *look at* an
# already-installed package with invalid metadata on every later command
# (e.g. checking "Requirement already satisfied: pytorch-lightning"), so
# pip has to stay below 24.1 for the rest of this image's build, not just
# for this one install.
RUN pip install --no-cache-dir "pip<24.1" && \
    pip install --no-cache-dir \
        biopython==1.79 \
        numpy==1.21.2 \
        scipy==1.7.1 \
        PyYAML==5.4.1 \
        dm-tree==0.1.6 \
        pytorch-lightning==1.5.10 \
        ml-collections==0.1.0 \
        deepspeed==0.5.9

# Official ESMFold install recipe (see https://github.com/facebookresearch/esm
# README, "ESMFold Structure Prediction"): fair-esm's `[esmfold]` extra plus
# openfold, pinned to the exact commit the README specifies.
RUN pip install --no-cache-dir "fair-esm[esmfold]==2.0.0"
RUN pip install --no-cache-dir 'dllogger @ git+https://github.com/NVIDIA/dllogger.git'

# openfold's setup.py imports torch directly (to build its CUDA extension),
# so it must see the torch already installed above rather than a clean,
# isolated build environment: --no-build-isolation, as openfold's own
# Dockerfile does via `python setup.py install`.
#
# That same setup.py also compiles its CUDA kernel only for the GPU
# architecture it detects at build time, falling back to a fixed multi-arch
# list (which includes sm_80/A100) only when no GPU is visible. Force that
# fallback path so the kernel works regardless of what (if anything) the
# image builder has attached, and matches the A100 this task runs on.
RUN CUDA_VISIBLE_DEVICES="" pip install --no-cache-dir --no-build-isolation \
    'openfold @ git+https://github.com/aqlaboratory/openfold.git@4b41059694619831a7db195b7e0988fc4ff3a307'

# Open-source PyMOL for rendering predicted structures (pdb/mmcif) as PNGs.
RUN /app/esmfold/.venv/bin/python -m pip install --no-cache-dir pymol-open-source==3.2.0a0

# Pre-download ESMFold v1's weights so trials don't pay for a multi-GB
# download on every run. ESMFold's checkpoint stores only the folding trunk;
# the ESM-2 3B language model backbone it wraps is a separate checkpoint,
# so both (plus its small contact-regression head) must be cached where
# torch.hub expects them.
ENV TORCH_HOME=/app/esmfold/.torch
RUN mkdir -p $TORCH_HOME/hub/checkpoints && \
    curl -L --fail -o $TORCH_HOME/hub/checkpoints/esmfold_3B_v1.pt \
        https://dl.fbaipublicfiles.com/fair-esm/models/esmfold_3B_v1.pt && \
    curl -L --fail -o $TORCH_HOME/hub/checkpoints/esm2_t36_3B_UR50D.pt \
        https://dl.fbaipublicfiles.com/fair-esm/models/esm2_t36_3B_UR50D.pt && \
    curl -L --fail -o $TORCH_HOME/hub/checkpoints/esm2_t36_3B_UR50D-contact-regression.pt \
        https://dl.fbaipublicfiles.com/fair-esm/regression/esm2_t36_3B_UR50D-contact-regression.pt
