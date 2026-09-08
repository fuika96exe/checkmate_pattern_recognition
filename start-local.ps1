$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:XDG_CONFIG_HOME = Join-Path $ProjectRoot ".wrangler-config"
$env:XDG_DATA_HOME = Join-Path $ProjectRoot ".wrangler-data"
$env:XDG_CACHE_HOME = Join-Path $ProjectRoot ".wrangler-cache"

$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
$PythonPath = if ($PythonCommand) {
  $PythonCommand.Source
} else {
  Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\*\python.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
}
if (-not $PythonPath) {
  throw "Python was not found. Install Python 3.12+ first."
}

Start-Process -FilePath $PythonPath `
  -ArgumentList "run.py" `
  -WorkingDirectory (Join-Path $ProjectRoot "backend") `
  -WindowStyle Hidden

Start-Process -FilePath "npm.cmd" `
  -ArgumentList "run", "dev" `
  -WorkingDirectory $ProjectRoot `
  -WindowStyle Hidden

function Wait-ForUrl($Url, $TimeoutSeconds = 60) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
      if ($response.StatusCode -lt 500) { return }
    } catch {}
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  throw "Service did not start: $Url"
}

Wait-ForUrl "http://127.0.0.1:8000/api/health"
Wait-ForUrl "http://127.0.0.1:3001/"
Start-Process "http://127.0.0.1:3001/"
Write-Host "Xiangqi app started at http://127.0.0.1:3001/"
Write-Host "Keep this window open while using the app. Press Enter to close this launcher."
[Console]::ReadLine() | Out-Null
