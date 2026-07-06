Hello! Please use UF-Symmetry (the symmetric-assembly mode of Uni-Fold, installed at
/opt/Uni-Fold) to predict the structure of the C2-symmetric homodimer formed by the
ColE1 Rop protein (UniProt P03051, PDB 1ROP), a classic 63-residue four-helix-bundle
dimer.

The asymmetric unit (a single Rop chain) is at /data/fastas/rop.fasta.

Note on the MSA: Uni-Fold's normal pipeline (homo_search.py) builds an MSA by
searching UniRef90/MGnify/BFD/Uniclust30, which together are several terabytes and
are not available in this environment. A real MSA for this exact sequence has
already been precomputed for you (via ColabFold's remote MMseqs2 API) and is
bundled at /data/msa_precomputed/rop (chains.txt, A.feature.pkl.gz,
A.uniprot.pkl.gz) in the layout UF-Symmetry's feature loader expects. You do not
need, and should not attempt, to run any genetic search yourself -- point
inference directly at this precomputed feature directory.

Run UF-Symmetry's symmetric inference script (unifold/inference_symmetry.py) with
symmetry group C2, the bundled features as input, and the provided model
parameters (uf_symmetry.pt) to predict the dimer.

Success criteria:
- The final predicted structure is a two-chain (C2) assembly, each chain 63
  residues, and the two chains are related by a true symmetry operation (e.g.
  superimposing chain A onto chain B in PyMOL gives an RMSD well under 1 Angstrom
  -- UF-Symmetry builds the assembly by applying the symmetry operator to a single
  predicted subunit, so a non-symmetric output means something went wrong).
- The mean predicted LDDT (pLDDT) across all residues is >= 0.7. Note this
  codebase reports pLDDT on a 0-1 scale (not the usual 0-100 AlphaFold scale) in
  both its per-residue arrays and the B-factor column of the output PDB.
- Use PyMOL to render the final predicted assembly (pdb/mmcif) as a PNG so the
  twofold symmetry is visible.

Do all scratch/intermediate work under /outputs/tmp, and output final files
(predicted structure, PNG render, and a short summary of the pLDDT/symmetry
checks) to /outputs.
