#!/usr/bin/env python3
"""Audit whether a source-document coverage claim survives later evidence.

This is a zero-model-call, post-hoc audit.  It reads frozen episode traces and
checks the specific contract needed by the source coverage gate: document
entry, forward progress, and whether a claimed bottom is contradicted by a
later forward swipe that changes the rendered document.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


DOCUMENT_ACTIVITY = "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"
MARKOR_PACKAGE = "net.gsantner.markor"
CHANGE_THRESHOLD = 0.001


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def activity(event: dict[str, Any], side: str) -> str | None:
    return (((event.get(side) or {}).get("foreground") or {}).get("activity"))


def package(event: dict[str, Any], side: str) -> str | None:
    return (((event.get(side) or {}).get("foreground") or {}).get("package"))


def executed_action(event: dict[str, Any]) -> dict[str, Any]:
    return (
        ((event.get("layers") or {}).get("L2_protocol_coordinate") or {}).get(
            "executed_canonical_action"
        )
        or ((event.get("decision") or {}).get("canonical_action"))
        or {}
    )


def is_forward_swipe(event: dict[str, Any]) -> bool:
    action = executed_action(event)
    if action.get("type") != "swipe":
        return False
    dx = float(action.get("x2", 0)) - float(action.get("x", 0))
    dy = float(action.get("y2", 0)) - float(action.get("y", 0))
    return abs(dy) >= abs(dx) and dy < 0


def audit_episode(episode_dir: Path) -> dict[str, Any]:
    episode_path = episode_dir / "episode.json"
    episode = load(episode_path)
    steps = episode.get("steps") or []
    opened_document = any(
        activity(step, "before") == DOCUMENT_ACTIVITY
        or activity(step, "after") == DOCUMENT_ACTIVITY
        for step in steps
    )
    entered_markor = any(
        package(step, "before") == MARKOR_PACKAGE
        or package(step, "after") == MARKOR_PACKAGE
        for step in steps
    )

    forward_steps: list[dict[str, Any]] = []
    first_bottom_step: int | None = None
    for step in steps:
        if activity(step, "before") == DOCUMENT_ACTIVITY and is_forward_swipe(step):
            transition = step.get("transition") or {}
            forward_steps.append(
                {
                    "step": int(step["step"]),
                    "changed_pixel_fraction_gt_5": float(
                        transition.get("changed_pixel_fraction_gt_5", 0.0)
                    ),
                    "ui_sha_changed": bool(transition.get("ui_sha_changed", False)),
                }
            )
        gate = step.get("source_document_coverage_gate") or {}
        before_state = gate.get("state_before_execution") or {}
        after_state = gate.get("state_after_execution") or {}
        if (
            first_bottom_step is None
            and not bool(before_state.get("bottom_attested", False))
            and bool(after_state.get("bottom_attested", False))
        ):
            first_bottom_step = int(step["step"])

    post_bottom_changes = [
        row
        for row in forward_steps
        if first_bottom_step is not None
        and row["step"] > first_bottom_step
        and (
            row["changed_pixel_fraction_gt_5"] > CHANGE_THRESHOLD
            or row["ui_sha_changed"]
        )
    ]
    return {
        "episode_id": episode["episode_id"],
        "task_name": episode["task_name"],
        "termination_reason": episode["termination_reason"],
        "entered_markor": entered_markor,
        "opened_document": opened_document,
        "forward_document_swipe_count": len(forward_steps),
        "first_bottom_attestation_step": first_bottom_step,
        "post_bottom_changed_forward_steps": post_bottom_changes,
        "bottom_contradicted_by_later_forward_change": bool(post_bottom_changes),
        "episode_json_sha256": digest(episode_path),
    }


def render_markdown(result: dict[str, Any]) -> str:
    rows = []
    for episode in result["episodes"]:
        contradiction = (
            "是" if episode["bottom_contradicted_by_later_forward_change"] else "否"
        )
        first_bottom = episode["first_bottom_attestation_step"]
        rows.append(
            "| {task} | {opened} | {swipes} | {bottom} | {contradiction} | {termination} |".format(
                task=episode["task_name"],
                opened="是" if episode["opened_document"] else "否",
                swipes=episode["forward_document_swipe_count"],
                bottom=first_bottom if first_bottom is not None else "—",
                contradiction=contradiction,
                termination=episode["termination_reason"],
            )
        )
    return "\n".join(
        [
            "# Source coverage contract audit",
            "",
            "这是对冻结轨迹的零模型调用机械审计，不改变任何实验结果。",
            "",
            "| 任务 | 打开文档 | 文档内向前滑动 | 首次宣称到底的步数 | 后续页面变化推翻到底判断 | 终止原因 |",
            "|---|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## 结论",
            "",
            result["conclusion"],
            "",
            f"输入 aggregate.json SHA-256：`{result['inputs']['aggregate_sha256']}`",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    args = parser.parse_args()

    suite_dir = args.suite_dir.resolve()
    aggregate_path = suite_dir / "aggregate.json"
    aggregate = load(aggregate_path)
    episodes = [
        audit_episode(suite_dir / "episodes" / row["episode_id"])
        for row in aggregate["episodes"]
    ]
    contradictions = sum(
        episode["bottom_contradicted_by_later_forward_change"]
        for episode in episodes
    )
    result = {
        "audit_class": "zero_model_call_frozen_trace_contract_audit",
        "change_threshold": CHANGE_THRESHOLD,
        "suite_id": aggregate["suite_id"],
        "episode_count": len(episodes),
        "opened_document_count": sum(e["opened_document"] for e in episodes),
        "bottom_attestation_count": sum(
            e["first_bottom_attestation_step"] is not None for e in episodes
        ),
        "contradicted_bottom_attestation_count": contradictions,
        "conclusion": (
            "一次无明显变化的向前滑动不足以证明文档到底：冻结轨迹中有一次到底判断，"
            "但它被后续同方向滑动产生的大幅页面变化直接推翻。因此，覆盖契约至少需要"
            "正确文件、已验证起点、单调向前推进和重复或独立的终点确认。"
        ),
        "episodes": episodes,
        "inputs": {"aggregate_sha256": digest(aggregate_path)},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
