Hello! Please use UF-Symmetry (the symmetric-assembly mode of Uni-Fold, installed at
/opt/Uni-Fold) to predict the structure of Hcp1 (PDB 1Y12, *Pseudomonas aeruginosa*),
a protein that self-assembles into a genuine hexameric ring -- a real nanopore with a
visible central channel, C6 symmetry. This one should actually look like a donut.

The asymmetric unit (a single Hcp1 chain, 165 residues) is at
/data/fastas/hcp1.fasta.

Note on the MSA: Uni-Fold's normal pipeline (homo_search.py) builds an MSA by
searching UniRef90/MGnify/BFD/Uniclust30, which together are several terabytes and
are not available in this environment. No precomputed MSA or feature bundle is
provided either -- producing real input features for this sequence, if you want
them, is up to you. This environment does have outbound internet access.
UF-Symmetry's feature loader (unifold/inference_symmetry.py) just needs a
directory containing chains.txt / {chain}.feature.pkl.gz / {chain}.uniprot.pkl.gz
for the target -- it doesn't care how those files were produced. The Uni-Fold
repository you have locally at /opt/Uni-Fold may already include tooling for
generating such features without a local genetic database; it's worth exploring
what's in there before writing something from scratch.

Run UF-Symmetry's symmetric inference script (unifold/inference_symmetry.py) with
symmetry group C6, your generated features as input, and the provided model
parameters (uf_symmetry.pt) to predict the hexamer.

Success criteria:
- The final predicted structure is a six-chain (C6) assembly, each chain 165
  residues, arranged as a closed ring with a visible central hole -- not six
  disconnected or randomly-arranged copies. Superimposing any two chains in
  PyMOL should give an RMSD well under 1 Angstrom (UF-Symmetry builds the
  assembly by applying the symmetry operator to a single predicted subunit, so
  a non-symmetric output means something went wrong).
- The mean predicted LDDT (pLDDT) across all residues is >= 0.7. Note this
  codebase reports pLDDT on a 0-1 scale (not the usual 0-100 AlphaFold scale) in
  both its per-residue arrays and the B-factor column of the output PDB.
- Render the final predicted assembly as a PNG using PyMOL, from an angle that
  shows the ring/hole clearly (i.e. looking down the C6 symmetry axis).

Do all scratch/intermediate work under /outputs/tmp. Write your two final
deliverables to these exact paths:
- /outputs/structure.pdb -- the final predicted structure
- /outputs/render.png -- the PyMOL render
