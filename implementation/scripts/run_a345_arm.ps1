param(
    [Parameter(Mandatory=$true)][ValidateSet("a3","a4","a5")][string]$Arm,
    [Parameter(Mandatory=$true)][string]$LaunchReceipt,
    [string]$ResumeSuiteDir = "",
    [string]$Url = "http://127.0.0.1:18000"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo "06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = Join-Path $repo "06_local_runtime\android\sdk\platform-tools\adb.exe"
$runner = Join-Path $repo "implementation\scripts\run_official_qwen_mobile.py"
$manifest = Join-Path $repo "implementation\configs\androidworld_hard_v2_instances.json"
$preflight = Join-Path $repo "evidence\a345\A345_ZERO_GENERATION_PREFLIGHT.json"
$bank = Join-Path $repo "evidence\a345\A4_FROZEN_DONOR_WORKFLOW_BANK.json"
$output = Join-Path $repo "runs\a345_public_memory"
foreach ($required in @($python,$adb,$runner,$manifest,$preflight,$LaunchReceipt)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing A345 runtime path: $required" }
}
if ($Arm -eq "a4" -and -not (Test-Path -LiteralPath $bank)) { throw "A4 bank is missing" }
$healthText = & curl.exe --silent --show-error --fail --noproxy "*" --max-time 30 "$Url/v1/models"
if ($LASTEXITCODE -ne 0) { throw "Model endpoint unavailable" }
$health = $healthText | ConvertFrom-Json
if (@($health.data.id) -notcontains "Qwen/Qwen3-VL-32B-Instruct") { throw "Model identity drift" }
$arguments = @($runner,"--url",$Url,"--adb-path",$adb,"--manifest",$manifest,
    "--a345-arm",$Arm,"--a345-preflight-report",$preflight,
    "--a345-launch-receipt",(Resolve-Path $LaunchReceipt).Path,
    "--run-stage","${Arm}_scored_gate_then_full","--output-root",$output,
    "--generation-seed","3407","--max-tokens","32768","--observation-backend","uiautomator")
if ($Arm -eq "a4") { $arguments += @("--a345-workflow-bank",$bank) }
if ($ResumeSuiteDir) { $arguments += @("--resume-suite-dir",(Resolve-Path $ResumeSuiteDir).Path) }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "$Arm stopped; inspect checkpoint before any continuation" }
