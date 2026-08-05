#!/usr/bin/env python3
"""Static M11 contamination boundary checker.

This checker reads the frozen lock and M11 candidate files only. It must never
open the excluded leaked path. The excluded path, identifiers, and known hash
come exclusively from lock metadata.
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
    "infra_m11_prereg_first_temporal_support_attestation_recovery.lock.json"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _candidate_paths(root: Path) -> Iterable[Path]:
    patterns = (
        "05_project/src/raven_m/role_binding_timing/infra_m11*.py",
        "05_project/tests/role_binding_timing/test_infra_m11*.py",
        "05_project/configs/role_binding_timing/infra_m11*.json",
    )
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            resolved = path.resolve()
            if path.is_file() and resolved not in seen:
                seen.add(resolved)
                yield path


def _import_names(text: str, path: Path) -> list[str]:
    if path.suffix.lower() != ".py":
        return []
    tree = ast.parse(text, filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def check(root: Path, lock_path: Path) -> dict[str, Any]:
    root = root.resolve()
    resolved_lock = (root / lock_path).resolve() if not lock_path.is_absolute() else lock_path.resolve()
    lock_bytes = resolved_lock.read_bytes()
    lock = json.loads(lock_bytes.decode("utf-8", errors="strict"))
    leaks = lock["contamination_boundary"]["known_leaks"]

    forbidden_paths = {(root / leak["path"]).resolve() for leak in leaks}
    forbidden_hashes = {str(leak["known_sha256"]).upper() for leak in leaks}
    forbidden_tokens: set[str] = set()
    for leak in leaks:
        forbidden_tokens.update(
            {
                str(leak["path"]),
                str(leak["filename"]),
                str(leak["module_identifier"]),
                str(leak["known_sha256"]),
                str(leak["known_sha256"]).lower(),
            }
        )

    findings: list[dict[str, str]] = []
    scanned: list[dict[str, str]] = []
    for path in _candidate_paths(root):
        resolved = path.resolve()
        rel = path.resolve().relative_to(root).as_posix()
        if resolved in forbidden_paths:
            findings.append({"path": rel, "code": "EXCLUDED_PATH_SELECTED_BEFORE_READ"})
            continue

        raw = path.read_bytes()
        digest = _sha256(raw)
        if digest in forbidden_hashes:
            findings.append({"path": rel, "code": "EXACT_LEAK_CONTENT_HASH_COPY"})

        if resolved == resolved_lock:
            sanitized = copy.deepcopy(lock)
            sanitized.pop("contamination_boundary", None)
            text = _canonical_json_bytes(sanitized).decode("utf-8")
        else:
            try:
                text = raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                findings.append({"path": rel, "code": "NON_UTF8_M11_SOURCE_OR_CONFIG"})
                scanned.append({"path": rel, "sha256": digest})
                continue

        for token in sorted(forbidden_tokens):
            if token and token in text:
                findings.append({"path": rel, "code": "FORBIDDEN_IDENTIFIER", "identifier": token})

        try:
            imports = _import_names(text, path)
        except SyntaxError:
            findings.append({"path": rel, "code": "IMPORT_GRAPH_PARSE_FAILURE"})
            imports = []
        for imported in imports:
            if any(token and token in imported for token in forbidden_tokens):
                findings.append(
                    {"path": rel, "code": "FORBIDDEN_IMPORT_EDGE", "identifier": imported}
                )

        scanned.append({"path": rel, "sha256": digest})

    return {
        "schema": "role_binding_timing.infra_m11.contamination_gate.v1",
        "passed": not findings,
        "leaked_path_opened": False,
        "scan_scope": "M11 source, tests, configs, and Python import graph",
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
