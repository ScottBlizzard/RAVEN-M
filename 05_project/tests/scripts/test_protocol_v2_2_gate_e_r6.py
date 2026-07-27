from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate_r6.json"
)
R5_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate_r5.json"
)
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_e_r6.py"
RAVEN_PROMPT = ROOT / "05_project/prompts/executor_raven_v2.md"


def test_v2_2_r6_is_prompt_only_and_preserves_r5_controls() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior = json.loads(R5_MANIFEST.read_text(encoding="utf-8"))
    assert value["protocol"] == prior["protocol"]
    assert value["instance_seed"] == prior["instance_seed"]
    assert value["blocked_order_seed"] == prior["blocked_order_seed"]
    assert value["schedule"] == prior["schedule"]
    assert value["limits"] == prior["limits"]
    assert value["prompts"] == prior["prompts"]
    assert value["schemas"] == prior["schemas"]
    assert value["acceptance"] == prior["acceptance"]


def test_v2_2_r6_wrapper_and_manifest_share_source_freeze() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = WRAPPER.read_text(encoding="utf-8")
    match = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert match
    assert match.group(1) == value["source_commit"]


def test_v2_2_r6_preserves_destination_picker_context() -> None:
    prompt = RAVEN_PROMPT.read_text(encoding="utf-8")
    assert "persistent bottom" in prompt
    assert "`CANCEL` and `COPY`/`MOVE` controls" in prompt
    assert "never\nuse `press_back` merely to leave the current folder" in prompt
    assert "Back exits the picker" in prompt
    assert "open\nthe picker's navigation drawer directly" in prompt
