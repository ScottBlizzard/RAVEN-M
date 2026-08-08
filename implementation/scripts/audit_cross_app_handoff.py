#!/usr/bin/env python3
"""Deterministically audit source-to-destination reach in cross-app Hard tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# Frozen from the explicit task wording.  Package presence is only an upper-bound
# observation of app reach; it does not prove the correct page or target object.
CROSS_APP_PACKAGES: dict[str, tuple[str, str]] = {
    "BrowserMultiply": ("com.google.android.documentsui", "com.android.chrome"),
    "ExpenseAddMultipleFromGallery": ("com.simplemobiletools.gallery.pro", "com.arduia.expense"),
    "ExpenseAddMultipleFromMarkor": ("net.gsantner.markor", "com.arduia.expense"),
    "MarkorCreateNoteAndSms": ("net.gsantner.markor", "com.simplemobiletools.smsmessenger"),
    "MarkorTranscribeVideo": ("org.videolan.vlc", "net.gsantner.markor"),
    "RecipeAddMultipleRecipesFromImage": ("com.simplemobiletools.gallery.pro", "com.flauschcode.broccoli"),
    "RecipeAddMultipleRecipesFromMarkor": ("net.gsantner.markor", "com.flauschcode.broccoli"),
    "RecipeAddMultipleRecipesFromMarkor2": ("net.gsantner.markor", "com.flauschcode.broccoli"),
    "SaveCopyOfReceiptTaskEval": ("com.simplemobiletools.gallery.pro", "com.google.android.documentsui"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_steps(events_path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            event = json.loads(line)
            if event.get("event") == "step":
                result.append(event)
    return result


def package(step: dict[str, Any]) -> str | None:
    return (((step.get("after") or {}).get("foreground") or {}).get("package"))


def first_step_with_package(steps: list[dict[str, Any]], expected: str) -> int | None:
    match = next((step for step in steps if package(step) == expected), None)
    return int(match["step"]) if match is not None else None


def audit_episode(episode: dict[str, Any]) -> dict[str, Any]:
    task = episode["task_name"]
    source_package, destination_package = CROSS_APP_PACKAGES[task]
    source_summary = Path(episode["source_summary"])
    events_path = source_summary.parent / "episodes" / episode["episode_id"] / "events.jsonl"
    steps = load_steps(events_path)
    source_step = first_step_with_package(steps, source_package)
    destination_step = first_step_with_package(steps, destination_package)

    if source_step is None:
        category = "source_not_reached"
    elif destination_step is None:
        category = "source_only"
    else:
        category = "destination_reached"

    return {
        "episode_id": episode["episode_id"],
        "task_name": task,
        "seed": episode["seed"],
        "evaluator_reward": episode["evaluator_reward"],
        "success": bool(episode["success"]),
        "positive_reward": float(episode["evaluator_reward"]) > 0.0,
        "source_package": source_package,
        "destination_package": destination_package,
        "source_entry_step": source_step,
        "destination_entry_step": destination_step,
        "handoff_action_span": (
            destination_step - source_step if source_step is not None and destination_step is not None else None
        ),
        "category": category,
        "events_path": str(events_path),
        "events_sha256": sha256(events_path),
    }


def fraction(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100.0 * numerator / denominator:.2f}%)"


def build_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Official Qwen Hard：跨应用交接漏斗审计",
        "",
        "## 核心结果",
        "",
        (
            "冻结的 57 条官方式 Hard 轨迹中，有 9 类、27 条任务明确要求先在一个源应用读取或选择信息，"
            "再到另一个目标应用完成操作。按 foreground package 做零调用回放后："
            f"{summary['source_not_reached']} 条没有进入源应用，"
            f"{summary['source_only']} 条进入源应用但没有到达目标应用，"
            f"{summary['destination_reached']} 条到达了目标应用。"
        ),
        "",
        (
            f"27 条中完整成功 {summary['full_successes']}/27；"
            f"到达目标应用的 {summary['destination_reached']} 条中，完整成功仍为 "
            f"{summary['destination_reached_full_successes']}，只有 "
            f"{summary['destination_reached_positive_rewards']} 条获得正奖励，且都是完成一半要求的 Markor--SMS 任务。"
            "因此跨应用到达是必要条件，但远不足以保证目标字段绑定和最终闭环。"
        ),
        "",
        "## 冻结定义",
        "",
        "- 任务集合只包含任务文字明确要求 source→destination 的 9 类任务，每类 3 个 seeds。",
        "- `source_not_reached`：轨迹未出现源应用 foreground package。",
        "- `source_only`：出现源应用，但未出现目标应用 foreground package。",
        "- `destination_reached`：源应用和目标应用都曾成为 foreground package。",
        "- package 出现只证明应用层到达，不证明进入正确页面、读取正确字段或写入正确对象。",
        "- 本审计不调用模型、不修改 reward，也不把 package reach 当作任务成功。",
        "",
        "## 漏斗",
        "",
        "| 阶段 | 条数 | 完整成功 | 正奖励 |",
        "|---|---:|---:|---:|",
        f"| 未进入源应用 | {summary['source_not_reached']} | {summary['source_not_reached_full_successes']} | {summary['source_not_reached_positive_rewards']} |",
        f"| 只到源应用 | {summary['source_only']} | {summary['source_only_full_successes']} | {summary['source_only_positive_rewards']} |",
        f"| 已到目标应用 | {summary['destination_reached']} | {summary['destination_reached_full_successes']} | {summary['destination_reached_positive_rewards']} |",
        "",
        "## 任务级结果",
        "",
        "| 任务 | 到达目标/3 | 正奖励/3 | 完整成功/3 |",
        "|---|---:|---:|---:|",
    ]
    for task in sorted(result["per_task"]):
        row = result["per_task"][task]
        lines.append(
            f"| {task} | {row.get('destination_reached', 0)}/3 | "
            f"{row.get('positive_rewards', 0)}/3 | {row.get('full_successes', 0)}/3 |"
        )
    lines.extend(
        [
            "",
            "## 机制解释",
            "",
            "第一道漏斗发生在跨应用导航：11/27 没有抵达目标应用，其中2条连源应用也未进入。第二道漏斗发生在目标应用内部：16条已经抵达目标应用，但14条仍为0奖励，另外2条只完成短信发送而没有同时满足 Markor 笔记要求。也就是说，增加更长记忆既不能自动打开目标应用，也不能自动保证记住的值被写到正确对象。",
            "",
            "这个结果与结构化记忆方向的关系不是‘记录正确就会成功’，而是把问题拆成三个分别可测的条件：来源值是否捕获、目标应用/对象是否保持、值是否真正写入并由 evaluator 闭环。本审计只测到中间的应用级 reach；页面角色、字段身份和写入事实仍需要下一层证据。",
            "",
            "## 有效性边界",
            "",
            "这是 post-hoc 观察，不是把同一任务随机分配到‘成功交接’和‘失败交接’的因果实验。foreground package 还可能高估真正到达：Agent 可以打开正确 App 却停在错误页面。因此 16/27 应理解为应用级上界，而不是跨应用信息传递成功率。",
            "",
            "## 可复现性",
            "",
            f"- 输入 JSON SHA-256：`{result['input_sha256']}`",
            "- 每条轨迹的 source/destination package、首次到达 step、事件路径和事件 SHA-256 均写入配套 JSON。",
            "- 生成脚本：`05_project/scripts/audit_cross_app_handoff.py`。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--md-output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    selected = [episode for episode in source["episodes"] if episode["task_name"] in CROSS_APP_PACKAGES]
    episodes = [audit_episode(episode) for episode in selected]
    counts = Counter(episode["category"] for episode in episodes)

    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    by_task: dict[str, Counter[str]] = defaultdict(Counter)
    for episode in episodes:
        category = episode["category"]
        by_category[category]["full_successes"] += int(episode["success"])
        by_category[category]["positive_rewards"] += int(episode["positive_reward"])
        by_task[episode["task_name"]][category] += 1
        by_task[episode["task_name"]]["full_successes"] += int(episode["success"])
        by_task[episode["task_name"]]["positive_rewards"] += int(episode["positive_reward"])

    result = {
        "audit_type": "deterministic_zero_generation_posthoc",
        "input": str(args.input.resolve()),
        "input_sha256": sha256(args.input),
        "cross_app_packages": {
            task: {"source": pair[0], "destination": pair[1]}
            for task, pair in CROSS_APP_PACKAGES.items()
        },
        "summary": {
            "episode_count": len(episodes),
            "task_class_count": len(CROSS_APP_PACKAGES),
            "source_not_reached": counts["source_not_reached"],
            "source_only": counts["source_only"],
            "destination_reached": counts["destination_reached"],
            "full_successes": sum(int(episode["success"]) for episode in episodes),
            "positive_rewards": sum(int(episode["positive_reward"]) for episode in episodes),
            "source_not_reached_full_successes": by_category["source_not_reached"]["full_successes"],
            "source_not_reached_positive_rewards": by_category["source_not_reached"]["positive_rewards"],
            "source_only_full_successes": by_category["source_only"]["full_successes"],
            "source_only_positive_rewards": by_category["source_only"]["positive_rewards"],
            "destination_reached_full_successes": by_category["destination_reached"]["full_successes"],
            "destination_reached_positive_rewards": by_category["destination_reached"]["positive_rewards"],
        },
        "per_task": {task: dict(counter) for task, counter in sorted(by_task.items())},
        "episodes": episodes,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_output.write_text(build_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
