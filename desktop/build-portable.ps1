$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $ProjectRoot "release-portable"
$ElectronZip = Get-ChildItem "$env:LOCALAPPDATA\electron\Cache" -Recurse -Filter "electron-v44.1.0-win32-x64.zip" | Select-Object -First 1

if (-not $ElectronZip) {
  throw "Electron runtime archive was not found"
}
if (Test-Path $OutputDir) {
  Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$temp = Join-Path $OutputDir "electron-runtime"
Expand-Archive -LiteralPath $ElectronZip.FullName -DestinationPath $temp
$runtimeRoot = Get-ChildItem $temp -Directory | Select-Object -First 1
Copy-Item (Join-Path $runtimeRoot.FullName "*") $OutputDir -Recurse -Force
Remove-Item -LiteralPath $temp -Recurse -Force

$resources = Join-Path $OutputDir "resources"
New-Item -ItemType Directory -Force -Path $resources | Out-Null
$stage = Join-Path $OutputDir "app-stage"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item (Join-Path $ProjectRoot "desktop\main.cjs") $stage -Force
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

$portableExe = Join-Path $OutputDir "象棋杀法识别.exe"
Move-Item -LiteralPath (Join-Path $OutputDir "electron.exe") -Destination $portableExe
Write-Host "Portable application created: $portableExe"
