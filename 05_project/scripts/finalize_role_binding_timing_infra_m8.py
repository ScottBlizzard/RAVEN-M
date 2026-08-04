"""Independent terminal finalizer and manifest writer for INFRA-M8."""

from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]; REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from raven_m.role_binding_timing.infra_m4_terminal_accounting import PhaseJournal, atomic_write_json  # noqa: E402
from raven_m.role_binding_timing.infra_m8_terminal import finalize_completion  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output-root", required=True); parser.add_argument("--schema", required=True)
    parser.add_argument("--run-id", required=True); parser.add_argument("--status", required=True); args = parser.parse_args()
    root = Path(args.output_root).resolve(); journal = PhaseJournal(root / "phase_journal")
    rich_path = root / "terminal_input.json"; rich = json.loads(rich_path.read_text(encoding="utf-8")) if rich_path.is_file() else None
    final = finalize_completion(output_root=root, journal=journal, run_id=args.run_id, status=args.status, rich_completion=rich)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8")); errors = [item.message for item in Draft202012Validator(schema).iter_errors(final)]
    atomic_write_json(root / "terminal_validation.json", {"schema_version": "role_binding_timing.infra_m8.terminal_validation.v1",
        "passed": not errors, "errors": errors, "terminal_mode": final["terminal_mode"], "first_broken_edge": final.get("first_broken_edge")}, replace=False)
    manifest_path = root / "artifact_manifest.json"; artifacts = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != manifest_path:
            payload = path.read_bytes(); artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(payload), "sha256": sha256(payload).hexdigest()})
    atomic_write_json(manifest_path, {"schema_version": "role_binding_timing.infra_m8.manifest.v1", "artifacts": artifacts}, replace=False)
    print(json.dumps({"status": final["status"], "terminal_mode": final["terminal_mode"], "first_broken_edge": final.get("first_broken_edge"), "schema_errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__": raise SystemExit(main())
