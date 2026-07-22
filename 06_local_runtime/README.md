# Local runtime

This directory isolates all Windows-side AndroidWorld dependencies from other projects.

Large runtime content is intentionally excluded from Git:

```text
downloads/              verified upstream archives
tools/android-studio/   optional Android Studio and bundled JBR
android/sdk/            Android SDK, emulator and platform tools
android/avd/            AndroidWorldAvd disk and configuration
android/user_home/      Android tool state
envs/androidworld/      Python 3.11 virtual environment
cache/                  Gradle and pip caches
logs/                   emulator and setup logs
temp/                   disposable setup state
```

Tracked files are limited to `scripts/` and `metadata/`, so the installation can be audited and recreated without committing SDK binaries or AVD images.

## Usage

Bootstrap the runtime:

```powershell
powershell -ExecutionPolicy Bypass -File .\06_local_runtime\scripts\bootstrap_local.ps1
```

If the Google SDK downloader stalls behind a local proxy, finish the already
downloaded, checksum-verified API 33 system image and create the AVD with:

```powershell
powershell -ExecutionPolicy Bypass -File .\06_local_runtime\scripts\finish_android_sdk.ps1
```

The default bootstrap uses Google's official command-line tools, which are sufficient for `sdkmanager`, `avdmanager`, ADB and the emulator. The optional IDE can be installed into the same isolated runtime later with:

```powershell
powershell -ExecutionPolicy Bypass -File .\06_local_runtime\scripts\bootstrap_local.ps1 -InstallAndroidStudio
```

Activate environment variables and the Python environment in the current shell:

```powershell
. .\06_local_runtime\scripts\activate_local.ps1
```

Start or stop the benchmark emulator:

```powershell
.\06_local_runtime\scripts\start_emulator.ps1
.\06_local_runtime\scripts\stop_emulator.ps1
```

Run the read-only audit:

```powershell
.\06_local_runtime\scripts\audit_local.ps1
```

Run the no-LLM end-to-end task initialization test after the emulator boots:

```powershell
$adb = "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe"
python .\06_local_runtime\scripts\androidworld_smoke.py --adb-path $adb --setup-apps --output .\06_local_runtime\metadata\androidworld_smoke.json
```

Use `--setup-apps` only on the first run. The smoke test initializes a real
`ContactsAddContact` task, captures a screen/UI observation, and does not call
any paid model API.

Launch an actual AndroidWorld evaluation through the project-local wrapper
(it accepts the same flags as upstream `run.py`):

```powershell
python .\06_local_runtime\scripts\run_androidworld.py `
  --adb_path "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe" `
  --console_port 5554 `
  --agent_name human_agent `
  --tasks ContactsAddContact `
  --output_path .\06_local_runtime\runs
```

The wrapper loads the narrowly scoped Windows compatibility hooks and then
executes the checked-out upstream runner without modifying its source tree.

The dependency installer also applies one narrowly scoped Windows compatibility
fix to `android_env==1.2.3`: on Python 3.11, its temporary APK must be closed
before `adb.exe` can read it. The patcher verifies the exact upstream source
block and refuses to modify an unknown version.

The pinned Joplin APK exposes an older SQLite schema than the current benchmark
row classes. A project-local compatibility hook filters Joplin inserts to
columns actually present in that APK; it does not alter other applications or
the checked-out AndroidWorld source. The same hook caches and validates the
4,490,495-byte AndroidEnv accessibility APK so transient GCS reads do not break
later environment launches. AndroidWorld app/data assets are redirected from
the Windows temporary directory into `cache/android_world/app_data` and use
resumable downloads.
