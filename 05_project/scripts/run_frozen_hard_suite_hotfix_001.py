"""Aggregation-only protocol-v1 hotfix for the frozen Hard runner.

The protocol-v1 runner is intentionally left byte-for-byte unchanged.  This
wrapper normalizes a nullable, non-semantic history instrumentation field
before the frozen ``record_result`` function is called.  It also backfills a
completed raw episode whose post-episode aggregation was interrupted by that
same bug.  No prompt, task, model call, action, evaluator output, retry rule,
or success label is changed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_frozen_hard_suite as frozen  # noqa: E402


AMENDMENT_ID = "protocol-v1-hotfix-001"
AMENDMENT_MANIFEST = (
    PROJECT_ROOT / "metadata/protocol_amendment_001.json"
)
ORIGINAL_RECORD_RESULT = frozen.record_result
ORIGINAL_VERIFY_FREEZE = frozen.verify_freeze


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_amendment_manifest(*, require_tag: bool) -> dict[str, Any]:
    if not AMENDMENT_MANIFEST.is_file():
        raise RuntimeError("Protocol amendment manifest is absent.")
    manifest = json.loads(AMENDMENT_MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("amendment_id") != AMENDMENT_ID
        or manifest.get("status") != "active"
        or manifest.get("scope") != "post_episode_aggregation_only"
    ):
        raise RuntimeError("Protocol amendment identity or scope is invalid.")
    required_files = {
        item["path"]: item["sha256"] for item in manifest["files"]
    }
    for relative_path, expected in required_files.items():
        path = REPOSITORY_ROOT / relative_path
        if not path.is_file() or file_sha256(path) != expected:
            raise RuntimeError(
                f"Protocol amendment hash mismatch: {relative_path}"
            )
    if require_tag:
        tag = manifest["git_tag"]
        tag_commit = frozen.git("rev-parse", f"{tag}^{{commit}}")
        frozen.git("merge-base", "--is-ancestor", tag_commit, "HEAD")
        manifest = {**manifest, "git_tag_commit": tag_commit}
    return manifest


def normalize_nullable_history_details(
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Return an aggregation-safe copy without altering the raw episode."""
    normalized = deepcopy(summary)
    for step in normalized.get("steps", []):
        history_update = step.get("history_update")
        if (
            isinstance(history_update, dict)
            and history_update.get("details") is None
        ):
            history_update["details"] = {}
    return normalized


def amendment_result_identity() -> dict[str, Any]:
    manifest = load_amendment_manifest(require_tag=False)
    return {
        "amendment_id": manifest["amendment_id"],
        "scope": manifest["scope"],
        "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
        "hotfix_runner_sha256": file_sha256(Path(__file__).resolve()),
    }


def record_result_hotfix_001(
    *,
    schedule_record: dict[str, Any],
    summary: dict[str, Any],
    attempt_count: int,
    infra_attempts: list[dict[str, Any]],
    episode_dir: Path,
) -> dict[str, Any]:
    result = ORIGINAL_RECORD_RESULT(
        schedule_record=schedule_record,
        summary=normalize_nullable_history_details(summary),
        attempt_count=attempt_count,
        infra_attempts=infra_attempts,
        episode_dir=episode_dir,
    )
    result["protocol_amendment"] = amendment_result_identity()
    return result


def verify_freeze_hotfix_001() -> dict[str, Any]:
    freeze = ORIGINAL_VERIFY_FREEZE()
    manifest = load_amendment_manifest(require_tag=True)
    return {
        **freeze,
        "protocol_amendment": {
            "amendment_id": manifest["amendment_id"],
            "scope": manifest["scope"],
            "manifest_sha256": file_sha256(AMENDMENT_MANIFEST),
            "git_tag": manifest["git_tag"],
            "git_tag_commit": manifest["git_tag_commit"],
        },
    }


def backfill_completed_raw_results(suite_dir: Path) -> list[str]:
    """Score already-finished, non-infrastructure raw episodes exactly once."""
    backfilled = []
    episodes_root = suite_dir / "episodes"
    if not episodes_root.is_dir():
        return backfilled
    for record_dir in sorted(episodes_root.iterdir()):
        if not record_dir.is_dir():
            continue
        final_path = record_dir / "scored_result.json"
        if final_path.is_file():
            continue
        schedule_path = record_dir / "schedule_record.json"
        if not schedule_path.is_file():
            continue
        schedule_record = json.loads(
            schedule_path.read_text(encoding="utf-8")
        )
        infra_attempts, _ = frozen.load_formal_infrastructure_attempts(
            record_dir / "infrastructure_attempts.json"
        )
        excluded_attempts = {
            int(item["attempt"]) for item in infra_attempts
        }
        candidates = []
        for attempt_dir in sorted(record_dir.glob("attempt_*")):
            if not attempt_dir.is_dir():
                continue
            try:
                attempt = int(attempt_dir.name.rsplit("_", 1)[1])
            except (IndexError, ValueError):
                continue
            episode_path = attempt_dir / "episode.json"
            if attempt in excluded_attempts or not episode_path.is_file():
                continue
            summary = json.loads(episode_path.read_text(encoding="utf-8"))
            if summary.get("error") is not None:
                continue
            if (
                summary.get("variant") != schedule_record["variant"]
                or int(summary.get("seed", -1))
                != int(schedule_record["instance_seed"])
            ):
                raise RuntimeError(
                    f"Raw episode identity mismatch: {attempt_dir}"
                )
            candidates.append((attempt, attempt_dir, summary))
        if len(candidates) > 1:
            raise RuntimeError(
                f"Multiple completed non-infrastructure attempts: {record_dir}"
            )
        if not candidates:
            continue
        attempt, attempt_dir, summary = candidates[0]
        result = record_result_hotfix_001(
            schedule_record=schedule_record,
            summary=summary,
            attempt_count=attempt,
            infra_attempts=infra_attempts,
            episode_dir=attempt_dir,
        )
        frozen.write_json(final_path, result)
        backfilled.append(result["episode_id"])
    return backfilled


def suite_dir_from_argv() -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--suite-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs/frozen_hard_v1",
    )
    args, _ = parser.parse_known_args()
    return args.output_root / args.suite_id


def main() -> None:
    # Verify the original freeze and this separately tagged amendment before
    # creating or backfilling any scored artifact.
    verify_freeze_hotfix_001()
    backfilled = backfill_completed_raw_results(suite_dir_from_argv())
    if backfilled:
        print(
            json.dumps(
                {"hotfix_backfilled_episode_ids": backfilled},
                ensure_ascii=False,
            ),
            flush=True,
        )
    frozen.record_result = record_result_hotfix_001
    frozen.verify_freeze = verify_freeze_hotfix_001
    frozen.main()


if __name__ == "__main__":
    main()
