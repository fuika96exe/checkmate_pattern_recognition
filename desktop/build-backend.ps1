$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$OutputDir = Join-Path $ProjectRoot "release-backend"

if (Test-Path $OutputDir) {
  Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

& $Python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name xiangqi-backend `
  --paths (Join-Path $ProjectRoot "backend") `
  --distpath $OutputDir `
  --workpath (Join-Path $ProjectRoot "build\pyinstaller") `
  --specpath (Join-Path $ProjectRoot "build\pyinstaller") `
  (Join-Path $ProjectRoot "backend\run_desktop.py")

if (-not (Test-Path (Join-Path $OutputDir "xiangqi-backend.exe"))) {
  throw "Backend executable generation failed"
}
