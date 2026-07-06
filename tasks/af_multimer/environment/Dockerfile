# AlphaFold-Multimer, adapted from the upstream docker/Dockerfile at
# https://github.com/google-deepmind/alphafold (commit pinned below). Base
# image, apt packages, HH-suite build, and the jax/jaxlib install line are
# copied from that upstream Dockerfile so the exact CUDA/Python/JAX
# combination AlphaFold was built and tested against is preserved. The
# task-specific additions (weights + tiny placeholder "databases" +
# precomputed MSA bundle, at the bottom) are what make this runnable without
# the ~2.6 TB of real genetic databases -- see README.md for the reasoning.
#
# Deviation from upstream: using ubuntu22.04 instead of upstream's ubuntu20.04.
# pymol-open-source (added below, for rendering) has never published a wheel
# older than manylinux_2_34/_35 (glibc >=2.34) -- there is no installable
# build on 20.04's glibc 2.31. 22.04 (glibc 2.35) is the same base OS this
# repo's other tasks already settled on for the same reason.
ARG CUDA=12.2.2
FROM nvidia/cuda:${CUDA}-cudnn8-runtime-ubuntu22.04
# FROM directive resets ARGS, so we specify again (the value is retained if
# previously set).
ARG CUDA

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update --quiet \
    && apt-get install --no-install-recommends --yes --quiet \
        build-essential \
        cmake \
        cuda-command-line-tools-$(cut -f1,2 -d- <<< ${CUDA//./-}) \
        git \
        hmmer \
        kalign \
        tzdata \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove --yes \
    && apt-get clean

# Compile HHsuite from source. Our db_preset/model_preset combination below
# never actually calls hhblits or hhsearch, but run_alphafold.py's startup
# checks require both binaries to be importable regardless of preset.
RUN git clone --branch v3.3.0 --single-branch https://github.com/soedinglab/hh-suite.git /tmp/hh-suite \
    && mkdir /tmp/hh-suite/build \
    && pushd /tmp/hh-suite/build \
    && cmake -DCMAKE_INSTALL_PREFIX=/opt/hhsuite .. \
    && make -j && make install \
    && ln -s /opt/hhsuite/bin/* /usr/bin \
    && popd \
    && rm -rf /tmp/hh-suite

# Install Miniconda package manager.
RUN wget -q -P /tmp \
  https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && rm /tmp/Miniconda3-latest-Linux-x86_64.sh

# Python 3.11: AlphaFold's model code uses typing.dataclass_transform, which
# needs 3.11+, and jax==0.4.26 (pinned below) has no wheels past 3.12.
ENV PATH="/opt/conda/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/conda/lib:$LD_LIBRARY_PATH"
ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS="yes"
RUN conda install --quiet --yes conda==24.11.1 pip python=3.11 \
    && conda install --quiet --yes --channel nvidia cuda=${CUDA_VERSION} \
    && conda clean --all --force-pkgs-dirs --yes

# Conda's own libffi shadows the system one via LD_LIBRARY_PATH above, which
# breaks git's https helper (symbol lookup error against libp11-kit) for the
# git clone right below -- and anything else needing network via git/curl
# for the rest of this build. Must come before that clone, not after it.
RUN ln -sf /usr/lib/x86_64-linux-gnu/libffi.so.7 /opt/conda/lib/libffi.so.7

# Fetch AlphaFold, pinned to the commit its requirements.txt / docker/Dockerfile
# were read from while authoring this task (2026-04-22, HEAD of main at the time).
ENV ALPHAFOLD_COMMIT=c77e5d2a8961d1a353632c462914ff0a32a950f6
RUN git clone https://github.com/google-deepmind/alphafold.git /app/alphafold \
    && cd /app/alphafold \
    && git checkout ${ALPHAFOLD_COMMIT}

RUN wget -q -P /app/alphafold/alphafold/common/ \
  https://git.scicore.unibas.ch/schwede/openstructure/-/raw/7102c63615b64735c4941278d92b554ec94415f8/modules/mol/alg/src/stereo_chemical_props.txt

# Exact pins from AlphaFold's own requirements.txt, plus the CUDA-matched
# jax/jaxlib build from upstream's jax-releases wheel index (cuda12+cudnn89,
# matching the cudnn8-runtime base image and CUDA 12.2 above).
RUN pip3 install --upgrade pip --no-cache-dir \
    && pip3 install -r /app/alphafold/requirements.txt --no-cache-dir \
    && pip3 install --upgrade --no-cache-dir \
      jax==0.4.26 \
      jaxlib==0.4.26+cuda12.cudnn89 \
      -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

# Open-source PyMOL for rendering predicted structures (pdb/mmcif) as PNGs.
# --no-deps: pymol-open-source's numpy constraint is unpinned, and without
# --no-deps pip silently upgrades the numpy==1.24.3 that AlphaFold's own
# requirements.txt just pinned above (to numpy 2.x) -- jaxlib/tensorflow-cpu
# here were built against NumPy 1.x's C-API, so that upgrade would break
# AlphaFold at runtime despite the image still building successfully. numpy
# is already present and sufficient for pymol; no other deps are needed.
RUN pip3 install --no-cache-dir --no-deps pymol-open-source==3.2.0a0

# Add SETUID bit to the ldconfig binary so that non-root users can run it.
RUN chmod u+s /sbin/ldconfig.real

# We need to run `ldconfig` first to ensure GPUs are visible, due to some
# quirk with Debian. This wrapper is a convenience only -- unlike upstream's
# own Dockerfile, it is NOT set as the image ENTRYPOINT, since the harness
# that runs this task execs solution/tests scripts directly.
WORKDIR /app/alphafold
RUN echo $'#!/bin/bash\n\
ldconfig\n\
python /app/alphafold/run_alphafold.py "$@"' > /app/run_alphafold.sh \
  && chmod +x /app/run_alphafold.sh

# ---------------------------------------------------------------------------
# Task-specific: AlphaFold-Multimer weights + placeholder "databases" that
# let the pipeline start up without the ~2.6 TB of real BFD/Uniclust30/
# MGnify/UniRef90/PDB70/PDB-seqres/UniProt genetic databases. See README.md
# for the full design rationale. In short:
#   - The 5 AlphaFold-Multimer v3 model parameter files (~1.8 GB) are real,
#     downloaded below.
#   - `small_dbs/*_placeholder.fasta` and `pdb_seqres/*_placeholder.fasta`
#     are NOT real sequence databases. They only need to exist on disk so
#     run_alphafold.py's DataPipeline can construct its jackhmmer/hmmsearch
#     wrapper objects (which validate the database path exists at
#     construction time). Pointing the pipeline at them with
#     --use_precomputed_msas=false gives a valid but low-quality
#     single-sequence-only run (no real homologs found) -- a safe fallback
#     that doesn't crash, not a shortcut to a good answer.
#   - Deliberately NOT bundled: a precomputed real MSA. Getting real homology
#     information for the target is left to the agent -- see instruction.md.
# ---------------------------------------------------------------------------

# AlphaFold-Multimer v3 model parameters. Download the full parameter tar
# (all monomer + pTM + multimer checkpoints, ~5.2 GiB) and keep only the 5
# multimer_v3 npz files (~1.8 GB) that this task's --model_preset=multimer
# needs; the tar itself is removed in the same layer so it isn't kept twice.
RUN mkdir -p /opt/af_multimer/data/params \
    && wget -q -O /tmp/alphafold_params.tar \
      https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar \
    && tar --extract --file=/tmp/alphafold_params.tar \
      --directory=/opt/af_multimer/data/params \
      --wildcards 'params_model_*_multimer_v3.npz' \
    && rm /tmp/alphafold_params.tar

# Placeholder "databases" (never searched -- see note above) and the
# always-on template search's inputs (empty result by design: the
# placeholder pdb_seqres has one unrelated 3-residue entry so hmmsearch has
# a well-formed, non-empty file to run against, and `pdb_mmcif/mmcif_files`
# holds one dummy .cif purely so TemplateHitFeaturizer's "at least one CIF
# present" startup check passes; neither is ever parsed for real because the
# search comes back with zero hits).
COPY small_dbs /opt/af_multimer/data/small_dbs
COPY pdb_seqres /opt/af_multimer/data/pdb_seqres
COPY pdb_mmcif /opt/af_multimer/data/pdb_mmcif

# The target FASTA. No precomputed MSA is bundled -- see instruction.md.
COPY fasta /opt/af_multimer/fasta
