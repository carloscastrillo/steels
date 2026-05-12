from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def describe_database() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")

        tables_cursor = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)
        tables = [row[0] for row in tables_cursor.fetchall()]

        for table in tables:
            print(f"\n=== TABLA: {table} ===")

            columns_cursor = connection.execute(f"PRAGMA table_info({table});")
            columns = columns_cursor.fetchall()

            print("Columnas:")
            for col in columns:
                cid, name, col_type, notnull, default_value, pk = col
                print(
                    f"  - {name} | {col_type} | "
                    f"NOT NULL={bool(notnull)} | PK={bool(pk)} | DEFAULT={default_value}"
                )

            fk_cursor = connection.execute(f"PRAGMA foreign_key_list({table});")
            foreign_keys = fk_cursor.fetchall()

            if foreign_keys:
                print("Foreign keys:")
                for fk in foreign_keys:
                    (
                        _id,
                        _seq,
                        ref_table,
                        from_col,
                        to_col,
                        on_update,
                        on_delete,
                        match,
                    ) = fk
                    print(
                        f"  - {from_col} -> {ref_table}.{to_col} | "
                        f"ON UPDATE {on_update} | ON DELETE {on_delete} | MATCH {match}"
                    )
            else:
                print("Foreign keys: ninguna")


if __name__ == "__main__":
    describe_database()