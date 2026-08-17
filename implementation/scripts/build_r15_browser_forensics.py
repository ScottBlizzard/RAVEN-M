from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCES = {
    "A1": "runs/a1_working_memory/official_qwen_20260810T122419_26573d7c/episodes/BrowserMultiply_20260806_579e82bd/episode.json",
    "A2": "runs/a2_verified_progress_memory/official_qwen_20260810T194249_54a44c76/episodes/BrowserMultiply_20260806_3575bd66/episode.json",
    "A6": "runs/a678_memory/official_qwen_20260811T035710_4b246fd9/episodes/BrowserMultiply_20260806_a29e4eb9/episode.json",
    "A7": "runs/a678_memory/official_qwen_20260811T094144_c61c8a37/episodes/BrowserMultiply_20260806_21614338/episode.json",
    "A1-R2": "runs/a1r2_cvp/official_qwen_20260814T145307_50081981/episodes/BrowserMultiply_20260806_54623170/episode.json",
    "SYS-NAG-V4": "runs/sys_nag_v4/official_qwen_20260816T041833_e5618ea5/episodes/BrowserMultiply_20260806_639ed27d/episode.json",
    "A1-R13D": "runs/a1r13d_evr/official_qwen_20260818T041551_0817d5eb/episodes/BrowserMultiply_20260806_497dd841/episode.json",
    "A1-R14": "runs/a1r14_rgvr/official_qwen_20260818T045139_bad7844b/episodes/BrowserMultiply_20260806_88e8e919/episode.json",
    "A1-R15": "runs/a1r15_eovr/official_qwen_20260818T053157_cab07201/episodes/BrowserMultiply_20260806_afd4acbc/episode.json",
}

