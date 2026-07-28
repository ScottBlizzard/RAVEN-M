from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate_r12.json"
)
R11_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate_r11.json"
)
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_e_r12.py"


def test_v2_2_r12_preserves_r11_experiment_controls() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior = json.loads(R11_MANIFEST.read_text(encoding="utf-8"))
    assert value["protocol"] == prior["protocol"]
    assert value["instance_seed"] == prior["instance_seed"]
    assert value["blocked_order_seed"] == prior["blocked_order_seed"]
    assert value["schedule"] == prior["schedule"]
    assert value["limits"] == prior["limits"]
    assert value["prompts"] == prior["prompts"]
    assert value["schemas"] == prior["schemas"]
    assert value["acceptance"] == prior["acceptance"]


def test_v2_2_r12_wrapper_and_manifest_share_source_freeze() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = WRAPPER.read_text(encoding="utf-8")
    match = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert match
    assert match.group(1) == value["source_commit"]
