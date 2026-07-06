# Evaluation Strategy: Symmetric Folding & Generation Benchmark

## Theme

Every task in this benchmark (`rfdiffusion`, `af_multimer`, `esmfold`, `unifold_symmetry`,
`combfold`, `symprofold`) asks a coding agent to use a real structural-biology tool to
produce a protein structure with a specific **symmetric** shape — a cyclic donut, a
symmetric homodimer, a multi-chain assembly, etc. The thing being graded is not "did a
file appear in `/outputs`" but "did the agent correctly operate a real scientific tool to
produce a structurally valid, correctly-symmetric result, and can it do so again."

Right now every task's `tests/test_outputs.py` is a stub (`pass`) copied from the
template — there is no real verifier yet. This document proposes what should replace it.

## Design goals

1. **Objective and automatable.** No human in the loop; runs inside `tests/test.sh`'s
   pytest invocation within the existing `[verifier] timeout_sec` budget.
2. **Tool-agnostic where possible.** Six tools emit six different file layouts and
   confidence metrics (pLDDT, ipTM, `weightedTransScore`, ...). The scoring *engine*
   should be shared; only a thin per-task adapter should be tool-specific.
3. **Symmetry is a first-class check, not an afterthought.** This is the one property
   every task shares — the verifier should check it geometrically, not just trust
   whatever confidence number the model self-reports.
4. **Hard to game.** The agent has a full shell inside the environment. A verifier that
   only inspects the final PDB/PNG can be satisfied by a hand-fabricated file that never
   touched the actual model. The strategy below is built in layers specifically so that
   fabrication has to defeat *all* of them, including one designed to catch fabrication
   directly (Layer 5).
5. **Graded, not just binary.** `reward.txt` currently gets a literal `1`/`0` from a
   pytest exit code. A single pass/fail throws away signal that matters for a benchmark
   (e.g. "technically symmetric but low confidence" vs. "correct and confident"). See
   "Scoring" below for how to keep today's harbor wiring but still emit a graded reward.

## The six layers

### Layer 0 — Artifact & format validity
Cheapest possible gate, run first, short-circuits everything else on failure.
- The expected output file exists under `/outputs` (not `/outputs/tmp` — that's scratch,
  per the instruction.md convention already in place).
- It parses as a structurally valid PDB or mmCIF via BioPython (`Bio.PDB.PDBParser` /
  `MMCIFParser`, `QUIET=False` so malformed records surface as errors, not silent skips).
- No NaN/Inf coordinates, no zero-occupancy-only models, atom count and chain count are
  in the range the task expects (e.g. combfold's 12-chain complex should have 12 chains,
  not 1 or 40).

### Layer 1 — Physical plausibility
Independent of what the model claims about itself.
- Bond lengths / bond angles within tolerance of standard values (a cheap check: CA-CA
  consecutive distance ≈3.8 Å ± tolerance catches broken chains and teleported atoms).
- No severe steric clashes (any two non-bonded heavy atoms closer than ~1.5 Å is a
  hallmark of a garbage or synthetic/hand-written structure).
- These two checks alone catch most "the agent wrote a fake PDB by hand" attempts, since
  hand-written or LLM-hallucinated coordinates essentially never satisfy real bond
  geometry by chance.

