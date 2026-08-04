"""Collect and freeze zero-model real traces without running the v0.2.3 oracle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world.env import adb_utils  # noqa: E402
from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022  # noqa: E402
from raven_m.eest_ac.outcome_oracle_v0_2_3 import canonical_json, value_sha256  # noqa: E402
from raven_m.eest_ac.runtime_v0_2_2 import assert_frozen_adb_server_port, load_and_setup_env  # noqa: E402
from raven_m.eest_ac.trace_harness_v0_2_3 import capture_post_sequence, capture_snapshot  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _adb(adb_path: str, port: int, serial: str, *args: str, timeout: int = 30) -> str:
    result = subprocess.run(
        [adb_path, "-P", str(port), "-s", serial, *args],
        capture_output=True, text=True, check=False, timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"ADB command failed: {args!r}")
    return result.stdout.strip()


def _execute_canonical(env: Any, adapter: EestActionAdapterV022, action: dict[str, Any]) -> dict[str, Any]:
    state = env.get_state(wait_to_stabilize=True)
    height, width = state.pixels.shape[:2]
    mapped = adapter.map_action(action, screen_width=int(width), screen_height=int(height))
    adapter.execute(env, mapped)
    return mapped.audit_record()


def _setup_action(
    *, env: Any, adapter: EestActionAdapterV022, action: dict[str, Any],
    base_url: str, adb_path: str, port: int, serial: str,
) -> dict[str, Any]:
    kind = action["kind"]
    if kind == "canonical":
        audit = _execute_canonical(env, adapter, action["action"])
    elif kind == "open_url":
        url = base_url + action["path"]
        output = _adb(
            adb_path, port, serial, "shell", "am", "start", "-W", "-a",
            "android.intent.action.VIEW", "-d", url, "-p", action["package"], timeout=40,
        )
        audit = {"kind": kind, "url": url, "package": action["package"], "adb_output_sha256": sha256(output.encode()).hexdigest()}
    elif kind == "sleep":
        time.sleep(float(action["seconds"]))
        audit = {"kind": kind, "seconds": float(action["seconds"])}
    else:
        raise RuntimeError(f"Unsupported setup action kind: {kind}")
    time.sleep(float(action.get("settle_seconds", 2.0)))
    return audit


def _resolver(app_name: str | None) -> dict[str, Any] | None:
    if app_name is None:
        return None
    activity = adb_utils.get_adb_activity(app_name)
    if not activity:
        package = app_name
        activities: list[str] = []
    else:
        package = adb_utils.extract_package_name(activity)
        activities = []
    source = {"resolver": "android_world.adb_utils.get_adb_activity", "app_name": app_name, "activity": activity}
    return {
        "target_packages": [package],
        "target_activities": activities,
        "provenance_sha256": value_sha256(source),
    }


def _apply_mutations(trace: dict[str, Any], mutations: list[str]) -> dict[str, Any]:
    value = json.loads(canonical_json(trace))
    for mutation in mutations:
        if mutation == "drop_terminal_a11y":
            for sample in value["post"][-2:]:
                sample["a11y_available"] = False
                sample["a11y_sha256"] = None
                sample["page_content_sha256"] = None
        elif mutation == "drop_resolver":
            value["resolver"] = None
        else:
            raise RuntimeError(f"Unknown frozen input mutation: {mutation}")
    return value


def _extract_pixel_hashes(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"pixel_sha256", "pixel_bytes_sha256"} and isinstance(item, str):
                result.add(item)
            result.update(_extract_pixel_hashes(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_extract_pixel_hashes(item))
    return result


def _terminal_stable(trace: dict[str, Any]) -> bool:
    left, right = trace["post"][-2:]
    fields = ("package_names", "activity", "route_signature", "a11y_available", "a11y_sha256", "page_content_sha256")
    return left["a11y_available"] and all(left[field] == right[field] for field in fields)


def _qualify_ground_truth(trace: dict[str, Any], scenario: dict[str, Any]) -> tuple[bool, list[str]]:
    expected = scenario["expected_decision"]
    control = scenario["ground_truth_control"]
    pre, terminal = trace["pre"], trace["post"][-1]
    stable = _terminal_stable(trace)
    checks = [f"terminal_semantics_stable={stable}"]
    passed = True
    if expected == "accept":
        passed = stable
        if scenario["action_class"] == "scroll":
            passed = passed and pre["route_signature"] == terminal["route_signature"] and pre["page_content_sha256"] != terminal["page_content_sha256"]
        elif scenario["action_class"] == "open_app":
            resolver = trace["resolver"] or {}
            passed = passed and bool(set(resolver.get("target_packages", [])) & set(terminal["package_names"]))
        else:
            passed = passed and (pre["route_signature"] != terminal["route_signature"] or pre["page_content_sha256"] != terminal["page_content_sha256"])
    elif control == "stable_noop":
        passed = stable and pre["route_signature"] == terminal["route_signature"] and pre["page_content_sha256"] == terminal["page_content_sha256"]
    elif control == "dynamic_pixel_only":
        passed = stable and pre["route_signature"] == terminal["route_signature"] and pre["page_content_sha256"] == terminal["page_content_sha256"] and trace["post"][-2]["pixel_sha256"] != terminal["pixel_sha256"]
    elif control == "wrong_target":
        resolver = trace["resolver"] or {}
        passed = stable and not bool(set(resolver.get("target_packages", [])) & set(terminal["package_names"]))
    elif control == "missing_a11y":
        mutated = _apply_mutations(trace, scenario["input_mutations"])
        passed = all(not item["a11y_available"] for item in mutated["post"][-2:])
    elif control == "missing_resolver":
        passed = _apply_mutations(trace, scenario["input_mutations"])["resolver"] is None
    else:
        passed = False
    checks.append(f"ground_truth_control={control}")
    return passed, checks


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--adb-server-port", type=int, required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    assert_frozen_adb_server_port(configured=5038, supplied=args.adb_server_port)
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise RuntimeError("Trace collection output root must be empty.")
    args.output_root.mkdir(parents=True, exist_ok=True)
    serial = config["runtime"]["device_serial"]
    web_root = (PROJECT_ROOT / config["web_server"]["root"]).resolve()
    handler = lambda *items, **kwargs: QuietHandler(*items, directory=str(web_root), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", config["web_server"]["host_port"]), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _adb(args.adb_path, args.adb_server_port, serial, "reverse", f"tcp:{config['web_server']['device_port']}", f"tcp:{config['web_server']['host_port']}")
    base_url = f"http://127.0.0.1:{config['web_server']['device_port']}"
    adapter = EestActionAdapterV022()
    env = load_and_setup_env(
        console_port=args.console_port, emulator_setup=False, freeze_datetime=True,
        adb_path=args.adb_path, adb_server_port=args.adb_server_port, grpc_port=args.grpc_port,
    )
    inputs = []
    labels = []
    records = []
    collection_failed = False
    try:
        for index, scenario in enumerate(config["scenarios"], 1):
            random.seed(scenario["seed"])
            trace_dir = args.output_root / "traces" / f"{index:02d}_{scenario['trace_id']}"
            raw_dir = trace_dir / "raw"
            setup_audit = []
            setup_audit.append(_execute_canonical(env, adapter, {"type": "press_home"}))
            time.sleep(2.0)
            for action in scenario["setup_actions"]:
                setup_audit.append(_setup_action(
                    env=env, adapter=adapter, action=action, base_url=base_url,
                    adb_path=args.adb_path, port=args.adb_server_port, serial=serial,
                ))
            before = capture_snapshot(
                env=env, output_dir=raw_dir, sample_id="pre",
                adb_path=args.adb_path, adb_server_port=args.adb_server_port, serial=serial,
            )
            execution = _execute_canonical(env, adapter, scenario["test_action"])
            posts = capture_post_sequence(
                env=env, output_dir=raw_dir, count=config["sampling"]["post_observations"],
                delay_seconds=config["sampling"]["delay_seconds"], adb_path=args.adb_path,
                adb_server_port=args.adb_server_port, serial=serial,
            )
            trace = {
                "trace_id": scenario["trace_id"],
                "action_class": scenario["action_class"],
                "action": scenario["test_action"],
                "resolver": _resolver(scenario.get("resolver_app_name")),
                "pre": before.oracle_observation,
                "post": [item.oracle_observation for item in posts],
            }
            qualified, qualification_checks = _qualify_ground_truth(trace, scenario)
            mutated = _apply_mutations(trace, scenario.get("input_mutations", []))
            _write(trace_dir / "oracle_input.json", mutated)
            raw_record = {
                "trace_id": scenario["trace_id"],
                "setup_audit": setup_audit,
                "execution": execution,
                "pre": before.raw_record,
                "post": [item.raw_record for item in posts],
                "unmutated_trace_sha256": value_sha256(trace),
                "oracle_input_sha256": value_sha256(mutated),
                "input_mutations": scenario.get("input_mutations", []),
                "ground_truth_qualification_pass": qualified,
                "ground_truth_qualification_checks": qualification_checks,
            }
            _write(trace_dir / "collection_record.json", raw_record)
            inputs.append(mutated)
            labels.append({
                "trace_id": scenario["trace_id"],
                "action_class": scenario["action_class"],
                "expected_decision": scenario["expected_decision"],
                "ground_truth_control": scenario["ground_truth_control"],
                "seed": scenario["seed"],
                "order": index,
                "oracle_input_sha256": value_sha256(mutated),
            })
            records.append({
                "trace_id": scenario["trace_id"],
                "qualified": qualified,
                "oracle_input_sha256": value_sha256(mutated),
                "collection_record_sha256": _hash(trace_dir / "collection_record.json"),
            })
            collection_failed = collection_failed or not qualified
            _execute_canonical(env, adapter, {"type": "press_home"})
            time.sleep(1.0)
    finally:
        env.close()
        server.shutdown()
        server.server_close()
        _adb(args.adb_path, args.adb_server_port, serial, "reverse", "--remove", f"tcp:{config['web_server']['device_port']}")
    input_path = args.output_root / "oracle_inputs.jsonl"
    input_path.write_text("".join(canonical_json(item) + "\n" for item in inputs), encoding="utf-8")
    _write(args.output_root / "labels_private.json", {"labels": labels})
    forbidden_pixels: set[str] = set()
    for relative in config.get("forbidden_contaminated_json", []):
        path = REPOSITORY_ROOT / relative
        forbidden_pixels.update(_extract_pixel_hashes(json.loads(path.read_text(encoding="utf-8"))))
    heldout_pixels = _extract_pixel_hashes(inputs)
    overlap = sorted(forbidden_pixels & heldout_pixels)
    if config["mode"] == "heldout_collection" and overlap:
        collection_failed = True
    counts = {
        action_class: {
            decision: sum(label["action_class"] == action_class and label["expected_decision"] == decision for label in labels)
            for decision in ("accept", "reject", "uncertain")
        }
        for action_class in ("scroll", "open_app", "navigation_press")
    }
    if config["mode"] == "heldout_collection":
        collection_failed = collection_failed or len(labels) < 12 or any(
            values["accept"] < 2 or values["reject"] + values["uncertain"] < 2
            for values in counts.values()
        )
    files = []
    for path in sorted(item for item in args.output_root.rglob("*") if item.is_file() and item.name != "hash_manifest.json"):
        files.append({"path": str(path.relative_to(args.output_root)).replace("\\", "/"), "sha256": _hash(path), "bytes": path.stat().st_size})
    _write(args.output_root / "hash_manifest.json", {"files": files})
    completion = {
        "schema_version": "eest_ac_trace_collection.v0_2_3",
        "corpus_id": config["corpus_id"],
        "mode": config["mode"],
        "status": "fail" if collection_failed else "pass",
        "completed_at_utc": _utc_now(),
        "zero_model_generation_calls": 0,
        "oracle_evaluations": 0,
        "trace_count": len(labels),
        "class_decision_counts": counts,
        "ground_truth_records": records,
        "contaminated_pixel_overlap": overlap,
        "inputs_sha256": _hash(input_path),
        "labels_sha256": _hash(args.output_root / "labels_private.json"),
        "hash_manifest_sha256": _hash(args.output_root / "hash_manifest.json"),
    }
    _write(args.output_root / "collection_complete.json", completion)
    print(json.dumps({
        "status": completion["status"], "mode": config["mode"], "traces": len(labels),
        "oracle_evaluations": 0, "output_root": str(args.output_root),
    }, indent=2))
    if collection_failed:
        raise RuntimeError("Trace collection qualification failed; oracle evaluation forbidden.")


if __name__ == "__main__":
    main()
