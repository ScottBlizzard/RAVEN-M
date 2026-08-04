from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from raven_m.eest_ac.collector_lifecycle_v0_2_4 import (
    AtomicCompletionWriter,
    DEFAULT_SCHEMA_PATH,
    DuplicateTerminalRecordError,
    acquire_pre_action_readiness,
    build_completion_schema,
    cleanup_reverse_listener,
    load_contract,
    preserve_primary_error,
    validate_completion,
)


H = "a" * 64
PROJECT_ROOT = Path(__file__).parents[2]


def observation(*, ready: bool, semantic: str = H) -> dict:
    return {
        "pixel_sha256": "b" * 64,
        "a11y_available": ready,
        "a11y_sha256": semantic if ready else None,
        "page_content_sha256": semantic if ready else None,
        "package_names": ["example.package"] if ready else [],
        "activity": "example.package/.Main" if ready else None,
        "route_signature": "c" * 64 if ready else None,
    }


def completion_record() -> dict:
    return {
        "schema_version": "eest_ac_collector_completion.v0_2_4",
        "run_id": "TEST-RUN-01",
        "status": "pass",
        "started_at_utc": "2026-08-04T00:00:00+00:00",
        "completed_at_utc": "2026-08-04T00:00:01+00:00",
        "generation_calls": 0,
        "held_out_traces": 0,
        "oracle_efficacy_evaluations": 0,
        "readiness": {
            "qualified": True,
            "attempt_count": 2,
            "max_attempts": 5,
            "delay_seconds": 1.0,
            "stable_consecutive_required": 2,
            "attempts": [{"attempt": 1}, {"attempt": 2}],
        },
        "action_executed": True,
        "action_execution_count": 1,
        "post_observation_count": 4,
        "collection_record_valid": True,
        "primary_error": None,
        "cleanup": {
            "reverse": {"status": "already_absent", "verified_absent": True},
            "reset": {"attempted": True, "passed": True},
            "environment_close": {"attempted": True, "passed": True},
            "owned_helpers": {"owned_pids": [], "residual_pids": [], "passed": True},
            "secondary_errors": [],
            "residue_free": True,
        },
        "isolation": {
            "adb_server_port": 5038,
            "device_serial": "emulator-5554",
            "client_binary_sha256": "d" * 64,
            "server_binary_sha256": "d" * 64,
            "fallback_to_5037": False,
            "passed": True,
        },
        "artifact_hashes": [],
        "terminal_record_ordinal": 1,
    }


def cp(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["adb"], returncode, stdout, stderr)


class QueueRunner:
    def __init__(self, values: list[subprocess.CompletedProcess[str] | BaseException]):
        self.values = list(values)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], _: int) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def test_schema_is_exact_machine_contract_derivative() -> None:
    assert json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")) == build_completion_schema(load_contract())


def test_frozen_config_matches_contract_scope_and_has_no_web_onboarding_path() -> None:
    config = json.loads(
        (PROJECT_ROOT / "configs/eest_ac/eest_ac_v0_2_4_collector_lifecycle_qualification.json").read_text(encoding="utf-8")
    )
    contract = load_contract()
    assert config["generation_calls"] == config["held_out_traces"] == config["oracle_efficacy_evaluations"] == 0
    assert config["readiness"]["max_attempts"] == contract["readiness"]["max_attempts"]
    assert config["readiness"]["delay_seconds"] == contract["readiness"]["delay_seconds"]
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["fallback_to_5037"] is False
    assert "chrome" not in json.dumps(config).casefold()
    assert "open_url" not in json.dumps(config).casefold()


