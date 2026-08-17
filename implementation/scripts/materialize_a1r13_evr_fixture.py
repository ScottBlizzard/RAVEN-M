#!/usr/bin/env python3
"""Materialize the minimal committed A1-R13 zero-generation replay fixture."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r3_contract import FULL_TASK_ORDER, TASK_SEED  # noqa: E402


DEFAULT_SUITE = ROOT / "runs/sys_nag_v4/official_qwen_20260816T041833_e5618ea5"
DEFAULT_OUTPUT = ROOT / "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json"
SOURCE_RESULT = ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_COMPLETE_RESULT_2026-08-18.json"


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def materialize(suite: Path) -> dict[str, Any]:
    suite = suite.resolve()
    checkpoint_path = suite / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("sys_nag_valid_entries") or [])
    if len(summaries) != len(entries) or len(summaries) != 19:
        raise RuntimeError("source suite does not contain 19 bound valid episodes")
    if [row.get("task_name") for row in summaries] != list(FULL_TASK_ORDER):
        raise RuntimeError("source task order drift")
    episodes: list[dict[str, Any]] = []
    for summary, entry in zip(summaries, entries, strict=True):
        episode_path = suite / "episodes" / str(summary["episode_id"]) / "episode.json"
        if file_sha256(episode_path) != entry.get("episode_json_sha256"):
            raise RuntimeError("source episode hash drift")
        on_disk = json.loads(episode_path.read_text(encoding="utf-8"))
        if on_disk != summary or canonical_sha256(summary) != entry.get("summary_sha256"):
            raise RuntimeError("source episode summary drift")
        steps: list[dict[str, Any]] = []
        for step in summary.get("steps") or []:
            decision = step.get("decision") or {}
            call = step.get("model_call") or {}
            steps.append(
                {
                    "source_step": int(step["step"]),
                    "action_summary": str(decision.get("action_summary") or ""),
                    "source_call_id": str(call.get("call_id") or ""),
                    "source_response_sha256": str(call.get("response_sha256") or ""),
                    "source_screenshot_sha256": str(step.get("before_screenshot_sha256") or ""),
                    "write_observed": step.get("memory_write") is not None,
                    "executed": bool(step.get("executed")),
                }
            )
        episodes.append(
            {
                "task_name": summary["task_name"],
                "seed": summary["seed"],
                "episode_id": summary["episode_id"],
                "success": bool(summary["success"]),
                "reward": summary["evaluator_reward"],
                "episode_json_file_sha256": entry["episode_json_sha256"],
                "summary_canonical_sha256": entry["summary_sha256"],
                "steps": steps,
            }
        )
    result = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    fixture: dict[str, Any] = {
        "schema": "a1r13_evr_replay_fixture_v1",
        "source_classification": "posthoc_design_development_not_confirmatory",
        "source_suite_id": suite.name,
        "source_checkpoint_file_sha256": file_sha256(checkpoint_path),
        "source_run_signature_file_sha256": file_sha256(suite / "run_signature.json"),
        "source_manifest_snapshot_file_sha256": file_sha256(suite / "manifest.snapshot.json"),
        "source_v4_result_content_sha256": result["content_sha256"],
        "source_v4_result_file_sha256": file_sha256(SOURCE_RESULT),
        "task_seed": TASK_SEED,
        "generation_calls": 0,
        "episode_count": len(episodes),
        "step_count": sum(len(row["steps"]) for row in episodes),
        "episodes": episodes,
    }
    fixture["content_sha256"] = content_sha256(fixture)
    return fixture


def write(output: Path, fixture: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    fixture = materialize(args.suite_dir)
    write(args.output, fixture)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "episode_count": fixture["episode_count"],
        "step_count": fixture["step_count"],
        "content_sha256": fixture["content_sha256"],
        "generation_calls": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
