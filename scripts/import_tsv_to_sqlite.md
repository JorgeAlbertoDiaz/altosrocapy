# Instrucciones de uso

El script `import_tsv_to_sqlite.py` permite generar la base de datos `sqlite` a partir de los archivos `.tsv` exportados.

Las rutas por defecto del script están resueltas de forma dinámica relativas a la ubicación del propio script, por lo que funcionará sin importar la carpeta de ejecución o la máquina en la que te encuentres.

## Uso Básico (Importación Completa)

Ejecuta el script desde la raíz del proyecto para realizar la importación de datos completa:

```bash
python3 scripts/import_tsv_to_sqlite.py
```

Esto generará la base de datos completa en `temps/altosroca.db` e importará todos los registros de la carpeta `temps/export_sqlserver/`.

## Solo Estructura (Sin Datos)

Si deseas generar únicamente las tablas vacías (útil para pruebas o documentación) sin importar registros:

```bash
python3 scripts/import_tsv_to_sqlite.py --only-schema
```

## Volcar la Estructura a Markdown (.md)

Para generar la documentación DDL de la estructura de tablas de la base de datos en formato markdown (sin datos sensibles):

```bash
python3 scripts/import_tsv_to_sqlite.py --only-schema --dump-schema temps/schema.md
```

Esto creará un archivo `temps/schema.md` limpio con la sintaxis `CREATE TABLE` de cada tabla.

## Parámetros Opcionales

Puedes sobrescribir las rutas predeterminadas utilizando los siguientes argumentos de línea de comandos:

* `--db`: Especifica una ruta personalizada para la base de datos SQLite.
* `--tsv-dir`: Especifica la ruta de la carpeta que contiene los archivos `.tsv`.
* `--dump-schema`: Especifica la ruta del archivo Markdown de salida para documentar el esquema.

Ejemplo con rutas personalizadas:
```bash
python3 scripts/import_tsv_to_sqlite.py --db "/ruta/personalizada/database.db" --tsv-dir "/ruta/personalizada/tsv_files"
```