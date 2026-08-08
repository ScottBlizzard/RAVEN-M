"""Find exact repeated screenshots and compare the next model action.

The input is a merged suite summary.  Only scientifically eligible episodes
listed in that summary are read, so infrastructure-invalid audit records never
enter the analysis.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _episode_dir(episode: dict[str, Any]) -> Path:
    source = Path(episode["source_summary"])
    return source.parent / "episodes" / episode["episode_id"]


def _tool_signature(step: dict[str, Any]) -> str:
    decision = step.get("decision") or {}
    tool = decision.get("tool") or {}
    payload = {
        "name": tool.get("name"),
        "arguments": tool.get("arguments"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def analyze(summary_path: Path) -> dict[str, Any]:
    summary = _read_json(summary_path)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in summary.get("episodes", []):
        if not episode.get("scientifically_eligible", False):
            continue
        events_path = _episode_dir(episode) / "events.jsonl"
        if not events_path.exists():
            continue
        for raw_line in events_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(raw_line)
            if event.get("event") != "step":
                continue
            before = event.get("before") or {}
            screenshot_hash = (
                before.get("screenshot_sha256")
                or event.get("before_screenshot_sha256")
            )
            if not screenshot_hash:
                continue
            decision = event.get("decision") or {}
            groups[str(screenshot_hash)].append(
                {
                    "episode_id": episode.get("episode_id"),
                    "task_name": episode.get("task_name"),
                    "seed": episode.get("seed"),
                    "step": event.get("step"),
                    "prompt_sha256": (event.get("model_call") or {}).get(
                        "prompt_sha256"
                    ),
                    "action_summary": decision.get("action_summary"),
                    "tool_signature": _tool_signature(event),
                    "screenshot": str(_episode_dir(episode) / before.get("screenshot", "")),
                }
            )

    reused: list[dict[str, Any]] = []
    for screenshot_hash, records in groups.items():
        if len(records) < 2:
            continue
        task_names = sorted({str(item["task_name"]) for item in records})
        action_signatures = sorted({item["tool_signature"] for item in records})
        prompt_hashes = sorted(
            {str(item["prompt_sha256"]) for item in records if item["prompt_sha256"]}
        )
        reused.append(
            {
                "screenshot_sha256": screenshot_hash,
                "record_count": len(records),
                "task_count": len(task_names),
                "task_names": task_names,
                "distinct_prompt_count": len(prompt_hashes),
                "distinct_action_count": len(action_signatures),
                "same_observation_different_action": len(action_signatures) > 1,
                "records": records,
            }
        )
    reused.sort(
        key=lambda item: (
            item["same_observation_different_action"],
            item["task_count"],
            item["record_count"],
        ),
        reverse=True,
    )
    return {
        "source_summary": str(summary_path.resolve()),
        "eligible_episode_count": summary.get(
            "scientifically_eligible_episode_count", 0
        ),
        "reused_observation_count": len(reused),
        "different_action_group_count": sum(
            bool(item["same_observation_different_action"]) for item in reused
        ),
        "groups": reused,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.summary_json)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
