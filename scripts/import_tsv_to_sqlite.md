# Intruccioens de uso

El script `import_tsv_to_sqlite.py` permite que a partir de los archivos `.tsv` se pueda generar la base de datos `sqlite`, para poder correrlo asegurate que los archivos esten al mismo nivel que este archivo.

   ```bash
   python3 scripts/import_tsv_to_sqlite.py
   ```


También puedes personalizar las rutas de la base de datos y de la carpeta TSV usando los argumentos `--db` y `--tsv-dir` si lo requieres.


   ```bash
   python3 scripts/import_tsv_to_sqlite.py --db="../temps/altosroca.db" --tsv-dir="../temps/export_sqlserver/"
   ```


El script tambien incluye una **Opción `--only-schema`**: El script ahora soporta argumentos de línea de comandos. Puedes ejecutarlo especificando la bandera `--only-schema` si deseas generar únicamente las tablas vacías para documentarlas luego:
   ```bash
   python3 scripts/import_tsv_to_sqlite.py --only-schema
   ```


