from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS request_specs (
        id INTEGER PRIMARY KEY,
        product TEXT NOT NULL,
        grade TEXT NOT NULL,
        thickness_mm REAL NOT NULL,
        width_mm REAL NOT NULL,
        thickness_tolerance_text TEXT,
        width_tolerance_text TEXT,
        cw_min REAL,
        cw_max REAL,
        spec_key TEXT NOT NULL UNIQUE,
        notes TEXT,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_request_specs_spec_key
    ON request_specs(spec_key);

    CREATE INDEX IF NOT EXISTS idx_request_specs_product_grade
    ON request_specs(product, grade);

    CREATE INDEX IF NOT EXISTS idx_request_specs_dimensions
    ON request_specs(thickness_mm, width_mm);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla request_specs creada correctamente.")


if __name__ == "__main__":
    main()