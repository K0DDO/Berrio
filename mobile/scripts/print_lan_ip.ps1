# Helper: print LAN IPv4 addresses for Flutter --dart-define=API_URL=
$addrs = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Select-Object -ExpandProperty IPAddress -Unique
Write-Host 'LAN IPv4:'
$addrs | ForEach-Object { Write-Host "  $_" }
Write-Host ''
Write-Host 'Examples:'
Write-Host '  flutter run --dart-define=API_URL=http://YOUR_IP:8000'
Write-Host '  flutter build apk --release --dart-define=API_URL=http://YOUR_IP'
