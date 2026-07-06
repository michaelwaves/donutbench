# raftbioworks/unifold_symmetry

## Design notes

UF-Symmetry (https://github.com/dptech-corp/Uni-Fold, `unifold/symmetry/`) predicts
symmetric protein assemblies from a single asymmetric-unit sequence plus a symmetry
group. Like AlphaFold(-Multimer), its default pipeline (`homo_search.py` /
`run_uf_symmetry.sh`) builds an MSA by searching UniRef90, MGnify, BFD, and
Uniclust30 (~3TB total) -- infeasible to bake into a Docker image or download
inside an agent's timeout.

Uni-Fold's feature loader (`unifold/inference_symmetry.py`) only needs a directory
of `{chain}.feature.pkl.gz` / `{chain}.uniprot.pkl.gz` / `chains.txt` per target;
it doesn't care how those files were produced. So instead of a live database
search (or a live call to a third-party MSA API during grading, which would add
an external flakiness/availability dependency to the benchmark), this task ships
a real MSA precomputed once, offline, using `unifold/msa_remote.py` (a
database-free feature generator that hits ColabFold's public MMseqs2 API,
https://api.colabfold.com) for one small target, and bakes the resulting feature
files directly into the Docker image. At grading time everything is fully local
and deterministic -- no network dependency for the MSA step.

Target: the ColE1 Rop protein (UniProt P03051, PDB 1ROP), a 63-residue helix-turn-
helix monomer that homodimerizes into a C2-symmetric four-helix bundle. It's a
textbook small symmetric assembly, short enough to predict quickly, and one where
getting the symmetry right is actually the point (a naive single-chain prediction
would miss the dimer interface entirely).

This setup (target sequence + precomputed MSA + model weights) was verified
end-to-end locally on CPU before this task was written: `inference_symmetry.py
--symmetry=C2` against the bundled features produced a proper two-chain assembly
(63 residues x 2) with mean pLDDT ~0.85 even under minimal (non-default)
recycling/ensemble settings.
