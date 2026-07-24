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
    [string]$SuiteId,
    [int]$MaxModelRecoverySeconds = 21600
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$suiteRoot = Join-Path $repositoryRoot "runs\frozen_hard_v1\$SuiteId"
$logRoot = Join-Path $suiteRoot "logs"
$pidFile = Join-Path $suiteRoot "hotfix_001_runner.pid"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Hotfix-001 Hard suite already running: PID $oldPid"
        exit 0
    }
}

$arguments = @(
    (Join-Path $PSScriptRoot "run_frozen_hard_suite_hotfix_001.py"),
    "--adb-path", $adb,
    "--phase", $Phase,
    "--suite-id", $SuiteId,
    "--max-model-recovery-seconds", $MaxModelRecoverySeconds
)
$stdout = Join-Path $logRoot "hotfix_001.stdout.log"
$stderr = Join-Path $logRoot "hotfix_001.stderr.log"
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $repositoryRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started hotfix-001 Hard $Phase suite with PID $($process.Id)."
