$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$pipeline = Join-Path $PSScriptRoot "run_frozen_pipeline.ps1"
$root = Join-Path $repositoryRoot "runs\frozen_hard_v1\pipeline"
$pidFile = Join-Path $root "pipeline.pid"
New-Item -ItemType Directory -Force -Path $root | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Frozen pipeline already running: PID $oldPid"
        exit 0
    }
}

& (Join-Path $PSScriptRoot "start_model_tunnel.ps1") | Out-Null
& (Join-Path $PSScriptRoot "start_model_tunnel_watchdog.ps1")
& (Join-Path $runtimeRoot "scripts\stop_emulator.ps1")
Start-Sleep -Seconds 5
& (Join-Path $runtimeRoot "scripts\start_emulator.ps1") `
    -BootTimeoutSeconds 300
if ($LASTEXITCODE -ne 0) {
    throw "Frozen pipeline Android emulator start failed."
}
& $python (Join-Path $runtimeRoot "scripts\androidworld_smoke.py") `
    --adb-path $adb `
    --output (Join-Path $root "androidworld_preflight.json")
if ($LASTEXITCODE -ne 0) {
    throw "Frozen pipeline AndroidWorld preflight smoke failed."
}

$stdout = Join-Path $root "stdout.log"
$stderr = Join-Path $root "stderr.log"
$process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $pipeline
) -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started frozen full pipeline with PID $($process.Id)."
