import os
import sqlite3
import csv
import argparse

def get_tsv_files(directory):
    return [f for f in os.listdir(directory) if f.endswith('.tsv') and not f.startswith('.')]

def import_tsv(db_path, tsv_dir, only_schema=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tsv_files = get_tsv_files(tsv_dir)
    print(f'Archivos TSV encontrados: {tsv_files}')
    
    for filename in tsv_files:
        table_name = os.path.splitext(filename)[0]
        filepath = os.path.join(tsv_dir, filename)
        
        print(f'Procesando tabla: {table_name}...')
        
        # Leer el archivo completo para determinar la cantidad de columnas
        rows = []
        max_cols = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    rows.append(row)
                    if len(row) > max_cols:
                        max_cols = len(row)
        except UnicodeDecodeError:
            rows = []
            max_cols = 0
            with open(filepath, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    rows.append(row)
                    if len(row) > max_cols:
                        max_cols = len(row)
        
        if max_cols == 0:
            print(f'Advertencia: El archivo {filename} está vacío.')
            continue
            
        # Crear la tabla con columnas col_1, col_2, ...
        columns_def = ', '.join([f'col_{i+1} TEXT' for i in range(max_cols)])
        cursor.execute(f'DROP TABLE IF EXISTS [{table_name}]')
        cursor.execute(f'CREATE TABLE [{table_name}] ({columns_def})')
        
        if only_schema:
            print(f'Tabla [{table_name}] creada (solo estructura).')
            continue
            
        # Insertar filas
        placeholders = ', '.join(['?' for _ in range(max_cols)])
        insert_query = f'INSERT INTO [{table_name}] VALUES ({placeholders})'
        
        # Normalizar filas para que coincida la cantidad de columnas
        normalized_rows = []
        for r in rows:
            if len(r) < max_cols:
                r = r + [None] * (max_cols - len(r))
            elif len(r) > max_cols:
                r = r[:max_cols]
            r = [None if val == 'NULL' else val for val in r]
            normalized_rows.append(r)
            
        cursor.executemany(insert_query, normalized_rows)
        conn.commit()
        print(f'Tabla [{table_name}] importada con {len(normalized_rows)} registros.')
        
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Importar archivos TSV de SQL Server a SQLite.')
    parser.add_argument('--db', default='/home/jorge/Proyectos/altosrocapy/temps/altosroca.db', help='Ruta a la BD SQLite')
    parser.add_argument('--tsv-dir', default='/home/jorge/Proyectos/altosrocapy/temps/export_sqlserver', help='Ruta al directorio de archivos TSV')
    parser.add_argument('--only-schema', action='store_true', help='Generar únicamente la estructura de tablas, sin importar registros')
    
    args = parser.parse_args()
    import_tsv(args.db, args.tsv_dir, args.only_schema)
