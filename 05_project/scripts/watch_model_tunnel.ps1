param(
    [string]$SshTarget = "ccj@10.10.217.244",
    [int]$LocalPort = 18000,
    [int]$RemotePort = 8000,
    [int]$PollSeconds = 15,
    [int]$HealthTimeoutSeconds = 8,
    [int]$RestartAfterFailures = 3
)

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$tempRoot = Join-Path $repositoryRoot "06_local_runtime\temp"
$logPath = Join-Path $tempRoot "model_tunnel_watchdog.log"
$stopFile = Join-Path $tempRoot "model_tunnel_watchdog.stop"
$startScript = Join-Path $PSScriptRoot "start_model_tunnel.ps1"
$stopScript = Join-Path $PSScriptRoot "stop_model_tunnel.ps1"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
Remove-Item -LiteralPath $stopFile -Force -ErrorAction SilentlyContinue

function Write-WatchdogLog {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("o")
    Add-Content -LiteralPath $logPath -Value "$timestamp`t$Message" -Encoding utf8
}

function Test-LocalPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        if (-not $task.Wait(250)) {
            return $false
        }
        return $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

$consecutiveFailures = 0
Write-WatchdogLog "watchdog_started target=$SshTarget local=$LocalPort remote=$RemotePort"

while (-not (Test-Path -LiteralPath $stopFile)) {
    $listener = Test-LocalPort -Port $LocalPort
    $healthy = $false
    if ($listener) {
        try {
            $health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:${LocalPort}/health" `
                -TimeoutSec $HealthTimeoutSeconds
            $healthy = (
                $health.status -eq "ok" -and
                $health.loaded -eq $true -and
                $health.revision -eq "0cfaf48183f594c314753d30a4c4974bc75f3ccb" -and
                $health.backend -eq "qwen3_vl_32b_transformers_bf16_4x4090_v1"
            )
        }
        catch {
            Write-WatchdogLog "health_failed $($_.Exception.Message)"
        }
    }

    if ($healthy) {
        if ($consecutiveFailures -gt 0) {
            Write-WatchdogLog "health_recovered failures=$consecutiveFailures"
        }
        $consecutiveFailures = 0
    }
    else {
        $consecutiveFailures += 1
        $activeCalls = $null
        if (
            $listener -and
            $consecutiveFailures -ge $RestartAfterFailures
        ) {
            $activeCalls = Get-NetTCPConnection -LocalPort $LocalPort `
                -State Established -ErrorAction SilentlyContinue
        }
        $restart = (
            -not $listener -or
            (
                $consecutiveFailures -ge $RestartAfterFailures -and
                -not $activeCalls
            )
        )
        if ($restart) {
            Write-WatchdogLog "restart_begin failures=$consecutiveFailures listener=$([bool]$listener)"
            try {
                & $stopScript -LocalPort $LocalPort
                & $startScript -SshTarget $SshTarget -LocalPort $LocalPort `
                    -RemotePort $RemotePort | Out-Null
                Write-WatchdogLog "restart_ok"
                $consecutiveFailures = 0
            }
            catch {
                Write-WatchdogLog "restart_failed $($_.Exception.Message)"
            }
        }
    }
    Start-Sleep -Seconds $PollSeconds
}

Write-WatchdogLog "watchdog_stopped"
Remove-Item -LiteralPath $stopFile -Force -ErrorAction SilentlyContinue
