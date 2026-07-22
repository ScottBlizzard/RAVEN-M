$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "activate_local.ps1")

$runtimeRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $runtimeRoot
$venvRoot = Join-Path $runtimeRoot "envs\androidworld"
$androidWorldRoot = Join-Path $repoRoot "03_code\third_party\android_world"

if (-not (Test-Path -LiteralPath (Join-Path $venvRoot "Scripts\python.exe"))) {
    & python -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python 3.11 virtual environment."
    }
}

$python = Join-Path $venvRoot "Scripts\python.exe"
& $python -m pip install --upgrade pip setuptools wheel
& $python -m pip install --prefer-binary --progress-bar off --timeout 120 --retries 5 -r (Join-Path $androidWorldRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "AndroidWorld requirements installation failed."
}

# These are declared by the package metadata but omitted from requirements.txt.
& $python -m pip install --prefer-binary --progress-bar off --timeout 120 --retries 5 fastapi uvicorn
& $python -m pip install --no-deps --editable $androidWorldRoot
& $python (Join-Path $PSScriptRoot "patch_android_env_windows.py")
if ($LASTEXITCODE -ne 0) {
    throw "Could not apply the AndroidEnv Python 3.11 Windows compatibility fix."
}
$venvSiteRoot = (& $python -c "import site; print(site.getsitepackages()[0])").Trim()
$pthPath = Join-Path $venvSiteRoot "raven_m_androidworld_compat.pth"
# Make the project-local launch helpers importable. The compatibility layer is
# loaded explicitly by run_androidworld.py instead of at every Python startup;
# this avoids interfering with pip's isolated build environments.
$PSScriptRoot | Set-Content -LiteralPath $pthPath -Encoding ASCII
& $python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "The Python environment contains broken dependencies."
}

& $python -c "import android_world, android_env, cv2, grpc, matplotlib, numpy, pandas; print('AndroidWorld Python environment: OK')"
