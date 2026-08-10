param([string]$Url = "http://127.0.0.1:18000")

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo "06_local_runtime\envs\androidworld\Scripts\python.exe"
$adb = Join-Path $repo "06_local_runtime\android\sdk\platform-tools\adb.exe"
$runner = Join-Path $repo "implementation\scripts\run_official_qwen_mobile.py"
$output = Join-Path $repo "runs\a4_donors"
foreach ($required in @($python, $adb, $runner)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing donor runtime path: $required" }
}
$healthText = & curl.exe --silent --show-error --fail --noproxy "*" --max-time 30 "$Url/v1/models"
if ($LASTEXITCODE -ne 0) { throw "Model health endpoint is unavailable at $Url" }
$health = $healthText | ConvertFrom-Json
$served = @($health.data | ForEach-Object { $_.id })
if ($served -notcontains "Qwen/Qwen3-VL-32B-Instruct") {
    throw "Frozen Qwen3-VL-32B is not served at $Url"
}
& $python $runner --url $Url --adb-path $adb --task ExpenseAddSingle `
    --seed 20260821 --max-steps 20 --run-stage a4_donor_acquisition `
    --diagnostic --output-root $output
if ($LASTEXITCODE -ne 0) { throw "Frozen A4 Expense donor acquisition stopped" }
