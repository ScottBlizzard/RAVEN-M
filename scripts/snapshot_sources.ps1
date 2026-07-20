$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot

$sources = @(
    @{
        Url = "https://google-research.github.io/android_world/"
        Target = "01_sources/official/androidworld/project_page.html"
    },
    @{
        Url = "https://google-research.github.io/android_world/task_list.html"
        Target = "01_sources/official/androidworld/task_list.html"
    },
    @{
        Url = "https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct"
        Target = "01_sources/official/qwen3_vl/model_card.html"
    },
    @{
        Url = "https://raw.githubusercontent.com/QwenLM/Qwen3-VL/main/cookbooks/mobile_agent.ipynb"
        Target = "01_sources/official/qwen3_vl/mobile_agent.ipynb"
    },
    @{
        Url = "https://zhoushengisnoob.github.io/"
        Target = "01_sources/official/people_lab/sheng_zhou_homepage.html"
    },
    @{
        Url = "https://eagle.zju.edu.cn/"
        Target = "01_sources/official/people_lab/eagle_lab.html"
    }
)

$statusRows = [System.Collections.Generic.List[object]]::new()
foreach ($source in $sources) {
    $target = Join-Path $repoRoot $source.Target
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    try {
        Invoke-WebRequest -Uri $source.Url -OutFile $target -MaximumRedirection 10 -UserAgent "RAVEN-M-research-bootstrap/1.0"
        $statusRows.Add([pscustomobject]@{
            url = $source.Url
            local_target = $source.Target
            status = "downloaded"
            bytes = (Get-Item -LiteralPath $target).Length
            sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            accessed_at = (Get-Date).ToString("s")
        })
        Write-Host "[OK] $($source.Url)"
    }
    catch {
        $statusRows.Add([pscustomobject]@{
            url = $source.Url
            local_target = $source.Target
            status = "download_failed"
            bytes = 0
            sha256 = ""
            accessed_at = (Get-Date).ToString("s")
        })
        Write-Warning "$($source.Url): $($_.Exception.Message)"
    }
}

$statusRows | Export-Csv -LiteralPath (Join-Path $repoRoot "01_sources/snapshot_status.csv") -NoTypeInformation -Encoding utf8

