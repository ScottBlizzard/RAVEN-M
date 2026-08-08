[CmdletBinding()]
param(
    [string]$SshHost = "connect.westb.seetacloud.com",
    [int]$SshPort = 22252,
    [string]$SshUser = "root",
    [string]$SshKey = "$env:USERPROFILE\.ssh\autodl_raven_m",
    [int]$LocalModelPort = 18000,
    [int]$ServerReadyTimeoutSeconds = 1800,
    [double]$RequestTimeoutSeconds = 3600,
    [ValidateSet("H01", "H06", "H09", "H17", "FULL")]
    [string]$ManifestId = "H01",
    [string]$ManifestPath = "",
    [int]$StepCap = 0,
    [switch]$Diagnostic,
    [switch]$TransientObservationCarry,
    [switch]$TransitionAttestedHistory,
    [switch]$EvidenceQualifiedProgress,
    [string]$RunStage = "held_out_full",
    [string]$HeldOutIneligibleReason = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repositoryRoot = (Resolve-Path (Join-Path $projectRoot "..")).Path
$python = Join-Path $repositoryRoot "06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = Join-Path $repositoryRoot "06_local_runtime\android\sdk\platform-tools\adb.exe"
$runner = Join-Path $projectRoot "scripts\run_official_qwen_mobile.py"
$manifest = if ($ManifestPath) {
    (Resolve-Path -LiteralPath $ManifestPath).Path
}
elseif ($ManifestId -eq "FULL") {
    Join-Path $projectRoot "configs\task_manifests\androidworld_hard_v2_instances.json"
}
else {
    Join-Path $projectRoot (
        "configs\task_manifests\hard_pulse_v0_3\{0}.json" -f $ManifestId
    )
}
$target = "$SshUser@$SshHost"
$commonSsh = @(
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=8",
    "-i", $SshKey,
    "-p", [string]$SshPort
)

foreach ($required in @($SshKey, $python, $adb, $runner, $manifest)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is absent: $required"
    }
}

Write-Host "[1/5] Checking that the paid GPU is actually attached..."
& ssh @commonSsh $target "nvidia-smi -L"
if ($LASTEXITCODE -ne 0) {
    throw "No usable GPU is attached. Keep the instance in no-card mode until ready to run."
}

Write-Host "[2/5] Running the zero-generation model/protocol preflight..."
$remotePreflight = @'
cd /root/autodl-tmp/RAVEN-M &&
/root/autodl-tmp/envs/qwen_vllm/bin/python \
  05_project/scripts/preflight_official_qwen.py \
  --model-dir /root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope
'@
& ssh @commonSsh $target $remotePreflight
if ($LASTEXITCODE -ne 0) {
    throw "Remote zero-generation preflight failed."
}

Write-Host "[3/5] Starting the pinned stock-vLLM server..."
$remoteStart = @'
if ! pgrep -f 'vllm serve.*Qwen3-VL-32B-Instruct' >/dev/null; then
  mkdir -p /root/autodl-tmp/runs/official_qwen_mobile_server
  nohup /root/autodl-tmp/RAVEN-M/05_project/scripts/start_official_qwen_server.sh \
    >/root/autodl-tmp/runs/official_qwen_mobile_server/stdout.log 2>&1 &
  echo $! >/root/autodl-tmp/runs/official_qwen_mobile_server/pid
fi
'@
& ssh @commonSsh $target $remoteStart
if ($LASTEXITCODE -ne 0) {
    throw "Could not start the remote model server."
}

Write-Host "[4/5] Opening a private SSH tunnel and waiting for model readiness..."
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
$watchdog = $null
try {
    $deadline = (Get-Date).AddSeconds($ServerReadyTimeoutSeconds)
    $modelReady = $false
    while ((Get-Date) -lt $deadline) {
        if ($tunnel.HasExited) {
            throw "The SSH tunnel exited before the model became ready."
        }
        try {
            $models = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalModelPort/v1/models" -TimeoutSec 5
            if ($models.data.id -contains "Qwen/Qwen3-VL-32B-Instruct") {
                $modelReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 10
        }
    }
    if (-not $modelReady) {
        throw "The model server did not become ready within $ServerReadyTimeoutSeconds seconds."
    }

    Write-Host "[5/5] Running frozen Hard Pulse $ManifestId..."
    $watchdogScript = Join-Path $PSScriptRoot "watch_model_tunnel.ps1"
    $watchdogLogDir = Join-Path $repositoryRoot "runs\official_qwen_mobile\background_launcher"
    New-Item -ItemType Directory -Force -Path $watchdogLogDir | Out-Null
    $watchdogLog = Join-Path $watchdogLogDir ("tunnel_watchdog_{0}.log" -f $PID)
    $watchdogArguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $watchdogScript,
        "-ParentProcessId", [string]$PID,
        "-SshHost", $SshHost,
        "-SshPort", [string]$SshPort,
        "-SshUser", $SshUser,
        "-SshKey", $SshKey,
        "-LocalPort", [string]$LocalModelPort,
        "-RemotePort", "18000",
        "-LogPath", $watchdogLog
    )
    $watchdog = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $watchdogArguments `
        -WindowStyle Hidden `
        -PassThru
    $runnerArguments = @(
        $runner,
        "--url", "http://127.0.0.1:$LocalModelPort",
        "--adb-path", $adb,
        "--manifest", $manifest,
        "--generation-seed", "3407",
        "--max-tokens", "32768",
        "--request-timeout-seconds", [string]$RequestTimeoutSeconds,
        "--run-stage", $RunStage
    )
    if ($Diagnostic) {
        $runnerArguments += "--diagnostic"
    }
    if ($TransientObservationCarry) {
        $runnerArguments += "--transient-observation-carry"
    }
    if ($TransitionAttestedHistory) {
        $runnerArguments += "--transition-attested-history"
    }
    if ($EvidenceQualifiedProgress) {
        $runnerArguments += "--evidence-qualified-progress"
    }
    if ($StepCap -gt 0) {
        $runnerArguments += @("--step-cap", [string]$StepCap)
    }
    if ($HeldOutIneligibleReason) {
        $runnerArguments += @(
            "--held-out-ineligible-reason",
            $HeldOutIneligibleReason
        )
    }
    & $python @runnerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ManifestId runner failed."
    }
}
finally {
    if ($null -ne $tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force
    }
}
