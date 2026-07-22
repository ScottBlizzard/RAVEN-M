"""Launch the checked-out AndroidWorld runner with local Windows fixes loaded."""

from __future__ import annotations

import runpy
import os
import sys
from pathlib import Path

import androidworld_compat  # noqa: F401  # Applies the scoped compatibility hooks.


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "06_local_runtime"
UPSTREAM_RUNNER = REPO_ROOT / "03_code" / "third_party" / "android_world" / "run.py"
LOCAL_ADB = RUNTIME_ROOT / "android" / "sdk" / "platform-tools" / "adb.exe"


def _has_flag(name: str) -> bool:
    prefix = f"--{name}="
    return any(argument == f"--{name}" or argument.startswith(prefix) for argument in sys.argv[1:])


if __name__ == "__main__":
    if not UPSTREAM_RUNNER.is_file():
        raise FileNotFoundError(f"AndroidWorld runner not found: {UPSTREAM_RUNNER}")
    if not LOCAL_ADB.is_file():
        raise FileNotFoundError(f"Project-local ADB not found: {LOCAL_ADB}")

    # AndroidWorld prints Unicode reward markers. Windows PowerShell may expose
    # a legacy GBK console encoding, which otherwise raises UnicodeEncodeError
    # after an episode has completed.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Upstream evaluates its macOS/Linux-only ADB default before absl parses a
    # supplied --adb_path. Redirect only those two discovery probes while the
    # module is loaded, then restore the standard-library function.
    original_expanduser = os.path.expanduser
    adb_probes = {
        "~/Library/Android/sdk/platform-tools/adb",
        "~/Android/Sdk/platform-tools/adb",
    }

    def local_expanduser(path: str) -> str:
        if path in adb_probes:
            return str(LOCAL_ADB)
        return original_expanduser(path)

    if not _has_flag("adb_path"):
        sys.argv.append(f"--adb_path={LOCAL_ADB}")
    if not _has_flag("output_path") and not _has_flag("checkpoint_dir"):
        sys.argv.append(f"--output_path={RUNTIME_ROOT / 'runs'}")
    sys.argv[0] = str(UPSTREAM_RUNNER)
    os.path.expanduser = local_expanduser
    try:
        runpy.run_path(str(UPSTREAM_RUNNER), run_name="__main__")
    finally:
        os.path.expanduser = original_expanduser
