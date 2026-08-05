"""Zero-generation import/task/parser audit for frozen external controllers."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def registry_check(hard_manifest: Path) -> tuple[list[str], list[str]]:
    from android_world import registry

    expected = [row["class_name"] for row in json.loads(
        hard_manifest.read_text(encoding="utf-8"))["tasks"]]
    available = registry.TaskRegistry().get_registry(
        registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    return expected, [name for name in expected if name not in available]


def audit_mobileagent(source: Path) -> dict:
    root = source / "Mobile-Agent-v3.5" / "android_world_v3.5"
    sys.path.insert(0, str(root))
    from android_world.agents import gui_owl, infer_ma3, mobile_agent_v3  # noqa: F401
    from android_world.agents import mobile_agent_utils_new
    from android_world.agents.coordinate_resize import update_image_size_
    from android_world.env.interface import AsyncAndroidEnv
    from PIL import Image

    with tempfile.TemporaryDirectory() as temporary:
        image_path = Path(temporary) / "fixture.png"
        Image.new("RGB", (1080, 2400), "white").save(image_path)
        transformed = update_image_size_({
            "image": str(image_path), "width": 1080, "height": 2400})
    answer_rows = []
    for text in ("one", "12.5", "Monday"):
        action, _ = mobile_agent_utils_new.convert_mobile_agent_action_to_json_action(
            {"name": "mobile_use", "arguments": {"action": "answer", "text": text}},
            {},
            src_format="abs_origin",
            tgt_format="abs_origin",
        )
        env = AsyncAndroidEnv.__new__(AsyncAndroidEnv)
        env.interaction_cache = ""
        env.display_message = lambda *_args, **_kwargs: None
        AsyncAndroidEnv.execute_action(env, action)
        answer_rows.append({
            "input": text,
            "action_type": action.action_type,
            "interaction_cache": env.interaction_cache,
            "passed": action.action_type == "answer" and env.interaction_cache == text,
        })
    return {
        "runner_entrypoint": str(root / "run_ma35.py"),
        "runner_entrypoint_sha256": digest(root / "run_ma35.py"),
        "official_gui_shell_target_missing_recorded": not (root / "run_ma3.py").exists(),
        "gui_owl_import": True,
        "mobile_agent_v3_import": True,
        "inference_wrapper_import": True,
        "coordinate_fixture": {
            "input": [1080, 2400],
            "resized": [transformed["resized_width"], transformed["resized_height"]],
            "passed": transformed["resized_width"] > 0 and transformed["resized_height"] > 0,
        },
        "answer_fixture": {
            "cases": answer_rows,
            "passed": len(answer_rows) == 3 and all(row["passed"] for row in answer_rows),
        },
    }


def audit_uivoyager(source: Path) -> dict:
    androidworld = source / "androidworld"
    sys.path[:0] = [str(androidworld), str(androidworld / "eval")]
    from eval.agents.qwen_agent import QwenAgent
    from eval.clients.openai_client import OpenAIClient  # noqa: F401
    from eval.runner import EvalRunner  # noqa: F401

    fake = QwenAgent.__new__(QwenAgent)
    fake.model_name = "qwen3vl"
    fake.env = type("FakeEnv", (), {"interaction_cache": None})()
    click = fake._parse_action(
        '<tool_call>{"arguments":{"action":"click","coordinate":[999,999]}}</tool_call>',
        1080,
        2400,
    )
    answer_rows = []
    for text in ("one", "12.5", "Monday"):
        fake.env.interaction_cache = None
        answer = fake._parse_action(
            '<tool_call>{"arguments":{"action":"answer","text":'
            + json.dumps(text) + '}}</tool_call>',
            1080,
            2400,
        )
        answer_rows.append({
            "input": text,
            "action_type": answer.action_type,
            "interaction_cache": fake.env.interaction_cache,
            "passed": answer.action_type == "answer" and fake.env.interaction_cache == text,
        })
    return {
        "runner_entrypoint": str(androidworld / "eval" / "runner.py"),
        "runner_entrypoint_sha256": digest(androidworld / "eval" / "runner.py"),
        "runner_import": True,
        "client_import": True,
        "coordinate_fixture": {
            "input": [999, 999],
            "output": [click.x, click.y],
            "expected": [1080, 2400],
            "passed": (click.x, click.y) == (1080, 2400),
        },
        "answer_fixture": {
            "cases": answer_rows,
            "passed": len(answer_rows) == 3 and all(row["passed"] for row in answer_rows),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("mobileagent", "uivoyager"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--hard-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    details = (audit_mobileagent(args.source) if args.arm == "mobileagent"
               else audit_uivoyager(args.source))
    expected, missing = registry_check(args.hard_manifest)
    details.update({
        "schema_version": "external_controller_runtime_audit.v0.2",
        "arm": args.arm,
        "python": sys.version,
        "generation_calls": 0,
        "android_actions": 0,
        "expected_hard_task_classes": expected,
        "missing_hard_task_classes": missing,
        "task_class_support_19_of_19": not missing and len(expected) == 19,
    })
    details["qualified"] = (
        details["task_class_support_19_of_19"]
        and details["coordinate_fixture"]["passed"]
        and details.get("answer_fixture", {"passed": True})["passed"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(details, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"arm": args.arm, "qualified": details["qualified"], "missing": missing}))


if __name__ == "__main__":
    main()