A0_SUMMARY = "evidence/baseline/official_qwen32b_full_hard_combined_corrected_final.json"
A0_NOTES = "evidence/baseline/official_qwen32b_full_hard_case_notes_2026-08-08.md"
R15_REPLAY = "evidence/a1r15/A1R15_EOVR_OFFLINE_REPLAY_REPORT.json"
NUMBER_VALUES = ("1", "8", "10", "7", "2")
R2_SUCCESSES = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(root: Path, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def visible_strings(path: Path) -> list[str]:
    if not path.exists():
        return []
    nodes = json.loads(path.read_text(encoding="utf-8"))
    result: list[str] = []
    for node in nodes if isinstance(nodes, list) else []:
        if not node.get("is_visible", True):
            continue
        for key in ("text", "content_description", "hint_text", "tooltip"):
            value = node.get(key)
            if isinstance(value, str):
                value = value.strip()
                if value and value not in result:
                    result.append(value)
    return result


def action_family(action: Any) -> str | None:
    if not isinstance(action, dict):
        return None
    kind = action.get("type")
    if kind == "tap":
        return "tap:%d:%d" % (
            int(float(action.get("x", 0)) * 20 + 0.5),
            int(float(action.get("y", 0)) * 20 + 0.5),
        )
    if kind == "swipe":
        return "swipe:%s" % json.dumps(action, sort_keys=True, separators=(",", ":"))
    if kind == "type_text":
        return "type_text"
    if kind == "wait":
        return "wait"
    return str(kind) if kind else None


def memory_injected_text(user_prompt: str) -> str:
    marker = "Memory context (controller-authored, use only if consistent with the current screenshot):"
    if marker not in user_prompt:
        return ""
    return user_prompt.split(marker, 1)[1].strip()


def step_record(root: Path, episode_dir: Path, step: dict[str, Any]) -> dict[str, Any]:
    ordinal = int(step["step"])
    before_ui = episode_dir / f"step_{ordinal:03d}_before.ui.json"
    after_ui = episode_dir / f"step_{ordinal:03d}_after.ui.json"
    before_png = episode_dir / f"step_{ordinal:03d}_before.png"
    after_png = episode_dir / f"step_{ordinal:03d}_after.png"
    model_call = step.get("model_call") or {}
    decision = step.get("decision") or {}
    user_prompt = step.get("user_prompt") or ""
    memory_read = step.get("memory_read") or {}
    before_text = visible_strings(before_ui)
    after_text = visible_strings(after_ui)
    return {
        "step": ordinal,
        "executed": bool(step.get("executed")),
        "before_screenshot": file_record(root, before_png) if before_png.exists() else None,
        "after_screenshot": file_record(root, after_png) if after_png.exists() else None,
        "before_ui": file_record(root, before_ui) if before_ui.exists() else None,
        "after_ui": file_record(root, after_ui) if after_ui.exists() else None,
        "before_visible_strings": before_text,
        "after_visible_strings": after_text,
        "foreground_before": (step.get("before") or {}).get("foreground"),
        "foreground_after": (step.get("after") or {}).get("foreground"),
        "user_prompt": user_prompt,
        "user_prompt_sha256": sha256_bytes(user_prompt.encode("utf-8")),
        "injected_memory_text": memory_injected_text(user_prompt),
        "memory_read": memory_read,
        "memory_write": step.get("memory_write"),
        "memory_response_write": step.get("memory_response_write"),
        "model_response": model_call.get("content"),
        "model_prompt_sha256": model_call.get("prompt_sha256"),
        "request_sha256": model_call.get("request_sha256"),
        "response_sha256": model_call.get("response_sha256"),
        "usage": model_call.get("usage"),
        "thought": decision.get("thought"),
        "action_summary": decision.get("action_summary"),
        "proposed_action": decision.get("canonical_action"),
        "proposed_action_family": action_family(decision.get("canonical_action")),
        "actual_action": ((step.get("mapped_action") or {}).get("canonical")),
        "actual_action_family": action_family(
            (step.get("mapped_action") or {}).get("canonical")
        ),
        "terminal_status": decision.get("terminal_status"),
        "history_before": step.get("history_before"),
        "history_after": step.get("history_after"),
        "transition": step.get("transition"),
    }


def load_episode(root: Path, name: str, relpath: str) -> dict[str, Any]:
    path = root / relpath
    episode = json.loads(path.read_text(encoding="utf-8"))
    episode_dir = path.parent
    steps = [step_record(root, episode_dir, step) for step in episode.get("steps", [])]
    typed = [
        {
            "step": row["step"],
            "text": (row["proposed_action"] or {}).get("text"),
        }
        for row in steps
        if isinstance(row["proposed_action"], dict)
        and row["proposed_action"].get("type") == "type_text"
    ]
    return {
        "arm": name,
        "availability": "RAW_EPISODE_AVAILABLE",
        "episode_file": file_record(root, path),
        "events_file": file_record(root, episode_dir / "events.jsonl")
        if (episode_dir / "events.jsonl").exists()
        else None,
        "episode_id": episode.get("episode_id"),
        "task_name": episode.get("task_name"),
        "reward": episode.get("evaluator_reward"),
        "success": episode.get("success"),
        "termination_reason": episode.get("termination_reason"),
        "model_claimed_status": episode.get("model_claimed_status"),
        "model_call_count": episode.get("model_call_count"),
        "executed_action_count": episode.get("executed_action_count"),
        "mechanism_id": (episode.get("memory_mechanism") or {}).get("mechanism_id"),
        "memory_summary": episode.get("memory_mechanism"),
        "typed_text_actions": typed,
        "steps": steps,
    }


def first_difference(a: list[dict[str, Any]], b: list[dict[str, Any]], key: str) -> int | None:
    for index, (left, right) in enumerate(zip(a, b)):
        if left.get(key) != right.get(key):
            return index
    return min(len(a), len(b)) if len(a) != len(b) else None


def number_timeline(r15: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for value in NUMBER_VALUES:
        ui_steps = []
        thought_steps = []
        action_steps = []
        evr_steps = []
        for row in r15["steps"]:
            if value in row["before_visible_strings"]:
                ui_steps.append(row["step"])
            thought = row.get("thought") or ""
            if value in thought.replace(",", " ").split():
                thought_steps.append(row["step"])
            summary = row.get("action_summary") or ""
            if value in summary.replace(",", " ").split():
                action_steps.append(row["step"])
            register = (row.get("memory_read") or {}).get("evidence_value_register") or {}
            if value in [str(v) for v in register.get("values", [])]:
                evr_steps.append(row["step"])
        result.append(
            {
                "value": int(value),
                "visible_before_steps": ui_steps,
                "model_thought_steps": thought_steps,
                "model_action_summary_steps": action_steps,
                "evr_read_steps": evr_steps,
            }
        )
    return result


def build(root: Path) -> dict[str, Any]:
    arms = {name: load_episode(root, name, path) for name, path in SOURCES.items()}
    r15 = arms["A1-R15"]
    comparisons = []
    for name, arm in arms.items():
        if name == "A1-R15":
            continue
        comparisons.append(
            {
                "arm": name,
                "first_before_screenshot_difference_step": first_difference(
                    arm["steps"], r15["steps"], "before_screenshot"
                ),
                "first_user_prompt_difference_step": first_difference(
                    arm["steps"], r15["steps"], "user_prompt_sha256"
                ),
                "first_response_difference_step": first_difference(
                    arm["steps"], r15["steps"], "response_sha256"
                ),
                "first_action_difference_step": first_difference(
                    arm["steps"], r15["steps"], "proposed_action"
                ),
                "typed_text_actions": arm["typed_text_actions"],
                "reward": arm["reward"],
                "exact_prefix_pairing_available": False,
                "pairing_reason": "Initial screenshot bytes differ, so no arm has an exact request-prefix counterfactual against R15.",
            }
        )

    replay_path = root / R15_REPLAY
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    protection = [
        row
        for row in replay["episodes"]
        if row["task_name"] in R2_SUCCESSES
    ]
    a0_summary_path = root / A0_SUMMARY
    a0_notes_path = root / A0_NOTES
    a0_summary = json.loads(a0_summary_path.read_text(encoding="utf-8"))
    a0_rows = [
        row
        for row in a0_summary.get("episodes", [])
        if row.get("task_name") == "BrowserMultiply"
        and row.get("seed") == 20260806
    ]

    payload: dict[str, Any] = {
        "schema": "r15_browser_forensic_report_v1",
        "analysis_type": "CPU_ONLY_ZERO_GENERATION_POST_HOC_FORENSIC",
        "generation_calls": 0,
        "source_commit": "152f3b92f6ad1d87f20fa0e6a54101a0d2c07711",
        "task_name": "BrowserMultiply",
        "task_seed": 20260806,
        "generation_seed": 3407,
        "formal_r15_classification": "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED",
        "a0": {
            "availability": "SUMMARY_ONLY_RAW_EPISODE_MISSING",
            "summary_file": file_record(root, a0_summary_path),
            "notes_file": file_record(root, a0_notes_path),
            "matching_summary_rows": a0_rows,
            "comparison_limit": "No raw A0 BrowserMultiply episode is present locally; step-aligned comparison is not fabricated.",
        },
        "arms": arms,
        "r15_number_timeline": number_timeline(r15),
        "r15_product": {
            "factors": [1, 8, 10, 7, 2],
            "correct_product": 1120,
            "type_text_actions": r15["typed_text_actions"],
            "submit_step": 19,
            "success_visible_step": 20,
        },
        "comparisons_to_r15": comparisons,
        "r2_six_success_protection_replay": {
            "source": file_record(root, replay_path),
            "rows": protection,
            "active_count": sum(1 for row in protection if row["activation_count"]),
            "render_count": sum(row["render_count"] for row in protection),
            "base_r2_rendered_read_count": sum(
                len(row["rendered_reads"])
                if isinstance(row["rendered_reads"], list)
                else int(row["rendered_reads"])
                for row in protection
            ),
        },
        "causal_candidates": [
            {
                "candidate": "EVR rendered values caused the correct product",
                "classification": "CONTRADICTED",
                "evidence": "R15 EVR render_count=0 and rendered_reads=0; no EVR text entered any model request.",
            },
            {
                "candidate": "Ordinary model-authored action history retained enough values for the model to reason correctly",
                "classification": "DIRECTLY_EVIDENCED",
                "evidence": "R15 thought/action prose enumerates the growing value sequence and the final five values before computing 1120.",
            },
            {
                "candidate": "A reusable memory intervention unique to R15 explains the win",
                "classification": "CONTRADICTED",
                "evidence": "The only R15-specific EVR treatment was never rendered/read; R15 diverged from failed runs before any EVR value was retained.",
            },
            {
                "candidate": "The remaining bottleneck is arithmetic/outcome reasoning rather than value availability",
                "classification": "PLAUSIBLE",
                "evidence": "R2, R13D, and R14 reached the same five-value UI sequence but typed 120, 720, and 2310; R15 typed 1120.",
            },
            {
                "candidate": "The R15 success is a stable deterministic consequence of its identity",
                "classification": "UNKNOWN",
                "evidence": "No exact-prefix counterfactual exists; initial screenshot bytes differ and the identity cannot be rerun.",
            },
        ],
        "go_no_go": {
            "decision": "NO_GO_R15_DERIVED_LIVE_CANDIDATE",
            "reason": "No task-agnostic R15-specific primitive is both causally supported and distinct from the frozen R2 path. Packaging the silent EVR or the observed arithmetic answer would be post-hoc task specialization.",
            "prohibited_followups": [
                "Do not rerun R15.",
                "Do not create R16/R17 by adding Browser expression regexes.",
                "Do not stitch the R15 Browser win onto R2 as 7/19.",
                "Do not attribute the success to EVR.",
            ],
            "next_action": "Proceed to the independently frozen Pro failure-recovery design direction.",
        },
    }
    payload["content_sha256"] = sha256_bytes(canonical_bytes(payload))
    return payload


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# A1-R15 BrowserMultiply 法证与第七题候选裁决（2026-08-18）",
        "",
        "## 结论",
        "",
        "**NO-GO：不建立 R15-derived live 候选。** R15 的 BrowserMultiply 是一条真实、形式可审计的成功轨迹，但 EVR `render_count=0`、`rendered_reads=0`。成功只能标为 `TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED`。",
        "",
        "R15 在普通模型 Thought/Action 历史中逐步保留了 `1, 8, 10, 7, 2`，计算并输入 `1120`；R2、R13D、R14 到达同一数字序列后分别输入 `120`、`720`、`2310`。现有证据支持“本次模型自身历史推理/算术走对了”，不支持“EVR 造成成功”。",
        "",
        "## 证据边界",
        "",
        f"- 冻结源提交：`{payload['source_commit']}`。",
        "- 本报告只读取既有 artifact，`generation_calls=0`。",
        "- A0 本地只有汇总/案例笔记，没有 raw Browser episode；因此明确标记 summary-only，不伪造逐步对照。",
        "- A1、A2、A6、A7、R2、SYS-NAG V4、R13D、R14、R15 均绑定 raw episode、events、截图和 UI artifact SHA-256。",
        "- 所有对照的初始截图字节均与 R15 不同，不能声称 exact-prefix causal counterfactual。",
        "",
        "## R15 数值链",
        "",
        "| 值 | 首次 UI 可见 step | Thought 提及 steps | EVR read steps |",
        "|---:|---:|---|---|",
    ]
    for row in payload["r15_number_timeline"]:
        lines.append(
            f"| {row['value']} | {row['visible_before_steps'][0] if row['visible_before_steps'] else '—'} | {row['model_thought_steps']} | {row['evr_read_steps'] or '[]'} |"
        )
    lines.extend(
        [
            "",
            "- step 17：模型在 Thought 中完整列出 `1, 8, 10, 7, 2` 并计算 `1120`。",
            "- step 18：实际 `type_text(1120)`。",
            "- step 19：点击 Submit。",
            "- step 20：当前截图/UI 出现 `Success!`，随后模型终止 success。",
            "",
            "## 逐臂结果与首个差异",
            "",
            "| Arm | reward | calls | typed text | 首图差异 | 首响应差异 | 首动作差异 |",
            "|---|---:|---:|---|---:|---:|---:|",
        ]
    )
    by_name = {row["arm"]: row for row in payload["comparisons_to_r15"]}
    for name, arm in payload["arms"].items():
        if name == "A1-R15":
            continue
        comparison = by_name[name]
        typed = [row["text"] for row in arm["typed_text_actions"]]
        lines.append(
            f"| {name} | {arm['reward']} | {arm['model_call_count']} | `{typed}` | {comparison['first_before_screenshot_difference_step']} | {comparison['first_response_difference_step']} | {comparison['first_action_difference_step']} |"
        )
    lines.extend(
        [
            "| A1-R15 | 1.0 | 21 | `[1120]` | — | — | — |",
            "",
            "关键语义对照：R2、R13D、R14 和 R15 都看到相同的五值 UI 序列；其决定性差异发生在计算/输入答案，而不是 EVR 注入。R15 与 R14 从 step 0 起因截图字节差异产生不同响应，且在 EVR 留存任何值之前轨迹已经分叉。",
            "",
            "## R2 六个成功题回归风险",
            "",
            "R15 冻结的 19 题零生成 replay 中，R2 六个成功题 EVR activation/render/read 均为 0。这个结果只说明历史轨迹静默，不证明一个扩大后的 Browser parser 在 prospective live 中安全。把单条 live 表达继续扩成 R16/R17 会把已观察答案形态编码进机制，并破坏因果边界。",
            "",
            "## 因果候选裁决",
            "",
            "| 候选解释 | 分类 | 依据 |",
            "|---|---|---|",
        ]
    )
    for row in payload["causal_candidates"]:
        lines.append(
            f"| {row['candidate']} | **{row['classification']}** | {row['evidence']} |"
        )
    lines.extend(
        [
            "",
            "## GO/NO-GO",
            "",
            "裁决：`NO_GO_R15_DERIVED_LIVE_CANDIDATE`。没有证据支持一个 R15 独有、任务无关、可复用且不会明显危及 R2 六个成功题的机制。强行把 EVR、数字序列或 1120 包装成候选只会形成 Browser 特例。",
            "",
            "因此第一阶段不烧 GPU；直接进入独立的 failure-recovery Pro 方向。R15 不重跑，不做 R16/R17 parser 正则补丁，不与 R2 拼成 7/19。",
            "",
            "## Machine-readable companion",
            "",
            "完整逐 step 的 prompt、memory read/write、model response、Thought/Action、实际动作、visible UI strings、截图/UI/events 文件哈希位于 `R15_BROWSER_FORENSIC_2026-08-18.json`。",
            "",
            f"JSON canonical content SHA-256：`{payload['content_sha256']}`。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/r15_browser_forensics"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = (root / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    payload = build(root)
    json_path = output / "R15_BROWSER_FORENSIC_2026-08-18.json"
    md_path = output / "R15_BROWSER_FORENSIC_2026-08-18.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(markdown(payload), encoding="utf-8", newline="\n")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "content_sha256": payload["content_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
