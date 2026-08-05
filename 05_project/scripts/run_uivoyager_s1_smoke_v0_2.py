"""Run the frozen two-task UI-Voyager S1 integration smoke."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
from typing import Any
import uuid


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
sys.path[:0] = [str(PROJECT_ROOT / "src"), str(REPO_ROOT / "06_local_runtime" / "scripts")]

from raven_m.multi_framework_benchmark.arm_registry import get_arm  # noqa: E402
from raven_m.multi_framework_benchmark.capability_manifest import (  # noqa: E402
    sha256_file,
    verify_protected,
)
from raven_m.multi_framework_benchmark.event_schema import (  # noqa: E402
    REQUIRED_EVENT_FIELDS,
    SCHEMA_VERSION,
    append_event,
    canonical_json,
)
from raven_m.multi_framework_benchmark.runner import assert_output_root_is_new  # noqa: E402
from raven_m.multi_framework_benchmark.task_instances import (  # noqa: E402
    instantiate_verified,
    load_frozen_instances,
)


ARM_ID = "NS-PX-UIV4"
TASKS = ("ContactsAddContact", "ClockStopWatchRunning")
TASK_SEED = 20260805
MAX_ACTIONS = 8


def array_hash(value: Any) -> str | None:
    return sha256(value.tobytes()).hexdigest() if hasattr(value, "tobytes") else None


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "json_str"):
        return json.loads(value.json_str())
    return {"type": type(value).__name__, "repr": repr(value)}


def value_hash(value: Any) -> str:
    return sha256(canonical_json(json_safe(value)).encode("utf-8")).hexdigest()


def require_authorization(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "s0_all_global_gates_pass": True,
        "minimum_potential_launch_set_pass": True,
        "s1_first_call_manifest_frozen": True,
        "s1_generation_authorized": True,
    }
    for key, expected in required.items():
        if value.get(key) is not expected:
            raise RuntimeError(f"S1 authorization denied: {key}")
    if ARM_ID not in value.get("qualified_arms", []):
        raise RuntimeError(f"S1 authorization does not qualify {ARM_ID}")
    return value


def empty_event() -> dict[str, Any]:
    return {field: None for field in REQUIRED_EVENT_FIELDS}


def main() -> None:
    # AndroidWorld prints Unicode status symbols.  Force a reproducible UTF-8
    # console on Windows so successful episodes cannot be invalidated while
    # merely reporting their result.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json")
    parser.add_argument("--adb-path", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--task-manifest", type=Path)
    parser.add_argument("--stage-label", default="DEV_S1")
    args = parser.parse_args()

    authorization = require_authorization(args.authorization)
    protocol = json.loads(args.config.read_text(encoding="utf-8"))
    verify_protected(REPO_ROOT, protocol["protected_paths"])
    assert_output_root_is_new(
        args.output_root,
        tuple(REPO_ROOT / path for path in protocol["old_frozen_roots"]),
    )
    if args.output_root.exists():
        raise RuntimeError("S1 output root must not pre-exist")
    args.output_root.mkdir(parents=True)

    androidworld = args.source_root / "androidworld"
    sys.path[:0] = [str(androidworld), str(androidworld / "eval")]
    import androidworld_compat  # noqa: F401
    import requests
    from android_world import constants, episode_runner, registry, suite_utils
    from eval.clients.openai_client import OpenAIClient
    from eval.runner import EvalRunner

    manifest = json.loads(args.task_manifest.read_text(encoding="utf-8")) if args.task_manifest else None
    task_specs = load_frozen_instances(args.task_manifest) if args.task_manifest else [
        {"task_class": task, "task_seed": TASK_SEED} for task in TASKS
    ]
    max_actions = int(manifest.get("maximum_actions_per_task", MAX_ACTIONS)) if manifest else MAX_ACTIONS

    class FixedBudgetRunner(EvalRunner):
        def _run_episode(self, task):
            return episode_runner.run_episode(
                goal=task.goal,
                agent=self.agent,
                max_n_steps=max_actions,
                start_on_home_screen=False,
                termination_fn=None,
                task_name=task.name,
                worker_id=self.worker_id,
            )

    call_records: list[dict[str, Any]] = []
    original_post = requests.post

    def logged_post(url, *post_args, **post_kwargs):
        call_index = len(call_records)
        request_path = args.output_root / "model_calls" / f"call_{call_index:04d}.request.json"
        response_path = args.output_root / "model_calls" / f"call_{call_index:04d}.response.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        payload = post_kwargs.get("json")
        request_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        started = time.perf_counter()
        record = {
            "call_id": str(uuid.uuid4()),
            "request_path": str(request_path),
            "request_hash": sha256_file(request_path),
            "started_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = original_post(url, *post_args, **post_kwargs)
            response_path.write_text(response.text + "\n", encoding="utf-8")
            parsed = response.json() if response.content else {}
            usage = parsed.get("usage") or {}
            record.update({
                "status_code": response.status_code,
                "ok": response.ok,
                "response_path": str(response_path),
                "response_hash": sha256_file(response_path),
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
            })
            return response
        except Exception as exc:
            record.update({"ok": False, "exception": repr(exc), "input_tokens": 0, "output_tokens": 0})
            raise
        finally:
            record["latency_seconds"] = time.perf_counter() - started
            call_records.append(record)

    requests.post = logged_post
    spec = get_arm(ARM_ID)
    env_manifest = PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/controller_environments/uivoyager/environment.manifest.sha256"
    runtime_hash = sha256_file(env_manifest)
    dependency_hash = sha256_file(PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/controller_environments/uivoyager/pip.freeze.txt")
    prompt_path = androidworld / "eval/prompts/qwen3vl_instruct.md"
    prompt_hash = sha256_file(prompt_path)
    run_id = f"s1_uivoyager_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    config = {
        "worker_id": 0,
        "env": {
            "console_port": 5554,
            "grpc_port": 8554,
            "adb_path": str(args.adb_path),
            "emulator_path": str(REPO_ROOT / "06_local_runtime/android/sdk/emulator/emulator.exe"),
            "avd_name": "AndroidWorldAvd",
            "android_sdk_root": str(REPO_ROOT / "06_local_runtime/android/sdk"),
            "android_avd_home": str(REPO_ROOT / "06_local_runtime/android/avd"),
            "adb_server_port": 5037,
        },
        "agent": {
            "type": "local", "name": "Qwen3VL-Agent", "model_name": "qwen3vl",
            "prompt_name": "qwen3vl_instruct", "wait_after_action_seconds": 1.5,
            "use_som": False, "resize": None, "history_len": 30,
            "sft_data_dir": None, "n_history_image": 0,
        },
        "eval": {
            "suite_family": "android_world", "tasks": [row["task_class"] for row in task_specs],
            "n_task_combinations": 1,
            "task_random_seed": manifest.get("nominal_seed", TASK_SEED) if manifest else TASK_SEED,
            "checkpoint_dir": "", "output_path": str(args.output_root / "official"),
        },
        "task_manifest": str(args.task_manifest) if args.task_manifest else None,
        "task_manifest_sha256": sha256_file(args.task_manifest) if args.task_manifest else None,
    }
    (args.output_root / "frozen_runtime_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    client = OpenAIClient(
        base_url=args.base_url,
        model="UI-Voyager",
        api_key="EMPTY",
        temperature=0.7,
        max_tokens=16384,
        top_p=0.8,
        max_retry=3,
        retry_delay=1.0,
    )
    runner = FixedBudgetRunner(config)
    lifecycle: dict[str, dict[str, int]] = {}
    task_results: list[dict[str, Any]] = []
    try:
        runner.setup_env()
        runner.setup_agent(client)
        if args.task_manifest:
            registered = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
            suite = suite_utils.Suite()
            for task_spec in task_specs:
                task = instantiate_verified(registered, task_spec)
                # Match AndroidWorld create_suite(): the seed is serializer
                # metadata added after construction, not part of the frozen
                # task parameter hash or goal.
                task.params[constants.EpisodeConstants.SEED] = int(task_spec["task_seed"])
                suite[task_spec["task_class"]] = [task]
            suite.suite_family = registry.TaskRegistry.ANDROID_WORLD_FAMILY
        else:
            suite = runner.create_suite()
        for task_name, instances in suite.items():
            for task in instances:
                counts = {"initialize": 0, "evaluator": 0, "tear_down": 0}
                lifecycle[task_name] = counts
                for method_name, count_name in (("initialize_task", "initialize"), ("is_successful", "evaluator"), ("tear_down", "tear_down")):
                    original = getattr(task, method_name)
                    def wrapped(*method_args, __original=original, __count=count_name, **method_kwargs):
                        counts[__count] += 1
                        return __original(*method_args, **method_kwargs)
                    setattr(task, method_name, wrapped)
                call_start = len(call_records)
                result = runner._run_task(task, demo_mode=False)
                call_end = len(call_records)
                data = result.get(constants.EpisodeConstants.EPISODE_DATA)
                step_rows = episode_runner.transpose_dol_to_lod(data) if isinstance(data, dict) and data else []
                reward = result.get(constants.EpisodeConstants.IS_SUCCESSFUL)
                events_path = args.output_root / "events.jsonl"
                for step_index, row in enumerate(step_rows):
                    step_dir = args.output_root / "steps" / task_name / f"step_{step_index:02d}"
                    step_dir.mkdir(parents=True, exist_ok=True)
                    before = row.get("before_screenshot")
                    after = row.get("after_screenshot")
                    action = json_safe(row.get("action"))
                    action_path = step_dir / "action.json"
                    action_path.write_text(json.dumps(action, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    response_text = row.get("model_response") or ""
                    response_file = step_dir / "model_response.txt"
                    response_file.write_text(str(response_text), encoding="utf-8")
                    call = call_records[call_start + step_index] if call_start + step_index < call_end else {}
                    action_type = action.get("action_type") if isinstance(action, dict) else None
                    event = empty_event()
                    event.update({
                        "schema_version": SCHEMA_VERSION, "run_id": run_id, "arm_id": ARM_ID,
                        "lane": spec.lane, "reproduction_label": spec.reproduction_label,
                        "source_repo": spec.source_repo, "source_commit": spec.source_commit,
                        "checkpoint_id": spec.checkpoint_id, "checkpoint_revision": spec.checkpoint_revision,
                        "code_license": "MIT", "model_license": "MIT", "runtime_hash": runtime_hash,
                        "dependency_lock_hash": dependency_hash, "prompt_hash": prompt_hash,
                        "task_id": task_name, "task_class": task_name,
                        "task_seed": next((int(item["task_seed"]) for item in task_specs if item["task_class"] == task_name), TASK_SEED),
                        "task_params_hash": next(
                            (str(item["task_params_hash"]) for item in task_specs if item["task_class"] == task_name),
                            value_hash(task.params),
                        ), "attempt_id": f"{run_id}:{task_name}",
                        "rerun_of": None, "step_index": step_index,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "observation_privileges": ["screenshot"],
                        "screenshot_hash_before": array_hash(before), "screenshot_hash_after_2s": array_hash(after),
                        "screenshot_hash_after_5s": None, "ui_tree_hash_before": None, "ui_tree_hash_after": None,
                        "model_role": "native_policy", "call_id": call.get("call_id"),
                        "input_tokens": call.get("input_tokens", 0), "output_tokens": call.get("output_tokens", 0),
                        "latency_seconds": call.get("latency_seconds", 0.0), "raw_prompt_path": call.get("request_path"),
                        "raw_response_path": str(response_file), "raw_response_hash": sha256_file(response_file),
                        "parse_status": "PARSED" if row.get("action") is not None else "UNPARSEABLE",
                        "feedback_event": False, "feedback_type": None, "action_raw_path": str(action_path),
                        "action_canonical": action, "action_execute_status": "EXECUTED" if row.get("success") else "NOT_EXECUTED",
                        "pixel_effect_class": "CHANGED" if array_hash(before) != array_hash(after) else "NO_CHANGE",
                        "tree_effect_class": None, "finish_claim": action_type in {"status", "answer"},
                        "evaluator_reward": reward, "validity_class": args.stage_label,
                        "failure_edge": None if row.get("success") else "controller_or_parse",
                    })
                    append_event(events_path, event)
                task_results.append({
                    "task": task_name,
                    "exception": result.get(constants.EpisodeConstants.EXCEPTION_INFO),
                    "reward": reward,
                    "steps": len(step_rows),
                    "parseable_decisions": sum(row.get("action") is not None for row in step_rows),
                    "nonterminal_actions": sum(
                        isinstance(json_safe(row.get("action")), dict)
                        and json_safe(row.get("action")).get("action_type") not in {None, "status", "answer"}
                        and bool(row.get("success")) for row in step_rows),
                    "screen_changes": sum(array_hash(row.get("before_screenshot")) != array_hash(row.get("after_screenshot")) for row in step_rows),
                    "model_calls": call_end - call_start,
                    "lifecycle": counts,
                })
    finally:
        requests.post = original_post
        runner.close()

    summary = {
        "schema_version": "multi_framework_s1_smoke.v0.2",
        "run_id": run_id,
        "arm_id": ARM_ID,
        "classification": "DEV_ONLY",
        "authorization_manifest": str(args.authorization),
        "authorization_manifest_sha256": sha256_file(args.authorization),
        "generation_calls": len(call_records),
        "android_action_ceiling_per_task": max_actions,
        "tasks": task_results,
        "lifecycle": lifecycle,
        "protected_hashes_verified": True,
        "qualified": all(
            row["exception"] is None
            and row["steps"] <= max_actions
            and row["parseable_decisions"] >= 1
            and row["nonterminal_actions"] >= 1
            and row["lifecycle"] == {"initialize": 1, "evaluator": 1, "tear_down": 1}
            for row in task_results
        ) and sum(row["screen_changes"] for row in task_results) >= 1,
    }
    (args.output_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_root / "model_calls.json").write_text(
        json.dumps(call_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"arm_id": ARM_ID, "qualified": summary["qualified"], "tasks": task_results}))


if __name__ == "__main__":
    main()
