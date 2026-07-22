$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "activate_local.ps1")

$runtimeRoot = Split-Path -Parent $PSScriptRoot
$downloadRoot = Join-Path $runtimeRoot "downloads"
$tempRoot = Join-Path $runtimeRoot "temp"
$sdkRoot = $env:ANDROID_SDK_ROOT
$systemImageRoot = Join-Path $sdkRoot "system-images\android-33\google_apis\x86_64"
$partialArchive = Join-Path $downloadRoot "x86_64-33_r17.zip.partial"
$archive = Join-Path $downloadRoot "x86_64-33_r17.zip"
$url = "https://dl.google.com/android/repository/sys-img/google_apis/x86_64-33_r17.zip"
$expectedBytes = 1707857511
$expectedSha1 = "2b96f5bd5c79bfe1cc645e70b3e630b5755d9711"

if (-not (Test-Path -LiteralPath (Join-Path $systemImageRoot "source.properties"))) {
    if (-not (Test-Path -LiteralPath $archive)) {
        & curl.exe --ssl-no-revoke --location --fail --retry 20 --retry-all-errors --retry-delay 5 --continue-at - --output $partialArchive $url
        if ($LASTEXITCODE -ne 0) {
            throw "Android API 33 system image download failed."
        }
        if ((Get-Item -LiteralPath $partialArchive).Length -ne $expectedBytes) {
            throw "System image size check failed."
        }
        $actualSha1 = (Get-FileHash -LiteralPath $partialArchive -Algorithm SHA1).Hash.ToLowerInvariant()
        if ($actualSha1 -ne $expectedSha1) {
            throw "System image checksum mismatch: $actualSha1"
        }
        Move-Item -LiteralPath $partialArchive -Destination $archive
    }

    $actualSha1 = (Get-FileHash -LiteralPath $archive -Algorithm SHA1).Hash.ToLowerInvariant()
    if ($actualSha1 -ne $expectedSha1) {
        throw "System image checksum mismatch: $actualSha1"
    }

    $stage = Join-Path $tempRoot "system_image_33"
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    & tar.exe -xf $archive -C $stage
    if ($LASTEXITCODE -ne 0) {
        throw "System image extraction failed."
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $systemImageRoot) | Out-Null
    Move-Item -LiteralPath (Join-Path $stage "x86_64") -Destination $systemImageRoot
}

# The standalone emulator archive contains source.properties but no package.xml.
# avdmanager requires the local package descriptor even though emulator.exe is
# already present and checksum-verified.
$emulatorPackageXml = Join-Path $sdkRoot "emulator\package.xml"
if ((Test-Path -LiteralPath (Join-Path $sdkRoot "emulator\emulator.exe")) -and -not (Test-Path -LiteralPath $emulatorPackageXml)) {
    @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:repository xmlns:ns2="http://schemas.android.com/repository/android/common/02" xmlns:ns5="http://schemas.android.com/repository/android/generic/02">
  <license id="android-sdk-preview-license" type="text"/>
  <localPackage path="emulator" obsolete="false">
    <type-details xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns5:genericDetailsType"/>
    <revision><major>36</major><minor>6</minor><micro>11</micro></revision>
    <display-name>Android Emulator</display-name>
    <uses-license ref="android-sdk-preview-license"/>
  </localPackage>
</ns2:repository>
'@ | Set-Content -LiteralPath $emulatorPackageXml -Encoding UTF8
}

$required = @(
    (Join-Path $sdkRoot "platform-tools\adb.exe"),
    (Join-Path $sdkRoot "emulator\emulator.exe"),
    (Join-Path $sdkRoot "platforms\android-33\android.jar"),
    (Join-Path $sdkRoot "build-tools\33.0.2\aapt2.exe"),
    (Join-Path $systemImageRoot "system.img")
)
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required Android SDK component is missing: $path"
    }
}

$avdConfig = Join-Path $env:ANDROID_AVD_HOME "AndroidWorldAvd.avd\config.ini"
if (-not (Test-Path -LiteralPath $avdConfig)) {
    $avdmanager = Join-Path $sdkRoot "cmdline-tools\latest\bin\avdmanager.bat"
    "no" | & $avdmanager create avd --force --name "AndroidWorldAvd" --package "system-images;android-33;google_apis;x86_64" --device "pixel_6"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $avdConfig)) {
        throw "AndroidWorldAvd creation failed."
    }
}

Write-Host "Android SDK, API 33 system image, and AndroidWorldAvd: OK"
