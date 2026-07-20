param(
    [ValidateSet("P0", "P0P1", "All")]
    [string]$PaperScope = "P0P1",
    [ValidateSet("core", "core+alignment", "all")]
    [string]$RepositoryScope = "core+alignment"
)

$ErrorActionPreference = "Continue"
$failures = [System.Collections.Generic.List[string]]::new()

& (Join-Path $PSScriptRoot "snapshot_sources.ps1")
if ($LASTEXITCODE -ne 0) {
    $failures.Add("snapshot_sources")
}

& (Join-Path $PSScriptRoot "fetch_papers.ps1") -Scope $PaperScope
if ($LASTEXITCODE -ne 0) {
    $failures.Add("fetch_papers")
}

& (Join-Path $PSScriptRoot "clone_repositories.ps1") -Scope $RepositoryScope
if ($LASTEXITCODE -ne 0) {
    $failures.Add("clone_repositories")
}

& (Join-Path $PSScriptRoot "generate_checksums.ps1")
if ($LASTEXITCODE -ne 0) {
    $failures.Add("generate_checksums")
}

& (Join-Path $PSScriptRoot "audit_repository.ps1")
if ($LASTEXITCODE -ne 0) {
    $failures.Add("audit_repository")
}

if ($failures.Count -gt 0) {
    Write-Warning ("Bootstrap completed with failed stages: " + ($failures -join ", "))
    exit 2
}

Write-Host "Resource bootstrap completed successfully."

