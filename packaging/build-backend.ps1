$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv310\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
& $python -m PyInstaller (Join-Path $root "packaging\device_edge.spec") --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
