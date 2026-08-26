# Agrega exclusiones de Windows Defender para la carpeta de distribucion
# de AltosRoca y para la carpeta de compilacion del proyecto.
#
# Debe ejecutarse como ADMINISTRADOR (Add-MpPreference lo requiere):
#   powershell -ExecutionPolicy Bypass -File scripts\exclusion_defender.ps1

param(
    [string[]]$Paths = @("C:\altos roca")
)

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: este script debe ejecutarse como Administrador." -ForegroundColor Red
    Write-Host "Clic derecho en PowerShell -> 'Ejecutar como administrador' y volver a intentar."
    Read-Host "Presione Enter para salir"
    exit 1
}

foreach ($p in $Paths) {
    Add-MpPreference -ExclusionPath $p
    Write-Host "Excluido del analisis: $p" -ForegroundColor Green
}

Read-Host "Presione Enter para salir"
