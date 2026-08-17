from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation" / "scripts" / "build_r15_browser_forensics.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_r15_browser_forensics", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_forensic_rebuild_is_bound_and_no_go() -> None:
    module = _module()
    payload = module.build(ROOT)
    content_sha = payload.pop("content_sha256")
    assert content_sha == hashlib.sha256(module.canonical_bytes(payload)).hexdigest()
    assert payload["generation_calls"] == 0
    assert payload["formal_r15_classification"] == (
        "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED"
    )
    assert payload["go_no_go"]["decision"] == "NO_GO_R15_DERIVED_LIVE_CANDIDATE"
    assert payload["arms"]["A1-R15"]["reward"] == 1.0
    assert payload["arms"]["A1-R15"]["typed_text_actions"] == [
        {"step": 18, "text": "1120"}
    ]


def test_r15_evr_was_never_rendered_or_read() -> None:
    payload = _module().build(ROOT)
    memory = payload["arms"]["A1-R15"]["memory_summary"]
    register = memory["evidence_register"]
    assert register["counters"]["render_count"] == 0
    assert all(not event["rendered"] for event in register["read_events"])
    assert payload["r2_six_success_protection_replay"]["active_count"] == 0
    assert payload["r2_six_success_protection_replay"]["render_count"] == 0
    assert payload["r2_six_success_protection_replay"]["base_r2_rendered_read_count"] > 0


def test_checked_in_artifact_matches_rebuild() -> None:
    module = _module()
    expected = module.build(ROOT)
    path = ROOT / "evidence" / "r15_browser_forensics" / "R15_BROWSER_FORENSIC_2026-08-18.json"
    actual = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected
