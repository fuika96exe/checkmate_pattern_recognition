$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $ProjectRoot "release-portable-final"
$ElectronZip = Get-ChildItem "$env:LOCALAPPDATA\electron\Cache" -Recurse -Filter "electron-v44.1.0-win32-x64.zip" | Select-Object -First 1

if (-not $ElectronZip) {
  throw "Electron runtime archive was not found"
}
if (Test-Path $OutputDir) {
  Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Expand-Archive -LiteralPath $ElectronZip.FullName -DestinationPath $OutputDir -Force

$resources = Join-Path $OutputDir "resources"
New-Item -ItemType Directory -Force -Path $resources | Out-Null
$stage = Join-Path $OutputDir "app-stage"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stage "desktop") | Out-Null
Copy-Item (Join-Path $ProjectRoot "desktop\main.cjs") (Join-Path $stage "desktop\main.cjs") -Force
Copy-Item (Join-Path $ProjectRoot "package.json") $stage -Force

& (Join-Path $ProjectRoot "node_modules\.bin\asar.cmd") pack $stage (Join-Path $resources "app.asar")
Remove-Item -LiteralPath $stage -Recurse -Force

$runtime = Join-Path $resources "app-runtime"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Copy-Item (Join-Path $ProjectRoot "dist") (Join-Path $runtime "dist") -Recurse -Force
Copy-Item (Join-Path $ProjectRoot "node_modules") (Join-Path $runtime "node_modules") -Recurse -Force
Copy-Item (Join-Path $ProjectRoot "package.json") (Join-Path $runtime "package.json") -Force
Copy-Item (Join-Path $ProjectRoot "vite.config.ts") (Join-Path $runtime "vite.config.ts") -Force
Copy-Item (Join-Path $ProjectRoot "next.config.ts") (Join-Path $runtime "next.config.ts") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $resources "backend") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $resources "backend-data") | Out-Null
Copy-Item (Join-Path $ProjectRoot "release-backend\xiangqi-backend.exe") (Join-Path $resources "backend\xiangqi-backend.exe") -Force
Copy-Item (Join-Path $ProjectRoot "backend\tests\fixtures") (Join-Path $resources "backend-data\tests\fixtures") -Recurse -Force

$portableExe = Join-Path $OutputDir "CheckmatePatternRecognition.exe"
Move-Item -LiteralPath (Join-Path $OutputDir "electron.exe") -Destination $portableExe
Write-Host "Portable application created: $portableExe"
