param(
    [ValidateSet("mobileagent", "uivoyager")]
    [string]$Arm,
    [string]$RepositoryRoot = "D:\ZJU\Summer_Camp\RAVEN-M-Research",
    [string]$ExternalRoot = "D:\ZJU\Summer_Camp\RAVEN-M-Research_external_v0_2",
    [string]$BasePython = "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe",
    [string]$RuntimeEnvRoot = "",
    [switch]$FinalizeExisting
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$envRoot = if ($RuntimeEnvRoot) {
    [IO.Path]::GetFullPath($RuntimeEnvRoot)
} else {
    Join-Path $RepositoryRoot "06_local_runtime\envs\multi_framework_v0_2"
}
$metaRoot = Join-Path $RepositoryRoot "05_project\metadata\multi_framework_s0_v0_2\controller_environments\$Arm"
$logRoot = Join-Path $RepositoryRoot "05_project\outputs\multi_framework_s0_v0_2"
New-Item -ItemType Directory -Force -Path $envRoot, $metaRoot, $logRoot | Out-Null

if ($Arm -eq "mobileagent") {
    $name = "mf_mobileagent_py311"
    $sourceRoot = Join-Path $ExternalRoot "MobileAgent\Mobile-Agent-v3.5\android_world_v3.5"
    $requirements = Join-Path $sourceRoot "requirements.txt"
    $extraRequirements = @()
}
else {
    $name = "mf_uivoyager_py311"
    $sourceRoot = Join-Path $ExternalRoot "UI-Voyager"
    $requirements = Join-Path $sourceRoot "androidworld\requirements.txt"
    # The frozen UI-Voyager controller imports yaml while its official
    # requirements omit PyYAML.  Its vendored AndroidWorld pyproject declares
    # FastAPI and Uvicorn, also omitted by that requirements file.  These pins
    # close only the declared/imported runtime dependency set; they do not
    # change prompts, controller logic, observations, actions, or decoding.
    $extraRequirements = @("PyYAML==6.0.3", "fastapi", "uvicorn")
}

function Invoke-CheckedPython {
    param([string[]]$Arguments)
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

$target = Join-Path $envRoot $name
$complete = Join-Path $metaRoot "complete"
if ((Test-Path -LiteralPath $target) -and -not (Test-Path -LiteralPath $complete) -and -not $FinalizeExisting) {
    throw "Refusing incomplete pre-existing controller environment: $target"
}
if ($FinalizeExisting -and -not (Test-Path -LiteralPath $target)) {
    throw "Cannot finalize missing controller environment: $target"
}
if (Test-Path -LiteralPath $complete) {
    Write-Output "$name=already_complete"
    exit 0
}
if (-not (Test-Path -LiteralPath $requirements)) {
    throw "Official requirements missing: $requirements"
}

Copy-Item -LiteralPath $requirements -Destination (Join-Path $metaRoot "official_requirements.txt")
(Get-FileHash -Algorithm SHA256 -LiteralPath $requirements).Hash.ToLowerInvariant() |
    Set-Content -Encoding ascii (Join-Path $metaRoot "official_requirements.sha256")
@(
    "source_root=$sourceRoot"
    "python=$BasePython"
    "runtime_env_root=$envRoot"
    "dependency_resolution_attempt=1"
    "bounded_adapter_patch_round=1"
    "bounded_adapter_patch_scope=dependency_closure_only"
    "extra_requirements=$($extraRequirements -join ',')"
    "finalize_existing=$FinalizeExisting"
) | Set-Content -Encoding utf8 (Join-Path $metaRoot "resolution_rule.txt")

$python = Join-Path $target "Scripts\python.exe"
if (-not $FinalizeExisting) {
    & $BasePython -m venv --copies $target
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual-environment creation failed with exit code $LASTEXITCODE"
    }
    $installArguments = @("-m", "pip", "install", "--disable-pip-version-check", "-r", $requirements) + $extraRequirements
    Invoke-CheckedPython $installArguments
    if ($Arm -eq "mobileagent") {
        # The official runner is a source-tree entry point and the S1 adapter
        # prepends this exact pinned root to sys.path.  Do not build an
        # unnecessary editable wheel (its setup.py depends on removed
        # pkg_resources behavior); record and audit the exact source instead.
        "source_import_mode=sys_path_exact_source_root" |
            Add-Content -Encoding utf8 (Join-Path $metaRoot "resolution_rule.txt")
    }
    else {
        $androidWorld = Join-Path $sourceRoot "androidworld"
        Invoke-CheckedPython @("-m", "pip", "install", "--disable-pip-version-check", "--no-deps", "-e", $androidWorld)
    }
}
Invoke-CheckedPython @("-m", "pip", "check")
& $python -m pip freeze --all | Sort-Object | Set-Content -Encoding utf8 (Join-Path $metaRoot "pip.freeze.txt")
if ($LASTEXITCODE -ne 0) { throw "pip freeze failed with exit code $LASTEXITCODE" }
& $python -m pip inspect | Set-Content -Encoding utf8 (Join-Path $metaRoot "pip.inspect.json")
if ($LASTEXITCODE -ne 0) { throw "pip inspect failed with exit code $LASTEXITCODE" }
& $python --version 2>&1 | Set-Content -Encoding utf8 (Join-Path $metaRoot "python.txt")
$manifestInputs = @(
    (Join-Path $target "pyvenv.cfg"),
    (Join-Path $target "Scripts\python.exe"),
    (Join-Path $metaRoot "official_requirements.txt"),
    (Join-Path $metaRoot "resolution_rule.txt"),
    (Join-Path $metaRoot "pip.freeze.txt"),
    (Join-Path $metaRoot "pip.inspect.json"),
    (Join-Path $metaRoot "python.txt")
)
$manifestInputs | ForEach-Object {
    if (-not (Test-Path -LiteralPath $_)) { throw "Environment manifest input missing: $_" }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToLowerInvariant()
    "$hash  $([IO.Path]::GetFullPath($_))"
} | Set-Content -Encoding utf8 (Join-Path $metaRoot "environment.manifest.sha256")
New-Item -ItemType File -Path $complete | Out-Null
Write-Output "$name=complete"
