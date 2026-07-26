"""Fail-closed task/action capability audit for protocol v2."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ACTION_TYPES = {
    "tap",
    "long_press",
    "swipe",
    "type_text",
    "press_back",
    "press_home",
    "press_enter",
    "open_app",
    "answer",
    "wait",
}


def _action_types(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        type_rule = value.get("type")
        if isinstance(type_rule, dict):
            constant = type_rule.get("const")
            if constant in ACTION_TYPES:
                found.add(constant)
            for item in type_rule.get("enum", []):
                if item in ACTION_TYPES:
                    found.add(item)
        for child in value.values():
            found.update(_action_types(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_action_types(child))
    return found


def audit(
    root: Path,
    *,
    matrix_path: Path | None = None,
) -> dict[str, Any]:
    matrix_path = (
        matrix_path
        or root / "05_project/configs/task_capabilities_v2.json"
    )
    schemas = [
        root / "05_project/schemas/action.v2.schema.json",
        root / "05_project/schemas/action.raven.v2.schema.json",
    ]
    prompts = [
        root / "05_project/prompts/executor_v2.md",
        root / "05_project/prompts/executor_raven_v2.md",
    ]
    adapter_path = (
        root / "05_project/src/raven_m/env/androidworld_adapter.py"
    )
    controller_path = (
        root / "05_project/src/raven_m/controller/episode_controller.py"
    )
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    schema_actions = [
        _action_types(json.loads(path.read_text(encoding="utf-8")))
        for path in schemas
    ]
    prompt_texts = [path.read_text(encoding="utf-8") for path in prompts]
    adapter_text = adapter_path.read_text(encoding="utf-8")
    controller_text = controller_path.read_text(encoding="utf-8")
    rows = []
    for task in matrix["tasks"]:
        errors: list[str] = []
        required = set(task["required_actions"])
        for path, available in zip(schemas, schema_actions, strict=True):
            missing = sorted(required - available)
            if missing:
                errors.append(f"{path.name} missing actions: {missing}")
        for path, text in zip(prompts, prompt_texts, strict=True):
            missing = sorted(action for action in required if action not in text)
            if missing:
                errors.append(f"{path.name} undocumented actions: {missing}")
            if task["requires_derived_text"] and (
                "deterministic" not in text
                or "Derived text" not in text
                or "allowed only" not in text
            ):
                errors.append(f"{path.name} forbids or omits derived text")
        for action in required:
            if f'action_type == "{action}"' not in adapter_text and (
                action not in {"swipe", "long_press", "wait"}
                or f'"{action}"' not in adapter_text
            ):
                errors.append(f"adapter lacks mapping/execution for {action}")
        if task["terminal_channel"] == "answer":
            if '"model_answer"' not in controller_text:
                errors.append("controller lacks answer termination")
            if "interaction_cache" not in controller_text:
                errors.append("controller lacks answer-channel audit")
            if "answer" not in required:
                errors.append("answer-terminal task does not require answer")
        if not task["evidence"]:
            errors.append("task has no source evidence")
        declared = bool(task["supported_by_protocol_v2"])
        selected = bool(task["selected_for_v2"])
        if selected and not declared:
            errors.append("selected task is declared unsupported")
        rows.append(
            {
                "task_id": task["task_id"],
                "task_class": task["task_class"],
                "selected": selected,
                "declared_supported": declared,
                "passed": not errors,
                "errors": errors,
            }
        )
    return {
        "schema_version": "task_action_coverage_audit.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": matrix["protocol"],
        "task_count": len(rows),
        "selected_task_count": sum(row["selected"] for row in rows),
        "passed_task_count": sum(row["passed"] for row in rows),
        "passed": all(row["passed"] for row in rows),
        "schema_actions": [sorted(value) for value in schema_actions],
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve())
    encoded = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        output = args.output
        if not output.is_absolute():
            output = args.root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
