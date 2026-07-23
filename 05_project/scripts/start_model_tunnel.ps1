param(
    [string]$SshTarget = "ccj@10.10.217.244",
    [int]$LocalPort = 18000,
    [int]$RemotePort = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Split-Path -Parent $projectRoot
$tempRoot = Join-Path $runtimeRoot "06_local_runtime\temp"
$pidFile = Join-Path $tempRoot "model_tunnel.pid"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$existing = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    $arguments = @(
        "-N",
        "-L", "${LocalPort}:127.0.0.1:${RemotePort}",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        $SshTarget
    )
    $process = Start-Process -FilePath "ssh.exe" -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        $existing = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
    } while (-not $existing -and (Get-Date) -lt $deadline)
}

if (-not $existing) {
    throw "SSH tunnel did not listen on port $LocalPort."
}
$health = Invoke-RestMethod -Uri "http://127.0.0.1:${LocalPort}/health" -TimeoutSec 30
if (-not $health.loaded -or $health.status -ne "ok") {
    throw "Model service is not healthy: $($health | ConvertTo-Json -Compress)"
}
$health
