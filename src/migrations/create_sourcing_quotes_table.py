from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS sourcing_quotes (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        supplier_code TEXT NOT NULL,
        supplier_name TEXT NOT NULL,
        quoted_price_per_ton REAL NOT NULL,
        transport_cost_per_ton REAL NOT NULL DEFAULT 0,
        surcharges_per_ton REAL NOT NULL DEFAULT 0,
        total_price_per_ton REAL NOT NULL,
        total_estimated_cost REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'EUR',
        quoted_tons REAL,
        lead_time_days INTEGER,
        transport_type TEXT,
        quality_confirmed TEXT,
        source_type TEXT NOT NULL DEFAULT 'manual',
        needs_manual_review INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

    CREATE INDEX IF NOT EXISTS idx_sourcing_quotes_request
    ON sourcing_quotes(sourcing_request_id);

    CREATE INDEX IF NOT EXISTS idx_sourcing_quotes_supplier
    ON sourcing_quotes(supplier_code);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla sourcing_quotes creada correctamente.")


if __name__ == "__main__":
    main()