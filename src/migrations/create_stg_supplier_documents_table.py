from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS stg_supplier_documents (
        id INTEGER PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,                -- pdf | excel | email | docx
        supplier_code TEXT,
        file_path TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        n_quotes_extracted INTEGER NOT NULL DEFAULT 0,
        raw_text TEXT,
        notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_documents_supplier_code
    ON stg_supplier_documents(supplier_code);

    CREATE INDEX IF NOT EXISTS idx_stg_supplier_documents_file_type
    ON stg_supplier_documents(file_type);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla stg_supplier_documents creada correctamente.")


if __name__ == "__main__":
    main()