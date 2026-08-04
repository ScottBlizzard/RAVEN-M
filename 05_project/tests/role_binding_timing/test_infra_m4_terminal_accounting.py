from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.infra_m4_terminal_accounting import (
    PHASES,
    PhaseJournal,
    atomic_write_json,
    finalize_completion,
    run_fault_injected_lifecycle,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPOSITORY_ROOT / "05_project/schemas/role_binding_timing_infra_m4_completion.v1.schema.json"
RUNNER_PATH = REPOSITORY_ROOT / "05_project/scripts/run_role_binding_timing_infra_m4.py"
FINALIZER_PATH = REPOSITORY_ROOT / "05_project/scripts/finalize_role_binding_timing_infra_m4.py"


def validate_completion(value: dict[str, object]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [item.message for item in Draft202012Validator(schema).iter_errors(value)]
    assert errors == []


def test_local_atomic_writer_preserves_old_file_on_json_failure(tmp_path: Path) -> None:
    path = tmp_path / "value.json"
    atomic_write_json(path, {"stable": True}, replace=False)

    class Hostile:
        pass

    with pytest.raises(TypeError):
        atomic_write_json(path, {"bad": Hostile()}, replace=True)
    assert json.loads(path.read_text(encoding="utf-8")) == {"stable": True}


def test_phase_journal_is_sequential_and_first_edge_is_write_once(tmp_path: Path) -> None:
    journal = PhaseJournal(tmp_path / "journal")
    journal.record(phase="launch", event="start", status="RUNNING")
    journal.record(phase="launch", event="end", status="FAIL", first_broken_edge="FIRST")
    journal.record(phase="cleanup", event="end", status="SECONDARY_FAIL", first_broken_edge="SECOND")
    entries = journal.read_entries()
    assert [entry["sequence"] for entry in entries] == [1, 2, 3]
    assert journal.first_edge() == "FIRST"
    assert len((tmp_path / "journal/journal.ndjson").read_text(encoding="utf-8").splitlines()) == 3
    assert all(path.name == f"{index:06d}.json" for index, path in enumerate(sorted((tmp_path / "journal/entries").glob("*.json")), 1))


@pytest.mark.parametrize("phase", PHASES)
def test_every_phase_failure_leaves_completion_journal_closed_sealed_and_canary(tmp_path: Path, phase: str) -> None:
    repository = tmp_path / f"repo_{phase}"
    runtime = tmp_path / f"runtime_{phase}"
    repository.mkdir()
    runtime.mkdir()
    result = run_fault_injected_lifecycle(root=runtime, inject_phase=phase, repository_root=repository)
    completion = result["completion"]
    validate_completion(completion)
    expected = "PROCESS_TIMEOUT:BOOT" if phase == "boot" else f"INJECTED:{phase.upper()}"
    assert result["first_edge"] == expected
    assert completion["first_broken_edge"] == expected
    assert completion["journal_terminal_event_present"] is True
    assert any(entry["phase"] == "terminal" and entry["event"] == "end" for entry in result["journal"])
    assert len(result["sealed_records"]) == 2
    assert result["temp_removed"] is True
    assert result["canary_unchanged"] is True
    assert (result["output"] / "qualification_completion.json").is_file()


def test_missing_helper_attribute_error_survives(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repository.mkdir(); runtime.mkdir()
    result = run_fault_injected_lifecycle(root=runtime, inject_phase="missing_helper", repository_root=repository)
    assert result["first_edge"] == "MISSING_HELPER_ATTRIBUTE_ERROR"
    assert result["completion"]["first_broken_edge"] == "MISSING_HELPER_ATTRIBUTE_ERROR"
    validate_completion(result["completion"])
    assert result["temp_removed"] and result["canary_unchanged"]


def test_rich_json_serialization_failure_uses_valid_minimal_completion(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repository.mkdir(); runtime.mkdir()
    result = run_fault_injected_lifecycle(
        root=runtime, inject_phase="none", repository_root=repository,
        rich_serialization_failure=True,
    )
    completion = result["completion"]
    assert completion["terminal_mode"] == "minimal_fallback"
    assert completion["first_broken_edge"].startswith("TERMINAL_RICH_SERIALIZATION:TypeError")
    assert completion["rich_serialization_error"]["type"] == "TypeError"
    validate_completion(completion)
    assert result["temp_removed"] and result["canary_unchanged"]


def test_cleanup_exception_does_not_replace_existing_edge(tmp_path: Path) -> None:
    journal = PhaseJournal(tmp_path / "journal")
    journal.record(phase="framework", event="end", status="FAIL", first_broken_edge="FRAMEWORK_PRIMARY")
    journal.record(phase="cleanup", event="end", status="SECONDARY_FAIL", first_broken_edge="CLEANUP_SECONDARY")
    assert journal.first_edge() == "FRAMEWORK_PRIMARY"


def test_process_timeout_has_exact_edge(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repository.mkdir(); runtime.mkdir()
    result = run_fault_injected_lifecycle(root=runtime, inject_phase="boot", repository_root=repository)
    assert result["completion"]["first_broken_edge"] == "PROCESS_TIMEOUT:BOOT"


def test_finalizer_never_uses_foreign_writer_dependency() -> None:
    module_source = (REPOSITORY_ROOT / "05_project/src/raven_m/role_binding_timing/infra_m4_terminal_accounting.py").read_text(encoding="utf-8")
    finalizer_source = FINALIZER_PATH.read_text(encoding="utf-8")
    assert "M1.write_json_atomic" not in module_source + finalizer_source
    assert "from raven_m.role_binding_timing.infra_m4_terminal_accounting" in finalizer_source


def test_duplicate_completion_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    journal = PhaseJournal(output / "phase_journal")
    journal.record(phase="launch", event="end", status="FAIL", first_broken_edge="EDGE")
    finalize_completion(output_root=output, journal=journal, status="FAULT_INJECTED", run_id="one", rich_completion=None)
    with pytest.raises(RuntimeError, match="DUPLICATE_TERMINAL_COMPLETION"):
        finalize_completion(output_root=output, journal=journal, status="FAULT_INJECTED", run_id="two", rich_completion=None)


def test_independent_finalizer_process_leaves_valid_terminal_record(tmp_path: Path) -> None:
    output = tmp_path / "independent"
    output.mkdir()
    journal = PhaseJournal(output / "phase_journal")
    journal.record(phase="framework", event="end", status="FAIL", first_broken_edge="FRAMEWORK_PRIMARY")
    completed = subprocess.run(
        [
            sys.executable, str(FINALIZER_PATH), "--output-root", str(output),
            "--schema", str(SCHEMA_PATH), "--run-id", "independent-test",
            "--status", "RUNTIME_UNSTABLE",
        ],
        capture_output=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    value = json.loads((output / "qualification_completion.json").read_text(encoding="utf-8"))
    validate_completion(value)
    assert value["terminal_mode"] == "minimal_fallback"
    assert value["first_broken_edge"] == "FRAMEWORK_PRIMARY"
    assert json.loads((output / "terminal_validation.json").read_text(encoding="utf-8"))["passed"] is True
    assert (output / "artifact_manifest.json").is_file()
