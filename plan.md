# Evaluation Strategy: Symmetric Folding & Generation Benchmark (v1)

## Theme

Every task in this benchmark (`rfdiffusion`, `af_multimer`, `esmfold`, `unifold_symmetry`,
`combfold`, `symprofold`) asks a coding agent to use a real structural-biology tool to
produce a protein structure with a specific **symmetric** shape. Right now every task's
`tests/test_outputs.py` is a stub (`pass`) — there is no real verifier yet.

v0 of this plan (see git history) designed a six-layer, per-tool-adapter verifier that
parsed each tool's own confidence-metric format (pLDDT columns, `weightedTransScore`,
ChimeraX's own score, ...). That's the wrong amount of complexity for a first pass, and
the per-tool parsing was the *only* thing forcing adapters in the first place. This
version throws that out.

## The contract: exactly one PDB, one PNG, zero adapters

**The verifier only ever looks at two files, with fixed names, identical across all six
tasks:**

- `/outputs/structure.pdb`
- `/outputs/render.png`

No per-task config, no per-tool metric parsing, no knowledge of which underlying tool
produced the file. One `test_outputs.py`, byte-identical across all six `tests/`
directories.

**Action item:** today's `instruction.md` files say "output the files to /outputs" or
similar loose language, and af_multimer/etc. don't pin down an exact filename. All six
need a one-line edit to require these exact two paths. This is the only place any
task-specific work remains — after that, the verifier code itself never needs to change
per task.

## The three checks

### 1. PDB validity + simple geometric checks
- Parses cleanly via `Bio.PDB.PDBParser(QUIET=False)` — malformed records are errors, not
  silently skipped.
- No NaN/Inf coordinates.
- CA-CA consecutive distance ≈3.8 Å within tolerance (catches broken/teleported chains).
- No severe steric clashes (any two non-bonded heavy atoms <1.5 Å apart) — this alone
  makes a hand-fabricated or hallucinated PDB very hard to fake, since real bond geometry
  essentially never happens by accident.

### 2. Symmetry, read straight off the coordinates
One routine, no per-task parameters, branching only on what's actually in the file:
- **Multiple chains present** (af_multimer, unifold_symmetry, combfold, symprofold):
  group chains by residue count, and for each same-length pair, superpose CA atoms with
  `Bio.PDB.Superimposer` (Kabsch) and compute RMSD. Pass if at least two chains superpose
  within a tolerance (e.g. RMSD < 2.5 Å) — i.e. the assembly actually contains repeated,
  equivalent subunits, not just multiple unrelated chains.
- **Single chain** (rfdiffusion's donut): check the backbone closes into a loop (first and
  last CA within a few Å of each other) and is roughly annular rather than an extended
  blob (low variance in each CA's distance from the backbone centroid — a ring has ~constant
  radius, an arbitrary fold doesn't).
This needs no knowledge of the *expected* symmetry order (C2 vs C6 vs whatever) — it just
asks "is there real repeated/rotational structure here," which is enough for a first pass
and is exactly what's checkable generically from one PDB with no side information.

### 3. Does it look right? (VLM judge on the render)
Feed `/outputs/render.png` to a vision-capable model with a narrow prompt:
- "Does this image show a well-formed protein structure, not a broken render or a jumble
  of disconnected atoms?"
- "Does it show a symmetric/repeating arrangement — e.g. a closed ring with a visible
  central hole, or multiple equivalent subunits arranged around a common axis?"
Kept exactly as proposed — this is the check best suited to catching things the numeric
checks miss (e.g. an RMSD-symmetric-on-paper structure that's visually a collapsed mess).

## Scoring (v1)

Keep today's harbor wiring exactly as-is: all three checks must pass →
`echo 1 > reward.txt`, otherwise `0`. No graded/weighted score yet — not worth the
complexity until there's real trial data showing binary pass/fail is too coarse.

## Implementation

- One shared `tests/test_outputs.py` (or a tiny shared module imported by an identical
  stub in each task) covering checks 1–2 with BioPython + numpy — light enough to install
  inline in `tests/test.sh` alongside the existing `uvx --with pytest ...` call.
- Check 3 needs a real API key in `[verifier.env]` (currently empty in every task.toml)
  and verifier-side network egress to whichever vision model is used.
- Update all six `instruction.md` files to require the exact `/outputs/structure.pdb` /
  `/outputs/render.png` paths.

## Deliberately deferred (not v1)

These were in the original six-layer design and are real ideas, just not worth the
complexity until v1 is running against real (non-oracle) agent trials:
- **Tool-native confidence metrics** (pLDDT/ipTM/`weightedTransScore`) — this is what
  required per-task adapters in the first place; skip it entirely for now.
- **Independent cross-checking of self-reported metrics** — moot if we're not reading
  them.
- **Reproducibility re-run** (agent leaves a script, verifier reruns it on a held-out
  seed/target to catch fabricated one-off outputs) — the strongest anti-cheating check,
  but roughly doubles verifier cost/runtime and needs GPU access in the verifier
  environment. Worth revisiting once there's evidence agents are gaming the simple
  checks, not before.

## Open risks / questions

- **Threshold calibration** (RMSD tolerances, clash distance, closed-loop tolerance) are
  starting guesses — expect to revisit after the first batch of real agent trials.
- **`esmfold`'s check 2** always takes the single-chain branch and will never show
  multi-chain symmetry — it's a legitimate no-symmetry control case, but worth being
  explicit that it's graded only on checks 1 and 3.
- **VLM judge noise** — consider a supermajority over a few calls if it proves flaky as a
  gate rather than averaging into a soft score.
