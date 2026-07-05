FROM rosettacommons/foundry:0.2.0-weights

WORKDIR /app/foundry

# Open-source PyMOL for rendering designed structures (pdb/mmcif) as PNGs.
RUN /app/foundry/.venv/bin/python -m ensurepip --upgrade && \
    /app/foundry/.venv/bin/python -m pip install --no-cache-dir pymol-open-source==3.2.0a0