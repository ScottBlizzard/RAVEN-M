$RuntimeRoot = Split-Path -Parent $PSScriptRoot
$SdkRoot = Join-Path $RuntimeRoot "android\sdk"
$AvdRoot = Join-Path $RuntimeRoot "android\avd"
$AndroidUserHome = Join-Path $RuntimeRoot "android\user_home"
$StudioRoot = Join-Path $RuntimeRoot "tools\android-studio"
$VenvRoot = Join-Path $RuntimeRoot "envs\androidworld"

$env:ANDROID_HOME = $SdkRoot
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:ANDROID_AVD_HOME = $AvdRoot
$env:ANDROID_USER_HOME = $AndroidUserHome
$env:GRADLE_USER_HOME = Join-Path $RuntimeRoot "cache\gradle"
$env:PIP_CACHE_DIR = Join-Path $RuntimeRoot "cache\pip"
# The current machine has JDK 25. The legacy sdkmanager launcher only parses
# older version strings unless this documented launcher escape hatch is set.
$env:SKIP_JDK_VERSION_CHECK = "true"
$studioJbr = Join-Path $StudioRoot "jbr"
if (Test-Path -LiteralPath (Join-Path $studioJbr "bin\java.exe")) {
    $env:JAVA_HOME = $studioJbr
}
elseif (-not $env:JAVA_HOME -or -not (Test-Path -LiteralPath (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
    $java = Get-Command java -ErrorAction SilentlyContinue
    if ($java) {
        $env:JAVA_HOME = Split-Path -Parent (Split-Path -Parent $java.Source)
    }
}

$toolPaths = @(
    (Join-Path $SdkRoot "platform-tools"),
    (Join-Path $SdkRoot "emulator"),
    (Join-Path $SdkRoot "cmdline-tools\latest\bin"),
    $(if ($env:JAVA_HOME) { Join-Path $env:JAVA_HOME "bin" })
)
$env:PATH = (($toolPaths + @($env:PATH)) -join [System.IO.Path]::PathSeparator)

$activate = Join-Path $VenvRoot "Scripts\Activate.ps1"
if (Test-Path -LiteralPath $activate) {
    . $activate
}
