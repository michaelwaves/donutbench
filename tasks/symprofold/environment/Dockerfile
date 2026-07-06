FROM ubuntu:22.04

# SymProFold (https://github.com/symprofold/SymProFold_code) does not predict
# protein structures itself: it post-processes AlphaFold-Multimer output
# (ranked PDBs + ranking_debug.json) through UCSF ChimeraX to identify
# symmetry axes and build the final assembly. There is no neural-network
# inference here, so no GPU is needed for this image - see the design note
# at the top of instruction.md for the full reasoning and for why a small
# bundle of precomputed AlphaFold-Multimer predictions is baked in below
# instead of running a live genetic-database search.

ENV DEBIAN_FRONTEND=noninteractive
ENV SYMPROFOLD_HOME=/opt/SymProFold

# Shared libraries ChimeraX's .deb depends on even in --nogui/--offscreen
# mode (no X server or GPU is used at runtime; --offscreen renders via
# OSMesa for the PNG snapshots the pipeline produces).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git python3 python3-pip \
    libgl1 libegl1 libglu1-mesa libosmesa6 \
    libx11-6 libx11-xcb1 libxcb1 libxext6 libxrender1 libxi6 libxtst6 \
    libxrandr2 libxfixes3 libxdamage1 libxcomposite1 libxcursor1 \
    libxkbcommon0 libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# UCSF ChimeraX 1.6 - the exact version SymProFold's README requires, and its
# only structural-computation runtime (domain separation, superposition,
# symmetry-axis assembly all run as ChimeraX scripts). The download page
# gates the .deb behind a non-commercial-use EULA click-through with no
# stable static URL; accept it non-interactively and follow the resulting
# signed redirect. This CGI flow is undocumented and could break if UCSF
# changes it; if this RUN step starts failing, check
# https://www.cgl.ucsf.edu/chimerax/download.html for the current EULA flow
# and .deb filename pattern.
RUN curl -sL -X POST \
      -d "file=1.6/ubuntu-22.04/ucsf-chimerax_1.6ubuntu22.04_amd64.deb&choice=Accept" \
      https://www.cgl.ucsf.edu/chimerax/cgi-bin/secure/chimerax-get.py \
      -o /tmp/chimerax_redirect.html \
    && CHIMERAX_URL=$(grep -oP '(?<=url=)[^"]+' /tmp/chimerax_redirect.html | head -1) \
    && curl -sL "https://www.cgl.ucsf.edu${CHIMERAX_URL}" -o /tmp/ucsf-chimerax.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/ucsf-chimerax.deb \
    && rm -f /tmp/ucsf-chimerax.deb /tmp/chimerax_redirect.html \
    && rm -rf /var/lib/apt/lists/*

# Python modules SymProFold's own scripts import (per its README), installed
# into ChimeraX's bundled Python interpreter via ChimeraX's built-in pip -
# SymProFold's scripts run inside ChimeraX's Python, not the system one.
# networkx>=3.3 requires Python>=3.10; ChimeraX 1.6's bundled interpreter is
# older than that, so pin to the newest release its pip actually accepts.
RUN chimerax -m pip install --no-cache-dir \
    beautifulsoup4==4.12.3 \
    matplotlib==3.9.2 \
    networkx==3.2.1 \
    numpy==1.26.4 \
    requests==2.32.3

# SymProFold pipeline code plus its Domain_Separator submodule.
RUN git clone --depth 1 https://github.com/symprofold/SymProFold_code.git "$SYMPROFOLD_HOME" \
    && rm -rf "$SYMPROFOLD_HOME/tools/domain_separator" \
    && git clone --depth 1 https://github.com/symprofold/Domain_Separator.git \
         "$SYMPROFOLD_HOME/tools/domain_separator"

# Small bundle of real, precomputed AlphaFold-Multimer predictions for
# SymProFold's own published tutorial target: the S-layer protein
# A0A1M5ZCF8 (Vibrio aerogenes). Sourced from SymProFold's public tutorial
# data repo (github.com/symprofold/SymProFold_Tutorial_Data) via a sparse
# checkout of only the top-ranked monomer prediction (needed for domain
# separation) and the two oligomeric subchain series (needed for the two
# symmetry axes of the final assembly) - roughly 30 MB total, not the full
# ~215 MB tutorial folder.
RUN git clone --depth 1 --filter=blob:none --sparse \
      https://github.com/symprofold/SymProFold_Tutorial_Data.git /tmp/tutorial_data \
    && cd /tmp/tutorial_data \
    && git sparse-checkout init --no-cone \
    && git sparse-checkout set \
         section4_begin/A0A1M5ZCF8_x1 \
         section4_begin/A0A1M5ZCF8_12x4 \
         section4_begin/A0A1M5ZCF8_23x4 \
         section4_begin/A0A1M5ZCF8.fa \
         section4_begin/A0A1M5ZCF8_d.fa \
         section4_begin/A0A1M5ZCF8_12x4.fa \
         section4_begin/A0A1M5ZCF8_23x4.fa \
    && mkdir -p "$SYMPROFOLD_HOME/preassemblies/Vaer" \
    && cp -r /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_x1 \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_12x4 \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_23x4 \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8.fa \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_d.fa \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_12x4.fa \
             /tmp/tutorial_data/section4_begin/A0A1M5ZCF8_23x4.fa \
             "$SYMPROFOLD_HOME/preassemblies/Vaer/" \
    && rm -rf /tmp/tutorial_data

WORKDIR ${SYMPROFOLD_HOME}
