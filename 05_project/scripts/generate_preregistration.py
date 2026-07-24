"""Hash every protocol-critical input before scored Hard evaluation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


FIXED_FILES = [
    ".gitattributes",
    "00_admin/requirements_trace.md",
    "04_protocols/experiment_protocol.md",
    "04_protocols/failure_codebook.md",
    "04_protocols/environment_lock.yaml",
    "01_sources/official/androidworld/task_list.html",
    "05_project/prompts/executor_v1.md",
    "05_project/prompts/executor_raven_v1.md",
    "05_project/prompts/summary_v1.md",
    "05_project/prompts/planner_v1.md",
    "05_project/prompts/critic_v1.md",
    "05_project/configs/experiments/seeds_v1.json",
    "05_project/configs/experiments/hard_schedule_v1.json",
    "05_project/configs/memory/raven_v1.yaml",
    "05_project/configs/task_manifests/androidworld_hard_v1.json",
    "05_project/configs/task_manifests/ablation8_v1.json",
    "05_project/configs/task_manifests/component_smoke_v1.json",
    "05_project/metadata/g4_audit.json",
    "05_project/metadata/g6_audit.json",
    "05_project/metadata/corruption_stress.json",
    "05_project/metadata/emulator_recovery_smoke_20260724.json",
    "05_project/metadata/component_smoke_audit.json",
    "05_project/metadata/protocol_audit.json",
    "05_project/metadata/reset_determinism_g4_final.json",
    "05_project/metadata/runtime_asset_manifest.json",
    "05_project/metadata/role_repair_smoke_20260724.json",
    "05_project/metadata/transport_recovery_smoke_20260724.json",
    "05_project/scripts/run_frozen_pipeline.ps1",
    "05_project/scripts/start_frozen_pipeline.ps1",
    "05_project/scripts/start_model_tunnel.ps1",
    "05_project/scripts/start_model_tunnel_watchdog.ps1",
    "05_project/scripts/stop_model_tunnel.ps1",
    "05_project/scripts/stop_model_tunnel_watchdog.ps1",
    "05_project/scripts/watch_model_tunnel.ps1",
    "05_project/scripts/apply_retrieval_audit_labels.py",
    "05_project/scripts/generate_preregistration.py",
    "06_local_runtime/scripts/androidworld_compat.py",
    "06_local_runtime/scripts/androidworld_smoke.py",
    "06_local_runtime/scripts/start_emulator.ps1",
    "06_local_runtime/scripts/stop_emulator.ps1",
]

FINAL_FILES = ["05_project/metadata/g7_audit.json"]

GLOB_GROUPS = [
    "05_project/configs/agents/*.yaml",
    "05_project/schemas/*.json",
    "05_project/src/raven_m/**/*.py",
    "05_project/scripts/run_*.py",
    "05_project/scripts/audit_*.py",
    "05_project/scripts/analyze_*.py",
    "05_project/scripts/sample_*.py",
    "05_project/scripts/generate_hard_schedule.py",
]


def selected_files(final: bool = False) -> list[Path]:
    items = [*FIXED_FILES, *(FINAL_FILES if final else [])]
    paths = {REPOSITORY_ROOT / item for item in items}
    for pattern in GLOB_GROUPS:
        paths.update(REPOSITORY_ROOT.glob(pattern))
    missing = [path for path in sorted(paths) if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing protocol-critical file(s): "
            + ", ".join(str(path) for path in missing)
        )
    return sorted(paths)


def record(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": sha256(payload).hexdigest(),
    }


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        [
            "git",
            "-c",
            "safe.directory=D:/ZJU/Summer_Camp/RAVEN-M-Research",
            *args,
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.final:
        gate_path = PROJECT_ROOT / "metadata" / "g7_audit.json"
        if not gate_path.is_file():
            raise SystemExit("G7 audit is absent; final freeze is forbidden.")
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("status") != "passed":
            raise SystemExit("G7 audit has not passed; final freeze is forbidden.")

    records = [record(path) for path in selected_files(final=args.final)]
    canonical_records = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    output = args.output or (
        PROJECT_ROOT
        / "metadata"
        / (
            "preregistration_v1.json"
            if args.final
            else "preregistration_v1.draft.json"
        )
    )
    payload = {
        "schema_version": "preregistration.v1",
        "status": "frozen" if args.final else "draft_pending_G7",
        "scored_hard_runs_permitted": bool(args.final),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head_before_freeze_commit": git_value("rev-parse", "HEAD"),
        "androidworld_commit": (
            "3e50888527ef9f29b9157ecd537e408008bb1c85"
        ),
        "model_revision": (
            "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
        ),
        "protocol_file_count": len(records),
        "protocol_records_sha256": sha256(canonical_records).hexdigest(),
        "files": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
