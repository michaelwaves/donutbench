FROM python:3.10-slim-bookworm

# metainformation
LABEL org.opencontainers.image.version="2.2.1"
LABEL org.opencontainers.image.authors="DP Technology"
LABEL org.opencontainers.image.source="https://github.com/dptech-corp/Uni-Fold"
LABEL org.opencontainers.image.licenses="Apache License 2.0"
LABEL org.opencontainers.image.description="UF-Symmetry (Uni-Fold) with a bundled precomputed MSA for a small C2-symmetric homodimer"

SHELL ["/bin/bash", "-c"]

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/Uni-Fold

# Pin to the commit this task was built and smoke-tested against.
RUN git clone https://github.com/dptech-corp/Uni-Fold.git . \
    && git checkout 7b55789e8c27c83cbe3b2b71065299f9edc4c3d8

# Uni-Fold's upstream setup.py deliberately leaves torch/Uni-Core unpinned
# (they depend on the host CUDA toolkit). Uni-Core ships a prebuilt wheel
# for torch==2.0.0+cu118 on Python 3.10, so no CUDA kernel compilation is
# needed here.
RUN pip install --no-cache-dir torch==2.0.0 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir "https://github.com/dptech-corp/Uni-Core/releases/download/0.0.3/unicore-0.0.1%2Bcu118torch2.0.0-cp310-cp310-linux_x86_64.whl" && \
    pip install --no-cache-dir absl-py biopython libmsym ml-collections "numpy<2" pandas scipy tqdm requests && \
    pip install --no-cache-dir -e .

# Open-source PyMOL for rendering the predicted assembly (pdb/mmcif) as a
# PNG. Base image bumped to -bookworm above (glibc 2.36) since this wheel's
# floor is manylinux_2_35. --no-deps avoids pip touching the numpy pin above.
RUN pip install --no-cache-dir --no-deps pymol-open-source==3.2.0a0

# UF-Symmetry model parameters (~350MB). This is the symmetry-aware model
# head trained on top of the multimer architecture -- NOT the ~3TB of
# UniRef90/MGnify/BFD/Uniclust30 genetic databases that Uni-Fold's normal
# homo_search.py pipeline needs to build an MSA from scratch.
RUN wget -q https://github.com/dptech-corp/Uni-Fold/releases/download/v2.2.0/uf_symmetry_params_2022-09-06.tar.gz && \
    tar -xzf uf_symmetry_params_2022-09-06.tar.gz && \
    rm uf_symmetry_params_2022-09-06.tar.gz

# The target FASTA (single asymmetric-unit chain). No precomputed MSA/
# feature bundle is shipped -- the genetic databases Uni-Fold's own
# homo_search.py needs are infeasible to bake into this image, and unlike an
# earlier version of this task, we deliberately don't pre-fetch and bundle
# a real MSA either: doing so would hand the agent the one genuinely hard
# part of this task for free. Uni-Fold's own repo, already cloned at
# /opt/Uni-Fold above, ships tooling for generating input features without
# a local genetic database -- see instruction.md and README.md.
COPY fastas/hcp1.fasta /data/fastas/hcp1.fasta

ENV PYTHONUNBUFFERED=1
