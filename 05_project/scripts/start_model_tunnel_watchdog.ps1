param(
    [string]$SshTarget = "ccj@10.10.217.244",
    [int]$LocalPort = 18000,
    [int]$RemotePort = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$tempRoot = Join-Path $repositoryRoot "06_local_runtime\temp"
$pidFile = Join-Path $tempRoot "model_tunnel_watchdog.pid"
$stdout = Join-Path $tempRoot "model_tunnel_watchdog.stdout.log"
$stderr = Join-Path $tempRoot "model_tunnel_watchdog.stderr.log"
$watchdog = Join-Path $PSScriptRoot "watch_model_tunnel.ps1"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $oldPid = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Model tunnel watchdog already running: PID $oldPid"
        exit 0
    }
}

$process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $watchdog,
    "-SshTarget", $SshTarget,
    "-LocalPort", $LocalPort,
    "-RemotePort", $RemotePort
) -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Started model tunnel watchdog with PID $($process.Id)."
