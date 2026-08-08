#!/usr/bin/env python3
"""Audit expected object identifiers that are typed in destination apps.

Ground-truth object identifiers are read only during post-hoc analysis from the
AndroidWorld task parameters.  They were not exposed to the model at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TASKS: dict[str, dict[str, str]] = {
    "ExpenseAddMultipleFromGallery": {"destination": "com.arduia.expense", "identifier": "name"},
    "ExpenseAddMultipleFromMarkor": {"destination": "com.arduia.expense", "identifier": "name"},
    "RecipeAddMultipleRecipesFromImage": {"destination": "com.flauschcode.broccoli", "identifier": "title"},
    "RecipeAddMultipleRecipesFromMarkor": {"destination": "com.flauschcode.broccoli", "identifier": "title"},
    "RecipeAddMultipleRecipesFromMarkor2": {"destination": "com.flauschcode.broccoli", "identifier": "title"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def load_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def foreground(step: dict[str, Any], when: str) -> str | None:
    return (((step.get(when) or {}).get("foreground") or {}).get("package"))


def audit_episode(episode: dict[str, Any]) -> dict[str, Any]:
    task = episode["task_name"]
    config = TASKS[task]
    source_summary = Path(episode["source_summary"])
    events_path = source_summary.parent / "episodes" / episode["episode_id"] / "events.jsonl"
    events = load_events(events_path)
    start = next(event for event in events if event.get("event") == "episode_start")
    steps = [event for event in events if event.get("event") == "step"]
    destination = config["destination"]

    row_objects = list((start.get("task_params") or {}).get("row_objects") or [])
    expected = [str(row[config["identifier"]]) for row in row_objects]
    destination_steps = [
        step
        for step in steps
        if foreground(step, "before") == destination or foreground(step, "after") == destination
    ]
    type_actions = [
        step
        for step in destination_steps
        if ((step.get("decision") or {}).get("canonical_action") or {}).get("type") == "type_text"
    ]
    typed_texts = [
        str(((step.get("decision") or {}).get("canonical_action") or {}).get("text") or "")
        for step in type_actions
    ]
    normalized_typed = [normalize(text) for text in typed_texts]
    matched = [
        identifier
        for identifier in expected
        if any(normalize(identifier) in text for text in normalized_typed)
    ]

    destination_reached = any(foreground(step, "after") == destination for step in steps)
    if not destination_reached:
        stage = "destination_not_reached"
    elif not type_actions:
        stage = "destination_reached_no_text_write"
    elif not matched:
        stage = "destination_text_wrong_set"
    else:
        stage = "destination_some_correct_identifier"

    return {
        "episode_id": episode["episode_id"],
        "task_name": task,
        "seed": episode["seed"],
        "evaluator_reward": episode["evaluator_reward"],
        "success": bool(episode["success"]),
        "destination_package": destination,
        "destination_reached": destination_reached,
        "expected_identifiers": expected,
        "typed_texts_in_destination": typed_texts,
        "matched_expected_identifiers": matched,
        "expected_identifier_count": len(expected),
        "matched_identifier_count": len(matched),
        "stage": stage,
        "events_path": str(events_path),
        "events_sha256": sha256(events_path),
    }


def pct(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100.0 * numerator / denominator:.2f}%)"


def build_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Official Qwen Hard：预期对象标识符跨应用落地审计",
        "",
        "## 结论",
        "",
        (
            "5 类多对象新增任务、15 条轨迹的 AndroidWorld 隐藏参数共包含 "
            f"{summary['expected_identifier_count']} 个应创建对象。"
            f"其中 {summary['destination_reached_episodes']}/15 条轨迹到达目标应用，"
            f"对应 {summary['destination_reached_expected_identifiers']} 个应创建对象；"
            f"实际 type_text 命令中只出现 {summary['matched_identifier_count']} 个规范化后匹配的正确对象标识符，"
            f"覆盖率为 {pct(summary['matched_identifier_count'], summary['destination_reached_expected_identifiers'])}。"
        ),
        "",
        (
            f"只有 {summary['episodes_with_any_match']} 条轨迹输入过至少一个正确对象名；"
            f"{summary['wrong_set_episodes']} 条虽然在目标应用开始输入，却没有输入任何属于该 seed 的预期对象名；"
            f"{summary['no_text_write_episodes']} 条到达目标应用但没有执行目标内文本写入。"
            "这说明对象集合在来源感知、筛选或跨页面保持阶段已经大量失真。"
        ),
        "",
        "## 冻结口径",
        "",
        "- 任务：两类 Expense 新增任务与三类 Recipe 新增任务，每类 3 个 seeds。",
        "- Ground truth：`episode_start.task_params.row_objects` 中的 expense `name` 或 recipe `title`；这些隐藏参数仅用于事后审计，运行时没有提供给模型。",
        "- 观察：目标应用前台状态下实际执行的 `type_text` 文本。",
        "- 匹配：Unicode NFKC、忽略大小写和标点后的标识符子串匹配；例如两种引号写法不构成差异。",
        "- 本审计只检查对象标识符是否进入动作流，不检查金额、日期、描述、方向、保存动作或数据库最终状态。",
        "",
        "## 逐层漏斗",
        "",
        "| 阶段 | 轨迹数 | 完整成功 |",
        "|---|---:|---:|",
        f"| 未到目标应用 | {summary['destination_not_reached_episodes']} | 0 |",
        f"| 到达但未执行文本写入 | {summary['no_text_write_episodes']} | 0 |",
        f"| 已写入，但对象集合全错 | {summary['wrong_set_episodes']} | 0 |",
        f"| 至少写入一个正确对象名 | {summary['episodes_with_any_match']} | 0 |",
        "",
        "## 出现过的正确标识符",
        "",
        "| 任务 | seed | 正确标识符 | 目标应用中的全部输入 |",
        "|---|---:|---|---|",
    ]
    for episode in result["episodes"]:
        if not episode["matched_expected_identifiers"]:
            continue
        lines.append(
            f"| {episode['task_name']} | {episode['seed']} | "
            f"{'；'.join(episode['matched_expected_identifiers'])} | "
            f"{'；'.join(episode['typed_texts_in_destination'])} |"
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "这个结果否定了一个容易混淆的说法：这批任务并不是普遍已经‘把正确内容记住，只是最后没保存’。至少从可执行动作看，多数轨迹没有把正确对象标识符带到目标应用；有些轨迹甚至输入了与该 seed ground truth 完全无关的对象。结构化记忆若要发挥作用，首先必须提高来源对象的可核验捕获和全量覆盖，随后才有资格讨论目标绑定与保存闭环。",
            "",
            "另一方面，3个正确标识符仍未带来任何完整成功，也说明 object-name transfer 只是必要子条件。两条有匹配的轨迹都只覆盖了部分对象，而且金额、描述、方向、字段和保存状态没有同时闭合。后续应以 object-level recall、field-level exactness、saved-object count 和 evaluator reward 四级指标报告，而不是只问 memory 里有没有一段看似正确的自然语言。",
            "",
            "## 有效性边界",
            "",
            "这是对实际 `type_text` 动作的严格、可复现下界。它可能漏掉通过非文本控件选择、预填字段或其他输入通道设置的标识符；但这批创建任务的名称/标题通常需要文本输入。标识符匹配也不能证明对应金额、描述等字段正确，更不能替代原生 evaluator。",
            "",
            "## 可复现性",
            "",
            f"- 输入 JSON SHA-256：`{result['input_sha256']}`",
            "- 逐轨迹 expected identifiers、目标内 type_text、规范化匹配、事件路径与事件 SHA-256 均写入配套 JSON。",
            "- 生成脚本：`05_project/scripts/audit_expected_object_transfer.py`。",
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
    episodes = [
        audit_episode(episode)
        for episode in source["episodes"]
        if episode["task_name"] in TASKS
    ]
    stages = Counter(episode["stage"] for episode in episodes)
    destination_episodes = [episode for episode in episodes if episode["destination_reached"]]
    result = {
        "audit_type": "deterministic_zero_generation_posthoc_hidden_ground_truth",
        "input": str(args.input.resolve()),
        "input_sha256": sha256(args.input),
        "task_configuration": TASKS,
        "summary": {
            "episode_count": len(episodes),
            "task_class_count": len(TASKS),
            "expected_identifier_count": sum(episode["expected_identifier_count"] for episode in episodes),
            "destination_reached_episodes": len(destination_episodes),
            "destination_reached_expected_identifiers": sum(
                episode["expected_identifier_count"] for episode in destination_episodes
            ),
            "matched_identifier_count": sum(episode["matched_identifier_count"] for episode in episodes),
            "destination_not_reached_episodes": stages["destination_not_reached"],
            "no_text_write_episodes": stages["destination_reached_no_text_write"],
            "wrong_set_episodes": stages["destination_text_wrong_set"],
            "episodes_with_any_match": stages["destination_some_correct_identifier"],
            "full_successes": sum(int(episode["success"]) for episode in episodes),
        },
        "episodes": episodes,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_output.write_text(build_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
