from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS request_intakes (
        id INTEGER PRIMARY KEY,
        input_mode TEXT NOT NULL,
        raw_input_text TEXT,
        parsed_input_json TEXT,
        input_quality_status TEXT,
        match_quality TEXT,
        warnings_json TEXT,
        chosen_spec_id INTEGER,
        sourcing_request_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (chosen_spec_id) REFERENCES request_specs(id),
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

    CREATE INDEX IF NOT EXISTS idx_request_intakes_mode
    ON request_intakes(input_mode);

    CREATE INDEX IF NOT EXISTS idx_request_intakes_spec
    ON request_intakes(chosen_spec_id);

    CREATE INDEX IF NOT EXISTS idx_request_intakes_request
    ON request_intakes(sourcing_request_id);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla request_intakes creada correctamente.")


if __name__ == "__main__":
    main()