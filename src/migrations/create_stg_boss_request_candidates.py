from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    sql = """
    CREATE TABLE IF NOT EXISTS stg_boss_request_candidates (
        id INTEGER PRIMARY KEY,
        boss_row_id INTEGER NOT NULL,
        our_ref TEXT,
        client_name TEXT,
        client_id INTEGER,
        product TEXT,
        grade TEXT,
        thickness_mm REAL,
        width_mm REAL,
        tn REAL,
        missing_tons REAL,
        sheet_date TEXT,
        matched_material_count INTEGER NOT NULL,
        matched_material_id INTEGER,
        match_status TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (boss_row_id) REFERENCES stg_boss_matrix(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (matched_material_id) REFERENCES materials(id)
    );
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(sql)
        conn.commit()

    print("Tabla stg_boss_request_candidates creada correctamente.")


if __name__ == "__main__":
    main()
    