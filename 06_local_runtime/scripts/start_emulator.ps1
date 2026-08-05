param(
    [switch]$Visible,
    [int]$BootTimeoutSeconds = 300,
    [ValidateSet("swiftshader_indirect", "auto")]
    [string]$GpuMode = "swiftshader_indirect"
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
        "-gpu", $GpuMode,
        "-grpc", "8554"
    )
    if (-not $Visible) {
        $arguments += "-no-window"
    }

    $stdout = Join-Path $logRoot "emulator_stdout.log"
    $stderr = Join-Path $logRoot "emulator_stderr.log"
    Start-Process -FilePath $emulator -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
}

$deadline = (Get-Date).AddSeconds($BootTimeoutSeconds)
do {
    # A freshly spawned emulator can briefly accept the transport and then
    # close it while adbd restarts. PowerShell converts native stderr into a
    # terminating error under ErrorActionPreference=Stop, so probe quietly
    # and let the bounded boot loop absorb that expected transient.
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $bootOutput = & $adb shell getprop sys.boot_completed 2>&1
        $bootExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $booted = ($bootOutput | Out-String).Trim()
    if ($bootExitCode -eq 0 -and $booted -eq "1") {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        try {
            & $adb shell input keyevent 82 2>&1 | Out-Null
            $unlockExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        if ($unlockExitCode -ne 0) {
            Start-Sleep -Seconds 3
            continue
        }
        $focusOutput = & $adb shell dumpsys activity activities 2>&1
        $focusText = ($focusOutput | Select-String "ResumedActivity" | Select-Object -First 1 | Out-String)
        if ($focusText -notmatch "nexuslauncher") {
            Start-Sleep -Seconds 3
            continue
        }
        Write-Host "AndroidWorldAvd is ready."
        return
    }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

throw "AndroidWorldAvd did not finish booting within $BootTimeoutSeconds seconds."
