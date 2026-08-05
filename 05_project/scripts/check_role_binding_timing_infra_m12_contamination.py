#!/usr/bin/env python3
"""Static contamination gate for the INFRA-M12 namespace.

The gate reads the M12 lock and M12 source/test/config candidates only. It
never opens any excluded path. Exact-copy checks use the known digest or Git
blob OID stored in lock metadata.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_LOCK = Path(
    "05_project/configs/role_binding_timing/"
    "infra_m12_dev_engineering_role_derivation_attestation.lock.json"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _git_blob_oid(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _candidate_paths(root: Path) -> Iterable[Path]:
    patterns = (
        "05_project/src/raven_m/role_binding_timing/*infra_m12*.py",
        "05_project/tests/role_binding_timing/*infra_m12*.py",
        "05_project/configs/role_binding_timing/infra_m12*.json",
    )
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            resolved = path.resolve()
            if path.is_file() and resolved not in seen:
                seen.add(resolved)
                yield path


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


def check(root: Path, lock_path: Path) -> dict[str, Any]:
    root = root.resolve()
    lock_abs = (root / lock_path).resolve() if not lock_path.is_absolute() else lock_path.resolve()
    lock_raw = lock_abs.read_bytes()
    lock = json.loads(lock_raw.decode("utf-8", errors="strict"))
    boundary = lock["contamination_boundary"]
    leak = boundary["excluded_untracked_leak"]
    excluded_v1 = boundary["excluded_m11_v1"]["forbidden_reuse"]

    excluded_paths = {(root / leak["path"]).resolve()}
    excluded_paths.update((root / item["path"]).resolve() for item in excluded_v1)
    forbidden_sha256 = {str(leak["known_sha256"]).upper()}
    forbidden_blob_oids = {str(item["blob_oid"]).lower() for item in excluded_v1}
    forbidden_tokens = {
        str(leak["path"]),
        str(leak["filename"]),
        str(leak["module_identifier"]),
        str(leak["known_sha256"]),
        str(leak["known_sha256"]).lower(),
    }
    for item in excluded_v1:
        path = Path(item["path"])
        forbidden_tokens.update(
            {
                item["path"],
                path.name,
                path.stem,
                item["blob_oid"],
            }
        )

    findings: list[dict[str, str]] = []
    scanned: list[dict[str, str]] = []
    for path in _candidate_paths(root):
        resolved = path.resolve()
        rel = resolved.relative_to(root).as_posix()
        if resolved in excluded_paths:
            findings.append({"path": rel, "code": "EXCLUDED_PATH_SELECTED_BEFORE_READ"})
            continue

        raw = path.read_bytes()
        digest = _sha256(raw)
        blob_oid = _git_blob_oid(raw)
        if digest in forbidden_sha256:
            findings.append({"path": rel, "code": "EXACT_EXCLUDED_LEAK_HASH_COPY"})
        if blob_oid in forbidden_blob_oids:
            findings.append({"path": rel, "code": "EXACT_EXCLUDED_V1_BLOB_COPY"})

        try:
            if resolved == lock_abs:
                sanitized = copy.deepcopy(lock)
                sanitized.pop("contamination_boundary", None)
                text = json.dumps(
                    sanitized,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            else:
                text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            findings.append({"path": rel, "code": "NON_UTF8_M12_SOURCE_TEST_OR_CONFIG"})
            scanned.append({"path": rel, "sha256": digest, "blob_oid": blob_oid})
            continue

        for token in sorted(forbidden_tokens):
            if token and token in text:
                findings.append({"path": rel, "code": "FORBIDDEN_IDENTIFIER", "identifier": token})
        try:
            imports = _imports(text, path)
        except SyntaxError:
            findings.append({"path": rel, "code": "IMPORT_GRAPH_PARSE_FAILURE"})
            imports = []
        for imported in imports:
            if any(token and token in imported for token in forbidden_tokens):
                findings.append(
                    {"path": rel, "code": "FORBIDDEN_IMPORT_EDGE", "identifier": imported}
                )
        scanned.append({"path": rel, "sha256": digest, "blob_oid": blob_oid})

    return {
        "schema": "role_binding_timing.infra_m12.contamination_gate.v1",
        "passed": not findings,
        "excluded_paths_opened": False,
        "scan_scope": "M12 source, tests, configs, exact-copy hashes, and Python import graph",
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
