$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "activate_local.ps1")
$adb = Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe"
if (Test-Path -LiteralPath $adb) {
    & $adb emu kill
}
