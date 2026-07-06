"""
Shared verifier for the symmetric-folding-and-generation benchmark tasks.
See /plan.md at the repo root for the full design rationale.

DEVIATION FROM THE OTHER FIVE TASKS: this is the one deliberately non-symmetric
control task (ESMFold predicts a single chain with no oligomeric/ring
structure -- Top7 is a compact, non-repeating designed fold). The
symmetry-from-coordinates check is not applicable here and is omitted; this
file is otherwise identical in structure to the other five tasks' verifiers.
See plan.md's "Open risks" section for why this task is graded on structural
validity + the vision judge only, not symmetry.

Reads exactly two files the agent must produce:
  - /outputs/structure.pdb
  - /outputs/render.png

and applies two checks, both of which must pass:
  1. The PDB parses and is geometrically sane (no broken/teleported chain,
     no severe steric clashes).
  2. A vision model looking at the render agrees it's a well-formed protein
     structure.

test.sh runs pytest with -x (stop at first failure), so a broken structure
never reaches the network-calling check in (2).
"""

import base64
import json
import os
import urllib.error
import urllib.request

import numpy as np
from Bio.PDB import PDBParser
from scipy.spatial import cKDTree

STRUCTURE_PATH = "/outputs/structure.pdb"
RENDER_PATH = "/outputs/render.png"

CA_BOND_LENGTH = 3.8
CA_BOND_TOLERANCE = 1.0
MAX_BROKEN_BOND_FRACTION = 0.15

CLASH_DISTANCE = 2.0
MAX_CLASH_FRACTION = 0.01

VLM_JUDGE_PROMPT = """\
You are grading a rendered image of a predicted protein structure for a \
structure-prediction benchmark.

Answer one yes/no question, then reply with EXACTLY one line in the form \
`VERDICT: PASS` or `VERDICT: FAIL`, with a brief one-sentence reason before \
it.

1. Is this a well-formed rendering of a folded protein structure (not a \
broken or corrupted render, not a jumble of disconnected atoms, not an \
obviously unfolded/extended chain)?

VERDICT: PASS only if the answer is yes.\
"""


def _load_structure():
    """Returns the full Structure (all Models), not just the first Model.

    Some tools (observed: ChimeraX's PDB export) write each chain of a
    multi-chain assembly as its own MODEL/ENDMDL block instead of one MODEL
    containing all chains -- the classic single-Model assumption
    (`next(iter(structure))`) silently sees only the first chain in that
    case. `get_chains()`/`get_atoms()` traverse every Model, so this is
    correct for both that case and the ordinary single-Model case. (ESMFold
    itself only ever emits a single chain, but this file stays structurally
    consistent with the other five tasks' verifiers.)
    """
    assert os.path.isfile(STRUCTURE_PATH), f"missing {STRUCTURE_PATH}"
    parser = PDBParser(QUIET=False)
    return parser.get_structure("model", STRUCTURE_PATH)


def _ca_atoms(chain):
    return [res["CA"] for res in chain if res.has_id("CA")]


def test_structure_parses_and_has_atoms():
    structure = _load_structure()
    chains = list(structure.get_chains())
    assert len(chains) >= 1, "no chains in structure"
    total_ca = sum(len(_ca_atoms(chain)) for chain in chains)
    assert total_ca >= 4, "too few CA atoms to be a real structure"


def test_no_nonfinite_coordinates():
    structure = _load_structure()
    for atom in structure.get_atoms():
        assert np.all(np.isfinite(atom.get_coord())), (
            "non-finite atom coordinate found"
        )


def test_chain_geometry_is_sane():
    structure = _load_structure()
    for chain in structure.get_chains():
        coords = np.array([a.get_coord() for a in _ca_atoms(chain)])
        if len(coords) < 2:
            continue
        distances = np.linalg.norm(coords[1:] - coords[:-1], axis=1)
        broken = np.abs(distances - CA_BOND_LENGTH) > CA_BOND_TOLERANCE
        fraction_broken = broken.mean()
        assert fraction_broken <= MAX_BROKEN_BOND_FRACTION, (
            f"chain {chain.id}: {fraction_broken:.0%} of consecutive CA-CA "
            f"distances are far from the expected ~{CA_BOND_LENGTH} "
            "Angstrom bond length (broken/teleported backbone)"
        )


