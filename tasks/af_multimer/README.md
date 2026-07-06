# raftbioworks/af_multimer

## Design notes

Target: the *E. coli* DNA polymerase III beta sliding clamp (gene dnaN, PDB 2POL),
a genuine ring-shaped homodimer (366 residues/chain, C2) that closes around DNA --
verified against RCSB's own structure page and FASTA endpoint
(https://www.rcsb.org/structure/2POL). Chosen over the original GCN4 leucine
zipper target specifically because it's a real donut shape (visible central
hole), not a linear coiled-coil, matching this benchmark's symmetric-folding
theme.

Earlier version of this task bundled a real, precomputed MSA (fetched once via
ColabFold's public API) directly into the image, on the reasoning that full
genetic-database search is infeasible to bake in or run within an agent's
timeout. On reflection that made the task too easy: handing over the *sequence*
to predict is a legitimate task input, but handing over the *MSA* hands over the
one genuinely hard part of running a real structure-prediction pipeline. This
version deliberately does not bundle an MSA. The placeholder "databases" remain
as a safe (but low-quality, single-sequence-only) fallback so the pipeline
doesn't hard-crash if the agent does nothing about it; getting a good score
requires the agent to actually go find real homology information itself, using
the outbound network access this environment provides. See /plan.md at the repo
root for the fuller reasoning behind this tradeoff (determinism/reliability of a
live third-party dependency vs. task difficulty).
