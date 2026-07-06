FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libboost-all-dev \
      git \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      biopython==1.84 \
      numpy==1.26.4 \
      scipy==1.13.1

WORKDIR /opt
RUN git clone https://github.com/dina-lab3D/CombFold.git && \
    cd CombFold && \
    git checkout f16de0376075df310f20fe75ef4fb64b4422e55b

RUN cd /opt/CombFold/CombinatorialAssembler && make

COPY example_input /opt/combfold_example

WORKDIR /opt/CombFold
