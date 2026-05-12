from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM materials
        """).fetchone()["total"]

        print(f"Total materials: {total}")
        print("-" * 120)

        rows = conn.execute("""
            SELECT
                m.id,
                c.name AS client_name,
                c.sap_code AS client_sap_code,
                m.quality,
                m.thickness_mm,
                m.width_mm,
                m.length_mm,
                m.coating,
                m.product_form_code,
                m.product_form_text,
                m.material_key,
                m.technical_notes
            FROM materials m
            JOIN clients c ON c.id = m.client_id
            ORDER BY c.name, m.id
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 120)


if __name__ == "__main__":
    main()