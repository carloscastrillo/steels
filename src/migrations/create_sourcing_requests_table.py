from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS sourcing_requests (
        id INTEGER PRIMARY KEY,
        source_row_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        request_spec_id INTEGER NOT NULL,
        our_ref TEXT NOT NULL,
        requested_tons REAL NOT NULL,
        missing_tons REAL,
        sheet_date TEXT,
        notes TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_row_id) REFERENCES stg_boss_matrix(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (request_spec_id) REFERENCES request_specs(id)
    );

    CREATE INDEX IF NOT EXISTS idx_sourcing_requests_client
    ON sourcing_requests(client_id);

    CREATE INDEX IF NOT EXISTS idx_sourcing_requests_spec
    ON sourcing_requests(request_spec_id);

    CREATE INDEX IF NOT EXISTS idx_sourcing_requests_our_ref
    ON sourcing_requests(our_ref);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla sourcing_requests creada correctamente.")


if __name__ == "__main__":
    main()