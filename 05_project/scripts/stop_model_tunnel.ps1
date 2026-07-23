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
    $forwardPattern = "(^|\s)$([regex]::Escape([string]$LocalPort)):127\.0\.0\.1:"
    $tunnels = Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
        Where-Object { $_.CommandLine -match $forwardPattern }
    foreach ($tunnel in $tunnels) {
        Stop-Process -Id $tunnel.ProcessId -ErrorAction SilentlyContinue
    }
}
