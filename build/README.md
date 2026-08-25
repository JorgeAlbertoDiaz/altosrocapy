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
