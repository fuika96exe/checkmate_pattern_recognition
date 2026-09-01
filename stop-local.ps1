$ports = 3001, 8000
$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $ports -contains $_.LocalPort }
foreach ($connection in $connections) {
  Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
}
Write-Host "Xiangqi app services stopped."
