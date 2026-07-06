Hello! Please assemble the full structure of a 12-chain protein complex using CombFold's Combinatorial Assembly algorithm

CombFold is installed at /opt/CombFold, with the C++ assembler already compiled at
/opt/CombFold/CombinatorialAssembler/CombinatorialAssembler.out. The complex has two unique
subunits, A0 and G0, each present in 6 copies. AlphaFold-Multimer predictions for pairs and
triples of these subunits, plus the subunits.json describing the complex, are provided at
/opt/combfold_example (subunits.json and a pdbs/ folder)

Run CombFold's assembly stage (scripts/run_on_pdbs.py) on this data to assemble the complex.
The assembler will look for full-length copies of A0 and G0 in the supplied PDBs, extract
their pairwise/triple-wise transformations, and combinatorially dock them into complete models

Confirm the run produced at least one assembled model with all 12 chains present (A through L,
matching subunits.json), and that its reported weightedTransScore (see
assembled_results/confidence.txt) is at least 70

Do all scratch/intermediate work under /outputs/tmp, and output final files to /outputs
