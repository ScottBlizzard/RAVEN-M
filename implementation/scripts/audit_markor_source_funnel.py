#!/usr/bin/env python3
"""Audit the Markor source-document to destination-write funnel without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TASKS: dict[str, dict[str, str]] = {
    "ExpenseAddMultipleFromMarkor": {
        "filename": "my_expenses.txt",
        "destination_package": "com.arduia.expense",
    },
    "RecipeAddMultipleRecipesFromMarkor": {
        "filename": "recipes.txt",
        "destination_package": "com.flauschcode.broccoli",
    },
    "RecipeAddMultipleRecipesFromMarkor2": {
        "filename": "recipes.txt",
        "destination_package": "com.flauschcode.broccoli",
    },
}
MARKOR_PACKAGE = "net.gsantner.markor"
DOCUMENT_ACTIVITY_SUFFIX = "/net.gsantner.markor.activity.DocumentActivity"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def state_package(state: dict[str, Any] | None) -> str | None:
    return ((((state or {}).get("foreground") or {}).get("package")))


def state_activity(state: dict[str, Any] | None) -> str | None:
    return ((((state or {}).get("foreground") or {}).get("activity")))


def audit_episode(
    episode: dict[str, Any],
    extractor_by_episode: dict[str, dict[str, Any]],
    transfer_by_episode: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    task = episode["task_name"]
    config = TASKS[task]
    source_summary = Path(episode["source_summary"])
    episode_dir = source_summary.parent / "episodes" / episode["episode_id"]
    events_path = episode_dir / "events.jsonl"
    events = load_events(events_path)

    source_steps: list[int] = []
    correct_document_steps: list[int] = []
    destination_steps: list[int] = []
    for event in events:
        if event.get("event") != "step":
            continue
        step = int(event["step"])
        for state in (event.get("before"), event.get("after")):
            package = state_package(state)
            activity = state_activity(state) or ""
            if package == MARKOR_PACKAGE:
                source_steps.append(step)
            if package == config["destination_package"]:
                destination_steps.append(step)
            if (
                package == MARKOR_PACKAGE
                and activity.endswith(DOCUMENT_ACTIVITY_SUFFIX)
            ):
                correct_document_steps.append(step)

    extractor = extractor_by_episode.get(episode["episode_id"])
    transfer = transfer_by_episode[episode["episode_id"]]
    extracted_correct_count = int((extractor or {}).get("true_positive", 0))
    extracted_full_recall = bool((extractor or {}).get("full_recall", False))
    correct_document_opened = bool(correct_document_steps)
    destination_reached = bool(destination_steps)
    typed_correct_count = int(transfer["matched_identifier_count"])

    if not source_steps:
        first_failure = "source_app_not_reached"
    elif not correct_document_opened:
        first_failure = "correct_document_not_opened"
    elif extracted_correct_count == 0:
        first_failure = "no_correct_object_extracted_from_observed_frames"
    elif not destination_reached:
        first_failure = "destination_not_reached_after_source_capture"
    elif typed_correct_count == 0:
        first_failure = "correct_object_not_written_in_destination"
    elif not episode["success"]:
        first_failure = "some_correct_object_written_but_task_not_closed"
    else:
        first_failure = "full_success"

    return {
        "episode_id": episode["episode_id"],
        "task_name": task,
        "seed": episode["seed"],
        "source_app_reached": bool(source_steps),
        "source_entry_step": min(source_steps) if source_steps else None,
        "correct_document": config["filename"],
        "correct_document_opened": correct_document_opened,
        "correct_document_first_step": min(correct_document_steps) if correct_document_steps else None,
        "extractor_eligible": extractor is not None,
        "extracted_correct_count": extracted_correct_count,
        "extracted_any_correct": extracted_correct_count > 0,
        "extracted_full_recall": extracted_full_recall,
        "destination_reached": destination_reached,
        "destination_entry_step": min(destination_steps) if destination_steps else None,
        "typed_correct_count": typed_correct_count,
        "typed_any_correct": typed_correct_count > 0,
        "success": bool(episode["success"]),
        "evaluator_reward": episode["evaluator_reward"],
        "first_failure": first_failure,
        "events_path": str(events_path),
        "events_sha256": sha256(events_path),
    }


def build_markdown(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# Official Qwen Hard：Markor 源材料到最终写入的分层漏斗",
        "",
        "## 核心结果",
        "",
        (
            f"9 条 Markor 批量新增轨迹全部进入了源应用，但只有 {s['correct_document_opened']}/9 "
            f"真正打开指定文件；在这 8 条中，离线可见对象提取器只有 {s['extracted_any_correct']}/8 "
            f"至少找回一个正确对象、{s['extracted_full_recall']}/8 找齐全部对象。"
            f"{s['destination_after_document']}/8 在打开正确文件后到达目标应用，"
            f"最终只有 {s['typed_any_correct']}/9 把至少一个正确对象名写进目标应用，完整成功为 0/9。"
        ),
        "",
        "这条漏斗把‘记忆没有效果’进一步拆开：主要损失在源材料覆盖与对象集合完整性，随后还有目标应用到达、字段写入和保存闭环。记忆即使忠实保存了已经看到的内容，也不能补回没有翻到的记录；而保存了正确对象名，也不等于金额、描述、分类以及最终数据库状态全部正确。",
        "",
        "## 累积漏斗",
        "",
        "| 条件 | 轨迹数 | 含义 |",
        "|---|---:|---|",
        f"| 进入 Markor | {s['source_app_reached']}/9 | 源应用级到达 |",
        f"| 打开指定文件 | {s['correct_document_opened']}/9 | 页面与文件身份正确 |",
        f"| 从已观察画面至少提取一个正确对象 | {s['extracted_any_correct']}/9 | 局部对象捕获 |",
        f"| 从已观察画面找齐全部对象 | {s['extracted_full_recall']}/9 | 对象集合完整 |",
        f"| 打开文件后又到达目标应用 | {s['destination_after_document']}/9 | 跨应用交接 |",
        f"| 上述条件中同时有正确提取且到达目标 | {s['extracted_and_destination_after_document']}/9 | 具备可写入的最低前提 |",
        f"| 目标应用实际写入至少一个正确对象名 | {s['typed_any_correct']}/9 | 可执行动作中的正确值传递 |",
        f"| AndroidWorld 完整成功 | {s['full_successes']}/9 | 最终闭环 |",
        "",
        "## 首个失败位置",
        "",
        "| 首个失败位置 | 轨迹数 |",
        "|---|---:|",
    ]
    for key, label in [
        ("source_app_not_reached", "未进入源应用"),
        ("correct_document_not_opened", "未打开指定文件"),
        ("no_correct_object_extracted_from_observed_frames", "已打开文件但已观察画面未提取到正确对象"),
        ("destination_not_reached_after_source_capture", "提取到对象但未到目标应用"),
        ("correct_object_not_written_in_destination", "已到目标应用但未写入正确对象名"),
        ("some_correct_object_written_but_task_not_closed", "写入部分正确对象但未完成闭环"),
        ("full_success", "完整成功"),
    ]:
        lines.append(f"| {label} | {s['first_failure_counts'].get(key, 0)} |")
    lines.extend([
        "",
        "## 逐轨迹证据",
        "",
        "| 任务 | seed | 指定文件 | 正确提取数 | 到目标应用 | 正确写入数 | 首个失败位置 |",
        "|---|---:|---|---:|---|---:|---|",
    ])
    for ep in result["episodes"]:
        lines.append(
            f"| {ep['task_name']} | {ep['seed']} | {'是' if ep['correct_document_opened'] else '否'} | "
            f"{ep['extracted_correct_count']} | {'是' if ep['destination_reached'] else '否'} | "
            f"{ep['typed_correct_count']} | {ep['first_failure']} |"
        )
    lines.extend([
        "",
        "## 有效性边界",
        "",
        "这是同一批开发轨迹的事后确定性审计，不是随机对照或 held-out 实验。‘打开指定文件’以 Markor `DocumentActivity` 为判据，并依赖 AndroidWorld 该任务初始化时写入指定文件名这一固定夹具；它比仅进入 Markor 更强，但不证明 Agent 浏览了全文。‘提取到正确对象’来自已经冻结、且资格门失败的离线提取器结果；它只能说明现有截图中可恢复的信息，不能证明在线 Agent 当时已经把这些值稳定保存。‘正确写入’只匹配目标应用中的 `type_text` 文本，不证明其余字段、保存动作或数据库状态正确。",
        "",
        "## 可复现性",
        "",
        f"- 官方汇总输入 SHA-256：`{result['inputs']['official_combined_sha256']}`",
        f"- 提取器汇总输入 SHA-256：`{result['inputs']['extractor_aggregate_sha256']}`",
        f"- 对象转移审计输入 SHA-256：`{result['inputs']['transfer_audit_sha256']}`",
        "- 脚本：`05_project/scripts/audit_markor_source_funnel.py`。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-combined", required=True, type=Path)
    parser.add_argument("--extractor-aggregate", required=True, type=Path)
    parser.add_argument("--transfer-audit", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--md-output", required=True, type=Path)
    args = parser.parse_args()

    official = load_json(args.official_combined)
    extractor = load_json(args.extractor_aggregate)
    transfer = load_json(args.transfer_audit)
    extractor_by_episode = {row["episode_id"]: row for row in extractor["episode_results"]}
    transfer_by_episode = {row["episode_id"]: row for row in transfer["episodes"]}
    selected = [row for row in official["episodes"] if row["task_name"] in TASKS]
    episodes = [audit_episode(row, extractor_by_episode, transfer_by_episode) for row in selected]

    first_failure_counts: dict[str, int] = {}
    for ep in episodes:
        key = ep["first_failure"]
        first_failure_counts[key] = first_failure_counts.get(key, 0) + 1
    summary = {
        "episode_count": len(episodes),
        "source_app_reached": sum(ep["source_app_reached"] for ep in episodes),
        "correct_document_opened": sum(ep["correct_document_opened"] for ep in episodes),
        "extracted_any_correct": sum(ep["extracted_any_correct"] for ep in episodes),
        "extracted_full_recall": sum(ep["extracted_full_recall"] for ep in episodes),
        "destination_after_document": sum(
            ep["correct_document_opened"] and ep["destination_reached"] for ep in episodes
        ),
        "extracted_and_destination_after_document": sum(
            ep["correct_document_opened"] and ep["extracted_any_correct"] and ep["destination_reached"]
            for ep in episodes
        ),
        "typed_any_correct": sum(ep["typed_any_correct"] for ep in episodes),
        "full_successes": sum(ep["success"] for ep in episodes),
        "first_failure_counts": first_failure_counts,
    }
    result = {
        "audit_type": "deterministic_zero_generation_posthoc_markor_source_funnel",
        "inputs": {
            "official_combined": str(args.official_combined.resolve()),
            "official_combined_sha256": sha256(args.official_combined),
            "extractor_aggregate": str(args.extractor_aggregate.resolve()),
            "extractor_aggregate_sha256": sha256(args.extractor_aggregate),
            "transfer_audit": str(args.transfer_audit.resolve()),
            "transfer_audit_sha256": sha256(args.transfer_audit),
        },
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
