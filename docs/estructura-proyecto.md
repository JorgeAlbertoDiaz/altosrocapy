# Estructura del proyecto (altosrocapy)

Esta es la estructura **canónica** del proyecto. No crear carpetas duplicadas
(`dist/`, `dist-windows/` anidadas, copias de `data/`, etc.). Si algo de esto
aparece duplicado, es un residuo de una compilación mal hecha: borrar y volver
a compilar siguiendo `build/README.md`.

```
altosrocapy/
├── app/                  # Código fuente Python (tkinter + sqlite3)
│   ├── __init__.py
│   ├── login.py          # Ventana de login (punto de entrada)
│   └── db.py             # Acceso a SQLite portable (data/altosroca.db)
├── data/
│   └── altosroca.db      # Base de datos SQLite (NO versionada, ver .gitignore)
├── build/                # Todo lo necesario para compilar el .exe en Windows
│   ├── app.spec          # Spec de PyInstaller (fuente única de la compilación)
│   ├── README.md         # Instrucciones de compilación
│   └── tmp/              # Workdir temporal de PyInstaller (se puede borrar)
├── dist-windows/         # SOLO salida de la compilación en Windows
│   ├── AltosRoca.exe     # Ejecutable generado (NO versionado)
│   └── data/
│       └── altosroca.db  # Copia de la DB junto al exe (requerida en runtime)
├── docs/                 # Documentación (esquema, especificaciones)
├── scripts/              # Scripts auxiliares (import TSV → SQLite)
├── temps/                # Material temporario / exports legacy (ignorado)
└── .github/workflows/    # CI: build automático del exe en windows-latest
```

## Reglas

1. **`build/app.spec` es la única receta de compilación.** No compilar con
   flags sueltos ni specs generados al azar; eso genera directorios duplicados.
2. **`dist-windows/` nunca se edita a mano ni se versiona.** Se regenera con
   PyInstaller y se le copia `data/altosroca.db` al lado del exe.
3. La base de datos vive **solo** en `data/`; para distribuir, se *copia*
   junto al exe (ver nota sobre `_MEIPASS` en `build/README.md`).
4. Compilar siempre en Windows (PyInstaller no hace cross-compile desde Linux).
