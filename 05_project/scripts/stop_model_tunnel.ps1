param(
    [int]$LocalPort = 18000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Split-Path -Parent $projectRoot
$pidFile = Join-Path $runtimeRoot "06_local_runtime\temp\model_tunnel.pid"

if (Test-Path -LiteralPath $pidFile) {
    $tunnelPid = [int](Get-Content -LiteralPath $pidFile)
    Stop-Process -Id $tunnelPid -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pidFile -Force
}
else {
    $listeners = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq "ssh") {
            Stop-Process -Id $process.Id
        }
    }
}
