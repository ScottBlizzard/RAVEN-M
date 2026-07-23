$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "activate_local.ps1")
$adb = Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"

function Get-AndroidWorldEmulatorProcess {
    @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -in @("emulator.exe", "qemu-system-x86_64.exe") -and
                $_.CommandLine -match "AndroidWorldAvd"
            }
    )
}

if (Test-Path -LiteralPath $adb) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & $adb -s emulator-5554 emu kill 2>&1 | Out-Null
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

$deadline = (Get-Date).AddSeconds(60)
do {
    $processes = Get-AndroidWorldEmulatorProcess
    $devicePresent = $false
    if (Test-Path -LiteralPath $adb) {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        try {
            $deviceOutput = & $adb devices 2>&1
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        $devicePresent = [bool](
            $deviceOutput | Select-String "emulator-5554\s+"
        )
    }
    if (-not $devicePresent -and $processes.Count -eq 0) {
        Write-Host "AndroidWorldAvd is stopped."
        return
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

# The graceful console command can return before Windows releases the AVD
# process and lock. Force only the explicitly named project AVD after the
# bounded wait; never target other emulator processes.
$processes = Get-AndroidWorldEmulatorProcess
foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
$forceDeadline = (Get-Date).AddSeconds(15)
do {
    if ((Get-AndroidWorldEmulatorProcess).Count -eq 0) {
        Write-Host "AndroidWorldAvd was force-stopped after graceful timeout."
        return
    }
    Start-Sleep -Seconds 1
} while ((Get-Date) -lt $forceDeadline)

if ((Get-AndroidWorldEmulatorProcess).Count -ne 0) {
    throw "AndroidWorldAvd did not stop within the bounded shutdown window."
}
