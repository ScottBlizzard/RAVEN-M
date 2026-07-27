from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate_r2.json"
)
R1_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate.json"
)
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_e_r2.py"


def test_v2_2_r2_preserves_r1_schedule_seeds_and_budgets() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior = json.loads(R1_MANIFEST.read_text(encoding="utf-8"))
    assert value["protocol"] == prior["protocol"]
    assert value["instance_seed"] == prior["instance_seed"]
    assert value["blocked_order_seed"] == prior["blocked_order_seed"]
    assert value["schedule"] == prior["schedule"]
    assert value["limits"] == prior["limits"]
    assert value["prompts"]["summary"] == prior["prompts"]["summary"]
    assert value["schemas"] == prior["schemas"]
    assert value["acceptance"][
        "consequential_action_adjudication_accounting"
    ]


def test_v2_2_r2_wrapper_and_manifest_share_source_freeze() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = WRAPPER.read_text(encoding="utf-8")
    match = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert match
    assert match.group(1) == value["source_commit"]

