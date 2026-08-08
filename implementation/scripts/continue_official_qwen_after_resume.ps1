[CmdletBinding()]
param(
    [int]$ResumeRunnerPid = 27352,
    [int]$PollSeconds = 20
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repositoryRoot "06_local_runtime\envs\androidworld\Scripts\python.exe"
$src = Join-Path $repositoryRoot "05_project\src"
$originalSuite = Join-Path $repositoryRoot "runs\official_qwen_mobile\official_qwen_20260808T012646_c8281b8f"
$resumeSuite = Join-Path $repositoryRoot "runs\official_qwen_mobile\official_qwen_20260808T081151_160c14c8"
$sourceManifest = Join-Path $repositoryRoot "05_project\configs\task_manifests\androidworld_hard_v2_instances.json"
$replacementManifest = Join-Path $repositoryRoot "05_project\configs\task_manifests\androidworld_hard_v2_replacements.final.json"
$rawCombined = Join-Path $repositoryRoot "reports\official_qwen32b_full_hard_combined_strict_raw.json"
$resumeOverlay = Join-Path $resumeSuite "layer_suite_summary.corrected_validity_overlay.json"
$finalCombined = Join-Path $repositoryRoot "reports\official_qwen32b_full_hard_combined_corrected_final.json"
$finalMarkdown = Join-Path $repositoryRoot "reports\official_qwen32b_full_hard_combined_corrected_final.md"
$finalReuse = Join-Path $repositoryRoot "reports\official_qwen32b_observation_reuse_final.json"

foreach ($required in @($python, $originalSuite, $resumeSuite, $sourceManifest)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path is absent: $required"
    }
}

Write-Host "Waiting for resume runner PID $ResumeRunnerPid..."
while (Get-Process -Id $ResumeRunnerPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds $PollSeconds
}

$originalSummary = Join-Path $originalSuite "layer_suite_summary.json"
$resumeSummary = Join-Path $resumeSuite "layer_suite_summary.json"
& $python (Join-Path $PSScriptRoot "analyze_official_qwen_suite.py") $originalSuite --output $originalSummary | Out-Null
& $python (Join-Path $PSScriptRoot "analyze_official_qwen_suite.py") $resumeSuite --output $resumeSummary | Out-Null

$resumeData = Get-Content -LiteralPath $resumeSummary -Raw | ConvertFrom-Json
if ($resumeData.completed_episode_count -ne 38) {
    throw "Resume suite ended without 38 completed episodes: $($resumeData.completed_episode_count)"
}

& $python (Join-Path $PSScriptRoot "merge_official_qwen_suite_summaries.py") `
    $originalSummary $resumeSummary --output $rawCombined | Out-Null

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $src
try {
    & $python (Join-Path $PSScriptRoot "build_official_parser_replacement_manifest.py") `
        $sourceManifest $rawCombined $replacementManifest `
        --include-infrastructure-summary $resumeSummary | Out-Null
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

$replacementData = Get-Content -LiteralPath $replacementManifest -Raw | ConvertFrom-Json
$overlayArgs = @(
    (Join-Path $PSScriptRoot "apply_official_qwen_validity_overlay.py"),
    $resumeSummary,
    $resumeOverlay,
    "--reason",
    "local_over_strict_parser"
)
foreach ($episodeId in $replacementData.parser_affected_episode_ids) {
    $overlayArgs += @("--exclude-episode-id", [string]$episodeId)
}
& $python @overlayArgs | Out-Null

$suiteRoot = Join-Path $repositoryRoot "runs\official_qwen_mobile"
$beforeSuites = @(Get-ChildItem -LiteralPath $suiteRoot -Directory -Filter "official_qwen_*" | ForEach-Object FullName)
$launcher = Join-Path $PSScriptRoot "run_official_qwen_h01.ps1"
& $launcher `
    -ManifestId FULL `
    -ManifestPath $replacementManifest `
    -RunStage "official_qwen32b_full_hard_parser_and_infra_replacements_v1" `
    -HeldOutIneligibleReason "replacement_for_local_implementation_or_infrastructure_invalid_source_records"
if ($LASTEXITCODE -ne 0) {
    throw "Replacement runner failed."
}

$afterSuites = @(Get-ChildItem -LiteralPath $suiteRoot -Directory -Filter "official_qwen_*" | ForEach-Object FullName)
$newSuites = @($afterSuites | Where-Object { $_ -notin $beforeSuites })
if ($newSuites.Count -ne 1) {
    throw "Could not identify exactly one replacement suite; found $($newSuites.Count)."
}
$replacementSuite = $newSuites[0]
$replacementSummary = Join-Path $replacementSuite "layer_suite_summary.json"
& $python (Join-Path $PSScriptRoot "analyze_official_qwen_suite.py") $replacementSuite --output $replacementSummary | Out-Null

& $python (Join-Path $PSScriptRoot "merge_official_qwen_suite_summaries.py") `
    $originalSummary $resumeOverlay $replacementSummary `
    --expected-eligible 57 --output $finalCombined | Out-Null
& $python (Join-Path $PSScriptRoot "render_official_qwen_suite_markdown.py") `
    $finalCombined --output $finalMarkdown | Out-Null
& $python (Join-Path $PSScriptRoot "analyze_official_qwen_observation_reuse.py") `
    $finalCombined --output $finalReuse | Out-Null

Write-Host "Corrected 57-key baseline completed: $finalCombined"
