"""Zero-generation A2-v1r1 runtime qualification (remote model/local Android)."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


EXPECTED_MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
EXPECTED_MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
EXPECTED_QWEN_COMMIT = "96588727e44c78b25ba03ea03b8e12f7e64fd0da"
EXPECTED_ANDROIDWORLD_COMMIT = "3e50888527ef9f29b9157ecd537e408008bb1c85"
SCORED_ANDROID_PACKAGES = (
    "com.android.chrome",
    "com.arduia.expense",
    "com.flauschcode.broccoli",
    "com.google.android.apps.messaging",
    "com.simplemobiletools.calendar.pro",
    "com.simplemobiletools.gallery.pro",
    "com.simplemobiletools.smsmessenger",
    "code.name.monkey.retromusic",
    "de.dennisguse.opentracks",
    "net.gsantner.markor",
    "net.osmand",
    "org.tasks",
    "org.videolan.vlc",
)


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(*command: str) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()


def _versions(names: list[str]) -> dict[str, str | None]:
    result = {}
    for name in names:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def _manifest(path: Path, model_dir: Path) -> tuple[list[dict[str, Any]], str]:
    if _hash(path) != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError("frozen model manifest hash drift")
    expected: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or len(digest) != 64:
            raise RuntimeError(f"invalid manifest line: {line!r}")
        expected[name] = digest
    actual_names = {item.name for item in model_dir.iterdir() if item.is_file()}
    if not set(expected).issubset(actual_names):
        raise RuntimeError("one or more manifest-listed model files are absent")
    files = []
    for name in sorted(expected):
        item = model_dir / name
        digest = _hash(item)
        if digest != expected[name]:
            raise RuntimeError(f"model file hash drift: {name}")
        files.append({"name": name, "bytes": item.stat().st_size, "sha256": digest, "realpath": str(item.resolve())})
    return files, _hash(path), sorted(actual_names - set(expected))


def remote_model(args: argparse.Namespace) -> dict[str, Any]:
    files, manifest_hash, unmanifested = _manifest(args.model_manifest.resolve(), args.model_dir.resolve())
    qwen_commit = _run("git", "-C", str(args.qwen_repo.resolve()), "rev-parse", "HEAD")
    if qwen_commit != EXPECTED_QWEN_COMMIT:
        raise RuntimeError(f"Qwen commit drift: {qwen_commit}")
    return {
        "schema": "a2_runtime_qualification_remote_model_v1",
        "status": "pass",
        "generation_calls": 0,
        "model_id": "Qwen/Qwen3-VL-32B-Instruct",
        "model_revision": EXPECTED_MODEL_REVISION,
        "model_realpath": str(args.model_dir.resolve()),
        "model_manifest_realpath": str(args.model_manifest.resolve()),
        "model_manifest_sha256": manifest_hash,
        "model_file_count": len(files),
        "model_total_bytes": sum(int(item["bytes"]) for item in files),
        "model_files": files,
        "unmanifested_ancillary_files": unmanifested,
        "official_qwen_commit": qwen_commit,
        "python": sys.version,
        "packages": _versions(["vllm", "torch", "transformers", "qwen-vl-utils"]),
        "disk": shutil.disk_usage(args.model_dir.resolve())._asdict(),
        "gpu_expected": False,
        "server_process_expected": False,
        "note": "Static no-GPU qualification; scored launcher must bind its live process and command to this model realpath and receipt hash.",
    }


def _tree_digest(root: Path) -> tuple[str, int]:
    records = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        records.append((str(path.relative_to(root)).replace("\\", "/"), _hash(path)))
    return sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest(), len(records)


def local_android(args: argparse.Namespace) -> dict[str, Any]:
    android_root = args.androidworld_repo.resolve()
    head = _run("git", "-C", str(android_root), "rev-parse", "HEAD")
    if head != EXPECTED_ANDROIDWORLD_COMMIT:
        raise RuntimeError(f"AndroidWorld commit drift: {head}")
    source_digest, source_count = _tree_digest(android_root / "android_world")
    manifest = json.loads(args.task_manifest.read_text(encoding="utf-8"))
    instances = manifest.get("instances") if isinstance(manifest, dict) else manifest
    scored = [item for item in instances if int(item["task_seed"]) == 20260806]
    if len(scored) != 19 or len({item["task_class"] for item in scored}) != 19:
        raise RuntimeError("task manifest does not contain 19 unique scored tasks")
    adb = str(args.adb.resolve())
    devices = _run(adb, "devices")
    if "emulator-5554\tdevice" not in devices:
        raise RuntimeError(f"frozen emulator unavailable: {devices!r}")
    size = _run(adb, "shell", "wm", "size")
    if "1080x2400" not in size:
        raise RuntimeError(f"resolution drift: {size}")
    packages = _run(adb, "shell", "pm", "list", "packages").splitlines()
    installed = {line.removeprefix("package:").strip() for line in packages}
    missing_packages = sorted(set(SCORED_ANDROID_PACKAGES) - installed)
    if missing_packages:
        raise RuntimeError(f"scored Android packages missing: {missing_packages!r}")
    scored_package_identity = {}
    for package in SCORED_ANDROID_PACKAGES:
        dump = _run(adb, "shell", "dumpsys", "package", package)
        identity_lines = [
            line.strip() for line in dump.splitlines()
            if line.strip().startswith(("versionCode=", "versionName=", "firstInstallTime=", "lastUpdateTime="))
        ]
        scored_package_identity[package] = identity_lines
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=True) as stream:
        stream.write(b"a2-runtime-write-check")
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "schema": "a2_runtime_qualification_local_android_v1",
        "status": "pass",
        "generation_calls": 0,
        "androidworld_commit": head,
        "androidworld_worktree_status": _run("git", "-C", str(android_root), "status", "--short"),
        "androidworld_source_tree_sha256": source_digest,
        "androidworld_source_file_count": source_count,
        "adb_realpath": str(args.adb.resolve()),
        "adb_devices": devices,
        "emulator_serial": _run(adb, "shell", "getprop", "ro.serialno"),
        "android_build_fingerprint": _run(adb, "shell", "getprop", "ro.build.fingerprint"),
        "resolution": size,
        "installed_package_count": len(packages),
        "scored_package_identity": scored_package_identity,
        "task_manifest_realpath": str(args.task_manifest.resolve()),
        "task_manifest_sha256": _hash(args.task_manifest.resolve()),
        "ordered_scored_keys": [[item["task_class"], int(item["task_seed"])] for item in scored],
        "ordered_scored_keys_sha256": sha256(json.dumps([[item["task_class"], int(item["task_seed"])] for item in scored], separators=(",", ":")).encode()).hexdigest(),
        "python": sys.version,
        "packages": _versions(["android-world", "android-env", "numpy", "Pillow"]),
        "output_write_check": "pass",
        "disk": shutil.disk_usage(args.output.parent.resolve())._asdict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("remote-model", "local-android", "combine"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument("--qwen-repo", type=Path)
    parser.add_argument("--androidworld-repo", type=Path)
    parser.add_argument("--task-manifest", type=Path)
    parser.add_argument("--adb", type=Path)
    parser.add_argument("--remote-report", type=Path)
    parser.add_argument("--local-report", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "remote-model":
        result = remote_model(args)
    elif args.mode == "local-android":
        result = local_android(args)
    else:
        remote = json.loads(args.remote_report.read_text(encoding="utf-8"))
        local = json.loads(args.local_report.read_text(encoding="utf-8"))
        if remote.get("status") != "pass" or local.get("status") != "pass":
            raise RuntimeError("component runtime qualification did not pass")
        result = {
            "schema": "a2_runtime_qualification_combined_v1",
            "status": "pass",
            "generation_calls": 0,
            "remote_model_report_sha256": _hash(args.remote_report),
            "local_android_report_sha256": _hash(args.local_report),
            "remote_model": remote,
            "local_android": local,
        }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output.resolve()), "sha256": _hash(args.output)}, indent=2))


if __name__ == "__main__":
    main()