def test_no_severe_clashes():
    structure = _load_structure()
    chain_ids, seq_idx, coords = [], [], []
    chain_lengths = []
    for chain in structure.get_chains():
        ca = _ca_atoms(chain)
        chain_lengths.append(len(ca))
        for i, atom in enumerate(ca):
            chain_ids.append(chain.id)
            seq_idx.append(i)
            coords.append(atom.get_coord())
    coords = np.array(coords)
    n = len(coords)
    if n < 2:
        return
    chain_ids = np.array(chain_ids)
    seq_idx = np.array(seq_idx)

    # Large assemblies (dozens of chains, tens of thousands of CA atoms) make
    # an all-pairs O(n^2) distance matrix infeasible (a 15k-atom structure
    # would need a ~7 billion-entry array). A KD-tree only ever materializes
    # pairs that are actually within the clash distance.
    tree = cKDTree(coords)
    close_pairs = tree.query_pairs(r=CLASH_DISTANCE, output_type="ndarray")

    total_pairs = n * (n - 1) // 2
    adjacent_pairs = sum(max(0, length - 1) for length in chain_lengths)
    checked = total_pairs - adjacent_pairs
    if checked <= 0:
        return

    if len(close_pairs) == 0:
        clashes = 0
    else:
        i_idx, j_idx = close_pairs[:, 0], close_pairs[:, 1]
        seq_adjacent = (chain_ids[i_idx] == chain_ids[j_idx]) & (
            np.abs(seq_idx[i_idx] - seq_idx[j_idx]) <= 1
        )
        clashes = int((~seq_adjacent).sum())

    fraction = clashes / checked
    assert fraction <= MAX_CLASH_FRACTION, (
        f"{clashes}/{checked} non-bonded CA pairs are closer than "
        f"{CLASH_DISTANCE} Angstrom -- severe steric clashes"
    )


def _call_vision_judge(image_b64: str, prompt: str) -> str:
    """Ask a vision model to grade the render. Prefers OpenRouter
    (OPENROUTER_API_KEY, OpenAI-compatible chat completions API) over a
    direct Anthropic API key (ANTHROPIC_API_KEY), since this is a raw HTTP
    call this script controls end to end -- no need to go through the
    Claude-Code-CLI-specific ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN dance
    used on the agent side of this repo. Returns the judge's raw text reply.
    """
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if openrouter_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {openrouter_key}",
        }
        payload = {
            "model": os.environ.get("VERIFIER_MODEL", "anthropic/claude-haiku-4.5"),
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
    elif anthropic_key:
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        headers = {
            "content-type": "application/json",
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": os.environ.get("VERIFIER_MODEL", "claude-haiku-4-5-20251001"),
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
    else:
        raise AssertionError(
            "Neither OPENROUTER_API_KEY nor ANTHROPIC_API_KEY is set in the "
            "verifier environment -- cannot run the image judge. Set one of "
            "them in [verifier.env] in task.toml."
        )

    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise AssertionError(
            f"vision model API call failed: {exc.code} {exc.read().decode(errors='replace')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AssertionError(f"vision model API call failed: {exc}") from exc

    if openrouter_key:
        return body.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
    return "".join(
        block.get("text", "")
        for block in body.get("content", [])
        if block.get("type") == "text"
    )


def test_render_looks_like_a_folded_protein():
    assert os.path.isfile(RENDER_PATH), f"missing {RENDER_PATH}"
    with open(RENDER_PATH, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("ascii")
    text = _call_vision_judge(image_b64, VLM_JUDGE_PROMPT)
    assert "VERDICT: PASS" in text, f"vision judge did not pass the render:\n{text}"
