# Estructura del proyecto (altosrocapy)

> Este archivo es una **referencia técnica**. Para la guía de uso (instalación,
> build y fotos) ver el [README de la raíz](../README.md). Para la guía de
> compilación ver `docs/compilar-exe.md`.

Estructura **canónica** del proyecto. No crear carpetas duplicadas (`dist/`,
`dist-windows/` anidadas, copias de `data/`, etc.). Si algo aparece duplicado,
suele ser un residuo de una compilación mal hecha: borrar y volver a compilar
siguiendo `scripts/build_windows.py`.

```
altosrocapy/
├── app/                  # ← TODO el código fuente Python (tkinter + sqlite3)
│   ├── login.py          # Ventana de login (punto de entrada del programa)
│   ├── principal.py      # Menú principal / panel
│   ├── registrar_socio.py# Alta y edición de socios (incluye foto/cámara)
│   ├── consultar_socios.py
│   ├── registrar_cobros.py
│   ├── anular_cobros.py
│   ├── historial_cobros.py
│   ├── caja.py
│   ├── registrar_gastos.py
│   ├── gestionar_gastos.py
│   ├── registrar_deudas.py
│   ├── cancelar_deudas.py
│   ├── acceso_socios.py
│   ├── consultar_estados_socios.py
│   ├── admin_cuentas.py
│   ├── abm_generico.py   # ABM genérico de tablas de control
│   ├── db.py             # Acceso a SQLite portable (data/altosroca.db)
│   ├── socios_foto.py    # Cómo se guardan/leen las fotos de socios
│   ├── resources.py      # Logo e iconos
│   ├── exporter.py       # Exportación a PDF/Excel
│   └── simclock.py       # Reloj simulado (para pruebas)
├── data/
│   └── altosroca.db      # Base de datos SQLite (NO versionada, ver .gitignore)
├── socios_img/           # Fotos de socios (se crea sola; NO versionada)
├── build/                # Specs autogenerados + temporales de PyInstaller
│   ├── *.spec            # Specs generados por el script de build (no editar)
│   ├── README.md
│   └── tmp/              # Workdir temporal (el build lo borra y recrea)
├── scripts/              # Scripts auxiliares / build
│   ├── build_windows.py  # ← RECETA ÚNICA de compilación del .exe (Windows)
│   └── import_tsv_to_sqlite.py
├── dist-windows/         # SOLO salida de la compilación en Windows (NO versionado)
│   ├── AltosRoca.exe     # Ejecutable generado
│   └── data/
│       └── altosroca.db  # Copia de la DB al lado del exe (requerida en runtime)
├── docs/                 # Documentación (este README, diagramas, especificaciones)
│   └── diagramas/
│       ├── *.png         # Diagramas renderizados (se muestran en los .md)
│       └── src/*.puml    # Código fuente PlantUML de los diagramas
├── temps/                # Material temporario / exports legacy (ignorado)
└── .github/workflows/    # CI: build automático del exe en windows-latest
```

## Reglas

1. **`scripts/build_windows.py` es la única receta de compilación.** No compilar
   con flags sueltos ni specs escritos a mano; eso genera directorios duplicados.
   El script borra el workdir temporario en cada build (evita que el .exe salga
   con código viejo en caché).
2. **`dist-windows/` nunca se edita a mano ni se versiona.** Se regenera con
   `py scripts\build_windows.py` y se le copia `data/altosroca.db` junto al exe.
3. La base de datos vive **solo** en `data/`; para distribuir se *copia* junto
   al exe. En ejecución, el exe busca `data/altosroca.db` **al lado de sí mismo**
   (no dentro de `_MEIPASS`, que es un temporario que se borra al cerrar).
4. Las fotos de socios viven en `socios_img/` y siguen la misma lógica de
   portabilidad que la base (ver `app/socios_foto.py` y sección 6 del README).
5. Compilar siempre en **Windows** (PyInstaller no hace cross-compile desde
   Linux); el script `build_windows.py` se ejecuta con PowerShell de Windows.
