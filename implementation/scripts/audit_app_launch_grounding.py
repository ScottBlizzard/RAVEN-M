#!/usr/bin/env python3
"""Audit the first intended-app entry in the frozen official Qwen Hard suite.

This is a deterministic, zero-generation post-hoc audit.  It does not score task
completion and must not be interpreted as a new efficacy experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LAUNCHER_PACKAGES = {
    "com.google.android.apps.nexuslauncher",
    "com.android.systemui",
}

# The expected first task-relevant app follows the explicit task wording.  Source
# apps (Files, Gallery, Markor, VLC) are intentionally accepted when the task says
# to read material there before operating on the destination app.
EXPECTED_FIRST_PACKAGES: dict[str, set[str]] = {
    "BrowserMultiply": {"com.google.android.documentsui"},
    "ExpenseAddMultipleFromGallery": {"com.simplemobiletools.gallery.pro"},
    "ExpenseAddMultipleFromMarkor": {"net.gsantner.markor"},
    "ExpenseDeleteMultiple2": {"com.arduia.expense"},
    "MarkorCreateNoteAndSms": {"net.gsantner.markor"},
    "MarkorMergeNotes": {"net.gsantner.markor"},
    "MarkorTranscribeVideo": {"org.videolan.vlc"},
    "OsmAndMarker": {"net.osmand"},
    "OsmAndTrack": {"net.osmand"},
    "RecipeAddMultipleRecipesFromImage": {"com.simplemobiletools.gallery.pro"},
    "RecipeAddMultipleRecipesFromMarkor": {"net.gsantner.markor"},
    "RecipeAddMultipleRecipesFromMarkor2": {"net.gsantner.markor"},
    "RecipeDeleteMultipleRecipesWithConstraint": {"com.flauschcode.broccoli"},
    "RetroSavePlaylist": {"code.name.monkey.retromusic"},
    "SaveCopyOfReceiptTaskEval": {"com.simplemobiletools.gallery.pro"},
    "SimpleCalendarAddOneEvent": {"com.simplemobiletools.calendar.pro"},
    "SportsTrackerActivitiesOnDate": {"de.dennisguse.opentracks"},
    "SportsTrackerTotalDistanceForCategoryOverInterval": {"de.dennisguse.opentracks"},
    "SportsTrackerTotalDurationForCategoryThisWeek": {"de.dennisguse.opentracks"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_steps(events_path: Path) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") == "step":
            steps.append(event)
    return steps


def after_package(step: dict[str, Any]) -> str | None:
    return (((step.get("after") or {}).get("foreground") or {}).get("package"))


def audit_episode(episode: dict[str, Any]) -> dict[str, Any]:
    task = episode["task_name"]
    if task not in EXPECTED_FIRST_PACKAGES:
        raise KeyError(f"No expected package mapping for task {task!r}")
    source_summary = Path(episode["source_summary"])
    events_path = source_summary.parent / "episodes" / episode["episode_id"] / "events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(events_path)
    steps = load_steps(events_path)
    expected = EXPECTED_FIRST_PACKAGES[task]

    first_nonlauncher = next(
        (
            step
            for step in steps
            if after_package(step) and after_package(step) not in LAUNCHER_PACKAGES
        ),
        None,
    )
    first_target = next((step for step in steps if after_package(step) in expected), None)

    first_package = after_package(first_nonlauncher) if first_nonlauncher else None
    first_nonlauncher_step = first_nonlauncher.get("step") if first_nonlauncher else None
    target_entry_step = first_target.get("step") if first_target else None

    if first_package in expected:
        category = "correct_first"
    elif first_target is not None:
        category = "wrong_then_recovered"
    else:
        category = "never_reached"

    if first_target is not None:
        actions_until_target_entry = int(target_entry_step) + 1
    else:
        actions_until_target_entry = None

    detour_actions = None
    if category == "wrong_then_recovered":
        detour_actions = int(target_entry_step) - int(first_nonlauncher_step)

    return {
        "episode_id": episode["episode_id"],
        "task_name": task,
        "seed": episode["seed"],
        "evaluator_reward": episode["evaluator_reward"],
        "success": bool(episode["success"]),
        "step_count": episode["step_count"],
        "expected_first_packages": sorted(expected),
        "first_nonlauncher_package": first_package,
        "first_nonlauncher_step": first_nonlauncher_step,
        "target_entry_step": target_entry_step,
        "actions_until_target_entry": actions_until_target_entry,
        "detour_actions": detour_actions,
        "category": category,
        "events_path": str(events_path),
        "events_sha256": sha256(events_path),
    }


def ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100.0 * numerator / denominator:.2f}%)"


def build_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Official Qwen Hard：首个任务相关应用进入审计",
        "",
        "## 结论",
        "",
        (
            f"在冻结的 57 条官方 Qwen3-VL-32B Hard 轨迹中，"
            f"{summary['correct_first']} 条第一次离开桌面后就进入正确的任务相关应用，"
            f"{summary['wrong_then_recovered']} 条先进入错误应用但随后恢复，"
            f"{summary['never_reached']} 条从未进入任务相关应用。"
        ),
        "",
        (
            "因此，应用入口定位确实是一个可测的早期失败层，但不是总体 0/低成功率的主因："
            f"正确首入组成功 {ratio(summary['correct_first_successes'], summary['correct_first'])}，"
            f"错误后恢复组成功 {ratio(summary['wrong_then_recovered_successes'], summary['wrong_then_recovered'])}，"
            f"未进入组成功 {ratio(summary['never_reached_successes'], summary['never_reached'])}。"
            "大量失败发生在 Agent 已经进入正确应用之后。"
        ),
        "",
        "## 冻结口径",
        "",
        "- 数据：`reports/official_qwen32b_full_hard_combined_corrected_final.json` 中的 57 条科学合格轨迹。",
        "- 首个任务相关应用：由任务文字显式要求的第一个源应用或目标应用决定；例如先从 Gallery/Markor/VLC 读取信息的任务，把该源应用视为正确入口。",
        "- `correct_first`：第一次进入的非 Launcher/SystemUI 包就是预期包。",
        "- `wrong_then_recovered`：先进入其他应用，后来才进入预期包。",
        "- `never_reached`：整条轨迹均未进入预期包。",
        "- 本审计不调用模型、不改变旧结果，也不重新判定任务成功。",
        "",
        "## 汇总",
        "",
        "| 类别 | 条数 | 成功 | 解释 |",
        "|---|---:|---:|---|",
        f"| 首次即正确 | {summary['correct_first']} | {summary['correct_first_successes']} | 应用入口不是该轨迹的首要瓶颈 |",
        f"| 点错后恢复 | {summary['wrong_then_recovered']} | {summary['wrong_then_recovered_successes']} | 视觉图标定位先失败，但控制器后来纠正 |",
        f"| 始终未进入 | {summary['never_reached']} | {summary['never_reached_successes']} | 启动层本身足以导致任务失败 |",
        "",
        "## 异常轨迹",
        "",
        "| 任务 | seed | 类别 | 首个错误包 | 进入正确包的 step | reward |",
        "|---|---:|---|---|---:|---:|",
    ]
    for episode in result["episodes"]:
        if episode["category"] == "correct_first":
            continue
        lines.append(
            "| {task_name} | {seed} | {category} | {first_nonlauncher_package} | {target} | {reward:g} |".format(
                **episode,
                target=(episode["target_entry_step"] if episode["target_entry_step"] is not None else "未进入"),
                reward=episode["evaluator_reward"],
            )
        )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "这是一项 post-hoc 机制审计，不是随机化干预。它能够回答“最早是否进入正确应用”，不能证明消除入口错误会提高多少最终成功率。尤其是点错后恢复组只有 6 条，而且其中成功的日历轨迹说明早期错误并非必然失败。后续分层实验应把‘进入正确应用’作为 L1/L2 的观察量，而不是把它误当作任务完成代理。",
            "",
            "更重要的是，两条始终未进入任务应用的轨迹都属于 `RecipeAddMultipleRecipesFromImage`，表现为在 Launcher 上重复上滑。这是明确的早期循环；而另外 55 条均最终进入了正确应用，说明后续研究应优先分析应用内控件定位、状态更新、跨应用副作用和完成验证。",
            "",
            "## 可复现性",
            "",
            f"- 输入 JSON SHA-256：`{result['input_sha256']}`",
            f"- 逐轨迹事件文件：{len(result['episodes'])} 个，每个 SHA-256 写入配套 JSON。",
            "- 生成脚本：`05_project/scripts/audit_app_launch_grounding.py`。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    episodes = [audit_episode(episode) for episode in source["episodes"]]
    categories = Counter(episode["category"] for episode in episodes)
    successes = defaultdict(int)
    for episode in episodes:
        successes[episode["category"]] += int(episode["success"])

    result = {
        "audit_type": "deterministic_zero_generation_posthoc",
        "input": str(args.input.resolve()),
        "input_sha256": sha256(args.input),
        "expected_first_packages": {
            task: sorted(packages) for task, packages in EXPECTED_FIRST_PACKAGES.items()
        },
        "summary": {
            "episode_count": len(episodes),
            "correct_first": categories["correct_first"],
            "wrong_then_recovered": categories["wrong_then_recovered"],
            "never_reached": categories["never_reached"],
            "correct_first_successes": successes["correct_first"],
            "wrong_then_recovered_successes": successes["wrong_then_recovered"],
            "never_reached_successes": successes["never_reached"],
        },
        "episodes": episodes,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_output.write_text(build_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
