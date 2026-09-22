"""Copia los datos de uptime.db a PostgreSQL una sola vez.

Uso:
    DATABASE_URL='postgresql://...' python scripts/migrate_sqlite_to_postgres.py --apply

Sin --apply solo muestra las filas que se copiarían.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path


TABLES = ("users", "service_records", "membership_payments")
PROJECT_DIR = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Migra datos SQLite a PostgreSQL.")
    parser.add_argument(
        "--sqlite-path", default=PROJECT_DIR / "uptime.db", help="Ruta del archivo SQLite origen."
    )
    parser.add_argument("--apply", action="store_true", help="Ejecuta la copia; sin esta opción es simulación.")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
        sys.exit("Define DATABASE_URL con la cadena de conexión PostgreSQL antes de ejecutar este script.")

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.is_file():
        sys.exit(f"No existe la base SQLite: {sqlite_path}")

    # Importar después de comprobar DATABASE_URL para que app.py elija PostgreSQL.
    sys.path.insert(0, str(PROJECT_DIR))
    from app import get_db, init_db

    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    try:
        available_tables = {
            row["name"]
            for row in source.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        counts = {
            table: source.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES
            if table in available_tables
        }
        print("Filas detectadas:", ", ".join(f"{table}={count}" for table, count in counts.items()))
        if not args.apply:
            print("Simulación terminada. Repite con --apply para copiar los datos.")
            return

        init_db()
        with get_db() as target:
            for table in TABLES:
                if table not in available_tables:
                    continue
                source_columns = [row[1] for row in source.execute(f"PRAGMA table_info({table})")]
                target_columns = {
                    row["column_name"]
                    for row in target.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
                        (table,),
                    ).fetchall()
                }
                columns = [column for column in source_columns if column in target_columns]
                if not columns:
                    continue
                quoted_columns = ", ".join(columns)
                placeholders = ", ".join("?" for _ in columns)
                insert = (
                    f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                    "ON CONFLICT (id) DO NOTHING"
                )
                rows = source.execute(f"SELECT {quoted_columns} FROM {table}").fetchall()
                for row in rows:
                    values = []
                    for column in columns:
                        value = row[column]
                        if table == "users" and column == "email_confirmed" and value is not None:
                            value = bool(value)
                        values.append(value)
                    target.execute(insert, tuple(values))
                target.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                )
                print(f"Copiadas {len(rows)} filas de {table}.")
    finally:
        source.close()


if __name__ == "__main__":
    main()