def test_v024_production_sources_do_not_import_or_evaluate_outcome_oracle() -> None:
    paths = [
        PROJECT_ROOT / "src/raven_m/eest_ac/collector_lifecycle_v0_2_4.py",
        PROJECT_ROOT / "scripts/run_eest_ac_v0_2_4_collector_qualification.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "evaluate_trace_v0_2_3" not in combined
    assert "model_call" not in combined
    assert "generation_endpoint" not in combined


def test_delayed_ready_requires_two_consecutive_stable_valid_samples() -> None:
    samples = [observation(ready=False), observation(ready=True), observation(ready=True)]
    sleeps: list[float] = []
    result = acquire_pre_action_readiness(lambda index: samples[index - 1], sleep_fn=sleeps.append)
    assert result.qualified
    assert result.audit["attempt_count"] == 3
    assert result.audit["attempts"][-1]["stable_with_previous"]
    assert sleeps == [1.0, 1.0]


def test_readiness_timeout_fails_before_action() -> None:
    action_calls = []
    result = acquire_pre_action_readiness(lambda _: observation(ready=False), sleep_fn=lambda _: None)
    if result.qualified:
        action_calls.append("executed")
    assert not result.qualified
    assert result.snapshot is None
    assert result.audit["attempt_count"] == 5
    assert action_calls == []


def test_changed_valid_semantics_do_not_count_as_stable_pair() -> None:
    values = [observation(ready=True, semantic="a" * 64), observation(ready=True, semantic="b" * 64), observation(ready=True, semantic="b" * 64)]
    result = acquire_pre_action_readiness(lambda index: values[index - 1], sleep_fn=lambda _: None)
    assert result.qualified
    assert result.audit["attempt_count"] == 3


def test_reverse_present_is_removed_and_verified() -> None:
    runner = QueueRunner([
        cp(stdout="emulator-5554 tcp:18765 tcp:18765\n"), cp(), cp(stdout=""),
    ])
    result = cleanup_reverse_listener(
        adb_path="adb", port=5038, serial="emulator-5554", listener="tcp:18765", runner=runner,
    )
    assert result["status"] == "removed"
    assert result["verified_absent"]
    assert runner.commands[1][-2:] == ["--remove", "tcp:18765"]


def test_reverse_already_absent_is_idempotent_success() -> None:
    runner = QueueRunner([cp(stdout=""), cp(stdout="")])
    result = cleanup_reverse_listener(
        adb_path="adb", port=5038, serial="emulator-5554", listener="tcp:18765", runner=runner,
    )
    assert result["status"] == "already_absent"
    assert result["verified_absent"]
    assert len(runner.commands) == 2


def test_reverse_not_found_race_requires_verified_absence() -> None:
    runner = QueueRunner([
        cp(stdout="emulator-5554 tcp:18765 tcp:18765\n"),
        cp(returncode=1, stderr="adb.exe: error: listener 'tcp:18765' not found"),
        cp(stdout=""),
    ])
    result = cleanup_reverse_listener(
        adb_path="adb", port=5038, serial="emulator-5554", listener="tcp:18765", runner=runner,
    )
    assert result["status"] == "already_absent_after_race"
    assert result["verified_absent"]


def test_reverse_other_error_remains_failure() -> None:
    runner = QueueRunner([cp(stdout="emulator-5554 tcp:18765 tcp:18765\n"), cp(returncode=1, stderr="permission denied")])
    result = cleanup_reverse_listener(
        adb_path="adb", port=5038, serial="emulator-5554", listener="tcp:18765", runner=runner,
    )
    assert result["status"] == "failed"
    assert not result["verified_absent"]
    assert result["error"] == "reverse_remove_failed"


def test_reverse_command_exception_is_audited_not_raised() -> None:
    runner = QueueRunner([subprocess.TimeoutExpired(["adb"], 10)])
    result = cleanup_reverse_listener(
        adb_path="adb", port=5038, serial="emulator-5554", listener="tcp:18765", runner=runner,
    )
    assert result["status"] == "failed"
    assert result["error"] == "reverse_list_before_exception"


def test_primary_error_is_preserved_when_cleanup_also_fails() -> None:
    primary = {"code": "PRE_READINESS_TIMEOUT", "message": "not ready", "layer": "readiness"}
    cleanup = [{"code": "REVERSE_CLEANUP_FAILED", "message": "timeout", "layer": "cleanup"}]
    actual_primary, actual_cleanup = preserve_primary_error(primary, cleanup)
    assert actual_primary == primary
    assert actual_cleanup == cleanup
    assert actual_primary is primary


def test_atomic_completion_is_schema_valid_and_exactly_once(tmp_path: Path) -> None:
    path = tmp_path / "collection_complete.json"
    writer = AtomicCompletionWriter(path)
    first_hash = writer.write_once(completion_record())
    assert path.is_file()
    assert len(first_hash) == 64
    validate_completion(json.loads(path.read_text(encoding="utf-8")))
    with pytest.raises(DuplicateTerminalRecordError):
        writer.write_once(completion_record())
    assert len(list(tmp_path.glob("collection_complete.json"))) == 1
    assert list(tmp_path.glob("*.tmp")) == []


def test_second_writer_cannot_overwrite_existing_terminal_record(tmp_path: Path) -> None:
    path = tmp_path / "collection_complete.json"
    AtomicCompletionWriter(path).write_once(completion_record())
    different = deepcopy(completion_record())
    different["status"] = "fail"
    different["action_executed"] = False
    different["action_execution_count"] = 0
    different["post_observation_count"] = 0
    different["collection_record_valid"] = False
    different["primary_error"] = {"code": "X", "message": "x", "layer": "test"}
    before = path.read_bytes()
    with pytest.raises(DuplicateTerminalRecordError):
        AtomicCompletionWriter(path).write_once(different)
    assert path.read_bytes() == before


def test_failure_completion_preserves_primary_and_secondary_errors(tmp_path: Path) -> None:
    record = completion_record()
    record.update({
        "status": "fail", "action_executed": False, "action_execution_count": 0,
        "post_observation_count": 0, "collection_record_valid": False,
        "primary_error": {"code": "PRE_READINESS_TIMEOUT", "message": "not ready", "layer": "readiness"},
    })
    record["readiness"]["qualified"] = False
    record["cleanup"]["secondary_errors"] = [
        {"code": "REVERSE_CLEANUP_FAILED", "message": "timeout", "layer": "cleanup"}
    ]
    record["cleanup"]["reverse"] = {"status": "failed", "verified_absent": False}
    record["cleanup"]["residue_free"] = False
    path = tmp_path / "collection_complete.json"
    AtomicCompletionWriter(path).write_once(record)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["primary_error"]["code"] == "PRE_READINESS_TIMEOUT"
    assert loaded["cleanup"]["secondary_errors"][0]["code"] == "REVERSE_CLEANUP_FAILED"
