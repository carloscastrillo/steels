from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS provider_capabilities (
        id INTEGER PRIMARY KEY,
        provider_code TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        product TEXT,
        grade_pattern TEXT,
        min_thickness_mm REAL,
        max_thickness_mm REAL,
        min_width_mm REAL,
        max_width_mm REAL,
        is_active INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_provider_capabilities_provider
    ON provider_capabilities(provider_code);

    CREATE INDEX IF NOT EXISTS idx_provider_capabilities_product
    ON provider_capabilities(product);
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)
        conn.commit()

    print("Tabla provider_capabilities creada correctamente.")


if __name__ == "__main__":
    main()