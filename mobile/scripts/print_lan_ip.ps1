# Helper: print LAN IPv4 addresses for Flutter --dart-define=API_BASE_URL=
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
  Select-Object IPAddress, InterfaceAlias |
  Format-Table -AutoSize

Write-Host ""
Write-Host "Example:"
Write-Host '  flutter run --dart-define=API_BASE_URL=http://YOUR_IP:8000'
Write-Host '  flutter build apk --release --dart-define=API_BASE_URL=http://YOUR_IP:8000'
