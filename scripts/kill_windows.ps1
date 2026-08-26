# Cierra AltosRoca si quedo algun proceso abierto.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\kill_windows.ps1
Get-Process AltosRoca, AltosRocaDebug -ErrorAction SilentlyContinue | Stop-Process -Force
