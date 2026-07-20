param(
    [ValidateSet("core", "core+alignment", "all")]
    [string]$Scope = "core+alignment"
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $repoRoot "03_code/manifests/repositories.csv"
$cloneRoot = Join-Path $repoRoot "03_code/third_party"
$lockPath = Join-Path $repoRoot "03_code/manifests/repositories.lock.csv"

$allowed = switch ($Scope) {
    "core" { @("core") }
    "core+alignment" { @("core", "alignment") }
    "all" { @("core", "alignment", "optional") }
}

$rows = Import-Csv -LiteralPath $manifest
$locks = [System.Collections.Generic.List[object]]::new()

foreach ($row in $rows) {
    if ($row.priority -notin $allowed) {
        continue
    }

    $target = Join-Path $cloneRoot $row.clone_dir
    $status = ""
    $commit = ""
    $branch = ""

    if (Test-Path -LiteralPath (Join-Path $target ".git")) {
        $status = "already_present"
    }
    elseif (Test-Path -LiteralPath $target) {
        $status = "blocked_non_git_directory"
        Write-Warning "$($row.name): target exists but is not a Git repository."
    }
    else {
        Write-Host "[CLONE] $($row.name)"
        & git clone --depth 1 --filter=blob:none $row.url $target
        if ($LASTEXITCODE -eq 0) {
            $status = "cloned"
        }
        else {
            $status = "clone_failed"
        }
    }

    if (Test-Path -LiteralPath (Join-Path $target ".git")) {
        $commit = (& git -C $target rev-parse HEAD 2>$null)
        $branch = (& git -C $target branch --show-current 2>$null)
        if ([string]::IsNullOrWhiteSpace($branch)) {
            $branch = "detached"
        }
    }

    $locks.Add([pscustomobject]@{
        repo_id = $row.repo_id
        name = $row.name
        url = $row.url
        status = $status
        branch = $branch
        commit = $commit
        fetched_at = (Get-Date).ToString("s")
        clone_dir = $row.clone_dir
    })
}

$locks | Export-Csv -LiteralPath $lockPath -NoTypeInformation -Encoding utf8
$failed = @($locks | Where-Object status -in @("clone_failed", "blocked_non_git_directory")).Count
Write-Host "Repository lock written to $lockPath"
if ($failed -gt 0) {
    exit 2
}
