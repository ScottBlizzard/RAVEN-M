param(
    [ValidateSet("P0", "P0P1", "All")]
    [string]$Scope = "P0P1"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $repoRoot "02_literature/metadata/papers.csv"
$paperRoot = Join-Path $repoRoot "02_literature/papers"
$logPath = Join-Path $repoRoot "02_literature/metadata/download_status.csv"

$allowed = switch ($Scope) {
    "P0" { @("P0") }
    "P0P1" { @("P0", "P1") }
    "All" { @("P0", "P1", "P2") }
}

$folderByPriority = @{
    "P0" = "P0_must_read"
    "P1" = "P1_core"
    "P2" = "P2_extended"
}

$records = Import-Csv -LiteralPath $manifest
$results = [System.Collections.Generic.List[object]]::new()

foreach ($record in $records) {
    if ($record.priority -notin $allowed) {
        continue
    }

    $targetDir = Join-Path $paperRoot $folderByPriority[$record.priority]
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    $target = Join-Path $targetDir $record.local_filename

    if ([string]::IsNullOrWhiteSpace($record.pdf_url)) {
        $results.Add([pscustomobject]@{
            paper_id = $record.paper_id
            priority = $record.priority
            filename = $record.local_filename
            status = "no_pdf_url"
            bytes = 0
            sha256 = ""
            url = $record.primary_url
            checked_at = (Get-Date).ToString("s")
        })
        continue
    }

    if (Test-Path -LiteralPath $target) {
        $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        $results.Add([pscustomobject]@{
            paper_id = $record.paper_id
            priority = $record.priority
            filename = $record.local_filename
            status = "already_present"
            bytes = (Get-Item -LiteralPath $target).Length
            sha256 = $hash
            url = $record.pdf_url
            checked_at = (Get-Date).ToString("s")
        })
        continue
    }

    $temporary = "$target.part"
    try {
        $downloadError = $null
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            try {
                Invoke-WebRequest -Uri $record.pdf_url -OutFile $temporary -MaximumRedirection 10 -TimeoutSec 90 -UserAgent "RAVEN-M-research-bootstrap/1.0"
                $downloadError = $null
                break
            }
            catch {
                $downloadError = $_
                if (Test-Path -LiteralPath $temporary) {
                    Remove-Item -LiteralPath $temporary -Force
                }
                if ($attempt -lt 3) {
                    Write-Warning "$($record.paper_id) attempt $attempt failed; retrying."
                    Start-Sleep -Seconds 2
                }
            }
        }
        if ($null -ne $downloadError) {
            $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($null -ne $curl) {
                Write-Warning "$($record.paper_id) switching to curl.exe fallback."
                & $curl.Source --location --fail --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 180 --output $temporary $record.pdf_url
                if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $temporary)) {
                    $downloadError = $null
                }
            }
        }
        if ($null -ne $downloadError) {
            throw $downloadError
        }
        $stream = [System.IO.File]::OpenRead($temporary)
        try {
            $header = New-Object byte[] 5
            $read = $stream.Read($header, 0, 5)
        }
        finally {
            $stream.Dispose()
        }

        $signature = if ($read -eq 5) { [System.Text.Encoding]::ASCII.GetString($header) } else { "" }
        if ($signature -ne "%PDF-") {
            throw "Downloaded content is not a PDF (header='$signature')."
        }

        Move-Item -LiteralPath $temporary -Destination $target -Force
        $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        $results.Add([pscustomobject]@{
            paper_id = $record.paper_id
            priority = $record.priority
            filename = $record.local_filename
            status = "downloaded"
            bytes = (Get-Item -LiteralPath $target).Length
            sha256 = $hash
            url = $record.pdf_url
            checked_at = (Get-Date).ToString("s")
        })
        Write-Host "[OK] $($record.paper_id) $($record.local_filename)"
    }
    catch {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
        $results.Add([pscustomobject]@{
            paper_id = $record.paper_id
            priority = $record.priority
            filename = $record.local_filename
            status = "download_failed"
            bytes = 0
            sha256 = ""
            url = $record.pdf_url
            checked_at = (Get-Date).ToString("s")
        })
        Write-Warning "$($record.paper_id) failed: $($_.Exception.Message)"
    }
}

$results | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding utf8
$failed = @($results | Where-Object status -eq "download_failed").Count
$downloaded = @($results | Where-Object status -in @("downloaded", "already_present")).Count
Write-Host "Complete: $downloaded available, $failed failed. Status: $logPath"
if ($failed -gt 0) {
    exit 2
}
