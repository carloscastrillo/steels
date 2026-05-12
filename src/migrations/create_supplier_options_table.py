from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS supplier_options (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        option_code TEXT NOT NULL,
        supplier_name TEXT,
        cost_type TEXT NOT NULL,
        unit_cost REAL,
        total_cost REAL,
        currency TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

    CREATE INDEX IF NOT EXISTS idx_supplier_options_request
    ON supplier_options(sourcing_request_id);

    CREATE INDEX IF NOT EXISTS idx_supplier_options_code
    ON supplier_options(option_code);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla supplier_options creada correctamente.")


if __name__ == "__main__":
    main()