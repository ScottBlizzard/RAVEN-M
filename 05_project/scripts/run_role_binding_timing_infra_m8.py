"""Run the frozen INFRA-M8 full-snapshot ancestry qualification chain."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json  # noqa: E402
from raven_m.role_binding_timing.infra_m8_full_snapshot_ancestry import M8ProcessIdentityMonitor  # noqa: E402


def load_m7() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m7.py"
    spec = importlib.util.spec_from_file_location("frozen_infra_m7_runner_for_m8", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M7_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


M7 = load_m7()


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        result[key] = merge_dict(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def resolve_overlay(path: Path) -> dict[str, Any]:
    overlay = json.loads(path.read_text(encoding="utf-8"))
    if overlay.get("schema_version") != "role_binding_timing.infra_m8.config_overlay.v1":
        raise RuntimeError("M8_CONFIG_SCHEMA")
    base_path = (REPOSITORY_ROOT / overlay["base_config"]).resolve()
    observed = sha256(base_path.read_bytes()).hexdigest()
    if observed != overlay["base_config_sha256"]:
        raise RuntimeError(f"M7_BASE_CONFIG_DRIFT:{observed}:{overlay['base_config_sha256']}")
    resolved = merge_dict(M7.resolve_overlay(base_path), overlay["overrides"])
    if resolved["generation_calls_authorized"] != 0 or resolved["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    if resolved["runtime"]["adb_server_port"] != 5038 or resolved["runtime"]["fallback_to_5037"] is not False:
        raise RuntimeError("ADB_PORT_BOUNDARY")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); args = parser.parse_args()
    resolved = resolve_overlay((REPOSITORY_ROOT / args.config).resolve())
    temp_root = Path(tempfile.mkdtemp(prefix="infra_m8_resolved_config_")); resolved_path = temp_root / "resolved_config.json"
    atomic_write_json(resolved_path, resolved, replace=False); original_argv = list(sys.argv)
    try:
        M7.M6.M6ProcessIdentityMonitor = M8ProcessIdentityMonitor
        sys.argv = [original_argv[0], "--config", str(resolved_path)]
        return M7.M6.main()
    finally:
        sys.argv = original_argv
        if resolved_path.exists(): resolved_path.unlink()
        temp_root.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
