$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "activate_local.ps1")

$runtimeRoot = Split-Path -Parent $PSScriptRoot
$adb = Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"
$emulator = Join-Path $env:ANDROID_SDK_ROOT "emulator\emulator.exe"
$sdkmanager = Join-Path $env:ANDROID_SDK_ROOT "cmdline-tools\latest\bin\sdkmanager.bat"
$studio = Join-Path $runtimeRoot "tools\android-studio\bin\studio64.exe"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$appCache = Join-Path $runtimeRoot "cache\android_world\app_data"
$smokePath = Join-Path $runtimeRoot "metadata\androidworld_smoke.json"
$repeatSmokePath = Join-Path $runtimeRoot "metadata\androidworld_repeat_smoke.json"
$validationRoot = Join-Path $runtimeRoot "runs\local_validation_utf8"

$expectedPackages = @(
    "ca.zgrs.clipper",
    "code.name.monkey.retromusic",
    "com.arduia.expense",
    "com.dimowner.audiorecorder",
    "com.example.androidworld",
    "com.flauschcode.broccoli",
    "com.google.androidenv.accessibilityforwarder",
    "com.google.androidenv.miniwob",
    "com.simplemobiletools.calendar.pro",
    "com.simplemobiletools.draw.pro",
    "com.simplemobiletools.gallery.pro",
    "com.simplemobiletools.smsmessenger",
    "de.dennisguse.opentracks",
    "net.cozic.joplin",
    "net.gsantner.markor",
    "net.osmand",
    "org.tasks",
    "org.videolan.vlc"
)

$connectedDevice = $null
$bootCompleted = $null
$deviceApi = $null
$deviceModel = $null
$installedPackages = @()
if (Test-Path -LiteralPath $adb) {
    $deviceLines = @(& $adb devices | Select-Object -Skip 1)
    $connectedDevice = $deviceLines | Where-Object { $_ -match "\sdevice$" } | Select-Object -First 1
    if ($connectedDevice) {
        $bootCompleted = (& $adb shell getprop sys.boot_completed).Trim()
        $deviceApi = (& $adb shell getprop ro.build.version.sdk).Trim()
        $deviceModel = (& $adb shell getprop ro.product.model).Trim()
        $installedPackages = @(& $adb shell pm list packages -3) |
            ForEach-Object { $_ -replace "^package:", "" } |
            Where-Object { $_ } |
            Sort-Object
    }
}

$cacheFiles = @(Get-ChildItem -LiteralPath $appCache -File -ErrorAction SilentlyContinue)
$smoke = if (Test-Path -LiteralPath $smokePath) { Get-Content -Raw -LiteralPath $smokePath | ConvertFrom-Json } else { $null }
$repeatSmoke = if (Test-Path -LiteralPath $repeatSmokePath) { Get-Content -Raw -LiteralPath $repeatSmokePath | ConvertFrom-Json } else { $null }
$pythonVersion = if (Test-Path -LiteralPath $python) { (& $python --version 2>&1 | Out-String).Trim() } else { $null }
$pipCheck = if (Test-Path -LiteralPath $python) { (& $python -m pip check 2>&1 | Out-String).Trim() } else { $null }
$grpcListening = [bool](Get-NetTCPConnection -LocalPort 8554 -State Listen -ErrorAction SilentlyContinue)
$validationEpisode = Get-ChildItem -LiteralPath $validationRoot -Filter "*.pkl.gz" -File -Recurse -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

$audit = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    android_studio = Test-Path -LiteralPath $studio
    sdkmanager = Test-Path -LiteralPath $sdkmanager
    adb = Test-Path -LiteralPath $adb
    emulator = Test-Path -LiteralPath $emulator
    platform_api_33 = Test-Path -LiteralPath (Join-Path $env:ANDROID_SDK_ROOT "platforms\android-33\android.jar")
    build_tools_33_0_2 = Test-Path -LiteralPath (Join-Path $env:ANDROID_SDK_ROOT "build-tools\33.0.2\aapt2.exe")
    system_image_api_33 = Test-Path -LiteralPath (Join-Path $env:ANDROID_SDK_ROOT "system-images\android-33\google_apis\x86_64\system.img")
    python_env = Test-Path -LiteralPath $python
    avd_config = Test-Path -LiteralPath (Join-Path $env:ANDROID_AVD_HOME "AndroidWorldAvd.avd\config.ini")
    ffmpeg = [bool]$ffmpeg
    ffmpeg_path = $(if ($ffmpeg) { $ffmpeg.Source } else { $null })
    python_version = $pythonVersion
    pip_check = $pipCheck
    emulator_running = [bool]$connectedDevice
    emulator_device = $connectedDevice
    boot_completed = $bootCompleted
    device_api = $deviceApi
    device_model = $deviceModel
    grpc_8554_listening = $grpcListening
    expected_app_packages = $expectedPackages.Count
    installed_expected_packages = @($expectedPackages | Where-Object { $_ -in $installedPackages }).Count
    missing_app_packages = @($expectedPackages | Where-Object { $_ -notin $installedPackages })
    app_cache_files = $cacheFiles.Count
    app_cache_bytes = ($cacheFiles | Measure-Object -Property Length -Sum).Sum
    initial_smoke_status = $(if ($smoke) { $smoke.status } else { $null })
    repeat_smoke_status = $(if ($repeatSmoke) { $repeatSmoke.status } else { $null })
    registered_android_world_tasks = $(if ($repeatSmoke) { $repeatSmoke.registered_android_world_tasks } elseif ($smoke) { $smoke.registered_android_world_tasks } else { $null })
    local_runner = Test-Path -LiteralPath (Join-Path $PSScriptRoot "run_androidworld.py")
    official_runner_validation = [bool]$validationEpisode
    official_runner_episode = $(if ($validationEpisode) { $validationEpisode.FullName } else { $null })
}
$audit | Format-List
$auditPath = Join-Path $runtimeRoot "metadata\runtime_audit.json"
$audit | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $auditPath -Encoding UTF8

if (Test-Path -LiteralPath $adb) {
    & $adb version
    & $adb devices -l
}
if (Test-Path -LiteralPath $emulator) {
    & $emulator -version
    & $emulator -accel-check
    & $emulator -list-avds
}
if (Test-Path -LiteralPath $python) {
    & $python --version
    & $python -m pip check
    & $python -c "import android_world, android_env, cv2, grpc, matplotlib, numpy, pandas; print('android_world_import=ok')"
}
