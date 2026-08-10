"""Build and verify the frozen A4 donor workflow bank.

The scored Hard suite is never an admissible donor source.  This module only
accepts evaluator-confirmed successful Easy/Medium episodes named in a frozen
manifest, verifies their byte hashes and suite provenance, and deterministically
abstracts their visible action trace.  It performs no model call.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(repository_root: Path, value: str) -> Path:
    return (repository_root / value).resolve()


def _replace_literal(text: str, literal: str, replacement: str) -> str:
    if not literal:
        return text
    return re.sub(re.escape(literal), replacement, text, flags=re.IGNORECASE)


def _abstract_workflow(episode: dict[str, Any]) -> tuple[str, list[str]]:
    """Produce an auditable, value-free workflow from the executed trace."""
    typed_values: list[str] = []
    for step in episode.get("steps") or []:
        action = ((step.get("decision") or {}).get("action") or {})
        if action.get("type") == "type_text" and str(action.get("text") or ""):
            typed_values.append(str(action["text"]))
    # Longer values first prevents a short substring from partially masking a
    # longer donor value.  Repeated literals share the same placeholder.
    unique_values = sorted(set(typed_values), key=lambda item: (-len(item), item))
    placeholders = {value: f"<task_value_{index + 1}>" for index, value in enumerate(unique_values)}

    procedure: list[str] = []
    for step in episode.get("steps") or []:
        decision = step.get("decision") or {}
        action = decision.get("action") or {}
        summary = " ".join(str(decision.get("decision_summary") or "").split())
        for value, placeholder in placeholders.items():
            summary = _replace_literal(summary, value, placeholder)
        action_type = str(action.get("type") or "done")
        if action_type == "type_text":
            value = str(action.get("text") or "")
            detail = f"enter {placeholders.get(value, '<task_value>')} into the visible goal-relevant field"
        elif action_type == "open_app":
            detail = f"open {str(action.get('app_name') or 'the required app')}"
        elif action_type == "swipe":
            detail = "scroll only when the current screen shows the needed content is off-screen"
        elif action_type == "wait":
            detail = "wait briefly only when the visible UI is loading"
        elif action_type == "press_back":
            detail = "return one screen when the current visible setup screen is complete"
        elif action_type == "tap":
            detail = "tap the currently visible control described by the step intent"
        else:
            detail = f"perform the visible {action_type} operation"
        procedure.append(f"{len(procedure) + 1}. {detail}; intent: {summary or 'advance the task'}")

    if not procedure:
        raise ValueError("donor episode has no decisions to abstract")
    workflow = (
        "Treat setup/onboarding steps as conditional and follow only controls supported by current pixels. "
        + " ".join(procedure)
        + " Do not reuse donor coordinates or literal values; stop only after visible persistence evidence."
    )
    leaked = [value for value in unique_values if value and value.lower() in workflow.lower()]
    if leaked:
        raise ValueError(f"donor literal leaked into workflow: {leaked}")
    return workflow, unique_values


def audit_manifest(manifest_path: Path, *, repository_root: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _read_json(manifest_path)
    hard_path = _resolve(repository_root, manifest["scored_hard_manifest"]["path"])
    errors: list[str] = []
    if file_sha256(hard_path) != manifest["scored_hard_manifest"]["sha256"]:
        errors.append("scored_hard_manifest_hash_drift")
    hard = _read_json(hard_path)
    hard_classes = {str(item["task_class"]) for item in hard.get("instances") or []}

    eligible: list[dict[str, Any]] = []
    # Hash declared, repository-relative source names rather than host absolute
    # paths so the frozen lock remains stable after copying the repository.
    source_lock: dict[str, str] = {
        "donor_manifest": file_sha256(manifest_path),
        str(manifest["scored_hard_manifest"]["path"]): file_sha256(hard_path),
    }
    seen_ids: set[str] = set()
    for donor in manifest.get("donors") or []:
        donor_id = str(donor["donor_id"])
        donor_errors: list[str] = []
        if donor_id in seen_ids:
            donor_errors.append("duplicate_donor_id")
        seen_ids.add(donor_id)
        task_class = str(donor["task_class"])
        if task_class in hard_classes:
            donor_errors.append("task_class_present_in_scored_hard")
        if str(donor["difficulty"]).lower() not in {"easy", "medium"}:
            donor_errors.append("difficulty_not_easy_or_medium")

        paths = {
            key: _resolve(repository_root, donor[key])
            for key in ("episode_path", "events_path", "suite_summary_path", "suite_manifest_path")
        }
        for key, path in paths.items():
            expected = str(donor[f"{key}_sha256"])
            if not path.is_file():
                donor_errors.append(f"{key}_missing")
                continue
            actual = file_sha256(path)
            source_lock[str(donor[key])] = actual
            if actual != expected:
                donor_errors.append(f"{key}_hash_drift")
        if donor_errors:
            errors.extend(f"{donor_id}:{item}" for item in donor_errors)
            continue

        episode = _read_json(paths["episode_path"])
        suite = _read_json(paths["suite_summary_path"])
        suite_manifest = _read_json(paths["suite_manifest_path"])
        suite_entry = next(
            (item for item in suite.get("episodes") or [] if item.get("episode_id") == episode.get("episode_id")),
            None,
        )
        manifest_entry = next(
            (item for item in suite_manifest.get("tasks") or [] if item.get("name") == task_class),
            None,
        )
        events = [json.loads(line) for line in paths["events_path"].read_text(encoding="utf-8").splitlines() if line.strip()]
        evaluator_events = [item for item in events if item.get("event") == "evaluator_result"]
        complete_events = [item for item in events if item.get("event") == "episode_complete"]
        checks = {
            "episode_reward_is_one": episode.get("evaluator_reward") == 1.0,
            "episode_has_no_error": episode.get("error") is None and episode.get("failure_code") is None,
            "seed_matches": int(episode.get("seed", -1)) == int(donor["seed"]),
            "suite_confirms_success": bool(suite_entry and suite_entry.get("success") is True),
            "suite_task_matches": bool(suite_entry and suite_entry.get("task_name") == task_class),
            "suite_seed_matches": bool(suite_entry and int(suite_entry.get("seed", -1)) == int(donor["seed"])),
            "manifest_confirms_nonhard": bool(
                manifest_entry
                and str(manifest_entry.get("difficulty")).lower() == str(donor["difficulty"]).lower()
                and str(manifest_entry.get("app")) == str(donor["app"])
            ),
            "evaluator_event_is_hidden_success": bool(
                len(evaluator_events) == 1
                and evaluator_events[0].get("reward") == 1.0
                and evaluator_events[0].get("visible_to_agent") is False
            ),
            "episode_complete_success": bool(
                len(complete_events) == 1 and complete_events[0].get("success") is True
            ),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            errors.extend(f"{donor_id}:{item}" for item in failed)
            continue
        workflow, masked_values = _abstract_workflow(episode)
        eligible.append(
            {
                "workflow_id": donor_id,
                "donor_task": task_class,
                "donor_seed": int(donor["seed"]),
                "donor_family": str(donor["coverage_family"]),
                "donor_split": str(donor["difficulty"]).title(),
                "keywords": [str(item).lower() for item in donor["keywords"]],
                "workflow": workflow,
                "source_episode_sha256": file_sha256(paths["episode_path"]),
                "source_evaluator_reward": 1.0,
                "provenance": {
                    "difficulty": str(donor["difficulty"]).lower(),
                    "app": str(donor["app"]),
                    "episode_id": str(episode["episode_id"]),
                    "events_sha256": file_sha256(paths["events_path"]),
                    "masked_task_value_count": len(masked_values),
                },
            }
        )

    required = set(str(item) for item in manifest.get("required_coverage_families") or [])
    covered = {str(item["donor_family"]) for item in eligible}
    missing = sorted(required - covered)
    status = "ready" if not errors and not missing and eligible else "not_ready"
    canonical = {
        "schema": "a4.frozen_donor_workflow_bank.v1",
        "status": status,
        "generation_calls": 0,
        "scored_hard_inputs_used": False,
        "workflows": eligible,
        "source_lock_sha256": json_sha256(source_lock),
        "bank_sha256": json_sha256(eligible),
    }
    return {
        **canonical,
        "manifest_id": manifest.get("manifest_id"),
        "eligible_donor_count": len(eligible),
        "eligible_donor_ids": [item["workflow_id"] for item in eligible],
        "covered_families": sorted(covered),
        "missing_required_families": missing,
        "errors": errors,
        "source_lock": dict(sorted(source_lock.items())),
        "acquisition_queue": manifest.get("acquisition_queue") or [],
    }


def _canonical_bank(report: dict[str, Any]) -> dict[str, Any]:
    """Return the exact payload consumed by runner/preflight."""
    return {
        key: report[key]
        for key in (
            "schema",
            "status",
            "generation_calls",
            "scored_hard_inputs_used",
            "workflows",
            "source_lock_sha256",
            "bank_sha256",
        )
    }


def write_audit_and_bank(
    manifest_path: Path,
    *,
    repository_root: Path,
    audit_path: Path,
    bank_path: Path,
) -> dict[str, Any]:
    report = audit_manifest(manifest_path, repository_root=repository_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if report["status"] == "ready":
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        bank_path.write_text(
            json.dumps(_canonical_bank(report), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif bank_path.exists():
        raise RuntimeError("A4 donor audit is not ready but a workflow bank already exists; refuse stale bank")
    return report


def validate_frozen_bank(
    manifest_path: Path,
    *,
    repository_root: Path,
    audit_path: Path,
    bank_path: Path,
) -> dict[str, Any]:
    expected = audit_manifest(manifest_path, repository_root=repository_root)
    if expected["status"] != "ready":
        raise RuntimeError(f"A4 donor source is not ready: {expected['missing_required_families']}")
    persisted_audit = _read_json(audit_path)
    persisted_bank = _read_json(bank_path)
    if persisted_audit != expected:
        raise RuntimeError("A4 donor audit drifted")
    if persisted_bank != _canonical_bank(expected):
        raise RuntimeError("A4 workflow bank differs from deterministic donor build")
    return expected
