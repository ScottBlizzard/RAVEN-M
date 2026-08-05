"""Zero-generation source/runner contract audit for protocol v0.2."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml


SPECS = {
    "MobileAgent": {
        "revision": "11cea575561fb7800b5fb6b6cafa56f7a91de11f",
        "required": [
            "LICENSE",
            "Mobile-Agent-v3.5/android_world_v3.5/requirements.txt",
            "Mobile-Agent-v3.5/android_world_v3.5/run_ma35.py",
            "Mobile-Agent-v3.5/android_world_v3.5/run_ma35.sh",
            "Mobile-Agent-v3.5/android_world_v3.5/run_guiowl15.sh",
            "Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py",
            "Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/mobile_agent_v3.py",
            "Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/function_call_mobile_answer.py",
            "Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/coordinate_resize.py",
        ],
    },
    "UI-Voyager": {
        "revision": "67b65e2be093753ecaa2964f48739339b870813e",
        "required": [
            "LICENSE",
            "run_android_world.sh",
            "androidworld/requirements.txt",
            "androidworld/eval/runner.py",
            "androidworld/eval/configs/UI-Voyager.yaml",
        ],
    },
    "ScaleCUA": {
        "revision": "5d92feea9f1e14b8303ce37da45b286fb1f4d3aa",
        "required": [
            "LICENSE",
            "evaluation/AndroidWorld/requirements.txt",
            "evaluation/AndroidWorld/run.py",
            "evaluation/AndroidWorld/android_world/agents/seeact_v.py",
        ],
    },
}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def source_evidence(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        rows[key] = value
    return rows


def audit(source_root: Path, evidence_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "multi_framework_source_contract_audit.v0.2",
        "generation_calls": 0,
        "android_actions": 0,
        "sources": {},
    }
    for key, spec in SPECS.items():
        root = source_root / key
        evidence_path = evidence_root / f"{key}.source.txt"
        row: dict[str, Any] = {
            "expected_revision": spec["revision"],
            "available": root.is_dir() and evidence_path.is_file(),
        }
        if not row["available"]:
            row["qualified_static_source"] = False
            result["sources"][key] = row
            continue
        evidence = source_evidence(evidence_path)
        missing = [name for name in spec["required"] if not (root / name).is_file()]
        row.update({
            "resolved_revision": evidence.get("revision"),
            "archive_sha256": evidence.get("archive_sha256"),
            "license_sha256": evidence.get("license_sha256"),
            "required_paths": spec["required"],
            "missing_paths": missing,
            "source_pin": evidence.get("revision") == spec["revision"],
            "code_license": bool(evidence.get("license_sha256")),
        })
        if key == "MobileAgent":
            base = root / "Mobile-Agent-v3.5/android_world_v3.5"
            official_gui_shell = (base / "run_guiowl15.sh").read_text(encoding="utf-8")
            runner = (base / "run_ma35.py").read_text(encoding="utf-8")
            row["official_gui_shell_target"] = "run_ma3.py"
            row["official_gui_shell_target_exists"] = (base / "run_ma3.py").is_file()
            row["minimal_adapter_entrypoint"] = "run_ma35.py"
            row["minimal_adapter_entrypoint_sha256"] = digest(base / "run_ma35.py")
            row["gui_owl_branch_present"] = "_AGENT_NAME.value == 'gui_owl'" in runner
            row["mobile_agent_v3_branch_present"] = "_AGENT_NAME.value == 'mobile_agent_v3'" in runner
            row["task_filter_present"] = "flags.DEFINE_list(" in runner and "'tasks'" in runner
            row["task_seed_present"] = "task_random_seed" in runner
            row["shell_mismatch_recorded"] = "run_ma3.py" in official_gui_shell
        elif key == "UI-Voyager":
            config = yaml.safe_load((root / "androidworld/eval/configs/UI-Voyager.yaml").read_text(encoding="utf-8"))
            runner = (root / "androidworld/eval/runner.py").read_text(encoding="utf-8")
            row["official_config"] = {
                "temperature": config["llm"]["temperature"],
                "top_p": config["llm"]["top_p"],
                "max_tokens": config["llm"]["max_tokens"],
                "max_retry": config["llm"]["max_retry"],
                "use_som": config["agent"]["use_som"],
                "history_len": config["agent"]["history_len"],
                "n_history_image": config["agent"]["n_history_image"],
            }
            row["pixel_only_config"] = config["agent"]["use_som"] is False
            row["task_filter_present"] = "eval_config.get('tasks')" in runner
            row["task_seed_present"] = "task_random_seed" in runner
            row["official_evaluator_present"] = "task.is_successful(self.env)" in runner
        else:
            runner = (root / "evaluation/AndroidWorld/run.py").read_text(encoding="utf-8")
            row["native_agent_mode_present"] = "mode=\"Agent\"" in runner or 'mode="Agent"' in runner
            row["task_filter_present"] = 'flags.DEFINE_list(' in runner and '"tasks"' in runner
            row["task_seed_present"] = "task_random_seed" in runner
        boolean_contracts = [value for name, value in row.items()
                             if name.endswith("_present") or name in {
                                 "source_pin", "code_license", "pixel_only_config",
                                 "shell_mismatch_recorded"}]
        row["qualified_static_source"] = not missing and all(boolean_contracts)
        result["sources"][key] = row
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = audit(args.source_root, args.evidence_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: row["qualified_static_source"]
                      for key, row in value["sources"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
