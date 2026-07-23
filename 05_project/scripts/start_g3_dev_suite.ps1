param(
    [string]$SuiteId = "g3_b0_20260723",
    [string]$Manifest = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$suiteRoot = Join-Path $repositoryRoot "runs\dev_nonhard_g3\$SuiteId"
$logRoot = Join-Path $suiteRoot "logs"
$pidFile = Join-Path $suiteRoot "suite.pid"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project-local AndroidWorld Python is missing: $python"
}
if (-not (Test-Path -LiteralPath $adb)) {
    throw "Project-local adb is missing: $adb"
}

$existing = $null
if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
}
if ($existing) {
    Write-Host "G3 suite is already running with PID $($existing.Id)."
    exit 0
}

$arguments = @(
    (Join-Path $PSScriptRoot "run_g3_dev_suite.py"),
    "--adb-path", $adb,
    "--suite-id", $SuiteId
)
if ($Manifest) {
    $arguments += @("--manifest", $Manifest)
}
$stdout = Join-Path $logRoot "stdout.log"
$stderr = Join-Path $logRoot "stderr.log"
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started G3 suite with PID $($process.Id)."
Write-Host "Progress: $suiteRoot\suite_progress.json"
