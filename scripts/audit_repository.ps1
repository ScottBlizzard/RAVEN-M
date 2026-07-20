$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

$paperManifest = Import-Csv -LiteralPath (Join-Path $repoRoot "02_literature/metadata/papers.csv")
$repoManifest = Import-Csv -LiteralPath (Join-Path $repoRoot "03_code/manifests/repositories.csv")

$folderByPriority = @{
    "P0" = "P0_must_read"
    "P1" = "P1_core"
    "P2" = "P2_extended"
}

$paperRows = foreach ($paper in $paperManifest) {
    $path = Join-Path $repoRoot ("02_literature/papers/{0}/{1}" -f $folderByPriority[$paper.priority], $paper.local_filename)
    [pscustomobject]@{
        id = $paper.paper_id
        priority = $paper.priority
        available = Test-Path -LiteralPath $path
        path = $path.Substring($repoRoot.Length).TrimStart("\", "/")
    }
}

$repoRows = foreach ($repo in $repoManifest) {
    $path = Join-Path $repoRoot ("03_code/third_party/{0}/.git" -f $repo.clone_dir)
    [pscustomobject]@{
        id = $repo.repo_id
        priority = $repo.priority
        available = Test-Path -LiteralPath $path
        path = "03_code/third_party/$($repo.clone_dir)"
    }
}

$summary = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    papers_total = $paperRows.Count
    p0_available = @($paperRows | Where-Object { $_.priority -eq "P0" -and $_.available }).Count
    p0_total = @($paperRows | Where-Object priority -eq "P0").Count
    p1_available = @($paperRows | Where-Object { $_.priority -eq "P1" -and $_.available }).Count
    p1_total = @($paperRows | Where-Object priority -eq "P1").Count
    repositories_available = @($repoRows | Where-Object available).Count
    repositories_total = $repoRows.Count
}

$paperRows | Export-Csv -LiteralPath (Join-Path $repoRoot "02_literature/metadata/library_audit.csv") -NoTypeInformation -Encoding utf8
$repoRows | Export-Csv -LiteralPath (Join-Path $repoRoot "03_code/manifests/repository_audit.csv") -NoTypeInformation -Encoding utf8
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot "checksums/audit_summary.json") -Encoding utf8
$summary | Format-List
