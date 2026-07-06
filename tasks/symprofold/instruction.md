<!--
Design note on scope:
SymProFold does not itself predict protein structures. Per its own README, it
"combines AlphaFold predictions with general symmetry considerations" and
requires a separate AlphaFold-Multimer installation "not necessarily on the
same system as the SymProFold installation". Every pipeline script under
lib/ and preassemblies/ consumes pre-existing AlphaFold-Multimer output
folders (ranked_*.pdb, ranking_debug.json) - it never runs MSA/genetic-
database search or structure inference itself. To avoid the AlphaFold
genetic-database problem entirely, this task bundles a small, real set of
precomputed AlphaFold-Multimer predictions (the monomer and two oligomeric
subchain series for SymProFold's own published tutorial target) directly in
the Docker image, and asks the agent to run only the SymProFold
post-processing/assembly steps against that bundled data.
-->

Hello! This environment has SymProFold and its Domain_Separator submodule installed at
`/opt/SymProFold`, along with a headless UCSF ChimeraX (SymProFold's required runtime for
all structural operations).

Under `/opt/SymProFold/preassemblies/Vaer/` you'll find bundled, precomputed AlphaFold-Multimer
predictions for the S-layer protein **A0A1M5ZCF8** from *Vibrio aerogenes* - this is the exact
target SymProFold's own paper and tutorial use to demonstrate symmetric assembly prediction. The
bundled data covers:

- `A0A1M5ZCF8_x1/` - top-ranked monomer prediction (needed for domain separation)
- `A0A1M5ZCF8_12x4/` and `A0A1M5ZCF8_23x4/` - oligomer predictions for the two overlapping
  subchains (domains 1-2 and domains 2-3) that SymProFold combines into the final symmetric
  assembly

Your task: run the SymProFold pipeline on this bundled data to reproduce the symmetric assembly
of A0A1M5ZCF8. Concretely:

1. Rank the bundled predictions and separate the top-ranked monomer into structural domains
   (Domain_Separator, invoked through ChimeraX).
2. Determine the oligomeric state (rotational fold) supported by each subchain's predictions.
3. Build the final layer assembly by superposing the two symmetry axes, using
   `assemblies/Vaer_run.py` in the SymProFold repo as your reference recipe for this exact
   target (it already encodes which subchains/multiplicities to combine).

Run ChimeraX scripts headlessly, e.g. `chimerax --nogui --offscreen --script <script.py> --exit`.

Success criteria:
- A final assembly structure file (PDB or mmCIF) exists showing at least two repeated copies of
  the aligned domain (the two symmetry axes combined).
- For each of the two bundled subchains (`12x4`, `23x4`), report the top model's ipTM+pTM
  confidence score - from `ranking_debug.json` where present, or otherwise from the score
  SymProFold encodes directly in the ranked filename (e.g. `unrelaxed_rank00_0.873.pdb` ->
  0.873) - and confirm it exceeds 0.5 (SymProFold's own filtering threshold).
- Superposing the shared alignment domain across the assembled copies gives an RMSD < 2 Angstroms.
- Render the final assembly as a PNG (via ChimeraX or PyMOL) so the rotational symmetry is
  visually apparent.

Do all scratch/intermediate work under /outputs/tmp, and output final files to /outputs
