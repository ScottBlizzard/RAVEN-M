"""Audit the frozen-source Hard manifest without running a Hard episode."""

from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag == "tr":
            self.in_row = True
            self.row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.row:
                self.rows.append(self.row)
            self.in_row = False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "configs"
        / "task_manifests"
        / "androidworld_hard_v1.json",
    )
    parser.add_argument(
        "--ablation",
        type=Path,
        default=PROJECT_ROOT
        / "configs"
        / "task_manifests"
        / "ablation8_v1.json",
    )
    parser.add_argument(
        "--task-list",
        type=Path,
        default=REPOSITORY_ROOT
        / "01_sources"
        / "official"
        / "androidworld"
        / "task_list.html",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metadata" / "protocol_audit.json",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ablation = json.loads(args.ablation.read_text(encoding="utf-8"))
    errors: list[str] = []

    actual_source_hash = sha256(args.task_list.read_bytes()).hexdigest()
    expected_source_hash = manifest["source"]["task_list_snapshot_sha256"]
    if actual_source_hash != expected_source_hash:
        errors.append("Official task-list snapshot hash does not match.")

    table_parser = TableParser()
    table_parser.feed(args.task_list.read_text(encoding="utf-8"))
    official: dict[str, dict[str, Any]] = {}
    for row in table_parser.rows:
        if len(row) < 5 or row[0] in {"Task Name", "Task"}:
            continue
        try:
            optimal = int(row[4])
        except ValueError:
            continue
        official[row[0]] = {
            "optimal_steps": optimal,
            "difficulty": row[2].lower(),
        }
    official_hard = {
        name for name, value in official.items() if value["difficulty"] == "hard"
    }

    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    ids = [item["id"] for item in manifest["tasks"]]
    names = [item["class_name"] for item in manifest["tasks"]]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate task IDs.")
    if len(names) != len(set(names)):
        errors.append("Duplicate task class names.")
    if len(names) != 19:
        errors.append(f"Expected 19 tasks, found {len(names)}.")
    if set(names) != official_hard:
        errors.append(
            "Manifest task names differ from the official hard set: "
            f"missing={sorted(official_hard-set(names))}, "
            f"extra={sorted(set(names)-official_hard)}"
        )

    checked = []
    for item in manifest["tasks"]:
        name = item["class_name"]
        if name not in registered:
            errors.append(f"{name} is not in the frozen registry.")
            continue
        if name not in official:
            errors.append(f"{name} is not in the frozen task-list snapshot.")
            continue
        task_type = registered[name]
        complexity = float(task_type.complexity)
        native_budget = int(10 * complexity)
        official_row = official[name]
        if official_row["difficulty"] != "hard":
            errors.append(f"{name} is not officially hard.")
        if item["optimal_steps_from_task_list"] != official_row["optimal_steps"]:
            errors.append(f"{name} optimal-step value differs.")
        if abs(float(item["complexity"]) - complexity) > 1e-9:
            errors.append(f"{name} complexity differs from the registry.")
        if item["native_max_steps"] != native_budget:
            errors.append(f"{name} native budget differs from suite_utils.")
        checked.append(
            {
                "id": item["id"],
                "class_name": name,
                "complexity": complexity,
                "native_max_steps": native_budget,
            }
        )

    ablation_ids = ablation["task_ids"]
    if len(ablation_ids) != 8 or len(set(ablation_ids)) != 8:
        errors.append("Ablation manifest must contain eight unique task IDs.")
    if not set(ablation_ids).issubset(set(ids)):
        errors.append("Ablation task IDs are not a subset of the Hard manifest.")

    result = {
        "status": "passed" if not errors else "failed",
        "hard_task_count": len(names),
        "official_hard_count": len(official_hard),
        "task_list_sha256": actual_source_hash,
        "androidworld_commit_expected": manifest["source"]["git_commit"],
        "instance_seeds": manifest["protocol"]["instance_seeds"],
        "ablation_task_ids": ablation_ids,
        "checked_tasks": checked,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
