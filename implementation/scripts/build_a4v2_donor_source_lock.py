#!/usr/bin/env python3
"""Verify donor outcomes and commit portable successful-trace snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "evidence/a4v2/A4V2_DONOR_SOURCE_LOCK.json"
DEFAULT_REPORT = ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_RESULT.json"
DEFAULT_SNAPSHOTS = ROOT / "evidence/a4v2/donor_snapshots"


def _replay_manifest_instance_identities(
    manifest_rows: dict[tuple[str, int], dict[str, Any]],
) -> dict[tuple[str, int], dict[str, Any]]:
    """Recreate the exact pre-initialization identity used by the runner.

    ``task_instances._digest`` intentionally hashes native AndroidWorld Python
    objects, while ``episode_start.task_params`` is the controller's JSON-safe
    projection of those objects.  Comparing either representation directly to
    the other incorrectly invalidates tasks whose params contain row objects.
    Re-instantiating through the runner's verifier closes both representations
    without weakening the frozen manifest check.
    """

    sys.path.insert(0, str(ROOT / "implementation/src"))
    from android_world import registry
    from raven_m.multi_framework_benchmark.task_instances import instantiate_verified
    from raven_m.official_qwen_mobile.controller import _json_safe

    available = registry.TaskRegistry().get_registry(
        registry.TaskRegistry.ANDROID_WORLD_FAMILY
    )
    identities: dict[tuple[str, int], dict[str, Any]] = {}
    for key, spec in manifest_rows.items():
        instance = instantiate_verified(available, spec)
        identities[key] = {
            "task_params": _json_safe(instance.params),
            "goal_before_initialization": str(instance.goal),
        }
    return identities


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _content_sha(payload: dict[str, Any]) -> str:
    return _digest({key: value for key, value in payload.items() if key != "content_sha256"})


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _episode_valid(episode: dict[str, Any]) -> bool:
    if episode.get("error") is not None or episode.get("lifecycle_errors"):
        return False
    steps = episode.get("steps") or []
    if len(steps) != int(episode.get("model_call_count") or -1):
        return False
    return all(
        int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1
        for step in steps
    )


def _events_valid(path: Path, *, episode: dict[str, Any]) -> bool:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = [str(row.get("event")) for row in rows]
    evaluator = [row for row in rows if row.get("event") == "evaluator_result"]
    complete = [row for row in rows if row.get("event") == "episode_complete"]
    return (
        len(rows) >= 6
        and names[0] == "episode_start"
        and names[1] == "task_initialized"
        and names[-4:] == ["evaluator_result", "task_torn_down", "post_episode_reset", "episode_complete"]
        and not set(names).intersection(
            {"episode_error", "evaluator_skipped", "teardown_error", "reset_error", "recovery_close_error"}
        )
        and rows[0].get("episode_id") == episode.get("episode_id")
        and rows[0].get("task_name") == episode.get("task_name")
        and int(rows[0].get("seed", -1)) == int(episode.get("seed", -2))
        and names.count("step") == int(episode.get("step_count") or len(episode.get("steps") or []))
        and len(evaluator) == 1
        and evaluator[0].get("visible_to_agent") is False
        and evaluator[0].get("reward") == episode.get("evaluator_reward")
        and evaluator[0].get("model_claimed_status") == episode.get("model_claimed_status")
        and len(complete) == 1
        and complete[0].get("success") is bool(episode.get("success"))
        and complete[0].get("termination_reason") == episode.get("termination_reason")
    )


def _portable_snapshot(
    episode: dict[str, Any], *, raw_sha: str, events_sha: str, task_params: Any
) -> dict[str, Any]:
    steps = []
    for step in episode.get("steps") or []:
        decision = step.get("decision") or {}
        call = step.get("model_call") or {}
        steps.append(
            {
                "step": step.get("step"),
                "executed": bool(step.get("executed")),
                "decision": {
                    "thought": decision.get("thought"),
                    "action_summary": decision.get("action_summary") or decision.get("decision_summary"),
                    "canonical_action": decision.get("canonical_action"),
                    "terminal_status": decision.get("terminal_status"),
                },
                "model_call": {
                    "request_sha256": call.get("request_sha256"),
                    "response_sha256": call.get("response_sha256"),
                    "transport_attempts": (call.get("raven_meta") or {}).get("transport_attempts"),
                },
            }
        )
    return {
        "schema": "a4v2.portable_successful_donor_episode.v1",
        "source_episode_sha256": raw_sha,
        "source_events_sha256": events_sha,
        "episode_id": episode["episode_id"],
        "task_name": episode["task_name"],
        "task_goal": episode["task_goal"],
        "task_params": task_params,
        "seed": episode["seed"],
        "evaluator_reward": episode["evaluator_reward"],
        "success": episode["success"],
        "error": episode.get("error"),
        "lifecycle_errors": episode.get("lifecycle_errors") or [],
        "model_call_count": episode["model_call_count"],
        "executed_action_count": episode["executed_action_count"],
        "termination_reason": episode["termination_reason"],
        "steps": steps,
    }


def build(
    *,
    plan_path: Path,
    manifest_paths: list[Path],
    suite_dirs: list[Path],
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    snapshots_dir: Path = DEFAULT_SNAPSHOTS,
) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in manifest_paths]
    if plan.get("schema") != "a4v2.awm_donor_acquisition_plan.v2":
        raise RuntimeError("wrong acquisition plan schema")
    if not manifests:
        raise RuntimeError("at least one acquisition manifest is required")
    manifest_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for manifest in manifests:
        if manifest.get("schema") != "a4v2.donor_acquisition_manifest.v1":
            raise RuntimeError("wrong acquisition manifest schema")
        if manifest.get("plan_file_sha256") != _file_sha(plan_path):
            raise RuntimeError("acquisition manifest/plan drift")
        amendment_path = ROOT / str(manifest.get("protocol_amendment_path") or "")
        if not amendment_path.is_file() or manifest.get("protocol_amendment_sha256") != _file_sha(amendment_path):
            raise RuntimeError("acquisition manifest/protocol amendment drift")
        if manifest.get("content_sha256") != _content_sha(manifest):
            raise RuntimeError("acquisition manifest content hash drift")
        for row in manifest.get("tasks") or []:
            key = (str(row["task_class"]), int(row["task_seed"]))
            if key in manifest_rows:
                raise RuntimeError(f"duplicate donor key across manifests: {key}")
            manifest_rows[key] = {**row, "manifest_role": manifest.get("manifest_role")}
    replayed_identities = _replay_manifest_instance_identities(manifest_rows)
    observed: dict[tuple[str, int], list[tuple[dict[str, Any], Path, Path, dict[str, Any], Path]]] = {}
    suite_provenance: list[dict[str, Any]] = []
    receipt_files = list((ROOT / "evidence/a4v2").glob("A4V2_ACQUISITION_SERVER_RECEIPT*.json"))
    receipts_by_file_sha = {
        _file_sha(path): (path, json.loads(path.read_text(encoding="utf-8")))
        for path in receipt_files
    }
    allowed_receipts_by_signature: dict[str, set[str]] = {}
    for suite in suite_dirs:
        signature_path = suite / "run_signature.json"
        if not signature_path.is_file():
            raise RuntimeError(f"donor suite run signature missing: {suite}")
        signature = json.loads(signature_path.read_text(encoding="utf-8"))
        if (
            signature.get("experiment_id")
            != "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1_DONOR_ACQUISITION"
            or signature.get("method") != "a0_official_qwen3vl32b_screenshot_only_donor_acquisition"
            or signature.get("manifest_sha256") not in {_file_sha(path) for path in manifest_paths}
            or signature.get("transport_policy") != "single_http_attempt_no_automatic_retry"
            or signature.get("donor_scored_hard_inputs_used") is not False
        ):
            raise RuntimeError(f"donor suite identity drift: {suite}")
        signature_sha = _file_sha(signature_path)
        checkpoint_path = suite / "checkpoint.json"
        if not checkpoint_path.is_file():
            raise RuntimeError(f"donor suite checkpoint missing: {suite}")
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        allowed_receipts = {str(signature.get("acquisition_server_receipt_sha256") or "")}
        receipt_records = list(checkpoint.get("acquisition_server_receipts") or [])
        allowed_receipts.update(str(item.get("file_sha256") or "") for item in receipt_records)
        if any(len(item) != 64 for item in allowed_receipts):
            raise RuntimeError(f"donor suite receipt rotation chain is invalid: {suite}")
        for receipt_sha in allowed_receipts:
            if receipt_sha not in receipts_by_file_sha:
                raise RuntimeError(f"donor acquisition receipt artifact missing: {receipt_sha}")
            receipt_path, receipt = receipts_by_file_sha[receipt_sha]
            if (
                receipt.get("status") != "pass"
                or len(str(receipt.get("repository_commit") or "")) != 40
                or receipt.get("served_model_id") != signature.get("model_id")
                or receipt.get("content_sha256") != _content_sha(receipt)
            ):
                raise RuntimeError(f"donor acquisition receipt identity drift: {receipt_path}")
            if (
                receipt_sha == signature.get("acquisition_server_receipt_sha256")
                and receipt.get("content_sha256")
                != signature.get("acquisition_server_receipt_content_sha256")
            ):
                raise RuntimeError(f"donor initial acquisition receipt binding drift: {receipt_path}")
            matching = [row for row in receipt_records if row.get("file_sha256") == receipt_sha]
            if matching and any(
                row.get("content_sha256") != receipt.get("content_sha256") for row in matching
            ):
                raise RuntimeError(f"donor acquisition receipt content drift: {receipt_path}")
        allowed_receipts_by_signature[_digest(signature)] = allowed_receipts
        suite_provenance.append(
            {
                "suite": str(suite.resolve()),
                "run_signature_sha256": signature_sha,
                "run_signature_content_sha256": _digest(signature),
                "checkpoint_sha256": _file_sha(checkpoint_path),
                "acquisition_server_receipt_sha256s": sorted(allowed_receipts),
            }
        )
        for episode_path in suite.glob("episodes/*/episode.json"):
            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            key = (str(episode.get("task_name")), int(episode.get("seed", -1)))
            if key not in manifest_rows:
                continue
            events_path = episode_path.with_name("events.jsonl")
            if not events_path.is_file():
                raise RuntimeError(f"donor events missing: {events_path}")
            observed.setdefault(key, []).append((episode, episode_path, events_path, signature, signature_path))
    outcomes: list[dict[str, Any]] = []
    successful_by_route: dict[str, list[dict[str, Any]]] = {}
    for key, spec in manifest_rows.items():
        records = observed.get(key) or []
        if not records:
            outcomes.append({"route_id": spec["route_id"], "task_class": key[0], "task_seed": key[1], "status": "NOT_RUN"})
            continue
        def valid_record(record: tuple[dict[str, Any], Path, Path, dict[str, Any], Path]) -> bool:
            candidate, _, candidate_events, candidate_signature, _ = record
            event_rows = [
                json.loads(line)
                for line in candidate_events.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            start = event_rows[0] if event_rows else {}
            initialized = event_rows[1] if len(event_rows) > 1 else {}
            replayed = replayed_identities[key]
            return (
                _episode_valid(candidate)
                and _events_valid(candidate_events, episode=candidate)
                and _digest(start.get("task_params")) == _digest(replayed["task_params"])
                and sha256(
                    str(start.get("task_goal_before_initialization")).encode("utf-8")
                ).hexdigest()
                == str(spec["goal_hash"])
                and str(start.get("task_goal_before_initialization"))
                == replayed["goal_before_initialization"]
                and str(initialized.get("task_goal_after_initialization"))
                == str(candidate.get("task_goal"))
                and int((candidate.get("run_metadata") or {}).get("native_max_steps") or -1)
                == int(spec["native_max_steps"])
                and (candidate.get("run_metadata") or {}).get("diagnostic") is True
                and (candidate.get("run_metadata") or {}).get("held_out_eligible") is False
                and (candidate.get("run_metadata") or {}).get("held_out_ineligible_reason")
                == "donor_acquisition_not_scored"
                and (candidate.get("run_metadata") or {}).get("run_signature_sha256")
                == _digest(candidate_signature)
                and (candidate.get("run_metadata") or {}).get("a4v2_acquisition_receipt_sha256")
                in allowed_receipts_by_signature[_digest(candidate_signature)]
            )
        valid_records = [record for record in records if valid_record(record)]
        if len(valid_records) > 1:
            raise RuntimeError(f"same donor slot has more than one scientifically valid attempt: {key}")
        record = valid_records[0] if valid_records else records[-1]
        episode, episode_path, events_path, signature, signature_path = record
        infrastructure_valid = bool(valid_records)
        success = infrastructure_valid and episode.get("success") is True and episode.get("evaluator_reward") == 1.0
        row = {
            "route_id": spec["route_id"],
            "task_class": key[0],
            "task_seed": key[1],
            "difficulty": spec["difficulty"],
            "optional": bool(spec["optional"]),
            "manifest_role": spec.get("manifest_role"),
            "status": "VALID_SUCCESS" if success else "VALID_SCIENTIFIC_FAILURE" if infrastructure_valid else "INFRA_INVALID",
            "reward": episode.get("evaluator_reward"),
            "episode_id": episode.get("episode_id"),
            "source_episode_sha256": _file_sha(episode_path),
            "source_events_sha256": _file_sha(events_path),
            "run_signature_sha256": _file_sha(signature_path),
            "attempts": [
                {
                    "episode_id": candidate.get("episode_id"),
                    "episode_sha256": _file_sha(candidate_path),
                    "events_sha256": _file_sha(candidate_events),
                    "infrastructure_valid": valid_record(candidate_record),
                }
                for candidate_record in records
                for candidate, candidate_path, candidate_events, _, _ in [candidate_record]
            ],
        }
        outcomes.append(row)
        if not success:
            continue
        donor_id = f"a4v2_{spec['route_id']}_{key[0]}_s{key[1]}"
        snapshot = _portable_snapshot(
            episode,
            raw_sha=row["source_episode_sha256"],
            events_sha=row["source_events_sha256"],
            task_params=json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])["task_params"],
        )
        snapshot_path = snapshots_dir / f"{donor_id}.json"
        _write(snapshot_path, snapshot)
        donor = {
            "donor_id": donor_id,
            "task_class": key[0],
            "task_seed": key[1],
            "difficulty": spec["difficulty"],
            "episode_path": str(snapshot_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
            "episode_sha256": _file_sha(snapshot_path),
            "source_episode_sha256": row["source_episode_sha256"],
            "source_events_sha256": row["source_events_sha256"],
        }
        successful_by_route.setdefault(str(spec["route_id"]), []).append(donor)
    required_successes: dict[str, int] = {}
    for row in outcomes:
        if row.get("manifest_role") == "required_panel" and row.get("status") == "VALID_SUCCESS":
            required_successes[str(row["route_id"])] = required_successes.get(str(row["route_id"]), 0) + 1
    for row in outcomes:
        if row.get("manifest_role") == "deficit_supplement" and required_successes.get(str(row["route_id"]), 0) >= 2:
            raise RuntimeError(f"supplement was run for an already-qualified route: {row['route_id']}")
    route_groups = []
    deficits = []
    attempted_keys = {
        (str(row.get("task_class")), int(row.get("task_seed", -1)))
        for row in outcomes
        if row.get("status") != "NOT_RUN"
    }
    fallback_by_route = {
        str(row["route_id"]): (str(row["task_class"]), int(row["task_seed"]))
        for row in plan.get("ordered_final_fallback_slots") or []
    }
    for group in plan.get("route_groups") or []:
        route_id = str(group["route_id"])
        donors = successful_by_route.get(route_id, [])
        if len({int(item["task_seed"]) for item in donors}) < int(group["minimum_successes"]):
            frozen_keys = {
                (str(item["task_class"]), int(item["task_seed"]))
                for item in group.get("slots") or []
            }
            if route_id in fallback_by_route:
                frozen_keys.add(fallback_by_route[route_id])
            exhausted = frozen_keys <= attempted_keys
            deficits.append(
                {
                    "route_id": route_id,
                    "minimum_successes": int(group["minimum_successes"]),
                    "observed_successes": len(donors),
                    "frozen_slot_count": len(frozen_keys),
                    "attempted_frozen_slot_count": len(frozen_keys & attempted_keys),
                    "frozen_attempts_exhausted": exhausted,
                    "next_action": (
                        "DONOR_COVERAGE_BLOCKED; no additional seed is authorized under this identity"
                        if exhausted
                        else "run the remaining already-frozen supplement slot"
                    ),
                }
            )
        route_groups.append({"route_id": route_id, "route": group["route"], "donors": donors})
    all_records = [record[0] for records in observed.values() for record in records]
    prompt_tokens = completion_tokens = transport_attempts = missing_usage_calls = 0
    elapsed_seconds = 0.0
    for episode in all_records:
        if episode.get("started_at") and episode.get("finished_at"):
            elapsed_seconds += (
                datetime.fromisoformat(str(episode["finished_at"]))
                - datetime.fromisoformat(str(episode["started_at"]))
            ).total_seconds()
        for step in episode.get("steps") or []:
            call = step.get("model_call") or {}
            if not call:
                continue
            usage = call.get("usage") or {}
            if not usage:
                missing_usage_calls += 1
            prompt_tokens += int(usage.get("prompt_tokens") or 0)
            completion_tokens += int(usage.get("completion_tokens") or 0)
            transport_attempts += int((call.get("raven_meta") or {}).get("transport_attempts") or 0)
    status = (
        "READY_FOR_SOURCE_LOCK"
        if not deficits and len(outcomes) >= 14
        else "DONOR_COVERAGE_BLOCKED"
        if deficits and all(bool(item["frozen_attempts_exhausted"]) for item in deficits)
        else "MORE_DONORS_REQUIRED"
    )
    report: dict[str, Any] = {
        "schema": "a4v2.donor_acquisition_result.v1",
        "status": status,
        "plan_file_sha256": _file_sha(plan_path),
        "manifest_file_sha256s": [_file_sha(path) for path in manifest_paths],
        "protocol_amendment_sha256": manifests[0]["protocol_amendment_sha256"],
        "suite_dirs": [str(path.resolve()) for path in suite_dirs],
        "suite_provenance": suite_provenance,
        "outcomes": outcomes,
        "route_deficits": deficits,
        "route_coverage": [
            {
                "route_id": item["route_id"],
                "minimum_successes": int(
                    next(
                        group["minimum_successes"]
                        for group in plan["route_groups"]
                        if group["route_id"] == item["route_id"]
                    )
                ),
                "observed_successes": len(item["donors"]),
                "qualified": len(item["donors"])
                >= int(
                    next(
                        group["minimum_successes"]
                        for group in plan["route_groups"]
                        if group["route_id"] == item["route_id"]
                    )
                ),
                "successful_donor_ids": [donor["donor_id"] for donor in item["donors"]],
                "successful_donor_seeds": [int(donor["task_seed"]) for donor in item["donors"]],
            }
            for item in route_groups
        ],
        "attempted_slot_count": len(outcomes),
        "valid_success_count": sum(row.get("status") == "VALID_SUCCESS" for row in outcomes),
        "valid_scientific_failure_count": sum(
            row.get("status") == "VALID_SCIENTIFIC_FAILURE" for row in outcomes
        ),
        "infrastructure_invalid_attempt_count": sum(
            not bool(attempt.get("infrastructure_valid"))
            for row in outcomes for attempt in row.get("attempts") or []
        ),
        "generation_calls": sum(
            int(record[0].get("model_call_count") or 0)
            for records in observed.values() for record in records
        ),
        "executed_actions": sum(int(item.get("executed_action_count") or 0) for item in all_records),
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "missing_usage_call_count": missing_usage_calls,
        },
        "transport": {
            "attempt_count": transport_attempts,
            "single_transport_per_completed_model_call": transport_attempts
            == sum(int(item.get("model_call_count") or 0) for item in all_records),
        },
        "elapsed_seconds_sum": elapsed_seconds,
        "downstream_authorization": {
            "source_lock": status == "READY_FOR_SOURCE_LOCK",
            "offline_induction": "AUTHORIZED" if status == "READY_FOR_SOURCE_LOCK" else "NOT_RUN_BY_PROTOCOL",
            "workflow_bank": "AUTHORIZED" if status == "READY_FOR_SOURCE_LOCK" else "NOT_RUN_BY_PROTOCOL",
            "scored_seven": "AUTHORIZED" if status == "READY_FOR_SOURCE_LOCK" else "NOT_RUN_BY_PROTOCOL",
        },
        "claim_boundary": {
            "evidence_class": "post_observed_donor_acquisition_diagnostic",
            "not_held_out": True,
            "failure_scope": "the frozen A0 screenshot-only controller, plan-v2 donor panel, seeds, budgets, and finite fallback schedule",
            "awm_general_invalidity_claim_forbidden": True,
            "no_induction_or_scored_transfer_claim": status != "READY_FOR_SOURCE_LOCK",
        },
    }
    report["content_sha256"] = _content_sha(report)
    _write(report_path, report)
    if deficits or len(observed) < 14:
        return report
    lock: dict[str, Any] = {
        "schema": "a4v2.donor_source_lock.v1",
        "status": "ready",
        "experiment_id": "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1",
        "plan_file_sha256": _file_sha(plan_path),
        "manifest_file_sha256s": [_file_sha(path) for path in manifest_paths],
        "protocol_amendment_sha256": manifests[0]["protocol_amendment_sha256"],
        "scored_hard_inputs_used": False,
        "route_groups": route_groups,
    }
    lock["content_sha256"] = _content_sha(lock)
    _write(output_path, lock)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=ROOT / "implementation/configs/a4v2_awm_donor_acquisition_plan.json")
    parser.add_argument("--manifest", type=Path, action="append")
    parser.add_argument("--suite-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--snapshots-dir", type=Path, default=DEFAULT_SNAPSHOTS)
    args = parser.parse_args()
    result = build(
        plan_path=args.plan.resolve(),
        manifest_paths=[path.resolve() for path in (args.manifest or [ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_V2.json"])],
        suite_dirs=[path.resolve() for path in args.suite_dir],
        output_path=args.output.resolve(),
        report_path=args.report.resolve(),
        snapshots_dir=args.snapshots_dir.resolve(),
    )
    print(json.dumps({"status": result["status"], "route_deficits": result["route_deficits"], "report": str(args.report)}, indent=2))
    if result["status"] != "READY_FOR_SOURCE_LOCK":
        raise SystemExit(3 if result["status"] == "DONOR_COVERAGE_BLOCKED" else 2)


if __name__ == "__main__":
    main()
