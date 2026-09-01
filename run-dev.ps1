$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process -FilePath "python" -ArgumentList "run.py" -WorkingDirectory (Join-Path $ProjectRoot "backend") -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Write-Host "象棋開局辨認實驗室正在啟動："
Write-Host "  前端 http://127.0.0.1:3001"
Write-Host "  後端 http://127.0.0.1:8000"
