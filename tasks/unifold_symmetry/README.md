# raftbioworks/unifold_symmetry

## Design notes

UF-Symmetry (https://github.com/dptech-corp/Uni-Fold, `unifold/symmetry/`) predicts
symmetric protein assemblies from a single asymmetric-unit sequence plus a symmetry
group. Like AlphaFold(-Multimer), its default pipeline (`homo_search.py` /
`run_uf_symmetry.sh`) builds an MSA by searching UniRef90, MGnify, BFD, and
Uniclust30 (~3TB total) -- infeasible to bake into a Docker image or download
inside an agent's timeout.

Target: Hcp1 (PDB 1Y12, *Pseudomonas aeruginosa* PAO1 gene PA0085), a bacterial
type VI secretion system protein that assembles into a genuine hexameric ring
(~40 Angstrom internal diameter -- a real nanopore) -- verified against RCSB's
own structure page and FASTA endpoint (https://www.rcsb.org/structure/1Y12).
Chosen over the original ColE1 Rop target (a compact four-helix-bundle dimer,
not ring-shaped at all) specifically because it's an actual donut, matching this
benchmark's symmetric-folding theme, and because C6 exercises UF-Symmetry's
higher-order cyclic-assembly capability more meaningfully than a C2 dimer does.

An earlier version of this task bundled a real, precomputed MSA/feature bundle
(fetched once via `unifold/msa_remote.py` hitting ColabFold's public MMseqs2
API) directly into the image, specifically to avoid a live third-party
dependency at grading time. On reflection that made the task too easy: handing
over the *sequence* to predict is a legitimate task input, but handing over the
already-generated *features* hands over the one genuinely hard part of running
this pipeline for real. This version deliberately does not bundle anything --
Uni-Fold's own repo (cloned into the image at /opt/Uni-Fold) does ship
`unifold/msa_remote.py`, so a competent agent exploring the repo has a real,
first-party path to a good answer; a fabricated or lower-effort feature file
should show up as a low-confidence or non-symmetric result instead. See
/plan.md at the repo root for the fuller reasoning behind this tradeoff
(determinism/reliability of a live third-party dependency vs. task difficulty).

This new setup has *not* been re-verified end-to-end locally the way the
original Rop target was (that would require actually generating Hcp1 features
via a live network call, which is exactly the step now deliberately left to
the agent) -- the smoke test this task needs is a real (non-oracle) agent
trial, not another oracle build check.
