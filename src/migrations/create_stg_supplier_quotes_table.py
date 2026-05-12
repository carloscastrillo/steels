from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS stg_supplier_quotes (
        id INTEGER PRIMARY KEY,
        supplier_document_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,                  -- pdf | excel | email
        supplier_code TEXT,
        supplier_name TEXT,

        extracted_grade TEXT,
        extracted_thickness_mm REAL,
        extracted_width_mm REAL,
        extracted_price_per_ton REAL,
        currency TEXT,
        incoterm TEXT,
        lead_time_days INTEGER,
        valid_until TEXT,

        raw_row_json TEXT,
        raw_text_snippet TEXT,

        matched_sourcing_request_id INTEGER,
        review_status TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
        notes TEXT,
        created_at TEXT NOT NULL,

        FOREIGN KEY (supplier_document_id) REFERENCES stg_supplier_documents(id),
        FOREIGN KEY (matched_sourcing_request_id) REFERENCES sourcing_requests(id)
    );

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_document
    ON stg_supplier_quotes(supplier_document_id);

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_supplier_code
    ON stg_supplier_quotes(supplier_code);

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_review_status
    ON stg_supplier_quotes(review_status);

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_matched_request
    ON stg_supplier_quotes(matched_sourcing_request_id);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla stg_supplier_quotes creada correctamente.")


if __name__ == "__main__":
    main()