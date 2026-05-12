from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


ALIASES_TO_LOAD = [
    {
        "alias_name": "AISLAMIENTOS Y CALORIFUGADOS CRIPTANA",
        "client_id": 5,
        "notes": "Alias manual validado desde sugerencia automática",
    },
    {
        "alias_name": "PEMSA CABLE MANAGEMENT, S. A.",
        "client_id": 102,
        "notes": "Alias manual validado desde sugerencia automática",
    },
    {
        "alias_name": "H. ÁNGEL BALLESTER",
        "client_id": 57,
        "notes": "Alias manual probable: abreviatura de HIJOS DE ANGEL BALLESTER S.L.",
    },
]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        inserted = 0
        updated = 0
        skipped = 0

        for item in ALIASES_TO_LOAD:
            existing = conn.execute("""
                SELECT id, client_id, notes
                FROM client_aliases
                WHERE alias_name = ?
            """, (item["alias_name"],)).fetchone()

            if existing:
                if existing[1] != item["client_id"] or existing[2] != item["notes"]:
                    conn.execute("""
                        UPDATE client_aliases
                        SET client_id = ?, notes = ?
                        WHERE id = ?
                    """, (item["client_id"], item["notes"], existing[0]))
                    updated += 1
                else:
                    skipped += 1
                continue

            conn.execute("""
                INSERT INTO client_aliases (alias_name, client_id, notes, created_at)
                VALUES (?, ?, ?, ?)
            """, (item["alias_name"], item["client_id"], item["notes"], created_at))
            inserted += 1

        conn.commit()

    print(f"Aliases insertados: {inserted}")
    print(f"Aliases actualizados: {updated}")
    print(f"Aliases omitidos: {skipped}")


if __name__ == "__main__":
    main()