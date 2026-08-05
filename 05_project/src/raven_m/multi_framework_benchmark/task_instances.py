"""Offline deterministic AndroidWorld task-instance manifest builder."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import random
import sys
from typing import Any


def _json_safe(value: Any) -> Any:
    try:
        from PIL import Image
        if isinstance(value, Image.Image):
            return {"__type__": "PIL.Image", "mode": value.mode,
                    "size": list(value.size),
                    "pixel_sha256": sha256(value.tobytes()).hexdigest()}
    except ImportError:
        pass
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"__type__": type(value).__name__, "repr": repr(value)}


def _digest(value: Any) -> str:
    payload = json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def goal_digest(goal: Any) -> str:
    """Hash the exact user-visible goal text used by AndroidWorld."""
    return sha256(str(goal).encode("utf-8")).hexdigest()


def load_frozen_instances(path: Path) -> list[dict[str, Any]]:
    """Load either a small ``tasks`` manifest or the Hard ``instances`` list."""
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("tasks", value.get("instances"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Frozen task manifest has no instances: {path}")
    return rows


def instantiate_verified(
    registered: dict[str, Any],
    spec: dict[str, Any],
) -> Any:
    """Instantiate one task and abort before generation on any instance drift.

    Small smoke manifests may carry JSON-native parameters directly.  Hard
    manifests carry hashes only, so each task independently resets both RNGs
    before calling the native AndroidWorld parameter generator.
    """
    import numpy as np

    task_class = str(spec["task_class"])
    seed = int(spec["task_seed"])
    task_type = registered[task_class]
    if "params" in spec:
        params = spec["params"]
    else:
        random.seed(seed)
        np.random.seed(seed)
        params = task_type.generate_random_params()
    instance = task_type(params)
    actual_params = _digest(instance.params)
    actual_goal = goal_digest(instance.goal)
    if actual_params != str(spec["task_params_hash"]):
        raise RuntimeError(
            f"Frozen params drift for {task_class}: "
            f"{actual_params} != {spec['task_params_hash']}"
        )
    if actual_goal != str(spec["goal_hash"]):
        raise RuntimeError(
            f"Frozen goal drift for {task_class}: "
            f"{actual_goal} != {spec['goal_hash']}"
        )
    return instance


def _order(arm_id: str, seed: int, task_ids: list[str]) -> list[str]:
    permutation = list(task_ids)
    order_seed = int(sha256(f"{arm_id}|{seed}".encode()).hexdigest(), 16)
    random.Random(order_seed).shuffle(permutation)
    return permutation


def build(repo_root: Path) -> dict[str, Any]:
    project = repo_root / "05_project"
    third_party = repo_root / "03_code" / "third_party" / "android_world"
    local_runtime = repo_root / "06_local_runtime" / "scripts"
    sys.path[:0] = [str(third_party), str(local_runtime)]
    try:
        import androidworld_compat  # type: ignore  # noqa: F401
    except ImportError:
        pass
    import numpy as np
    from android_world import registry

    hard = json.loads((project / "configs/task_manifests/androidworld_hard_v1.json").read_text(encoding="utf-8"))
    registered = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    seeds = [20260806, 20260807, 20260808]
    instances = []
    for seed in seeds:
        for task in hard["tasks"]:
            random.seed(seed)
            np.random.seed(seed)
            task_type = registered[task["class_name"]]
            instance = task_type(task_type.generate_random_params())
            instances.append({"task_id": task["id"], "task_class": task["class_name"], "task_seed": seed, "task_params_hash": _digest(instance.params), "goal_hash": sha256(str(instance.goal).encode("utf-8")).hexdigest(), "native_max_steps": task["native_max_steps"]})
    arm_ids = ["CB-PX-B3", "CB-PX-M0", "NS-PX-GO15", "NS-PX-MA35", "NS-PX-SCUA32", "NS-PX-UIV4", "CB-PX-B0", "CB-ST-M3A", "CB-PX-MU"]
    task_ids = [task["id"] for task in hard["tasks"]]
    orders = {str(seed): {arm: _order(arm, seed, task_ids) for arm in arm_ids} for seed in seeds}
    return {"manifest_id": "androidworld_hard_v2_instances", "protocol_id": "MULTI_FRAMEWORK_HARD_BENCHMARK_V0_2", "androidworld_commit": "3e50888527ef9f29b9157ecd537e408008bb1c85", "source_hard_manifest_sha256": "e651aedeb18f112be3a06562328618d19e9d33eaea94187b1edec51cb00f6ca7", "task_classes_and_budgets_unchanged": True, "instance_generation": "random.seed(seed); numpy.random.seed(seed); task_type.generate_random_params()", "instances": instances, "orders": orders}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    value = build(repo_root)
    destination = repo_root / "05_project/configs/task_manifests/androidworld_hard_v2_instances.json"
    destination.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
