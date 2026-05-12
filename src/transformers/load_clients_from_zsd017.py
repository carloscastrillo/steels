from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        source_rows = conn.execute("""
            SELECT DISTINCT
                TRIM(requester_code) AS sap_code,
                TRIM(requester_name) AS name
            FROM stg_sap_zsd017_sales
            WHERE requester_code IS NOT NULL
              AND TRIM(requester_code) <> ''
              AND requester_name IS NOT NULL
              AND TRIM(requester_name) <> ''
            ORDER BY name
        """).fetchall()

        inserted = 0
        updated = 0
        skipped = 0

        for row in source_rows:
            sap_code = row["sap_code"]
            name = row["name"]

            existing_by_code = conn.execute("""
                SELECT id, name, sap_code
                FROM clients
                WHERE sap_code = ?
            """, (sap_code,)).fetchone()

            if existing_by_code:
                if existing_by_code["name"] != name:
                    conn.execute("""
                        UPDATE clients
                        SET name = ?
                        WHERE id = ?
                    """, (name, existing_by_code["id"]))
                    updated += 1
                else:
                    skipped += 1
                continue

            existing_by_name = conn.execute("""
                SELECT id, name, sap_code
                FROM clients
                WHERE name = ?
            """, (name,)).fetchone()

            if existing_by_name:
                if not existing_by_name["sap_code"]:
                    conn.execute("""
                        UPDATE clients
                        SET sap_code = ?
                        WHERE id = ?
                    """, (sap_code, existing_by_name["id"]))
                    updated += 1
                else:
                    skipped += 1
                continue

            conn.execute("""
                INSERT INTO clients (name, sap_code, notes, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, sap_code, "Loaded from ZSD017 staging", created_at))
            inserted += 1

        conn.commit()

        total_clients = conn.execute("""
            SELECT COUNT(*) AS total
            FROM clients
        """).fetchone()["total"]

    print(f"Clientes fuente detectados: {len(source_rows)}")
    print(f"Clientes insertados: {inserted}")
    print(f"Clientes actualizados: {updated}")
    print(f"Clientes omitidos: {skipped}")
    print(f"Total clientes en core: {total_clients}")


if __name__ == "__main__":
    main()