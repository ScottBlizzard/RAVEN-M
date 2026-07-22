param(
    [switch]$InstallAndroidStudio
)

$ErrorActionPreference = "Stop"

$runtimeRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $runtimeRoot
$downloadRoot = Join-Path $runtimeRoot "downloads"
$studioRoot = Join-Path $runtimeRoot "tools\android-studio"
$sdkRoot = Join-Path $runtimeRoot "android\sdk"
$avdRoot = Join-Path $runtimeRoot "android\avd"
$androidUserHome = Join-Path $runtimeRoot "android\user_home"
$venvRoot = Join-Path $runtimeRoot "envs\androidworld"
$tempRoot = Join-Path $runtimeRoot "temp"

$directories = @(
    $downloadRoot,
    (Split-Path -Parent $studioRoot),
    $sdkRoot,
    $avdRoot,
    $androidUserHome,
    (Split-Path -Parent $venvRoot),
    (Join-Path $runtimeRoot "cache\gradle"),
    (Join-Path $runtimeRoot "cache\pip"),
    (Join-Path $runtimeRoot "logs"),
    $tempRoot
)
foreach ($directory in $directories) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

$studioArchive = Join-Path $downloadRoot "android-studio-quail2-windows.zip"
$studioUrl = "https://dl.google.com/dl/android/studio/ide-zips/2026.1.2.10/android-studio-quail2-windows.zip"
$studioSha256 = "fb0d9573d5252bf683b2255458b88fbc358166071d587a066e27cf3449d916b0"
$toolsArchive = Join-Path $downloadRoot "commandlinetools-win-15859902_latest.zip"
$toolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip"
$toolsSha256 = "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a"

function Get-VerifiedArchive {
    param(
        [string]$Url,
        [string]$Target,
        [string]$ExpectedSha256
    )
    if (Test-Path -LiteralPath $Target) {
        $existing = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existing -eq $ExpectedSha256) {
            Write-Host "[PRESENT] $(Split-Path -Leaf $Target)"
            return
        }
        Write-Host "[RESUME] Existing archive is incomplete or unverified: $(Split-Path -Leaf $Target)"
    }

    Write-Host "[DOWNLOAD] $Url"
    & curl.exe --location --fail --retry 5 --retry-all-errors --continue-at - --output $Target $Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed: $Url"
    }
    $actual = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256) {
        throw "Checksum mismatch for $Target. Expected $ExpectedSha256, got $actual"
    }
}

if ($InstallAndroidStudio) {
    Get-VerifiedArchive -Url $studioUrl -Target $studioArchive -ExpectedSha256 $studioSha256
}
Get-VerifiedArchive -Url $toolsUrl -Target $toolsArchive -ExpectedSha256 $toolsSha256

if ($InstallAndroidStudio -and -not (Test-Path -LiteralPath (Join-Path $studioRoot "bin\studio64.exe"))) {
    Write-Host "[EXTRACT] Android Studio"
    Expand-Archive -LiteralPath $studioArchive -DestinationPath (Split-Path -Parent $studioRoot) -Force
}

$latestTools = Join-Path $sdkRoot "cmdline-tools\latest"
if (-not (Test-Path -LiteralPath (Join-Path $latestTools "bin\sdkmanager.bat"))) {
    $toolsExtractRoot = Join-Path $tempRoot "commandlinetools"
    New-Item -ItemType Directory -Force -Path $toolsExtractRoot | Out-Null
    Expand-Archive -LiteralPath $toolsArchive -DestinationPath $toolsExtractRoot -Force
    New-Item -ItemType Directory -Force -Path $latestTools | Out-Null
    Copy-Item -Path (Join-Path $toolsExtractRoot "cmdline-tools\*") -Destination $latestTools -Recurse -Force
}

. (Join-Path $PSScriptRoot "activate_local.ps1")
$sdkmanager = Join-Path $latestTools "bin\sdkmanager.bat"
$avdmanager = Join-Path $latestTools "bin\avdmanager.bat"

Write-Host "[LICENSES] Accepting Android SDK licenses for this isolated SDK."
1..100 | ForEach-Object { "y" } | & $sdkmanager --sdk_root=$sdkRoot --licenses | Out-Host

$packageMarkers = [ordered]@{
    "platform-tools" = Join-Path $sdkRoot "platform-tools\adb.exe"
    "emulator" = Join-Path $sdkRoot "emulator\emulator.exe"
    "platforms;android-33" = Join-Path $sdkRoot "platforms\android-33\android.jar"
    "build-tools;33.0.2" = Join-Path $sdkRoot "build-tools\33.0.2\aapt2.exe"
    "system-images;android-33;google_apis;x86_64" = Join-Path $sdkRoot "system-images\android-33\google_apis\x86_64\system.img"
}
$missingPackages = @($packageMarkers.Keys | Where-Object { -not (Test-Path -LiteralPath $packageMarkers[$_]) })
if ($missingPackages.Count -gt 0) {
    Write-Host "[SDK] Installing missing Android SDK packages: $($missingPackages -join ', ')"
    & $sdkmanager "--sdk_root=$sdkRoot" $missingPackages
    foreach ($package in $missingPackages) {
        if (-not (Test-Path -LiteralPath $packageMarkers[$package])) {
            throw "sdkmanager did not finish installing $package. Run finish_android_sdk.ps1 if the Google downloader stalled."
        }
    }
}

$avdConfig = Join-Path $avdRoot "AndroidWorldAvd.avd\config.ini"
if (-not (Test-Path -LiteralPath $avdConfig)) {
    Write-Host "[AVD] Creating Pixel 6 / API 33 AndroidWorldAvd."
    "no" | & $avdmanager create avd --force --name "AndroidWorldAvd" --package "system-images;android-33;google_apis;x86_64" --device "pixel_6"
    if ($LASTEXITCODE -ne 0) {
        throw "AVD creation failed."
    }
}

& (Join-Path $PSScriptRoot "install_python_deps.ps1")

Write-Host "Local bootstrap complete. Run start_emulator.ps1 next."
