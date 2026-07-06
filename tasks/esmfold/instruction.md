Hello! Please predict the 3D structure of Top7 (PDB 1QYS), a 93-residue de novo
designed protein with no natural homolog, using ESMFold.

Sequence:
DIQVQVNIDDNGKNFDYTYTVTTESELQKVLNELMDYIKKQGAKRVRISITARTKKEAEKFAAILIKVFAELGYNDINVTFDGDTVTVEGQLE

Use esm.pretrained.esmfold_v1() (weights are already cached in this
environment) to fold the sequence into a PDB file, then use pymol to render
the predicted structure as a PNG.

ESMFold writes per-residue pLDDT (0-100 confidence scale) into the B-factor
column of its output PDB. Check that the mean pLDDT across all residues is
greater than 70.

Do all scratch/intermediate work under /outputs/tmp, and output final files to /outputs
