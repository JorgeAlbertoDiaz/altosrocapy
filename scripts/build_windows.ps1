# Build de AltosRoca para Windows: compila los .exe y los copia a una
# carpeta de destino configurable.
#
# Uso (desde PowerShell, en la raiz del proyecto):
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -Dest "D:\mi-carpeta"
#
# Requisitos: Python 3.12+ y PyInstaller (`py -m pip install pyinstaller`).

param(
    [string]$Dest = "C:\altos roca\dist-windows"
)

$ErrorActionPreference = "Stop"

# Raiz del proyecto = carpeta padre de scripts\
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = "py"
try { & $Python --version | Out-Null } catch { $Python = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }

$LogoData = "temps\logo.png;temps"

Write-Host "== Compilando AltosRoca.exe (windowed) ==" -ForegroundColor Cyan
& $Python -m PyInstaller --noconfirm --onefile --windowed `
    --name AltosRoca `
    --add-data "$ProjectRoot\$LogoData" `
    --distpath dist-windows --workpath build\tmp --specpath build `
    app\login.py
if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion de AltosRoca.exe" }

Write-Host "== Compilando AltosRocaDebug.exe (consola) ==" -ForegroundColor Cyan
& $Python -m PyInstaller --noconfirm --onefile `
    --name AltosRocaDebug `
    --add-data "$ProjectRoot\$LogoData" `
    --distpath dist-windows --workpath build\tmp --specpath build `
    app\login.py
if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion de AltosRocaDebug.exe" }

# Cerrar instancias en ejecucion antes de copiar
Get-Process AltosRoca, AltosRocaDebug -ErrorAction SilentlyContinue | Stop-Process -Force

# Destino: crear directorios si no existen
New-Item -ItemType Directory -Force $Dest | Out-Null
New-Item -ItemType Directory -Force "$Dest\data" | Out-Null

Copy-Item "dist-windows\AltosRoca.exe"      $Dest -Force
Copy-Item "dist-windows\AltosRocaDebug.exe" $Dest -Force
Copy-Item "data\altosroca.db"               "$Dest\data\" -Force

Write-Host "== Listo. Ejecutables y DB en: $Dest ==" -ForegroundColor Green
