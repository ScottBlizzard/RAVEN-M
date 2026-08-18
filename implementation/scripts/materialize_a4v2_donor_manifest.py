#!/usr/bin/env python3
"""Materialize the exact CPU-only A4-v2 donor acquisition instances."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.multi_framework_benchmark.task_instances import _digest, goal_digest  # noqa: E402


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _content_sha(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "content_sha256"}
    return _digest(body)


def materialize(
    plan_path: Path,
    output_path: Path,
    *,
    include_optional: bool = False,
    supplement_routes: tuple[str, ...] = (),
) -> dict[str, Any]:
    import numpy as np
    import android_world
    from android_world import registry

    android_root = Path(
        subprocess.check_output(
            ["git", "-C", str(Path(android_world.__file__).resolve().parent), "rev-parse", "--show-toplevel"],
            text=True,
        ).strip()
    )
    android_head = subprocess.check_output(
        ["git", "-C", str(android_root), "rev-parse", "HEAD"], text=True
    ).strip()
    tracked_diff = subprocess.check_output(
        ["git", "-C", str(android_root), "diff", "--no-ext-diff", "--binary", "HEAD"]
    )
    untracked = subprocess.check_output(
        ["git", "-C", str(android_root), "ls-files", "--others", "--exclude-standard"],
        text=True,
    ).splitlines()
    android_worktree = {
        "head": android_head,
        "tracked_diff_sha256": sha256(tracked_diff).hexdigest(),
        "untracked_files": {
            relative.replace("\\", "/"): _file_sha(android_root / relative)
            for relative in sorted(untracked)
            if (android_root / relative).is_file()
        },
    }

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("schema") != "a4v2.awm_donor_acquisition_plan.v2":
        raise RuntimeError("wrong A4-v2 donor plan schema")
    available = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    tasks: list[dict[str, Any]] = []
    selected = set(supplement_routes)

    def add_task(route_id: str, ordinal: int, slot: dict[str, Any], *, optional: bool) -> None:
        task_class = str(slot["task_class"])
        seed = int(slot["task_seed"])
        if task_class not in available:
            raise RuntimeError(f"AndroidWorld task is not registered: {task_class}")
        random.seed(seed)
        np.random.seed(seed)
        instance = available[task_class](available[task_class].generate_random_params())
        tasks.append(
            {
                "task_id": f"{route_id}_{ordinal:02d}_s{seed}",
                "route_id": route_id,
                "task_class": task_class,
                "task_seed": seed,
                "native_max_steps": int(slot["native_max_steps"]),
                "difficulty": str(slot["difficulty"]).lower(),
                "optional": optional,
                "task_params_hash": _digest(instance.params),
                "goal_hash": goal_digest(instance.goal),
            }
        )

    for group in plan.get("route_groups") or []:
        route_id = str(group["route_id"])
        if selected and route_id not in selected:
            continue
        for ordinal, slot in enumerate(group.get("slots") or [], start=1):
            optional = bool(slot.get("optional"))
            if selected and not optional:
                continue
            if not selected and optional and not include_optional:
                continue
            add_task(route_id, ordinal, slot, optional=optional)
    if selected:
        fallback_by_route = {
            str(slot["route_id"]): slot for slot in plan.get("ordered_final_fallback_slots") or []
        }
        unknown = selected - set(fallback_by_route)
        if unknown:
            raise RuntimeError(f"unknown supplement routes: {sorted(unknown)}")
        for route_id in supplement_routes:
            add_task(route_id, 90, fallback_by_route[route_id], optional=True)
    expected = (
        sum(1 for group in plan["route_groups"] if group["route_id"] in selected for slot in group["slots"] if slot.get("optional"))
        + len(selected)
        if selected
        else int(plan["required_slot_count"]) + (int(plan["optional_slot_count"]) if include_optional else 0)
    )
    if len(tasks) != expected:
        raise RuntimeError(f"donor manifest count drift: {len(tasks)} != {expected}")
    payload: dict[str, Any] = {
        "schema": "a4v2.donor_acquisition_manifest.v1",
        "experiment_id": "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1",
        "parent_controller": "A0_OFFICIAL_QWEN3VL32B_SCREENSHOT_ONLY",
        "androidworld_commit": str(plan["androidworld_commit"]),
        "androidworld_worktree_identity": android_worktree,
        "plan_path": str(plan_path.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/"),
        "plan_file_sha256": _file_sha(plan_path),
        "protocol_amendment_path": "protocols/A4V2_DONOR_ACQUISITION_PLAN_V2_AMENDMENT_2026-08-19.md",
        "protocol_amendment_sha256": _file_sha(
            REPOSITORY_ROOT / "protocols/A4V2_DONOR_ACQUISITION_PLAN_V2_AMENDMENT_2026-08-19.md"
        ),
        "include_optional": include_optional,
        "supplement_routes": list(supplement_routes),
        "manifest_role": "deficit_supplement" if selected else "required_panel",
        "instance_generation": "random.seed(seed); numpy.random.seed(seed); task_type.generate_random_params()",
        "tasks": tasks,
    }
    payload["content_sha256"] = _content_sha(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=REPOSITORY_ROOT / "implementation/configs/a4v2_awm_donor_acquisition_plan.json")
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_V2.json")
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument("--supplement-route", action="append", default=[])
    args = parser.parse_args()
    if args.include_optional and args.supplement_route:
        parser.error("--include-optional and --supplement-route are mutually exclusive")
    result = materialize(
        args.plan.resolve(), args.output.resolve(),
        include_optional=args.include_optional,
        supplement_routes=tuple(args.supplement_route),
    )
    print(json.dumps({"status": "ready", "task_count": len(result["tasks"]), "content_sha256": result["content_sha256"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
