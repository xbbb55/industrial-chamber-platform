$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root "artifacts\electron\win-unpacked"
$artifactDir = Join-Path $root "artifacts"
$zip = Join-Path $artifactDir "Industrial-Chamber-Platform-win-x64-portable.zip"
if (-not (Test-Path $source)) { throw "Electron unpacked output not found: $source" }
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $source "*") -DestinationPath $zip -CompressionLevel Optimal
Write-Output "portable package: $zip"
