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
            FROM supplier_options
        """).fetchone()["total"]

        print(f"Total supplier_options: {total}")
        print("-" * 140)

        summary = conn.execute("""
            SELECT option_code, COUNT(*) AS total
            FROM supplier_options
            GROUP BY option_code
            ORDER BY total DESC, option_code
        """).fetchall()

        print("Resumen por option_code:")
        for row in summary:
            print(f"- {row['option_code']}: {row['total']}")

        print("-" * 140)

        rows = conn.execute("""
            SELECT
                so.id,
                so.sourcing_request_id,
                so.option_code,
                so.supplier_name,
                so.cost_type,
                so.unit_cost,
                so.currency
            FROM supplier_options so
            ORDER BY so.id
            LIMIT 20
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 140)


if __name__ == "__main__":
    main()