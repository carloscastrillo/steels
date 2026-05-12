from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS sourcing_request_shortlist (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL UNIQUE,
        best_option_code TEXT,
        best_supplier_name TEXT,
        best_unit_cost REAL,
        best_total_cost REAL,

        second_option_code TEXT,
        second_supplier_name TEXT,
        second_unit_cost REAL,
        second_total_cost REAL,

        third_option_code TEXT,
        third_supplier_name TEXT,
        third_unit_cost REAL,
        third_total_cost REAL,

        am_spot_unit_cost REAL,
        am_spot_total_cost REAL,
        delta_best_vs_am_spot REAL,
        savings_total_vs_am_spot REAL,

        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla sourcing_request_shortlist creada correctamente.")


if __name__ == "__main__":
    main()