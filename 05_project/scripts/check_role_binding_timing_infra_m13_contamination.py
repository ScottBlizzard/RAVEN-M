#!/usr/bin/env python3
"""Frozen static contamination gate for the future INFRA-M13 namespace.

The gate reads only explicitly enumerated M13 candidates and its sanitized
input lock. It never opens an excluded implementation or boundary file.
This gate is frozen but deliberately NOT RUN in the M13 freeze-only phase.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_LOCK = Path(
    "05_project/configs/role_binding_timing/"
    "infra_m13_post_diagnosis_proof_binding_issuer_ledger.lock.json"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _imports(text: str, path: Path) -> list[str]:
    if path.suffix.lower() != ".py":
        return []
    tree = ast.parse(text, filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def _candidate_paths(root: Path, lock: dict[str, Any], lock_abs: Path) -> list[Path]:
    future = lock["future_namespace"]
    paths = [
        root / future["implementation"],
        root / future["canonical_view_tests"],
        root / future["issuer_ledger_tests"],
        root / lock["contract_bindings"]["protocol"]["path"],
        root / lock["contract_bindings"]["config"]["path"],
        root / "05_project/schemas/role_binding_timing_infra_m13_completion.v1.schema.json",
        lock_abs,
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def check(root: Path, lock_path: Path) -> dict[str, Any]:
    root = root.resolve()
    lock_abs = (root / lock_path).resolve() if not lock_path.is_absolute() else lock_path.resolve()
    lock_raw = lock_abs.read_bytes()
    lock = json.loads(lock_raw.decode("utf-8", errors="strict"))
    boundary = lock["contamination_boundary"]
    leak = boundary["excluded_untracked_leak"]
    prior = boundary["excluded_m11_v1"]
    audited = boundary["excluded_m12_runtime_reuse"]

    excluded_paths = {
        (root / leak["path"]).resolve(),
        (root / audited["path"]).resolve(),
    }
    forbidden_sha256 = {
        str(leak["known_sha256"]).upper(),
        str(audited["known_sha256"]).upper(),
    }
    forbidden_blob_oids = {str(audited["known_blob_oid"]).lower()}
    forbidden_tokens = {
        str(leak["path"]),
        str(leak["module_identifier"]),
        str(audited["path"]),
        str(audited["module_identifier"]),
        "infra" + "_m11",
        str(prior["commit"]),
        str(prior["tag"]),
        str(prior["tag_object_oid"]),
    }

    findings: list[dict[str, str]] = []
    scanned: list[dict[str, str]] = []
    for resolved in _candidate_paths(root, lock, lock_abs):
        rel = resolved.relative_to(root).as_posix()
        if resolved in excluded_paths:
            findings.append({"path": rel, "code": "EXCLUDED_PATH_SELECTED_BEFORE_READ"})
            continue
        if not resolved.exists():
            scanned.append({"path": rel, "status": "ABSENT"})
            continue
        raw = resolved.read_bytes()
        digest = _sha256(raw)
        blob_oid = _git_blob_oid(raw)
        if digest in forbidden_sha256:
            findings.append({"path": rel, "code": "EXACT_EXCLUDED_SHA256_COPY"})
        if blob_oid in forbidden_blob_oids:
            findings.append({"path": rel, "code": "EXACT_EXCLUDED_BLOB_COPY"})

        try:
            if resolved == lock_abs:
                sanitized = copy.deepcopy(lock)
                sanitized.pop("contamination_boundary", None)
                sanitized.get("legitimate_inputs", {}).pop("m12_locked_implementation_audit", None)
                text = json.dumps(
                    sanitized,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            else:
                text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            findings.append({"path": rel, "code": "NON_UTF8_M13_CANDIDATE"})
            scanned.append({"path": rel, "status": "READ", "sha256": digest, "blob_oid": blob_oid})
            continue

        for token in sorted(forbidden_tokens):
            if token and token in text:
                findings.append({"path": rel, "code": "FORBIDDEN_IDENTIFIER", "identifier": token})
        try:
            imports = _imports(text, resolved)
        except SyntaxError:
            findings.append({"path": rel, "code": "IMPORT_GRAPH_PARSE_FAILURE"})
            imports = []
        for imported in imports:
            if any(token and token in imported for token in forbidden_tokens):
                findings.append(
                    {"path": rel, "code": "FORBIDDEN_IMPORT_EDGE", "identifier": imported}
                )
        scanned.append({"path": rel, "status": "READ", "sha256": digest, "blob_oid": blob_oid})

    return {
        "schema": "role_binding_timing.infra_m13.contamination_gate.v1",
        "passed": not findings,
        "executed_phase_expected": "AFTER_SEPARATE_IMPLEMENTATION_LOCK_ONLY",
        "excluded_paths_opened": False,
        "scan_scope": "Explicit M13 implementation/tests/protocol/config/schema and sanitized lock only",
        "scanned": scanned,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()
    result = check(args.root, args.lock)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
