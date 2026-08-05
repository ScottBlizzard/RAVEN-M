"""Frozen, non-executed static boundary gate for INFRA-M14.

This checker never opens an excluded implementation.  It relies only on
already-frozen path/module identifiers and whole-file SHA-256 values.  At M14
freeze time the future implementation is absent and this gate is NOT RUN.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FUTURE_IMPLEMENTATION = Path(
    "05_project/src/raven_m/role_binding_timing/"
    "infra_m14_authority_context_attestation.py"
)
SCAN_PATHS = (
    FUTURE_IMPLEMENTATION,
    Path(
        "05_project/tests/role_binding_timing/"
        "test_infra_m14_authority_context_contract.py"
    ),
    Path(
        "05_project/tests/role_binding_timing/"
        "test_infra_m14_context_bound_issuer_ledger_contract.py"
    ),
    Path("05_project/configs/role_binding_timing/infra_m14_opaque_authority_context.json"),
    Path("05_project/schemas/role_binding_timing_infra_m14_completion.v1.schema.json"),
    Path("04_protocols/role_binding_timing/INFRA_M14_OPAQUE_AUTHORITY_CONTEXT_V1.md"),
)

# Metadata only.  The excluded files are never resolved, statted, or opened.
EXCLUDED_IMPLEMENTATIONS = (
    {
        "path": (
            "05_project/src/raven_m/role_binding_timing/"
            "infra_m10_temporal_attestation.py"
        ),
        "module": "infra_m10_temporal_attestation",
        "sha256": "D5C0439A39ECD271625502E64F6EBD0BC018F262B9256F6095F44358F90C4BBA",
    },
    {
        "path": (
            "05_project/src/raven_m/role_binding_timing/"
            "infra_m13_proof_bound_attestation.py"
        ),
        "module": "infra_m13_proof_bound_attestation",
        "sha256": "8257123377AFBD9328F13CCA6B1C3C8749A9B8D72B3888CA022F63B4E7C7CA8F",
    },
)
FORBIDDEN_TEXT = tuple(
    sorted(
        {
            "infra_m11",
            "infra_m12_sealed_role_derivation",
            *(
                item
                for record in EXCLUDED_IMPLEMENTATIONS
                for item in (record["path"], record["module"], record["sha256"])
            ),
        }
    )
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _assert_inside_repo(path: Path) -> Path:
    resolved = (REPO_ROOT / path).resolve()
    resolved.relative_to(REPO_ROOT.resolve())
    return resolved


def _imports(text: str, path: Path) -> set[str]:
    if path.suffix != ".py":
        return set()
    tree = ast.parse(text, filename=path.as_posix())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _scan_candidate(relative: Path) -> dict:
    if relative.as_posix() in {record["path"] for record in EXCLUDED_IMPLEMENTATIONS}:
        raise RuntimeError(f"EXCLUDED_PATH_IN_SCAN_SET:{relative.as_posix()}")
    absolute = _assert_inside_repo(relative)
    if not absolute.exists():
        if relative == FUTURE_IMPLEMENTATION:
            return {"path": relative.as_posix(), "status": "EXPECTED_ABSENT"}
        raise RuntimeError(f"REQUIRED_M14_FILE_MISSING:{relative.as_posix()}")
    data = absolute.read_bytes()
    digest = _sha256(data)
    if digest in {record["sha256"] for record in EXCLUDED_IMPLEMENTATIONS}:
        raise RuntimeError(f"EXCLUDED_WHOLE_FILE_COPY:{relative.as_posix()}:{digest}")
    text = data.decode("utf-8", errors="strict")
    lowered = text.lower()
    hits = [needle for needle in FORBIDDEN_TEXT if needle.lower() in lowered]
    if hits:
        raise RuntimeError(
            f"FORBIDDEN_IDENTIFIER_OR_METADATA:{relative.as_posix()}:{hits}"
        )
    imported = sorted(_imports(text, relative))
    bad_imports = [
        name
        for name in imported
        if any(record["module"] in name for record in EXCLUDED_IMPLEMENTATIONS)
        or "infra_m11" in name
        or "infra_m12_sealed_role_derivation" in name
    ]
    if bad_imports:
        raise RuntimeError(f"FORBIDDEN_IMPORT:{relative.as_posix()}:{bad_imports}")
    return {
        "path": relative.as_posix(),
        "status": "SCANNED",
        "sha256": digest,
        "imports": imported,
    }


def main() -> int:
    results = [_scan_candidate(path) for path in SCAN_PATHS]
    print(
        json.dumps(
            {
                "schema_version": "role_binding_timing.infra_m14.static_gate.v1",
                "verdict": "PASS",
                "excluded_files_opened": False,
                "results": results,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
