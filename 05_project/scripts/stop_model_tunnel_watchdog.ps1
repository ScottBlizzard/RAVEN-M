$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$tempRoot = Join-Path $repositoryRoot "06_local_runtime\temp"
$pidFile = Join-Path $tempRoot "model_tunnel_watchdog.pid"
$stopFile = Join-Path $tempRoot "model_tunnel_watchdog.stop"

New-Item -ItemType File -Force -Path $stopFile | Out-Null
if (Test-Path -LiteralPath $pidFile) {
    $watchdogPid = [int](Get-Content -LiteralPath $pidFile)
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        $process = Get-Process -Id $watchdogPid -ErrorAction SilentlyContinue
    } while ($process -and (Get-Date) -lt $deadline)
    if ($process) {
        Stop-Process -Id $watchdogPid -Force
    }
    Remove-Item -LiteralPath $pidFile -Force
}
