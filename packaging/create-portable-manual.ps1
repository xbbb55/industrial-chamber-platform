$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$electronDist = Join-Path $root "node_modules\electron\dist"
$backendDist = Join-Path $root "dist\device_edge"
$artifactDir = Join-Path $root "artifacts"
$stage = Join-Path $artifactDir "Industrial-Chamber-Platform-win-x64-portable"
$appSource = Join-Path $root ".codex-temp\electron-app"
$zip = Join-Path $artifactDir "Industrial-Chamber-Platform-win-x64-portable.zip"

if (-not (Test-Path (Join-Path $electronDist "electron.exe"))) { throw "Electron runtime not found: $electronDist" }
if (-not (Test-Path (Join-Path $backendDist "device_edge.exe"))) { throw "PyInstaller output not found: $backendDist" }

if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
if (Test-Path $appSource) { Remove-Item -LiteralPath $appSource -Recurse -Force }
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
New-Item -ItemType Directory -Force -Path $stage, (Join-Path $stage "resources"), $appSource | Out-Null
Copy-Item (Join-Path $electronDist "*") $stage -Recurse -Force
Rename-Item (Join-Path $stage "electron.exe") "Industrial Chamber Platform.exe"
Copy-Item (Join-Path $PSScriptRoot "..\electron") (Join-Path $appSource "electron") -Recurse -Force
Copy-Item (Join-Path $root "package.json") (Join-Path $appSource "package.json") -Force
& (Join-Path $root "node_modules\.bin\asar.cmd") pack $appSource (Join-Path $stage "resources\app.asar")
if ($LASTEXITCODE -ne 0) { throw "asar pack failed with exit code $LASTEXITCODE" }
Copy-Item $backendDist (Join-Path $stage "resources\device_edge") -Recurse -Force
Copy-Item (Join-Path $PSScriptRoot "device-edge.config.sample.json") (Join-Path $stage "resources\device-edge.config.sample.json") -Force
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -CompressionLevel Optimal
Write-Output "portable package: $zip"
