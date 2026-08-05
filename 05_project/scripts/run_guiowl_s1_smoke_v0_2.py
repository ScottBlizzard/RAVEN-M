"""Run the frozen two-task GUI-Owl-1.5 S1 integration smoke."""

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
from raven_m.multi_framework_benchmark.androidworld_adapter import normalize_guiowl_image_urls  # noqa: E402
from raven_m.multi_framework_benchmark.capability_manifest import sha256_file, verify_protected  # noqa: E402
from raven_m.multi_framework_benchmark.event_schema import REQUIRED_EVENT_FIELDS, SCHEMA_VERSION, append_event, canonical_json  # noqa: E402
from raven_m.multi_framework_benchmark.runner import assert_output_root_is_new  # noqa: E402
from raven_m.multi_framework_benchmark.task_instances import (  # noqa: E402
    instantiate_verified,
    load_frozen_instances,
)


ARM_ID = "NS-PX-GO15"
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
    for key in ("s0_all_global_gates_pass", "minimum_potential_launch_set_pass", "s1_first_call_manifest_frozen", "s1_generation_authorized"):
        if value.get(key) is not True:
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
    parser.add_argument("--stage-label", default="multi_framework_s1_v0_2_dev_only")
    args = parser.parse_args()

    require_authorization(args.authorization)
    protocol = json.loads(args.config.read_text(encoding="utf-8"))
    verify_protected(REPO_ROOT, protocol["protected_paths"])
    assert_output_root_is_new(args.output_root, tuple(REPO_ROOT / path for path in protocol["old_frozen_roots"]))
    if args.output_root.exists():
        raise RuntimeError("S1 output root must not pre-exist")
    args.output_root.mkdir(parents=True)

    source = args.source_root / "Mobile-Agent-v3.5" / "android_world_v3.5"
    sys.path.insert(0, str(source))
    import androidworld_compat  # noqa: F401
    from android_world import constants, episode_runner, registry, suite_utils
    from android_world.agents import gui_owl, infer_ma3
    from android_world.env import env_launcher

    call_records: list[dict[str, Any]] = []
    model = infer_ma3.GUIOwlWrapper(
        api_key="EMPTY",
        base_url=args.base_url,
        model_name="GUI-Owl-1.5-8B-Think",
        max_retry=10,
        temperature=0.0,
    )
    original_create = model.bot.chat.completions.create

    class CompletionsProxy:
        def create(self, *create_args, **create_kwargs):
            # The official wrapper stores temperature but omits all decoding
            # arguments from the API call. Apply the already-frozen protocol
            # values at the transport boundary without changing policy logic.
            create_kwargs.setdefault("temperature", 0.0)
            create_kwargs.setdefault("top_p", 1.0)
            create_kwargs.setdefault("max_tokens", 4096)
            create_kwargs, normalized_image_urls = normalize_guiowl_image_urls(create_kwargs)
            call_index = len(call_records)
            call_dir = args.output_root / "model_calls"
            call_dir.mkdir(parents=True, exist_ok=True)
            request_path = call_dir / f"call_{call_index:04d}.request.json"
            response_path = call_dir / f"call_{call_index:04d}.response.json"
            request_path.write_text(json.dumps(json_safe(create_kwargs), ensure_ascii=False) + "\n", encoding="utf-8")
            started = time.perf_counter()
            record = {
                "call_id": str(uuid.uuid4()), "request_path": str(request_path),
                "request_hash": sha256_file(request_path),
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "transport_adapter": "raw_png_base64_to_data_url.v1",
                "normalized_image_urls": normalized_image_urls,
            }
            try:
                response = original_create(*create_args, **create_kwargs)
                response_path.write_text(response.model_dump_json(indent=2) + "\n", encoding="utf-8")
                usage = response.usage
                record.update({
                    "ok": True, "response_path": str(response_path),
                    "response_hash": sha256_file(response_path),
                    "input_tokens": int(usage.prompt_tokens if usage else 0),
                    "output_tokens": int(usage.completion_tokens if usage else 0),
                })
                return response
            except Exception as exc:
                record.update({"ok": False, "exception": repr(exc), "input_tokens": 0, "output_tokens": 0})
                raise
            finally:
                record["latency_seconds"] = time.perf_counter() - started
                call_records.append(record)

    class ChatProxy:
        completions = CompletionsProxy()

    class BotProxy:
        chat = ChatProxy()

    model.bot = BotProxy()
    arm_spec = get_arm(ARM_ID)
    env_manifest = PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/controller_environments/mobileagent/environment.manifest.sha256"
    runtime_hash = sha256_file(env_manifest)
    dependency_hash = sha256_file(PROJECT_ROOT / "metadata/multi_framework_s0_v0_2/controller_environments/mobileagent/pip.freeze.txt")
    prompt_hash = sha256_file(source / "android_world/agents/gui_owl.py")
    run_id = f"s1_guiowl_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    manifest = json.loads(args.task_manifest.read_text(encoding="utf-8")) if args.task_manifest else None
    task_specs = load_frozen_instances(args.task_manifest) if args.task_manifest else [
        {"task_class": task, "task_seed": TASK_SEED} for task in TASKS
    ]
    max_actions = int(manifest.get("maximum_actions_per_task", MAX_ACTIONS)) if manifest else MAX_ACTIONS
    frozen = {
        "arm_id": ARM_ID, "tasks": [row["task_class"] for row in task_specs],
        "task_seed": manifest.get("nominal_seed", TASK_SEED) if manifest else TASK_SEED,
        "task_manifest": str(args.task_manifest) if args.task_manifest else None,
        "task_manifest_sha256": sha256_file(args.task_manifest) if args.task_manifest else None,
        "maximum_actions_per_task": max_actions, "base_url": args.base_url,
        "model": "GUI-Owl-1.5-8B-Think", "temperature": 0.0,
        "official_internal_retry_limit": 10,
        "transport_adapter": "raw_png_base64_to_data_url.v1",
    }
    (args.output_root / "frozen_runtime_config.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    env = env_launcher.load_and_setup_env(
        console_port=5554,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=str(args.adb_path),
        grpc_port=8554,
    )
    agent = gui_owl.GUIOwl(
        env, model, "qwen-vl", api_key=None, url=None,
        output_path=str(args.output_root / "official_trajectory"),
    )
    agent.name = "gui_owl"
    agent.transition_pause = None
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(family=registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    if args.task_manifest:
        suite = suite_utils.Suite()
        for task_spec in task_specs:
            suite[task_spec["task_class"]] = [instantiate_verified(registered, task_spec)]
    else:
        suite = suite_utils.create_suite(
            registered, n_task_combinations=1, seed=TASK_SEED,
            tasks=list(TASKS), use_identical_params=True,
        )
    suite.suite_family = registry.TaskRegistry.ANDROID_WORLD_FAMILY
    agent.get_task_name(suite)
    task_results: list[dict[str, Any]] = []
    lifecycle: dict[str, dict[str, int]] = {}
    try:
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
                def fixed_episode(current_task):
                    return episode_runner.run_episode(
                        goal=current_task.goal,
                        agent=agent,
                        max_n_steps=max_actions,
                        start_on_home_screen=current_task.start_on_home_screen,
                        termination_fn=None,
                    )
                result = suite_utils._run_task(task, fixed_episode, env, demo_mode=False)
                call_end = len(call_records)
                data = result.get(constants.EpisodeConstants.EPISODE_DATA)
                rows = episode_runner.transpose_dol_to_lod(data) if isinstance(data, dict) and data else []
                successful_calls = [row for row in call_records[call_start:call_end] if row.get("ok")]
                reward = result.get(constants.EpisodeConstants.IS_SUCCESSFUL)
                screenshot_hashes = [array_hash(row.get("screenshot")) for row in rows]
                for step_index, row in enumerate(rows):
                    step_dir = args.output_root / "steps" / task_name / f"step_{step_index:02d}"
                    step_dir.mkdir(parents=True, exist_ok=True)
                    action = json_safe(row.get("action"))
                    action_path = step_dir / "action.json"
                    action_path.write_text(json.dumps(action, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    response_path = step_dir / "model_response.txt"
                    response_path.write_text(str(row.get("action_response") or ""), encoding="utf-8")
                    call = successful_calls[step_index] if step_index < len(successful_calls) else {}
                    action_type = action.get("action_type") if isinstance(action, dict) else None
                    next_hash = screenshot_hashes[step_index + 1] if step_index + 1 < len(screenshot_hashes) else None
                    event = empty_event()
                    event.update({
                        "schema_version": SCHEMA_VERSION, "run_id": run_id, "arm_id": ARM_ID,
                        "lane": arm_spec.lane, "reproduction_label": arm_spec.reproduction_label,
                        "source_repo": arm_spec.source_repo, "source_commit": arm_spec.source_commit,
                        "checkpoint_id": arm_spec.checkpoint_id, "checkpoint_revision": arm_spec.checkpoint_revision,
                        "code_license": "MIT", "model_license": "MIT", "runtime_hash": runtime_hash,
                        "dependency_lock_hash": dependency_hash, "prompt_hash": prompt_hash,
                        "task_id": task_name, "task_class": task_name,
                        "task_seed": next((int(row["task_seed"]) for row in task_specs if row["task_class"] == task_name), TASK_SEED),
                        "task_params_hash": value_hash(task.params), "attempt_id": f"{run_id}:{task_name}",
                        "rerun_of": None, "step_index": step_index,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "observation_privileges": ["screenshot"],
                        "screenshot_hash_before": screenshot_hashes[step_index],
                        "screenshot_hash_after_2s": next_hash, "screenshot_hash_after_5s": None,
                        "ui_tree_hash_before": None, "ui_tree_hash_after": None,
                        "model_role": "native_policy", "call_id": call.get("call_id"),
                        "input_tokens": call.get("input_tokens", 0), "output_tokens": call.get("output_tokens", 0),
                        "latency_seconds": call.get("latency_seconds", 0.0), "raw_prompt_path": call.get("request_path"),
                        "raw_response_path": str(response_path), "raw_response_hash": sha256_file(response_path),
                        "parse_status": "PARSED" if action_type not in {None, "unknown"} else "UNPARSEABLE",
                        "feedback_event": False, "feedback_type": None, "action_raw_path": str(action_path),
                        "action_canonical": action,
                        "action_execute_status": "EXECUTED" if action_type not in {None, "unknown", "status"} else "NOT_EXECUTED",
                        "pixel_effect_class": "CHANGED" if next_hash and next_hash != screenshot_hashes[step_index] else "UNOBSERVED_OR_NO_CHANGE",
                        "tree_effect_class": None, "finish_claim": action_type == "status",
                        "evaluator_reward": reward, "validity_class": args.stage_label,
                        "failure_edge": None if action_type not in {None, "unknown"} else "parse",
                    })
                    append_event(args.output_root / "events.jsonl", event)
                task_results.append({
                    "task": task_name,
                    "exception": result.get(constants.EpisodeConstants.EXCEPTION_INFO),
                    "reward": reward,
                    "steps": len(rows),
                    "parseable_decisions": sum(
                        isinstance(json_safe(row.get("action")), dict)
                        and json_safe(row.get("action")).get("action_type") not in {None, "unknown"}
                        for row in rows),
                    "nonterminal_actions": sum(
                        isinstance(json_safe(row.get("action")), dict)
                        and json_safe(row.get("action")).get("action_type") not in {None, "unknown", "status", "answer"}
                        for row in rows),
                    "screen_changes": sum(
                        screenshot_hashes[index] != screenshot_hashes[index + 1]
                        for index in range(max(0, len(screenshot_hashes) - 1))),
                    "model_calls": call_end - call_start,
                    "lifecycle": counts,
                })
    finally:
        env.close()

    summary = {
        "schema_version": "multi_framework_s1_smoke.v0.2", "run_id": run_id,
        "arm_id": ARM_ID, "classification": "DEV_ONLY",
        "authorization_manifest": str(args.authorization),
        "authorization_manifest_sha256": sha256_file(args.authorization),
        "generation_calls": len(call_records), "android_action_ceiling_per_task": max_actions,
        "tasks": task_results, "lifecycle": lifecycle, "protected_hashes_verified": True,
        "qualified": all(
            row["exception"] is None and row["steps"] <= max_actions
            and row["parseable_decisions"] >= 1 and row["nonterminal_actions"] >= 1
            and row["lifecycle"] == {"initialize": 1, "evaluator": 1, "tear_down": 1}
            for row in task_results
        ) and sum(row["screen_changes"] for row in task_results) >= 1,
    }
    (args.output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_root / "model_calls.json").write_text(json.dumps(call_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"arm_id": ARM_ID, "qualified": summary["qualified"], "tasks": task_results}))


if __name__ == "__main__":
    main()
