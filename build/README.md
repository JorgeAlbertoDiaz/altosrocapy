# Build de AltosRoca para Windows

## Requisitos (una sola vez)

1. **Python 3.12+** para Windows: https://www.python.org/downloads/
   - En el instalador marcar "Add python.exe to PATH".
   - O con winget: `winget install --id Python.Python.3.12 -e`
2. **PyInstaller**:
   ```
   py -m pip install pyinstaller
   ```

No se necesita nada más: tkinter y sqlite3 vienen incluidos con Python en Windows.

## Compilación (línea de comandos)

Desde la **raíz del proyecto** (en PowerShell o CMD de Windows, NO desde WSL):

```
py -m PyInstaller build\app.spec --noconfirm --distpath dist-windows --workpath build\tmp
copy data\altosroca.db dist-windows\data\
```

Resultado:

```
dist-windows/
├── AltosRoca.exe        ← doble clic para probar la interfaz
└── data/altosroca.db    ← requerido junto al exe (portable)
```

Credenciales de prueba (tabla `Login`): `Admin / Lola88mora`, `MARCO / MKACHA1`, etc.

## Máxima compatibilidad: Windows 7 x86

Si el exe debe correr incluso en **Windows 7 de 32 bits** (p. ej. AMD Sempron),
la regla es:

- **Python de build obligatorio: 3.8** (la última versión que soporta Windows 7;
  3.9+ lo dejó de soportar). Un exe hecho con 3.9+ no arranca en una PC con
  Windows 7.
- **Exe de 32 bits** (x86): corre en Windows 7/8/10/11, tanto en equipos de 32
  como de 64 bits. Un exe de 64 bits solo corre en Windows de 64 bits.

El helper `scripts\build_windows.py` detecta el Python y, si es 3.8, fuerza
versiones de dependencias compatibles con 3.8 (p. ej. `fpdf2<2.8.4`, ya que
fpdf2 >= 2.8.4 dejó de soportar Python 3.8).

En Windows local (necesitás un Python 3.8 de 32 bits instalado):

```
py -3.8-32 -m pip install pyinstaller "fpdf2<2.8.4" "openpyxl<4" tkcalendar
py -3.8-32 scripts\build_windows.py --dest "C:\altos roca\dist-windows"
```

> El workflow de GitHub Actions ya produce ambas variantes automáticamente al
> taggear `v*` o con *Run workflow*: `AltosRoca-modern-x64.zip` (Windows 10/11)
> y `AltosRoca-win7-x86.zip` (máxima compatibilidad, hasta Windows 7 x86).

> Nota sobre Windows 7: Python 3.5+ usa el *Universal CRT*, que en Windows 7
> puede requerir la actualización KB2999226 si la PC no está al día. Si da el
> error "no es compatible con la versión de Windows", instalar primero esa
> actualización de Windows Update en la máquina de destino.

## Ejecutables de 32 y 64 bits (PCs viejas)

Un Windows de **32 bits no puede ejecutar un exe de 64 bits** (da el error
"No se puede ejecutar esta aplicación en el equipo"). Para que el programa
corra también en PCs viejas, generar las dos arquitecturas. PyInstaller no es
cross-compiler: el exe toma la arquitectura del Python que lo compila.

Usar el helper `scripts\build_windows.py`, una vez con cada Python:

```
py -0p                                    :: ver los Pythons instalados

:: 2) Compilar las dos arquitecturas al mismo destino
py -3-32 scripts\build_windows.py --dest "C:\altos roca\dist-windows"
py -3-64 scripts\build_windows.py --dest "C:\altos roca\dist-windows"
```

En el destino quedan `AltosRoca.exe` (nativo de la última compilación) más
`AltosRoca-32.exe` y `AltosRoca-64.exe` (junto con la carpeta `data/` en cada
caso). Se puede verificar la arquitectura de cualquier exe con:

```
py scripts\build_windows.py --check "C:\altos roca\dist-windows\AltosRoca-32.exe"
```

> Nota: un exe de 32 bits corre tanto en Windows de 32 como de 64 bits; uno de
> 64 bits solo en Windows de 64 bits. Si no sabés la arquitectura del destino,
> enviá el `AltosRoca-32.exe`.

## Compilación (interfaz)

Si no querés usar la terminal: instalar Python + PyInstaller igual,
luego abrir el proyecto en VS Code y ejecutar los dos comandos anteriores
desde la terminal integrada. No hay builder gráfico oficial de PyInstaller;
el spec (`build/app.spec`) es la forma declarativa de configurarlo.

## Base de datos portable

La app busca la base de datos en `data/altosroca.db` **junto al ejecutable**
(no dentro del exe). El spec incluye la DB dentro del bundle onefile solo como
fallback, pero en modo onefile PyInstaller la extrae a un directorio temporal
(`_MEIPASS`), no junto al exe. Por eso siempre se copia la carpeta `data/` al
lado del exe.

## Logo

El logo NO se toma de `dist-windows/data` (esa carpeta es solo la DB). Para
mostrarlo hay que empaquetarlo: agregar a `datas` en `build/app.spec`:

```python
datas=[("../data/altosroca.db", "data"), ("../temps/logo.png", "temps")],
```

y recompilar. Sin logo, la app muestra el texto "ALTOS ROCA" como fallback.

## CI (GitHub Actions)

El workflow `.github/workflows/build-windows.yml` se dispara manualmente
(`workflow_dispatch`) o al pushear un tag `v*`. Corre en `windows-latest`,
compila y sube como artifacts:

- `dist/AltosRoca.exe`
- `dist/AltosRoca-portable.zip` (exe + `data/altosroca.db`, listo para usar)

## Estructura del proyecto

Ver [docs/estructura-proyecto.md](../docs/estructura-proyecto.md).
No crear carpetas `dist/` o copias de `data/` fuera de lo indicado arriba.
