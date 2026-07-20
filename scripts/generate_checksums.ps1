$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$checksumRoot = Join-Path $repoRoot "checksums"
New-Item -ItemType Directory -Force -Path $checksumRoot | Out-Null

$groups = @(
    @{
        Name = "papers"
        Paths = @(Join-Path $repoRoot "02_literature/papers")
    },
    @{
        Name = "official_sources"
        Paths = @(Join-Path $repoRoot "01_sources/official")
    },
    @{
        Name = "admin"
        Paths = @(Join-Path $repoRoot "00_admin")
    }
)

foreach ($group in $groups) {
    $rows = foreach ($path in $group.Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
        Get-ChildItem -LiteralPath $path -File -Recurse | ForEach-Object {
            $relative = $_.FullName.Substring($repoRoot.Length).TrimStart("\", "/").Replace("\", "/")
            [pscustomobject]@{
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                bytes = $_.Length
                path = $relative
            }
        }
    }
    $rows | Sort-Object path | Export-Csv -LiteralPath (Join-Path $checksumRoot "$($group.Name).sha256.csv") -NoTypeInformation -Encoding utf8
}

Write-Host "Checksums updated in $checksumRoot"
