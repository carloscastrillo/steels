from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
SOURCE_DB_PATH = BASE_DIR / "db" / "steel_mvp.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
TEST_DB_PATH = BASE_DIR / "db" / "test_schema_tmp.db"


def get_tables(conn: sqlite3.Connection) -> list[str]:
    return sorted(
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
    )


def get_columns(conn: sqlite3.Connection, table: str) -> list[tuple]:
    return [
        (
            row[1],  # name
            row[2],  # type
            row[3],  # notnull
            row[5],  # pk
        )
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]


def get_indexes(conn: sqlite3.Connection) -> list[str]:
    return sorted(
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
    )


def main() -> None:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(SOURCE_DB_PATH) as source_conn:
        source_tables = get_tables(source_conn)
        source_indexes = get_indexes(source_conn)

    with sqlite3.connect(TEST_DB_PATH) as test_conn:
        test_conn.executescript(schema_sql)
        test_conn.commit()

        test_tables = get_tables(test_conn)
        test_indexes = get_indexes(test_conn)

        missing_tables = sorted(set(source_tables) - set(test_tables))
        extra_tables = sorted(set(test_tables) - set(source_tables))

        print("SMOKE TEST schema.sql")
        print("-" * 80)
        print(f"Tablas DB real : {len(source_tables)}")
        print(f"Tablas schema  : {len(test_tables)}")

        if missing_tables:
            print("TABLAS FALTANTES:")
            for t in missing_tables:
                print(f" - {t}")

        if extra_tables:
            print("TABLAS EXTRA:")
            for t in extra_tables:
                print(f" - {t}")

        column_errors = []

        with sqlite3.connect(SOURCE_DB_PATH) as source_conn:
            for table in source_tables:
                if table not in test_tables:
                    continue

                source_cols = get_columns(source_conn, table)
                test_cols = get_columns(test_conn, table)

                if source_cols != test_cols:
                    column_errors.append(table)

        if column_errors:
            print("TABLAS CON DIFERENCIAS DE COLUMNAS:")
            for t in column_errors:
                print(f" - {t}")

        print("-" * 80)
        print(f"Índices DB real: {len(source_indexes)}")
        print(f"Índices schema : {len(test_indexes)}")

        missing_indexes = sorted(set(source_indexes) - set(test_indexes))
        if missing_indexes:
            print("ÍNDICES FALTANTES:")
            for idx in missing_indexes:
                print(f" - {idx}")

        if not missing_tables and not extra_tables and not column_errors:
            print("OK: schema.sql crea las mismas tablas y columnas que la DB real.")
        else:
            raise SystemExit("ERROR: schema.sql no reproduce correctamente la DB real.")

    try:
        TEST_DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        print(f"AVISO: no se pudo borrar {TEST_DB_PATH} porque Windows lo mantiene bloqueado.")
        print("Puedes borrarlo manualmente cuando termine el proceso.")


if __name__ == "__main__":
    main()