### Layer 2 — Symmetry verification (the throughline of this whole benchmark)
A single shared routine, parameterized by the expected symmetry group (`C2`, `C3`, `C6`,
`D2`, ...) and which chains/subunits are supposed to be equivalent:
1. Extract CA-atom coordinate sets for each candidate symmetric unit (each chain, or each
   ASU repeat for cyclic assemblies like RFdiffusion's donut or SGNet-style folds).
2. For every pair of nominally-equivalent units, run Kabsch/`Bio.PDB.Superimposer` to
   find the best-fit rigid rotation and report post-superposition RMSD.
3. For cyclic (Cn) targets, additionally fit a symmetry axis (e.g. via the rotation
   matrices relating consecutive units — their common rotation axis/angle should be
   consistent) and check the rotation angle matches `360°/n` within tolerance.
4. Report a single **symmetry RMSD** metric and, for Cn/Dn targets, an **axis-angle
   error**. Threshold both per task.
This is the check most specific to this benchmark's theme, and the one most likely to
catch a superficially-plausible but wrong answer (e.g. a real, well-folded protein that
just isn't the requested oligomeric symmetry).

### Layer 3 — Tool-native confidence metrics
Parse whatever the specific tool actually reports and threshold it:
- RFdiffusion/AF-Multimer/UniFold Symmetry/ESMFold: pLDDT (mind the 0–1 vs 0–100 scale
  difference already noted for UF-Symmetry), ipTM/pTM where available.
- CombFold: `assembled_results/confidence.txt`'s `weightedTransScore`.
- SymProFold: whatever confidence score its ChimeraX pipeline writes into its assembly
  output for the chosen axis/oligomer.
Necessary but *not sufficient* — a model can be "confident" about a self-consistent but
wrong or degenerate structure, which is exactly why Layers 1, 2, and 4 exist.

### Layer 4 — Independent cross-check of self-reported metrics
Don't just `cat` the tool's own confidence file and trust it. At minimum:
- Confirm the confidence file/column is actually populated by the real tool's output
  writer (each of these tools has a distinguishable output format/header — e.g.
  AlphaFold's B-factor-as-pLDDT convention, its specific `ranking_debug.json` schema,
  UniFold's feature-dict pickle naming) rather than a plausible-looking value stuiffed in
  by hand.
- Where cheap to do so, recompute one metric independently of the tool's own report
  (e.g. an independent per-residue confidence estimate, or at minimum recomputing overall
  structure quality via Layer 1's geometric checks and confirming it correlates with the
  claimed confidence — a structure claiming pLDDT 95 with visible clashes/broken chains
  is a red flag, not just low confidence).

### Layer 5 — Reproducibility / anti-fabrication re-run
The strongest defense against reward hacking, and directly addresses the "did the agent
actually automate the tool, or fabricate one lucky file" question:
1. Require the agent to leave a runnable script behind (already possible today — nothing
   in `/outputs` structure currently mandates this; propose adding it as an explicit
   instruction.md requirement, e.g. `/outputs/run.sh` that takes a seed/target parameter).
2. The verifier re-invokes that script with a **held-out parameter** the agent didn't see
   spelled out in the instructions — a different random seed for RFdiffusion, a different
   (but structurally analogous) target sequence or symmetry order for the others.
3. Re-run Layers 0–3 against the *new* output. A hardcoded/fabricated pipeline will fail
   this immediately (wrong shape, parse error, or literally the same cached file); a
   genuine, correctly-wired pipeline should produce a fresh, similarly-valid result.
This does roughly double verifier runtime/cost (one extra model inference), so it should
be weighted as a bonus/gate rather than always run at full cost — see "Cost" below.

### Layer 6 — Qualitative judge on the rendered image
Every task already renders PDB/mmCIF to PNG via pymol (baked into every Dockerfile in
this batch). Feed that PNG to a vision-capable model with a narrow, structured prompt:
- "Does this image show a well-formed protein structure (not a jumble of disconnected
  atoms or an obviously broken render)?"
- "Does the assembly exhibit the requested symmetry/shape (e.g. a closed ring/donut with
  a visible central hole; a clean two-fold dimer; N equivalent subunits arranged around a
  common axis)?"
Use this as a **soft, ensemble signal alongside the numeric layers, not a sole gate** —
LLM/VLM judges are noisy and shouldn't be a single point of failure for a 0/1 reward, but
they're good at catching the specific failure mode numeric thresholds miss: a technically
symmetric-by-RMSD arrangement that is visually degenerate (e.g. two chains collapsed
into each other rather than meaningfully assembled).

## Per-task mapping

| Task | Symmetry check (Layer 2) | Primary metric (Layer 3) | Held-out re-run param (Layer 5) |
|---|---|---|---|
| `rfdiffusion` | Cn axis fit on the single-chain backbone (closed ring, hole in middle) | pTM, RMSD to designed contig | different ring size / random seed |
| `af_multimer` | C2 (homodimer) chain-pair RMSD | pLDDT, ipTM+pTM | different random seed |
| `esmfold` | N/A (single chain, no symmetry) — Layers 0/1/3/6 only | pLDDT | different (but similarly-sized) target sequence |
| `unifold_symmetry` | C2 axis fit (Rop dimer) | pLDDT (0–1 scale) | different precomputed-MSA target bundled at build time |
| `combfold` | 6-fold pairwise RMSD across the two 6-mer rings (A0×6, G0×6) | `weightedTransScore` | different subset of the bundled pairwise predictions |
| `symprofold` | axis fit per SymProFold's own detected symmetry group | SymProFold's own reported axis/assembly confidence | the other bundled oligomer series (`12x4` vs `23x4`) |

`esmfold` is the odd one out (no symmetry, single chain) — worth deciding whether it
belongs in a *symmetric folding* benchmark at all, or whether it's meant as a baseline/
control task specifically because it has no symmetry to check.

## Scoring: keep today's wiring, add graded signal underneath

`tests/test.sh` currently does:
```bash
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
echo $?  # 1 or 0 into /logs/verifier/reward.txt
```
Two ways to get graded signal out of this without changing the harbor-facing contract:
1. **Simplest:** keep the pass/fail gate exactly as-is, built from a conjunction of hard
   gates (Layers 0/1/2 must all pass) plus a threshold on Layers 3/4 — this is what today's
   `rfdiffusion`/`af_multimer`/etc. instruction.md success criteria already describe, just
   not yet wired into `test_outputs.py`.
2. **Richer:** have `test_outputs.py` write a computed float (e.g. a weighted sum of the
   layers, or a straight pass-rate across the layer checks) directly into
   `/logs/verifier/reward.txt` instead of `test.sh`'s current `1`/`0` echo, and treat
   pytest's own pass/fail as a coarser "did verification *run* successfully" signal.
   `reward.txt` accepts any value harbor parses as a float — confirmed directly in the
   installed harbor package: `verifier/verifier.py`'s `_parse_reward_text` returns
   `dict[str, float | int]`, not a bool/int-only type. The aggregation harbor already
   shows (`Mean: 1.000` across trials) works the same whether the underlying value is
   binary or continuous.
Recommend starting with (1) per task (fast to implement, matches existing instruction.md
thresholds already drafted) and migrating to (2) once there's enough trial data to know
what a meaningful continuous scale looks like per tool.

## Implementation notes

- **Shared verifier library.** Layers 0–2 (parsing, geometry, symmetry-axis fitting) are
  identical across all six tasks and should live in one shared Python module (e.g.
  vendored into each task's `tests/` via a common file, or published as a small internal
  package) rather than copy-pasted six times. Only the per-task adapter (which file to
  read, which chains are equivalent, which confidence field to parse) should differ.
- **Dependencies.** The verifier environment needs BioPython (+ `gemmi` if mmCIF parsing
  needs more than BioPython's `MMCIFParser` handles) and numpy for the Kabsch fit — these
  are light enough to install directly in `tests/test.sh` alongside the existing
  `uvx --with pytest ...` invocation, no need to touch the agent-side Dockerfiles.
- **Layer 6 needs a real API key in the verifier environment.** `[verifier.env]` in each
  `task.toml` is currently empty; calling a vision model from inside `test_outputs.py`
  means adding a credential there (mirrors the `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN`
  wiring already worked out for the agent side earlier this session) and giving the
  verifier's `network_mode` egress to whichever provider is used.
- **Layer 5 roughly doubles verifier cost/runtime** (one extra model inference per
  trial) and needs GPU access in the verifier's environment for the GPU-backed tasks,
  which today's `[verifier]` config doesn't request. Worth gating behind a flag/sampling
  rate (e.g. run the reproducibility re-run on 1-in-N trials) rather than every trial,
  once this is live for real evaluation runs rather than one-off smoke tests.

## Open risks / questions

- **Threshold calibration.** Every numeric threshold mentioned above (pLDDT >0.7,
  symmetry RMSD tolerance, clash distance cutoff) is a starting guess, not something
  empirically tuned against real model runs yet — expect to revisit after the first batch
  of real (non-oracle) agent trials.
- **`esmfold`'s fit in a *symmetric* folding benchmark** — flagged above, worth an
  explicit decision rather than leaving it ambiguous.
- **Layer 6 noise.** VLM judges can be inconsistent run-to-run; if used as a gate rather
  than a soft signal, consider averaging over a few calls or requiring a supermajority.
- **Layer 5 cost/latency** may make it impractical to run on every trial at benchmark
  scale — needs a decision on sampling rate once real usage volume is known.
