from __future__ import annotations

import json
import importlib.util

from raven_m.official_qwen_mobile import a1r13_contract as contract


SPEC = importlib.util.spec_from_file_location(
    "replay_a1r13_evidence_value_register",
    contract.REPOSITORY_ROOT
    / "implementation/scripts/replay_a1r13_evidence_value_register.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_replay_recomputes_exact_committed_report() -> None:
    observed = module.replay(contract.FIXTURE_PATH)
    committed = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert observed == committed
    assert observed["status"] == "PASS"
    assert observed["totals"]["active_episode_count"] == 1
    assert observed["totals"]["six_success_active_count"] == 0


def test_fixture_and_report_are_self_hashed() -> None:
    fixture = json.loads(contract.FIXTURE_PATH.read_text(encoding="utf-8"))
    report = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert fixture["content_sha256"] == contract.content_sha256(fixture)
    assert report["content_sha256"] == contract.content_sha256(report)
