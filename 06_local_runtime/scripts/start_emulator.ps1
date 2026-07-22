param(
    [switch]$Visible,
    [int]$BootTimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "activate_local.ps1")

$runtimeRoot = Split-Path -Parent $PSScriptRoot
$emulator = Join-Path $env:ANDROID_SDK_ROOT "emulator\emulator.exe"
$adb = Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"
$logRoot = Join-Path $runtimeRoot "logs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (-not (Test-Path -LiteralPath $emulator)) {
    throw "Android Emulator is missing. Run bootstrap_local.ps1 first."
}

$running = & $adb devices | Select-String "emulator-\d+\s+device"
if (-not $running) {
    $arguments = @(
        "-avd", "AndroidWorldAvd",
        "-no-snapshot",
        "-no-boot-anim",
        "-no-audio",
        "-grpc", "8554"
    )
    if (-not $Visible) {
        $arguments += "-no-window"
    }

    $stdout = Join-Path $logRoot "emulator_stdout.log"
    $stderr = Join-Path $logRoot "emulator_stderr.log"
    Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
}

& $adb wait-for-device
$deadline = (Get-Date).AddSeconds($BootTimeoutSeconds)
do {
    $booted = (& $adb shell getprop sys.boot_completed 2>$null).Trim()
    if ($booted -eq "1") {
        & $adb shell input keyevent 82 | Out-Null
        Write-Host "AndroidWorldAvd is ready."
        exit 0
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

throw "AndroidWorldAvd did not finish booting within $BootTimeoutSeconds seconds."
