param(
    [string]$Url = "http://127.0.0.1:18000"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$suiteId = "nonhard_capability_v2_1_seed20260729_r1"
$suiteRoot = Join-Path $repositoryRoot "runs\protocol_v2_1\$suiteId"
$logRoot = Join-Path $suiteRoot "logs"
$pidFile = Join-Path $suiteRoot "runner.pid"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Protocol-v2.1 Gate E already running: PID $oldPid"
        exit 0
    }
}

$arguments = @(
    (Join-Path $PSScriptRoot "run_protocol_v2_1_gate_e.py"),
    "--adb-path", $adb,
    "--url", $Url
)
$stdout = Join-Path $logRoot "runner.stdout.log"
$stderr = Join-Path $logRoot "runner.stderr.log"
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started protocol-v2.1 Gate E with PID $($process.Id)."
