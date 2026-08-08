#!/usr/bin/env python3
"""Relate Markor document browsing coverage to frozen object-extractor recall."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


DOCUMENT_ACTIVITY = "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def activity(state: dict[str, Any] | None) -> str | None:
    return ((((state or {}).get("foreground") or {}).get("activity")))


def screenshot_hash(state: dict[str, Any] | None) -> str | None:
    state = state or {}
    return state.get("screenshot_sha256") or state.get("pixel_sha256")


def audit_episode(result: dict[str, Any], events_path: Path) -> dict[str, Any]:
    unique_doc_hashes: set[str] = set()
    scroll_up = 0
    scroll_down = 0
    horizontal_swipes = 0
    doc_actions = 0
    doc_steps: set[int] = set()
    for event in load_events(events_path):
        if event.get("event") != "step":
            continue
        before = event.get("before")
        after = event.get("after")
        before_doc = activity(before) == DOCUMENT_ACTIVITY
        after_doc = activity(after) == DOCUMENT_ACTIVITY
        if before_doc:
            doc_steps.add(int(event["step"]))
            doc_actions += 1
        for state in (before, after):
            if activity(state) == DOCUMENT_ACTIVITY:
                value = screenshot_hash(state)
                if value:
                    unique_doc_hashes.add(value)
        if not before_doc:
            continue
        action = ((event.get("decision") or {}).get("canonical_action") or {})
        if action.get("type") != "swipe":
            continue
        dx = float(action.get("x2", 0)) - float(action.get("x", 0))
        dy = float(action.get("y2", 0)) - float(action.get("y", 0))
        if abs(dy) >= abs(dx):
            if dy < 0:
                scroll_up += 1
            elif dy > 0:
                scroll_down += 1
        else:
            horizontal_swipes += 1

    if scroll_up == 0:
        coverage_band = "no_forward_scroll"
    elif scroll_up == 1:
        coverage_band = "one_forward_scroll"
    else:
        coverage_band = "multiple_forward_scrolls"
    return {
        "episode_id": result["episode_id"],
        "task_name": result["task_name"],
        "seed": result["seed"],
        "expected_count": len(result["expected_identifiers_hidden_for_scoring_only"]),
        "extractor_frame_count": len(result["record_ids"]),
        "unique_document_observation_count": len(unique_doc_hashes),
        "document_action_count": doc_actions,
        "forward_scroll_count": scroll_up,
        "backward_scroll_count": scroll_down,
        "horizontal_swipe_count": horizontal_swipes,
        "coverage_band": coverage_band,
        "true_positive": result["true_positive"],
        "false_negative": result["false_negative"],
        "recall": result["true_positive"] / len(result["expected_identifiers_hidden_for_scoring_only"]),
        "full_recall": result["full_recall"],
        "events_path": str(events_path),
        "events_sha256": sha256(events_path),
    }


def build_markdown(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# Markor 文档浏览覆盖与对象召回审计",
        "",
        "## 结论",
        "",
        (
            f"8条已打开 Markor 文档的轨迹中，{s['episodes_without_forward_scroll']}/8 没有执行任何向前浏览文档的纵向滑动，"
            f"全部轨迹合计为 {s['forward_scrolls']} 次向前滑动。整个零滑动组的对象召回为 "
            f"{s['no_scroll_true_positive']}/{s['no_scroll_expected']}（{100*s['no_scroll_recall']:.2f}%）。"
        ),
        "",
        "这里不存在可比较的‘已滚动组’，所以不能估计滑动动作的因果效应；但它给出了更直接的过程事实：原 Agent 从未通过纵向滑动系统遍历文档，却在多个轨迹中声称已经读完、已经筛选或没有符合条件的对象。更严格的下一步需要预注册 coverage contract，例如持续采样直到页面指纹不再前进，并在新实例上测覆盖率与对象召回。",
        "",
        "## 逐轨迹结果",
        "",
        "| 任务 | seed | 提取截图 | 文档唯一画面 | 向前滑动 | 找回/目标 | 完整召回 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for ep in result["episodes"]:
        lines.append(
            f"| {ep['task_name']} | {ep['seed']} | {ep['extractor_frame_count']} | "
            f"{ep['unique_document_observation_count']} | {ep['forward_scroll_count']} | "
            f"{ep['true_positive']}/{ep['expected_count']} | {'是' if ep['full_recall'] else '否'} |"
        )
    lines.extend([
        "",
        "## 有效性边界",
        "",
        "本审计只复用冻结事件日志和已经完成的提取器结果，模型调用为0。滑动方向由规范化动作坐标判定，文档画面数按 screenshot SHA-256 去重；页面哈希不同可能来自光标、滚动或其他局部变化，不能等价于覆盖了新的完整记录。零滑动轨迹仍可能在首屏看见全部目标，而有滑动轨迹也可能反复浏览同一区域。",
        "",
        "## 可复现性",
        "",
        f"- 提取器汇总 SHA-256：`{result['extractor_aggregate_sha256']}`",
        "- 逐轨迹事件路径与事件 SHA-256 均保存在 JSON 结果中。",
        "- 脚本：`05_project/scripts/audit_markor_document_coverage.py`。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractor-aggregate", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--md-output", required=True, type=Path)
    args = parser.parse_args()
    aggregate = json.loads(args.extractor_aggregate.read_text(encoding="utf-8"))
    frame_by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in aggregate["frame_results"]:
        frame_by_episode[frame["record"]["episode_id"]].append(frame)
    episodes = []
    for episode_result in aggregate["episode_results"]:
        first_frame = frame_by_episode[episode_result["episode_id"]][0]
        events_path = Path(first_frame["record"]["events_path"])
        episodes.append(audit_episode(episode_result, events_path))
    no_scroll = [ep for ep in episodes if ep["forward_scroll_count"] == 0]
    scrolled = [ep for ep in episodes if ep["forward_scroll_count"] > 0]
    no_scroll_expected = sum(ep["expected_count"] for ep in no_scroll)
    scroll_expected = sum(ep["expected_count"] for ep in scrolled)
    no_scroll_tp = sum(ep["true_positive"] for ep in no_scroll)
    scroll_tp = sum(ep["true_positive"] for ep in scrolled)
    summary = {
        "episode_count": len(episodes),
        "episodes_without_forward_scroll": len(no_scroll),
        "episodes_with_forward_scroll": len(scrolled),
        "forward_scrolls": sum(ep["forward_scroll_count"] for ep in episodes),
        "no_scroll_true_positive": no_scroll_tp,
        "no_scroll_expected": no_scroll_expected,
        "no_scroll_recall": no_scroll_tp / no_scroll_expected if no_scroll_expected else None,
        "scroll_true_positive": scroll_tp,
        "scroll_expected": scroll_expected,
        "scroll_recall": scroll_tp / scroll_expected if scroll_expected else None,
    }
    result = {
        "audit_type": "deterministic_zero_generation_posthoc_markor_document_coverage",
        "extractor_aggregate": str(args.extractor_aggregate.resolve()),
        "extractor_aggregate_sha256": sha256(args.extractor_aggregate),
        "summary": summary,
        "episodes": episodes,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_output.write_text(build_markdown(result), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
