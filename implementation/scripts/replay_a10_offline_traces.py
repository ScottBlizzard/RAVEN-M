#!/usr/bin/env python3
"""Materialize, hash-verify, and replay the frozen real A10 trace set.

The materialized PNG bundle is intentionally kept outside git.  The committed
manifest freezes every copied byte; formal preflight verifies that manifest and
replays the real RGB frames with zero generation calls.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (  # noqa: E402
    EvidenceCalibratedObligationBranchFrontierMemory,
    canonical_action_family,
    describe_visual_state,
)


SOURCE_SPEC = ROOT / "evidence/a10/A10_OFFLINE_TRACE_SOURCE_SPEC.json"
TRACE_MANIFEST = ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json"
MECHANISM_SOURCE = ROOT / "implementation/src/raven_m/official_qwen_mobile/a10_obligation_branch_frontier.py"


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(path: Path) -> str:
    value = load_json(path)
    return sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_sources(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        role, separator, raw_path = value.partition("=")
        if not separator or not role or not raw_path:
            raise RuntimeError(f"invalid --source mapping: {value!r}")
        result[role] = Path(raw_path).resolve()
    return result


def _provenance_errors(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for relative, expected in (
        (spec.get("provenance") or {}).get("evidence_json_canonical_sha256") or {}
    ).items():
        path = ROOT / str(relative)
        if not path.is_file() or canonical_json_sha256(path) != expected:
            errors.append(f"provenance_evidence_hash_mismatch:{relative}")
    return errors


def _paired_expected_episode_hashes() -> dict[tuple[str, str], str]:
    reference = load_json(ROOT / "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json")
    expected: dict[tuple[str, str], str] = {}
    for item in reference.get("tasks") or []:
        for arm, role in (("A0", "a0"), ("A1", "a1_recipe")):
            record = item.get(arm) or {}
            if record.get("episode_id") and record.get("episode_json_sha256"):
                expected[(role, str(record["episode_id"]))] = str(
                    record["episode_json_sha256"]
                )
    return expected


def _required_episode_files(episode_dir: Path, episode: dict[str, Any]) -> list[Path]:
    files = [episode_dir / "episode.json"]
    for step in episode.get("steps") or []:
        if not step.get("executed"):
            continue
        for side in ("before", "after"):
            screenshot = str((step.get(side) or {}).get("screenshot") or "")
            if not screenshot:
                raise RuntimeError(f"missing {side} screenshot reference in {episode_dir}")
            path = episode_dir / screenshot
            expected = str((step.get(side) or {}).get("screenshot_sha256") or "")
            if not path.is_file() or file_sha256(path) != expected:
                raise RuntimeError(f"source screenshot hash mismatch: {path}")
            files.append(path)
    return sorted(set(files), key=lambda path: path.name)


def build_materialized(
    *, destination: Path, sources: dict[str, Path], manifest_path: Path
) -> dict[str, Any]:
    spec = load_json(SOURCE_SPEC)
    provenance_errors = _provenance_errors(spec)
    if provenance_errors:
        raise RuntimeError(f"source provenance invalid: {provenance_errors}")
    paired_expected = _paired_expected_episode_hashes()
    expected_suite_metadata = (
        (spec.get("provenance") or {}).get("suite_metadata_sha256") or {}
    )
    expected_roles = set((spec.get("roles") or {}).keys())
    if set(sources) != expected_roles:
        raise RuntimeError(
            f"source roles differ: expected={sorted(expected_roles)} got={sorted(sources)}"
        )
    records: list[dict[str, Any]] = []
    suite_files: list[dict[str, Any]] = []
    for role, role_spec in spec["roles"].items():
        suite_dir = sources[role]
        if suite_dir.name != role_spec["suite_id"]:
            raise RuntimeError(f"{role} suite id mismatch: {suite_dir.name}")
        for metadata_name in ("aggregate.json", "checkpoint.json", "run_signature.json"):
            source_metadata = suite_dir / metadata_name
            if source_metadata.is_file():
                expected_metadata_sha = expected_suite_metadata.get(
                    f"{role}/{metadata_name}"
                )
                if (
                    not expected_metadata_sha
                    or file_sha256(source_metadata) != expected_metadata_sha
                ):
                    raise RuntimeError(
                        f"source suite metadata provenance mismatch: {role}/{metadata_name}"
                    )
                relative = Path(role) / "suite_metadata" / metadata_name
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_metadata, target)
                suite_files.append(
                    {
                        "role": role,
                        "path": relative.as_posix(),
                        "sha256": file_sha256(target),
                        "bytes": target.stat().st_size,
                    }
                )
        for episode_id in role_spec["episodes"]:
            source_episode = suite_dir / "episodes" / episode_id
            episode_path = source_episode / "episode.json"
            if not episode_path.is_file():
                raise RuntimeError(f"missing source episode: {episode_path}")
            episode = load_json(episode_path)
            if str(episode.get("episode_id")) != episode_id:
                raise RuntimeError(f"episode id mismatch: {episode_path}")
            paired_sha = paired_expected.get((role, episode_id))
            if paired_sha is not None and file_sha256(episode_path) != paired_sha:
                raise RuntimeError(
                    f"paired reference episode hash mismatch: {role}/{episode_id}"
                )
            copied: list[dict[str, Any]] = []
            for source_file in _required_episode_files(source_episode, episode):
                relative = Path(role) / "episodes" / episode_id / source_file.name
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target)
                copied.append(
                    {
                        "path": relative.as_posix(),
                        "sha256": file_sha256(target),
                        "bytes": target.stat().st_size,
                    }
                )
            records.append(
                {
                    "role": role,
                    "suite_id": role_spec["suite_id"],
                    "episode_id": episode_id,
                    "task_name": episode.get("task_name"),
                    "seed": episode.get("seed"),
                    "reward": episode.get("evaluator_reward"),
                    "success": episode.get("success"),
                    "episode_json_sha256": file_sha256(episode_path),
                    "files": copied,
                }
            )
    manifest = {
        "schema": "a10_offline_trace_manifest_v1",
        "generation_calls": 0,
        "source_spec_sha256": file_sha256(SOURCE_SPEC),
        "episode_count": len(records),
        "file_count": sum(len(record["files"]) for record in records) + len(suite_files),
        "total_bytes": sum(
            item["bytes"] for record in records for item in record["files"]
        ) + sum(item["bytes"] for item in suite_files),
        "suite_files": suite_files,
        "records": records,
    }
    write_json(manifest_path, manifest)
    return manifest


def verify_materialized(destination: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    spec = load_json(SOURCE_SPEC)
    errors: list[str] = []
    errors.extend(_provenance_errors(spec))
    if manifest.get("schema") != "a10_offline_trace_manifest_v1":
        errors.append("manifest_schema_drift")
    if manifest.get("source_spec_sha256") != file_sha256(SOURCE_SPEC):
        errors.append("source_spec_hash_drift")
    expected_suite_metadata = (
        (spec.get("provenance") or {}).get("suite_metadata_sha256") or {}
    )
    observed_suite_metadata = {
        f"{item.get('role')}/{Path(str(item.get('path'))).name}": item.get("sha256")
        for item in manifest.get("suite_files") or []
    }
    if observed_suite_metadata != expected_suite_metadata:
        errors.append("suite_metadata_provenance_drift")
    paired_expected = _paired_expected_episode_hashes()
    observed_records = {
        (str(item.get("role")), str(item.get("episode_id"))): str(
            item.get("episode_json_sha256")
        )
        for item in manifest.get("records") or []
    }
    paired_observed = {
        key: value
        for key, value in observed_records.items()
        if key[0] in {"a0", "a1_recipe"}
    }
    if any(paired_expected.get(key) != value for key, value in paired_observed.items()):
        errors.append("paired_reference_episode_hash_drift")
    items = list(manifest.get("suite_files") or []) + [
        item for record in manifest.get("records") or [] for item in record.get("files") or []
    ]
    for item in items:
        path = destination / str(item.get("path") or "")
        if (
            not path.is_file()
            or path.stat().st_size != int(item.get("bytes") or -1)
            or file_sha256(path) != item.get("sha256")
        ):
            errors.append(f"materialized_file_invalid:{item.get('path')}")
    if len(items) != int(manifest.get("file_count") or -1):
        errors.append("manifest_file_count_drift")
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "verified_file_count": len(items),
        "verified_total_bytes": sum(path.stat().st_size for path in [destination / item["path"] for item in items] if path.is_file()),
        "manifest_sha256": file_sha256(manifest_path),
    }


def _pixels(path: Path, cache: dict[str, np.ndarray], sha_key: str) -> np.ndarray:
    if sha_key in cache:
        return cache[sha_key]
    with Image.open(path) as image:
        pixels = np.asarray(image.convert("RGB"), dtype=np.uint8)
    cache[sha_key] = pixels
    # A route window is at most eight actions; 20 images covers both sides
    # without turning replay into an unbounded image store.
    while len(cache) > 20:
        del cache[next(iter(cache))]
    return pixels


def replay_episode(trace_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    episode_dir = trace_root / record["role"] / "episodes" / record["episode_id"]
    episode = load_json(episode_dir / "episode.json")
    executed = [step for step in episode.get("steps") or [] if step.get("executed")]
    if not executed:
        raise RuntimeError(f"no executed steps in {record['episode_id']}")
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    pixel_cache: dict[str, np.ndarray] = {}
    goal = str(episode.get("task_goal") or "")
    first_pixels = _pixels(
        episode_dir / executed[0]["before"]["screenshot"],
        pixel_cache,
        str(executed[0]["before"]["screenshot_sha256"]),
    )
    rendered, _ = memory.read({"goal": goal, "before": {"pixels": first_pixels}})
    rendered_blocks = [rendered]
    debug_events: list[dict[str, Any]] = []
    bad_branch_counts: dict[tuple[str, str], int] = {}
    qualifying_loop_segments = qualified_loop_segments = 0
    loop_qualification_records: list[dict[str, Any]] = []
    created_trigger_steps: list[dict[str, Any]] = []
    earliest_second_bad_branch_step: int | None = None
    earliest_closed_route_step: int | None = None
    for source_step, step in enumerate(executed):
        before = _pixels(
            episode_dir / step["before"]["screenshot"],
            pixel_cache,
            str(step["before"]["screenshot_sha256"]),
        )
        after = _pixels(
            episode_dir / step["after"]["screenshot"],
            pixel_cache,
            str(step["after"]["screenshot_sha256"]),
        )
        action = dict(
            (step.get("decision") or {}).get("canonical_action")
            or (step.get("mapped_action") or {}).get("canonical")
            or {}
        )
        summary = str((step.get("decision") or {}).get("action_summary") or "")
        result = memory.observe_step(
            source_step=source_step,
            action_summary=summary,
            canonical_action=action,
            before={"pixels": before},
            after={"pixels": after},
            source_response_sha256=str((step.get("model_call") or {}).get("response_sha256") or ""),
        )
        for trigger_id in result["trigger_ids_enqueued"]:
            trigger = next(
                (item for item in memory.trigger_candidates if item.trigger_id == trigger_id),
                None,
            )
            if trigger:
                created_trigger_steps.append(
                    {"step": source_step, "kind": trigger.kind, "frontier_id": trigger.query_frontier_id}
                )
        if result["immediate_outcome"].startswith("NO_PROGRESS"):
            key = (str(result["source_frontier_id"]), str(result["branch_id"]))
            bad_branch_counts[key] = bad_branch_counts.get(key, 0) + 1
            if bad_branch_counts[key] == 2:
                if earliest_second_bad_branch_step is None:
                    earliest_second_bad_branch_step = source_step
                qualifying_loop_segments += 1
                qualifying_trigger = any(
                    item["step"] <= source_step
                    and item["kind"] in {
                        "BAD_BRANCH_REPEAT",
                        "CLOSED_ROUTE_WITHOUT_ADVANCE",
                        "FRONTIER_COLLAPSE",
                    }
                    and item["frontier_id"] == key[0]
                    for item in created_trigger_steps
                )
                if qualifying_trigger:
                    qualified_loop_segments += 1
                loop_qualification_records.append(
                    {
                        "source_frontier_id": key[0],
                        "branch_id": key[1],
                        "second_no_progress_step": source_step,
                        "qualified_before_third_attempt": bool(qualifying_trigger),
                    }
                )
        closed_route_steps = [
            item["step"]
            for item in created_trigger_steps
            if item["kind"] == "CLOSED_ROUTE_WITHOUT_ADVANCE"
        ]
        if closed_route_steps:
            earliest_closed_route_step = min(closed_route_steps)
        rendered, read_audit = memory.read({"goal": goal, "before": {"pixels": after}})
        rendered_blocks.append(rendered)
        if result["trigger_ids_enqueued"] or result["route_resolutions"] or rendered:
            debug_events.append(
                {
                    "source_step": source_step,
                    "phase_switch": result["phase_switch"],
                    "route_resolutions": result["route_resolutions"],
                    "trigger_ids_enqueued": result["trigger_ids_enqueued"],
                    "read_nonempty": bool(rendered),
                    "read_audit": read_audit,
                }
            )
    audit = memory.audit_record()
    original_first_read = next(
        (
            int(step["step"])
            for step in episode.get("steps") or []
            if bool((step.get("memory_read") or {}).get("nonempty"))
        ),
        None,
    )
    return {
        "role": record["role"],
        "episode_id": record["episode_id"],
        "task_name": episode.get("task_name"),
        "reward_audit_only": episode.get("evaluator_reward"),
        "executed_actions_replayed": len(executed),
        "anchor_count": audit["goal"]["anchor_count"],
        "nonempty_reads": audit["reads"]["nonempty_read_count"],
        "delivered_trigger_count": sum(audit["triggers"]["delivered_counts_by_kind"].values()),
        "candidate_trigger_count": sum(audit["triggers"]["created_counts_by_kind"].values()),
        "created_counts_by_kind": audit["triggers"]["created_counts_by_kind"],
        "created_trigger_steps": created_trigger_steps,
        "debug_events": debug_events,
        "first_nonempty_read_step": (
            audit["reads"]["read_events"][0]["step"]
            if audit["reads"]["read_events"] else None
        ),
        "original_first_memory_read_step": original_first_read,
        "max_rendered_chars": max((len(item) for item in rendered_blocks), default=0),
        "qualifying_loop_segments": qualifying_loop_segments,
        "qualified_loop_segments": qualified_loop_segments,
        "loop_qualification_records": loop_qualification_records,
        "earliest_second_bad_branch_step": earliest_second_bad_branch_step,
        "earliest_closed_route_step": earliest_closed_route_step,
        "rendered_contains_boundary": all(
            "Open:" in item and "Evidence:" in item
            for item in rendered_blocks if item
        ),
        "completion_claim_present": any(
            phrase in item.casefold()
            for item in rendered_blocks
            for phrase in ("verified by evaluator", "task finished", "completed", "success")
        ),
    }


def verify_and_replay(trace_root: Path, manifest_path: Path = TRACE_MANIFEST) -> dict[str, Any]:
    verification = verify_materialized(trace_root, manifest_path)
    if verification["status"] != "pass":
        return {
            "schema": "a10_offline_replay_report_v1",
            "status": "fail",
            "generation_calls": 0,
            "replay_source_sha256": file_sha256(Path(__file__)),
            "mechanism_source_sha256": file_sha256(MECHANISM_SOURCE),
            "source_spec_sha256": file_sha256(SOURCE_SPEC),
            "manifest_sha256": file_sha256(manifest_path),
            "verification": verification,
            "errors": list(verification["errors"]),
        }
    manifest = load_json(manifest_path)
    episodes = [replay_episode(trace_root, record) for record in manifest["records"]]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for item in episodes:
        by_role.setdefault(item["role"], []).append(item)
    errors: list[str] = []
    a0_success = [
        item for item in by_role["a0"]
        if item["task_name"] != "RecipeDeleteMultipleRecipesWithConstraint"
    ]
    if len(a0_success) != 4 or any(
        item["nonempty_reads"] or item["delivered_trigger_count"] or item["max_rendered_chars"]
        for item in a0_success
    ):
        errors.append("a0_success_silence_gate_failed")
    a6_segments = sum(item["qualifying_loop_segments"] for item in by_role["a6"])
    a6_qualified = sum(item["qualified_loop_segments"] for item in by_role["a6"])
    a6_rate = a6_qualified / a6_segments if a6_segments else 0.0
    if a6_rate < .80 or any(item["nonempty_reads"] > 5 for item in by_role["a6"]):
        errors.append("a6_loop_activation_gate_failed")
    a8 = by_role["a8v2_expense"][0]
    a8_deadline_sources = [
        value
        for value in (
            a8["earliest_second_bad_branch_step"],
            a8["earliest_closed_route_step"],
        )
        if value is not None
    ]
    a8_deadline = min(a8_deadline_sources) + 1 if a8_deadline_sources else None
    if (
        not a8["candidate_trigger_count"]
        or a8["first_nonempty_read_step"] is None
        or a8_deadline is None
        or a8["first_nonempty_read_step"] > a8_deadline
        or a8["nonempty_reads"] > 5
        or not a8["rendered_contains_boundary"]
    ):
        errors.append("a8v2_expense_replay_gate_failed")
    a9 = by_role["a9_retro"][0]
    a9_first_candidate_step = min(
        (item["step"] for item in a9["created_trigger_steps"]),
        default=None,
    )
    if (
        a9_first_candidate_step is None
        or a9["nonempty_reads"] > 5
        or not a9["rendered_contains_boundary"]
        or (
            a9_first_candidate_step is not None
            and a9["original_first_memory_read_step"] is not None
            and a9_first_candidate_step > a9["original_first_memory_read_step"]
        )
    ):
        errors.append("a9_retro_replay_gate_failed")
    a1_recipe = by_role["a1_recipe"][0]
    # Apply the preregistered gate literally.  This exact query currently has
    # no legal candidate under the frozen parser; that specification conflict
    # is a failed gate, not permission to invent an object or weaken the gate.
    a1_recipe_has_required_evidence = any(
        a1_recipe["created_counts_by_kind"].get(kind, 0)
        for kind in (
            "PARTIAL_OBLIGATION_ESCAPE",
            "BAD_BRANCH_REPEAT",
            "CLOSED_ROUTE_WITHOUT_ADVANCE",
        )
    )
    if a1_recipe["anchor_count"] < 2 or not a1_recipe_has_required_evidence:
        errors.append("a1_recipe_sentinel_or_trace_evidence_failed")
    if any(item["completion_claim_present"] for item in episodes):
        errors.append("forbidden_completion_claim")
    return {
        "schema": "a10_offline_replay_report_v1",
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "replay_source_sha256": file_sha256(Path(__file__)),
        "mechanism_source_sha256": file_sha256(MECHANISM_SOURCE),
        "source_spec_sha256": file_sha256(SOURCE_SPEC),
        "manifest_sha256": file_sha256(manifest_path),
        "verification": verification,
        "episode_count": len(episodes),
        "a6_qualifying_loop_segments": a6_segments,
        "a6_qualified_loop_segments": a6_qualified,
        "a6_qualification_rate": a6_rate,
        "episodes": episodes,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=TRACE_MANIFEST)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.build:
        build_materialized(
            destination=args.trace_root.resolve(),
            sources=parse_sources(args.source),
            manifest_path=args.manifest.resolve(),
        )
    report = verify_and_replay(args.trace_root.resolve(), args.manifest.resolve())
    if args.report:
        write_json(args.report.resolve(), report)
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "generation_calls": report.get("generation_calls"),
                "episode_count": report.get("episode_count"),
                "verified_file_count": (report.get("verification") or {}).get(
                    "verified_file_count"
                ),
                "a6_qualification_rate": report.get("a6_qualification_rate"),
                "errors": report.get("errors") or [],
                "report": str(args.report.resolve()) if args.report else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
