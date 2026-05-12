from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT
                so.id,
                so.unit_cost,
                so.is_rankable,
                sr.requested_tons
            FROM supplier_options so
            JOIN sourcing_requests sr
              ON sr.id = so.sourcing_request_id
            ORDER BY so.id
        """).fetchall()

        updated = 0

        for row in rows:
            total_cost = None

            if row["is_rankable"] == 1 and row["unit_cost"] is not None and row["requested_tons"] is not None:
                total_cost = float(row["unit_cost"]) * float(row["requested_tons"])

            conn.execute("""
                UPDATE supplier_options
                SET total_cost = ?
                WHERE id = ?
            """, (total_cost, row["id"]))
            updated += 1

        conn.commit()

    print(f"Supplier options con total_cost actualizado: {updated}")


if __name__ == "__main__":
    main()