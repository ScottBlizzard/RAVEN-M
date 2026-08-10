param(
    [string]$ResumeSuiteDir = ""
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo "06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = Join-Path $repo "06_local_runtime\android\sdk\platform-tools\adb.exe"
$runner = Join-Path $repo "implementation\scripts\run_official_qwen_mobile.py"
$manifest = Join-Path $repo "implementation\configs\androidworld_hard_v2_instances.json"
$preflight = Join-Path $repo "evidence\a2\A2_ZERO_GENERATION_PREFLIGHT.json"
$outputRoot = Join-Path $repo "runs\a2_verified_progress_memory"

foreach ($required in @($python, $adb, $runner, $manifest, $preflight)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required A2 path is missing: $required"
    }
}

$health = Invoke-RestMethod -Uri "http://127.0.0.1:18000/v1/models" -TimeoutSec 30
$served = @($health.data | ForEach-Object { $_.id })
if ($served -notcontains "Qwen/Qwen3-VL-32B-Instruct") {
    throw "Frozen Qwen3-VL-32B model is not served on localhost:18000"
}

$arguments = @(
    $runner,
    "--url", "http://127.0.0.1:18000",
    "--adb-path", $adb,
    "--manifest", $manifest,
    "--a2-verified-progress-memory",
    "--a2-preflight-report", $preflight,
    "--run-stage", "a2_scored_full",
    "--output-root", $outputRoot,
    "--generation-seed", "3407",
    "--max-tokens", "32768",
    "--observation-backend", "uiautomator"
)
if ($ResumeSuiteDir) {
    $arguments += @("--resume-suite-dir", (Resolve-Path $ResumeSuiteDir).Path)
}

& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "A2 runner stopped. Preserve the suite and resume only the infrastructure-invalid task."
}
