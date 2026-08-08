[CmdletBinding()]
param(
    [string]$SshHost = "connect.westb.seetacloud.com",
    [int]$SshPort = 22252,
    [string]$SshUser = "root",
    [string]$SshKey = "$env:USERPROFILE\.ssh\autodl_raven_m",
    [int]$LocalModelPort = 18000,
    [double]$RequestTimeoutSeconds = 120,
    [string]$ManifestPath = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repositoryRoot = (Resolve-Path (Join-Path $projectRoot "..")).Path
$python = Join-Path $repositoryRoot "06_local_runtime\envs\androidworld\Scripts\python.exe"
$runner = Join-Path $projectRoot "scripts\run_offline_completion_verifier.py"
$manifest = if ($ManifestPath) {
    (Resolve-Path -LiteralPath $ManifestPath).Path
}
else {
    Join-Path $projectRoot "configs\completion_verifier\official_qwen32b_success_claims_27.final.json"
}
$target = "$SshUser@$SshHost"
$commonSsh = @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-i", $SshKey,
    "-p", [string]$SshPort
)

foreach ($required in @($SshKey, $python, $runner, $manifest)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is absent: $required"
    }
}

& ssh @commonSsh $target "nvidia-smi -L"
if ($LASTEXITCODE -ne 0) {
    throw "No usable paid GPU is attached."
}

$tunnelArguments = @(
    "-N",
    "-o", "BatchMode=yes",
    "-o", "ExitOnForwardFailure=yes",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=2",
    "-o", "TCPKeepAlive=yes",
    "-i", $SshKey,
    "-p", [string]$SshPort,
    "-L", "${LocalModelPort}:127.0.0.1:18000",
    $target
)
$tunnel = Start-Process -FilePath "ssh" -ArgumentList $tunnelArguments -WindowStyle Hidden -PassThru
try {
    $deadline = (Get-Date).AddMinutes(5)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if ($tunnel.HasExited) {
            throw "SSH tunnel exited before the model was ready."
        }
        try {
            $models = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalModelPort/v1/models" -TimeoutSec 5
            if ($models.data.id -contains "Qwen/Qwen3-VL-32B-Instruct") {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 5
        }
    }
    if (-not $ready) {
        throw "The pinned model server was not ready within five minutes."
    }
    & $python $runner `
        --url "http://127.0.0.1:$LocalModelPort" `
        --manifest $manifest `
        --request-timeout-seconds $RequestTimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        throw "Offline completion verifier failed."
    }
}
finally {
    if ($null -ne $tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force
    }
}
