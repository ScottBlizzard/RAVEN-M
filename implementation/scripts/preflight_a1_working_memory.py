"""Zero-generation qualification for A1 Action Working Memory."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a1_contract import (  # noqa: E402
    A1_CONFIG,
    A1_MANIFEST,
    A1_PREFLIGHT_REPORT,
    current_source_freeze,
)
from raven_m.official_qwen_mobile.protocol import (  # noqa: E402
    A1_WORKING_MEMORY_SYSTEM_PROMPT,
    OFFICIAL_SYSTEM_PROMPT,
    build_user_prompt,
)
from raven_m.official_qwen_mobile.working_memory import (  # noqa: E402
    ActionWorkingMemory,
    append_working_memory,
)


EXPECTED_OFFICIAL_PROMPT_SHA256 = (
    "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=A1_PREFLIGHT_REPORT)
    args = parser.parse_args()
    errors: list[str] = []

    config = json.loads(A1_CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(A1_MANIFEST.read_text(encoding="utf-8"))
    instances = [
        item
        for item in (manifest.get("instances") or [])
        if int(item.get("task_seed", -1)) == 20260806
    ]
    if len(instances) != 19:
        errors.append(f"expected_19_instances_received_{len(instances)}")
    if any(int(item.get("task_seed", -1)) != 20260806 for item in instances):
        errors.append("task_seed_drift")
    if len({item.get("task_class") for item in instances}) != 19:
        errors.append("task_classes_not_unique")
    if config.get("benchmark", {}).get("task_count") != 19:
        errors.append("config_task_count_drift")
    if config.get("agent", {}).get("extra_model_calls") != 0:
        errors.append("a1_must_not_add_model_calls")
    memory_config = config.get("agent", {}).get("memory", {})
    if memory_config.get("max_items") != 6 or memory_config.get("max_chars") != 3000:
        errors.append("memory_capacity_drift")

    official_prompt_sha = sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if official_prompt_sha != EXPECTED_OFFICIAL_PROMPT_SHA256:
        errors.append("official_prompt_drift")
    if not A1_WORKING_MEMORY_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT):
        errors.append("a1_prompt_not_additive")

    canary = "A1-CANARY-4721"
    memory = ActionWorkingMemory(max_items=6, max_chars=3000)
    empty_block, empty_read = memory.read()
    baseline_prompt = build_user_prompt("preflight", [])
    if append_working_memory(baseline_prompt, empty_block) != baseline_prompt:
        errors.append("empty_memory_changes_a0_prompt")
    write = memory.write(
        source_step=0,
        action_summary=(
            f"MEMORY[observed={canary}; verified=none; pending=continue] | "
            "Tap the target."
        ),
        source_call_id="preflight-call",
        source_response_sha256="preflight-response",
        source_screenshot_sha256="preflight-screen",
    )
    block, nonempty_read = memory.read()
    injected_prompt = append_working_memory(baseline_prompt, block)
    if not write.get("written") or canary not in injected_prompt:
        errors.append("canary_write_read_injection_failed")
    if not nonempty_read.get("nonempty") or not memory.audit_record().get("active"):
        errors.append("memory_activation_audit_failed")
    if empty_read.get("nonempty"):
        errors.append("empty_memory_read_marked_nonempty")

    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/official_qwen_mobile/test_protocol.py",
            "tests/official_qwen_mobile/test_official_qwen_controller.py",
            "tests/official_qwen_mobile/test_working_memory.py",
            "tests/models/test_vllm_client.py",
            "-q",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    if tests.returncode != 0:
        errors.append("targeted_tests_failed")

    report = {
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "errors": errors,
        "experiment_id": config.get("experiment_id"),
        "official_prompt_sha256": official_prompt_sha,
        "a1_prompt_sha256": sha256(
            A1_WORKING_MEMORY_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "manifest_sha256": sha256(A1_MANIFEST.read_bytes()).hexdigest(),
        "manifest_task_order": [item["task_class"] for item in instances],
        "task_seed": 20260806,
        "memory_canary": {
            "value": canary,
            "write": write,
            "empty_read": empty_read,
            "nonempty_read": nonempty_read,
            "present_in_next_prompt": canary in injected_prompt,
        },
        "tests": {
            "returncode": tests.returncode,
            "stdout": tests.stdout,
            "stderr": tests.stderr,
        },
        "source_freeze": current_source_freeze(),
    }
    _atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
