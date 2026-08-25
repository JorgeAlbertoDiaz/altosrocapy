import os
import re
import csv
import sqlite3
import argparse


def get_tsv_files(directory):
    return [
        f
        for f in os.listdir(directory)
        if f.endswith('.tsv') and not f.startswith('.')
    ]


def sanitize_column_name(name):
    name = (name or "").strip()

    if not name:
        name = "col"

    # reemplazar espacios por _
    name = re.sub(r"\s+", "_", name)

    # dejar solo letras, números y _
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)

    return name


def make_unique_columns(headers):
    seen = {}
    result = []

    for header in headers:
        if header not in seen:
            seen[header] = 1
            result.append(header)
        else:
            seen[header] += 1
            result.append(f"{header}_{seen[header]}")

    return result


def import_tsv(db_path, tsv_dir, only_schema=False):

    db_dir = os.path.dirname(db_path)

    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tsv_files = get_tsv_files(tsv_dir)

    print(f"Archivos TSV encontrados: {tsv_files}")

    for filename in tsv_files:

        table_name = os.path.splitext(filename)[0]
        filepath = os.path.join(tsv_dir, filename)

        print(f"Procesando tabla: {table_name}...")

        rows = []

        try:
            with open(filepath, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f, delimiter="\t")
                rows = list(reader)

        except UnicodeDecodeError:

            with open(filepath, "r", encoding="latin-1", newline="") as f:
                reader = csv.reader(f, delimiter="\t")
                rows = list(reader)

        if not rows:
            print(f"Advertencia: El archivo {filename} está vacío.")
            continue

        headers = rows[0]
        data_rows = rows[1:]

        headers = [
            sanitize_column_name(h) if h.strip() else f"col_{i+1}"
            for i, h in enumerate(headers)
        ]

        headers = make_unique_columns(headers)

        max_cols = len(headers)

        columns_def = ", ".join(
            [f"[{column}] TEXT" for column in headers]
        )

        cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")

        cursor.execute(
            f"CREATE TABLE [{table_name}] ({columns_def})"
        )

        if only_schema:
            print(
                f"Tabla [{table_name}] creada (solo estructura)."
            )
            continue

        placeholders = ", ".join(
            ["?" for _ in range(max_cols)]
        )

        column_list = ", ".join(
            [f"[{c}]" for c in headers]
        )

        insert_query = (
            f"INSERT INTO [{table_name}] "
            f"({column_list}) "
            f"VALUES ({placeholders})"
        )

        normalized_rows = []

        for row in data_rows:

            if len(row) < max_cols:
                row = row + [None] * (max_cols - len(row))

            elif len(row) > max_cols:
                row = row[:max_cols]

            row = [
                None if value == "NULL" else value
                for value in row
            ]

            normalized_rows.append(row)

        if normalized_rows:
            cursor.executemany(
                insert_query,
                normalized_rows
            )

        conn.commit()

        print(
            f"Tabla [{table_name}] importada con "
            f"{len(normalized_rows)} registros."
        )

    conn.close()


def dump_db_schema(db_path, md_out_path):

    md_dir = os.path.dirname(md_out_path)

    if md_dir and not os.path.exists(md_dir):
        os.makedirs(md_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    )

    tables = cursor.fetchall()

    with open(md_out_path, "w", encoding="utf-8") as f:

        f.write("# Estructura de la Base de Datos\n\n")

        f.write(
            "Este documento contiene la estructura "
            "de tablas (DDL) de la base de datos SQLite.\n\n"
        )

        for table_name, sql_def in tables:

            if not sql_def:
                continue

            f.write(
                f"## Tabla: `{table_name}`\n\n"
            )

            f.write("```sql\n")
            f.write(f"{sql_def};\n")
            f.write("```\n\n")

    print(
        f"Esquema exportado exitosamente a "
        f"{md_out_path}"
    )

    conn.close()


if __name__ == "__main__":

    SCRIPT_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    BASE_DIR = os.path.dirname(SCRIPT_DIR)

    default_db = os.path.join(
        BASE_DIR,
        "temps",
        "altosroca.db"
    )

    default_tsv_dir = os.path.join(
        BASE_DIR,
        "temps",
        "export_sqlserver"
    )

    default_dump_schema = os.path.join(
        BASE_DIR,
        "temps",
        "schema.md"
    )

    parser = argparse.ArgumentParser(
        description="Importar archivos TSV de SQL Server a SQLite."
    )

    parser.add_argument(
        "--db",
        default=default_db,
        help="Ruta a la BD SQLite"
    )

    parser.add_argument(
        "--tsv-dir",
        default=default_tsv_dir,
        help="Ruta al directorio de archivos TSV"
    )

    parser.add_argument(
        "--only-schema",
        action="store_true",
        help="Generar únicamente la estructura de tablas"
    )

    parser.add_argument(
        "--dump-schema",
        default=default_dump_schema,
        help="Ruta del archivo Markdown (.md)"
    )

    args = parser.parse_args()

    import_tsv(
        args.db,
        args.tsv_dir,
        args.only_schema
    )

    if args.dump_schema:
        dump_db_schema(
            args.db,
            args.dump_schema
        )

