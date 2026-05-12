from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS sourcing_decisions (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        selected_quote_id INTEGER NOT NULL,
        decision_reason TEXT,
        decided_by TEXT,
        decided_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id),
        FOREIGN KEY (selected_quote_id) REFERENCES sourcing_quotes(id)
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_sourcing_decisions_request_unique
    ON sourcing_decisions(sourcing_request_id);

    CREATE INDEX IF NOT EXISTS idx_sourcing_decisions_quote
    ON sourcing_decisions(selected_quote_id);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla sourcing_decisions creada correctamente.")


if __name__ == "__main__":
    main()