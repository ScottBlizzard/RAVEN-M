"""Build the frozen screenshot-only verifier set from the 57-key baseline."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports"
        / "official_qwen32b_full_hard_combined_corrected_final.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    combined = json.loads(source.read_text(encoding="utf-8"))
    selected = [
        item
        for item in combined["episodes"]
        if item["scientifically_eligible"]
        and item["model_claimed_status"] == "success"
    ]
    records: list[dict] = []
    for item in sorted(selected, key=lambda value: (value["task_name"], value["seed"])):
        suite_dir = Path(item["source_summary"]).resolve().parent
        episode_dir = suite_dir / "episodes" / item["episode_id"]
        episode_path = episode_dir / "episode.json"
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        terminal_steps = [
            step
            for step in episode["steps"]
            if step["decision"]["terminal_status"] == "success"
        ]
        if len(terminal_steps) != 1:
            raise RuntimeError(
                f"{item['episode_id']} has {len(terminal_steps)} success claims"
            )
        terminal = terminal_steps[0]
        screenshot = episode_dir / terminal["before"]["screenshot"]
        recorded_sha = terminal["before"]["screenshot_sha256"]
        if file_sha(screenshot) != recorded_sha:
            raise RuntimeError(f"screenshot hash mismatch: {screenshot}")
        records.append(
            {
                "episode_id": item["episode_id"],
                "task_name": item["task_name"],
                "seed": int(item["seed"]),
                "task_goal": episode["task_goal"],
                "terminal_step": int(terminal["step"]),
                "screenshot_path": screenshot.relative_to(REPOSITORY_ROOT).as_posix(),
                "screenshot_sha256": recorded_sha,
                "evaluator_reward": float(item["evaluator_reward"]),
                "evaluator_success": bool(item["success"]),
                "false_success_claim": not bool(item["success"]),
                "source_episode_json": episode_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "source_episode_json_sha256": file_sha(episode_path),
            }
        )

    if len(records) != 27:
        raise RuntimeError(f"expected 27 success claims, received {len(records)}")
    if sum(int(item["evaluator_success"]) for item in records) != 6:
        raise RuntimeError("expected six evaluator-confirmed success claims")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "completion_verifier_claim_set_v1",
        "source_report": source.relative_to(REPOSITORY_ROOT).as_posix(),
        "source_report_sha256": file_sha(source),
        "selection": (
            "scientifically eligible official 57-key episodes with "
            "model_claimed_status=success"
        ),
        "record_count": len(records),
        "evaluator_success_count": sum(
            int(item["evaluator_success"]) for item in records
        ),
        "false_success_count": sum(
            int(item["false_success_claim"]) for item in records
        ),
        "records": records,
    }
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), **{k: payload[k] for k in (
        "record_count", "evaluator_success_count", "false_success_count"
    )}}, indent=2))


if __name__ == "__main__":
    main()
