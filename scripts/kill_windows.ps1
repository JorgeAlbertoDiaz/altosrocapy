# Cierra AltosRoca si quedo algun proceso abierto.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\kill_windows.ps1
Get-Process AltosRoca, AltosRocaDebug -ErrorAction Ignore | Stop-Process -Force -ErrorAction Ignore

Write-Host "Procesos de AltosRoca finalizados."
Read-Host "Presione Enter para salir"
