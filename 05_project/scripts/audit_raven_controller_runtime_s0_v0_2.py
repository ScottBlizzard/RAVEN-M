"""Zero-generation S0 audit of the frozen RAVEN B3/M0 source snapshot."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

EXPECTED_COMMIT = "08b21d06db165d1fb6908c457f955988061b10ca"
EXPECTED_VARIANTS = {"CB-PX-B3": "B3", "CB-PX-M0": "M0"}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--androidworld-source", type=Path, required=True)
    parser.add_argument("--hard-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    project = source / "05_project"
    third_party = args.androidworld_source.resolve()
    sys.path[:0] = [str(project / "src"), str(third_party)]

    from android_world import registry
    from raven_m.controller.episode_controller import EpisodeController  # noqa: F401

    expected_tasks = [row["class_name"] for row in json.loads(
        args.hard_manifest.read_text(encoding="utf-8"))["tasks"]]
    available = registry.TaskRegistry().get_registry(
        registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    missing = [name for name in expected_tasks if name not in available]

    arms = {}
    for arm_id, variant in EXPECTED_VARIANTS.items():
        config_path = project / "configs" / "agents" / f"{variant.casefold()}.yaml"
        config_text = config_path.read_text(encoding="utf-8")
        variant_line = next(
            (line.split(":", 1)[1].strip() for line in config_text.splitlines()
             if line.startswith("variant:")),
            None,
        )
        arms[arm_id] = {
            "variant": variant,
            "config_path": str(config_path),
            "config_sha256": digest(config_path),
            "variant_matches": variant_line == variant,
            "screenshot_only": "ui_tree" not in config_text.casefold(),
            "runner_import": True,
            "task_class_support_19_of_19": len(expected_tasks) == 19 and not missing,
            "missing_hard_task_classes": missing,
        }
        arms[arm_id]["qualified"] = all((
            arms[arm_id]["variant_matches"],
            arms[arm_id]["screenshot_only"],
            arms[arm_id]["runner_import"],
            arms[arm_id]["task_class_support_19_of_19"],
        ))

    runner_path = project / "src" / "raven_m" / "controller" / "episode_controller.py"
    result = {
        "schema_version": "raven_controller_runtime_audit.v0.2",
        "source_root": str(source),
        "expected_commit": EXPECTED_COMMIT,
        "resolved_commit": git_head(source),
        "source_pin": git_head(source) == EXPECTED_COMMIT,
        "runner_path": str(runner_path),
        "runner_sha256": digest(runner_path),
        "python": sys.version,
        "generation_calls": 0,
        "android_actions": 0,
        "arms": arms,
    }
    result["qualified"] = result["source_pin"] and all(
        row["qualified"] for row in arms.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"qualified": result["qualified"], "missing": missing}))
    if not result["qualified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
