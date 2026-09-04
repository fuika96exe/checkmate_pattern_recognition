$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
  throw "Python was not found. Install Python 3.12+ first."
}

Start-Process -FilePath $PythonCommand.Source `
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
