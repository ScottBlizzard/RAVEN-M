param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "breadth",
        "confirmatory_additional",
        "strict_control",
        "ablation_controls"
    )]
    [string]$Phase,
    [Parameter(Mandatory = $true)]
    [string]$SuiteId
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$suiteRoot = Join-Path $repositoryRoot "runs\frozen_hard_v1\$SuiteId"
$logRoot = Join-Path $suiteRoot "logs"
$pidFile = Join-Path $suiteRoot "suite.pid"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Frozen Hard suite already running: PID $oldPid"
        exit 0
    }
}

$arguments = @(
    (Join-Path $PSScriptRoot "run_frozen_hard_suite.py"),
    "--adb-path", $adb,
    "--phase", $Phase,
    "--suite-id", $SuiteId
)
$stdout = Join-Path $logRoot "stdout.log"
$stderr = Join-Path $logRoot "stderr.log"
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started frozen Hard $Phase suite with PID $($process.Id)."
