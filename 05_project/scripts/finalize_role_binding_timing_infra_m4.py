"""Independent terminal finalizer for INFRA-M4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m4_terminal_accounting import (  # noqa: E402
    PhaseJournal,
    atomic_write_json,
    finalize_completion,
)


def load_optional(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest(output_root: Path) -> dict[str, Any]:
    from hashlib import sha256

    manifest_path = output_root / "artifact_manifest.json"
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path != manifest_path:
            payload = path.read_bytes()
            try:
                manifest_name = path.relative_to(REPOSITORY_ROOT).as_posix()
            except ValueError:
                manifest_name = path.relative_to(output_root).as_posix()
            artifacts.append(
                {
                    "path": manifest_name,
                    "bytes": len(payload),
                    "sha256": sha256(payload).hexdigest(),
                }
            )
    value = {"schema_version": "role_binding_timing.infra_m4.manifest.v1", "artifacts": artifacts}
    atomic_write_json(manifest_path, value, replace=False)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--inject-rich-serialization-failure", action="store_true")
    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    journal = PhaseJournal(output_root / "phase_journal")
    rich = load_optional(output_root / "terminal_input.json")
    final = finalize_completion(
        output_root=output_root,
        journal=journal,
        status=args.status,
        run_id=args.run_id,
        rich_completion=rich,
        inject_rich_serialization_failure=args.inject_rich_serialization_failure,
    )
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    errors = [item.message for item in Draft202012Validator(schema).iter_errors(final)]
    atomic_write_json(
        output_root / "terminal_validation.json",
        {
            "schema_version": "role_binding_timing.infra_m4.terminal_validation.v1",
            "passed": not errors,
            "errors": errors,
            "terminal_mode": final["terminal_mode"],
            "first_broken_edge": final.get("first_broken_edge"),
        },
        replace=False,
    )
    build_manifest(output_root)
    print(json.dumps({"status": final["status"], "terminal_mode": final["terminal_mode"], "first_broken_edge": final.get("first_broken_edge"), "schema_errors": errors}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
