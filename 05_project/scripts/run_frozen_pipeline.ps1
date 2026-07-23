$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $projectRoot
$runtimeRoot = Join-Path $repositoryRoot "06_local_runtime"
$python = Join-Path $runtimeRoot "envs\androidworld\Scripts\python.exe"
$adb = Join-Path $runtimeRoot "android\sdk\platform-tools\adb.exe"
$runner = Join-Path $PSScriptRoot "run_frozen_hard_suite.py"
$analyzer = Join-Path $PSScriptRoot "analyze_frozen_results.py"
$root = Join-Path $repositoryRoot "runs\frozen_hard_v1"

$phases = @(
    @{Phase = "breadth"; Suite = "hard_v1_breadth"},
    @{Phase = "strict_control"; Suite = "hard_v1_strict_control"},
    @{
        Phase = "confirmatory_additional"
        Suite = "hard_v1_confirmatory_additional"
    },
    @{Phase = "ablation_controls"; Suite = "hard_v1_ablation_controls"}
)

foreach ($item in $phases) {
    & $python $runner --adb-path $adb --phase $item.Phase `
        --suite-id $item.Suite
    if ($LASTEXITCODE -ne 0) {
        throw "Frozen phase $($item.Phase) failed with $LASTEXITCODE."
    }
}

$summaries = @(
    (Join-Path $root "hard_v1_breadth\suite_summary.json"),
    (Join-Path $root "hard_v1_strict_control\suite_summary.json"),
    (Join-Path $root "hard_v1_confirmatory_additional\suite_summary.json"),
    (Join-Path $root "hard_v1_ablation_controls\suite_summary.json")
)
& $python $analyzer --suite-summary $summaries
if ($LASTEXITCODE -ne 0) {
    throw "Frozen result analysis failed with $LASTEXITCODE."
}
