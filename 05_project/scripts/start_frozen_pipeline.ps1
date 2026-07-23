$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
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
