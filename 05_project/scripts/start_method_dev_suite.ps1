param(
    [string]$SuiteId = "method_dev_g6_g7_20260723"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$suiteRoot = Join-Path $repositoryRoot "runs\method_dev_g6_g7\$SuiteId"
$logRoot = Join-Path $suiteRoot "logs"
$pidFile = Join-Path $suiteRoot "suite.pid"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Method dev suite already running: PID $oldPid"
        exit 0
    }
}

$arguments = @(
    (Join-Path $PSScriptRoot "run_method_dev_suite.py"),
    "--adb-path", $adb,
    "--suite-id", $SuiteId
)
$stdout = Join-Path $logRoot "stdout.log"
$stderr = Join-Path $logRoot "stderr.log"
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started method dev suite with PID $($process.Id)."
