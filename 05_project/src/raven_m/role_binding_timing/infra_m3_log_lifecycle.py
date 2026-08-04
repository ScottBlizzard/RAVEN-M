"""Task-agnostic live-log ownership and sealing invariants for INFRA-M3."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Iterable


Rename = Callable[[str | os.PathLike[str], str | os.PathLike[str]], None]


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def live_root_issues(
    candidate: Path,
    *,
    repository_root: Path,
    forbidden_roots: Iterable[Path],
    required_parent: Path,
) -> list[str]:
    """Return stable fail-closed reasons for an unsafe live-log root."""
    candidate = candidate.resolve()
    repository_root = repository_root.resolve()
    required_parent = required_parent.resolve()
    issues: list[str] = []
    if not candidate.is_absolute():
        issues.append("LIVE_ROOT_NOT_ABSOLUTE")
    if _within(candidate, repository_root):
        issues.append("LIVE_ROOT_INSIDE_REPOSITORY")
    for root in forbidden_roots:
        if _within(candidate, root.resolve()):
            issues.append(f"LIVE_ROOT_INSIDE_FORBIDDEN:{root.resolve()}")
    if not _within(candidate, required_parent):
        issues.append("LIVE_ROOT_OUTSIDE_REQUIRED_TEMP_PARENT")
    return sorted(set(issues))


def create_live_root(
    *,
    temp_parent: Path,
    repository_root: Path,
    forbidden_roots: Iterable[Path],
    prefix: str,
) -> Path:
    """Create one fresh OS-temporary root after validating its parent boundary."""
    parent = temp_parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve()
    issues = live_root_issues(
        candidate,
        repository_root=repository_root,
        forbidden_roots=forbidden_roots,
        required_parent=parent,
    )
    if issues:
        shutil.rmtree(candidate, ignore_errors=True)
        raise RuntimeError(f"UNSAFE_LIVE_LOG_ROOT:{issues}")
    return candidate


def prove_handle_closed(path: Path, *, rename: Rename = os.replace) -> dict[str, Any]:
    """Use a same-directory rename round trip as the frozen Windows handle proof."""
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"LIVE_LOG_MISSING:{path}")
    probe = path.with_name(f"{path.name}.handle_probe")
    if probe.exists():
        raise RuntimeError(f"HANDLE_PROBE_RESIDUE:{probe}")
    try:
        rename(path, probe)
        rename(probe, path)
    except Exception as exc:
        if probe.exists() and not path.exists():
            try:
                rename(probe, path)
            except Exception:
                pass
        raise RuntimeError(f"LIVE_LOG_HANDLE_NOT_CLOSED:{path.name}:{type(exc).__name__}:{exc}") from exc
    return {"path": str(path), "rename_round_trip": True}


def seal_live_logs(
    *,
    live_root: Path,
    result_root: Path,
    names: Iterable[str],
    repository_root: Path,
    forbidden_roots: Iterable[Path],
    required_temp_parent: Path,
    owners_gone: bool,
    parent_handles_closed: bool,
    rename: Rename = os.replace,
) -> list[dict[str, Any]]:
    """Seal each closed live log exactly once into a new result directory."""
    live_root = live_root.resolve()
    result_root = result_root.resolve()
    issues = live_root_issues(
        live_root,
        repository_root=repository_root,
        forbidden_roots=forbidden_roots,
        required_parent=required_temp_parent,
    )
    if issues:
        raise RuntimeError(f"UNSAFE_LIVE_LOG_ROOT:{issues}")
    if not owners_gone:
        raise RuntimeError("LIVE_LOG_OWNER_STILL_RUNNING")
    if not parent_handles_closed:
        raise RuntimeError("PARENT_LOG_HANDLES_NOT_CLOSED")
    if _within(result_root, live_root):
        raise RuntimeError("RESULT_ROOT_INSIDE_LIVE_ROOT")
    if result_root.exists():
        raise RuntimeError(f"SEALED_RESULT_ALREADY_EXISTS:{result_root}")

    ordered_names = tuple(names)
    if not ordered_names or len(set(ordered_names)) != len(ordered_names):
        raise RuntimeError("INVALID_LIVE_LOG_NAME_SET")
    for name in ordered_names:
        if Path(name).name != name:
            raise RuntimeError(f"NON_BASENAME_LIVE_LOG:{name}")
        prove_handle_closed(live_root / name, rename=rename)

    result_root.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    for name in ordered_names:
        source = live_root / name
        destination = result_root / name
        payload = source.read_bytes()
        destination.write_bytes(payload)
        if destination.read_bytes() != payload:
            raise RuntimeError(f"SEALED_LOG_COPY_MISMATCH:{name}")
        records.append(
            {
                "name": name,
                "source_outside_repository": True,
                "destination": destination.relative_to(repository_root).as_posix(),
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "handle_closed_before_copy": True,
                "sealed_once": True,
            }
        )
    return records
