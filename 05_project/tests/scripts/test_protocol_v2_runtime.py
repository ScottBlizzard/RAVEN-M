from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "05_project/scripts/protocol_v2_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("protocol_v2_runtime", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_startup_clean_load_is_audited(tmp_path: Path) -> None:
    module = load_module()
    marker = object()
    path = tmp_path / "startup.json"
    env, audit = module.initialize_androidworld_environment(
        audit_path=path,
        load_fn=lambda: marker,
        recover_fn=lambda: (_ for _ in ()).throw(
            AssertionError("recovery must not run")
        ),
    )
    assert env is marker
    assert audit["last_status"] == "clean"
    assert audit["failure_count"] == 0
    assert json.loads(path.read_text(encoding="utf-8")) == audit


def test_startup_failure_cold_recovers_and_is_audited(
    tmp_path: Path,
) -> None:
    module = load_module()
    marker = object()
    path = tmp_path / "startup.json"

    def fail_load():
        raise RuntimeError("ADB install timeout")

    env, audit = module.initialize_androidworld_environment(
        audit_path=path,
        load_fn=fail_load,
        recover_fn=lambda: marker,
    )
    assert env is marker
    assert audit["last_status"] == "recovered"
    assert audit["failure_count"] == 1
    assert audit["recovery_success_count"] == 1
    failures = [
        event for event in audit["events"] if event["event"] == "failure"
    ]
    assert failures[0]["code"] == "INFRA_ENVIRONMENT_CONSTRUCTION"


def test_startup_two_failures_stop_with_persisted_evidence(
    tmp_path: Path,
) -> None:
    module = load_module()
    path = tmp_path / "startup.json"

    def fail():
        raise RuntimeError("emulator unavailable")

    with pytest.raises(RuntimeError, match="failed twice"):
        module.initialize_androidworld_environment(
            audit_path=path,
            load_fn=fail,
            recover_fn=fail,
        )
    audit = json.loads(path.read_text(encoding="utf-8"))
    assert audit["last_status"] == "failed"
    assert audit["failure_count"] == 2
    assert [
        event["phase"]
        for event in audit["events"]
        if event["event"] == "failure"
    ] == ["initial_load", "cold_recovery"]
