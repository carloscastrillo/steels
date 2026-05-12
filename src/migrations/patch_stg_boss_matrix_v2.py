from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


NEW_COLUMNS = [
    ("am_flag", "TEXT"),
    ("luso_flag", "TEXT"),
    ("import_flag", "TEXT"),
    ("missing_tons", "REAL"),
    ("client_name", "TEXT"),
    ("sheet_date", "TEXT"),
    ("grouping_text", "TEXT"),
    ("agreement_am", "TEXT"),
    ("notes", "TEXT"),
    ("sales_price_or_cost", "REAL"),

    ("am_spot_cost", "REAL"),
    ("am_spot_cost_net", "REAL"),
    ("am_auto_cost", "REAL"),
    ("am_auto_cost_net", "REAL"),

    ("ssab_cost", "REAL"),
    ("ssab_cost_net", "REAL"),

    ("adi_cost", "REAL"),
    ("adi_cost_net", "REAL"),

    ("luso_cost", "REAL"),
    ("luso_cost_net", "REAL"),

    ("galmed_cost", "REAL"),
    ("leon_cost", "REAL"),

    ("tata_cost", "REAL"),
    ("tata_cost_net", "REAL"),

    ("bao_cfrfo", "REAL"),
    ("bao_ddp_hl", "REAL"),
    ("base_equivalent", "REAL"),

    ("offer_14", "REAL"),
    ("offer_15", "REAL"),
    ("offer_16", "REAL"),
    ("offer_17", "REAL"),
]


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    return column_name in [row[1] for row in cursor.fetchall()]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        for column_name, column_type in NEW_COLUMNS:
            if column_exists(conn, "stg_boss_matrix", column_name):
                print(f"La columna {column_name} ya existe")
                continue

            conn.execute(
                f"ALTER TABLE stg_boss_matrix ADD COLUMN {column_name} {column_type}"
            )
            print(f"Añadida columna: {column_name} ({column_type})")

        conn.commit()

    print("Patch aplicado correctamente.")


if __name__ == "__main__":
    main()