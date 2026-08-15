#!/usr/bin/env python3
"""Qualify a SYS-TRRC server without a generation request."""
from __future__ import annotations
import argparse, json, sys
from hashlib import sha256
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"implementation/src"))
from raven_m.official_qwen_mobile import sys_trrc_contract as contract  # noqa:E402

SUPPLEMENTAL_MODEL_FILES = (".gitattributes", "README.md", "merges.txt")


def _hash_file(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_model_manifest(model_root: Path, manifest: Path) -> dict:
    model_root = model_root.resolve()
    if not model_root.is_dir():
        raise RuntimeError("model root missing")
    rows = []
    manifest_paths = set()
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, relative = raw.split(maxsplit=1)
        relative = relative.strip().lstrip("*")
        if (
            not relative
            or Path(relative).is_absolute()
            or Path(relative).as_posix() != relative
        ):
            raise RuntimeError("model manifest path syntax")
        target = (model_root / relative).resolve()
        try:
            target.relative_to(model_root.resolve())
        except ValueError as exc:
            raise RuntimeError("model manifest path escape") from exc
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RuntimeError("model manifest digest syntax")
        if not target.is_file():
            raise RuntimeError(f"model manifest file missing: {relative}")
        if relative in manifest_paths:
            raise RuntimeError("model manifest duplicate path")
        manifest_paths.add(relative)
        stat = target.stat()
        rows.append({"path": relative, "sha256": digest,
                     "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    if not rows:
        raise RuntimeError("model manifest closure")
    observed_paths = {
        path.relative_to(model_root).as_posix()
        for path in model_root.rglob("*") if path.is_file()
    }
    supplemental_paths = set(SUPPLEMENTAL_MODEL_FILES)
    if observed_paths != manifest_paths | supplemental_paths:
        raise RuntimeError(
            "model manifest directory closure: "
            f"missing={sorted(manifest_paths - observed_paths)}, "
            f"unexpected={sorted(observed_paths - manifest_paths - supplemental_paths)}, "
            f"supplemental_missing={sorted(supplemental_paths - observed_paths)}"
        )
    rows.sort(key=lambda row: row["path"])
    supplemental_rows = []
    for relative in sorted(supplemental_paths):
        target = model_root / relative
        stat = target.stat()
        supplemental_rows.append({
            "path": relative, "sha256": _hash_file(target),
            "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        })
    manifest_sha = contract.file_sha256(manifest)
    for row in rows:
        target = model_root / row["path"]
        if _hash_file(target) != row["sha256"]:
            raise RuntimeError(f"model content drift: {row['path']}")
        final_stat = target.stat()
        if (
            final_stat.st_size != row["size"]
            or final_stat.st_mtime_ns != row["mtime_ns"]
        ):
            raise RuntimeError(f"model file changed during qualification: {row['path']}")
    final_observed_paths = {
        path.relative_to(model_root).as_posix()
        for path in model_root.rglob("*") if path.is_file()
    }
    for row in supplemental_rows:
        target = model_root / row["path"]
        final_stat = target.stat()
        if (
            _hash_file(target) != row["sha256"]
            or final_stat.st_size != row["size"]
            or final_stat.st_mtime_ns != row["mtime_ns"]
        ):
            raise RuntimeError(
                f"supplemental model file changed during qualification: {row['path']}"
            )
    if final_observed_paths != manifest_paths | supplemental_paths:
        raise RuntimeError("model directory changed during qualification")
    payload = {"schema": "sys_trrc_model_content_verification_v1",
               "status": "PASS", "manifest_file_sha256": manifest_sha,
               "file_count": len(rows), "directory_closed": True,
               "file_set_sha256": contract.canonical_sha256([
                   {"path": row["path"], "sha256": row["sha256"]}
                   for row in rows
               ]), "files": rows,
               "supplemental_file_count": len(supplemental_rows),
               "supplemental_file_set_sha256": contract.canonical_sha256([
                   {"path": row["path"], "sha256": row["sha256"]}
                   for row in supplemental_rows
               ]),
               "supplemental_files": supplemental_rows,
               "directory_file_count": len(rows) + len(supplemental_rows)}
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    return report


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=contract.MODE_BINDINGS,required=True); p.add_argument("--pid",type=int,required=True); p.add_argument("--port",type=int,default=18000); p.add_argument("--preflight",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    pre=contract.validate_preflight_report(a.preflight,expected_mode=a.mode); arm=contract.binding(a.mode)
    manifest=Path(contract.MODEL_REALPATH+".sha256")
    if not manifest.is_file() or contract.file_sha256(manifest)!=contract.MODEL_MANIFEST_SHA256: raise RuntimeError("model manifest drift")
    model_verification=verify_model_manifest(Path(contract.MODEL_REALPATH),manifest)
    cmd=Path(f"/proc/{a.pid}/cmdline").read_bytes().replace(b"\0",b" ").decode()
    if "vllm" not in cmd or contract.MODEL_REALPATH not in cmd or str(a.port) not in cmd: raise RuntimeError("server cmdline drift")
    with urlopen(f"http://127.0.0.1:{a.port}/v1/models",timeout=10) as response: ids=[str(x.get("id")) for x in (json.load(response).get("data") or [])]
    payload={"schema":contract.LIVE_RECEIPT_SCHEMA,"status":"PASS","errors":[],"generation_calls":0,"protocol_id":contract.PROTOCOL_ID,"system_id":contract.SYSTEM_ID,"mode":a.mode,"arm_id":arm["arm_id"],"experiment_id":arm["experiment_id"],"implementation_commit":pre["implementation_commit"],"preflight_content_sha256":pre["content_sha256"],"served_model_id":contract.MODEL_ID,"served_model_ids_observed":ids,"model_realpath":contract.MODEL_REALPATH,"model_manifest_sha256":contract.MODEL_MANIFEST_SHA256,"model_content_verification":model_verification,"process_pid":a.pid,"process_cmdline":cmd,"port":a.port,"packages":{n:version(n) for n in ("vllm","torch","transformers")},"qualified_at":datetime.now(timezone.utc).isoformat()}
    receipt={**payload,"content_sha256":contract.content_sha256(payload)}; a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8"); contract.validate_launch_receipt(a.output,preflight_path=a.preflight,expected_mode=a.mode); print(json.dumps({"status":"PASS","output":str(a.output)},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
