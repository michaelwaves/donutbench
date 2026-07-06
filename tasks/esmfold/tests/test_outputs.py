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


def _load_model():
    assert os.path.isfile(STRUCTURE_PATH), f"missing {STRUCTURE_PATH}"
    parser = PDBParser(QUIET=False)
    structure = parser.get_structure("model", STRUCTURE_PATH)
    return next(iter(structure))


def _ca_atoms(chain):
    return [res["CA"] for res in chain if res.has_id("CA")]


def test_structure_parses_and_has_atoms():
    model = _load_model()
    chains = list(model)
    assert len(chains) >= 1, "no chains in structure"
    total_ca = sum(len(_ca_atoms(chain)) for chain in chains)
    assert total_ca >= 4, "too few CA atoms to be a real structure"


def test_no_nonfinite_coordinates():
    model = _load_model()
    for atom in model.get_atoms():
        assert np.all(np.isfinite(atom.get_coord())), (
            "non-finite atom coordinate found"
        )


def test_chain_geometry_is_sane():
    model = _load_model()
    for chain in model:
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
    model = _load_model()
    chain_ids, seq_idx, coords = [], [], []
    for chain in model:
        for i, atom in enumerate(_ca_atoms(chain)):
            chain_ids.append(chain.id)
            seq_idx.append(i)
            coords.append(atom.get_coord())
    coords = np.array(coords)
    n = len(coords)
    if n < 2:
        return
    chain_ids = np.array(chain_ids)
    seq_idx = np.array(seq_idx)
    dist = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    same_chain = chain_ids[:, None] == chain_ids[None, :]
    seq_adjacent = same_chain & (np.abs(seq_idx[:, None] - seq_idx[None, :]) <= 1)
    upper_triangle = np.triu(np.ones((n, n), dtype=bool), k=1)
    candidate_pairs = upper_triangle & ~seq_adjacent
    checked = int(candidate_pairs.sum())
    if checked == 0:
        return
    clashes = int((candidate_pairs & (dist < CLASH_DISTANCE)).sum())
    fraction = clashes / checked
    assert fraction <= MAX_CLASH_FRACTION, (
        f"{clashes}/{checked} non-bonded CA pairs are closer than "
        f"{CLASH_DISTANCE} Angstrom -- severe steric clashes"
    )


def test_render_looks_like_a_folded_protein():
    assert os.path.isfile(RENDER_PATH), f"missing {RENDER_PATH}"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    assert api_key, (
        "ANTHROPIC_API_KEY is not set in the verifier environment -- cannot "
        "run the image judge. Set it in [verifier.env] in task.toml."
    )

    with open(RENDER_PATH, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("ascii")

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
                    {"type": "text", "text": VLM_JUDGE_PROMPT},
                ],
            }
        ],
    }

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
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

    text = "".join(
        block.get("text", "")
        for block in body.get("content", [])
        if block.get("type") == "text"
    )
    assert "VERDICT: PASS" in text, f"vision judge did not pass the render:\n{text}"
