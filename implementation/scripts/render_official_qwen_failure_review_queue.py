"""Render a compact, evidence-linked queue for manual earliest-failure review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _episode_dir(item: dict[str, Any]) -> Path:
    source = Path(str(item["source_summary"]))
    return source.parent / "episodes" / str(item["episode_id"])


def _short(text: Any, limit: int = 100) -> str:
    value = " ".join(str(text or "").split()).replace("|", "\\|")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("combined_summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.combined_summary.read_text(encoding="utf-8"))

    lines = [
        "# Official Qwen3-VL-32B Full Hard：人工最早失败审查队列",
        "",
        "本表仅列科学有效记录。自动信号用于定位截图，不能代替语义根因标注。",
        "",
        "| Task | Seed | Reward | Calls | Terminal | Protocol step | Stagnant ranges | Last action | Episode |",
        "|---|---:|---:|---:|---|---|---|---|---|",
    ]
    for item in payload.get("episodes") or []:
        episode_dir = _episode_dir(item)
        episode_path = episode_dir / "episode.json"
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        steps = episode.get("steps") or []
        protocol_steps = ",".join(str(x) for x in item.get("protocol_error_steps") or []) or "-"
        stagnant = ",".join(
            f"{r['start']}-{r['end']}"
            for r in item.get("nearly_unchanged_ranges") or []
            if int(r.get("length", 0)) >= 2
        ) or "-"
        last_action = (
            steps[-1].get("decision", {}).get("action_summary") if steps else ""
        )
        lines.append(
            f"| {item.get('task_name')} | {item.get('seed')} | "
            f"{item.get('evaluator_reward')} | {item.get('step_count')} | "
            f"{item.get('termination_reason')} | {protocol_steps} | {stagnant} | "
            f"{_short(last_action)} | `{episode_dir}` |"
        )
    lines.extend(
        [
            "",
            "## 人工标注字段",
            "",
            "每条失败记录补充：`earliest_step`、`primary_layer`、`hard_constraint`、"
            "`evidence_before/after`、`later_amplifier`、`candidate_intervention`。"
            "成功记录只说明形成闭环的关键条件，不反向虚构失败层。",
            "",
        ]
    )
    rendered = "\n".join(lines)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
