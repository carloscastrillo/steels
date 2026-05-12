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
        print("-" * 120)

        summary = conn.execute("""
            SELECT
                option_code,
                COUNT(*) AS total_rows,
                SUM(CASE WHEN unit_cost IS NULL THEN 1 ELSE 0 END) AS null_cost_rows,
                SUM(CASE WHEN unit_cost = 0 THEN 1 ELSE 0 END) AS zero_cost_rows,
                SUM(CASE WHEN unit_cost > 0 THEN 1 ELSE 0 END) AS positive_cost_rows,
                MIN(CASE WHEN unit_cost > 0 THEN unit_cost END) AS min_positive_cost,
                MAX(unit_cost) AS max_cost
            FROM supplier_options
            GROUP BY option_code
            ORDER BY option_code
        """).fetchall()

        print("Resumen por option_code:")
        for row in summary:
            print(
                f"- {row['option_code']}: "
                f"total={row['total_rows']}, "
                f"null={row['null_cost_rows']}, "
                f"zero={row['zero_cost_rows']}, "
                f"positive={row['positive_cost_rows']}, "
                f"min_positive={row['min_positive_cost']}, "
                f"max={row['max_cost']}"
            )

        print("-" * 120)

        print("Muestras con unit_cost = 0:")
        zero_rows = conn.execute("""
            SELECT
                so.id,
                so.sourcing_request_id,
                so.option_code,
                so.supplier_name,
                so.unit_cost
            FROM supplier_options so
            WHERE so.unit_cost = 0
            ORDER BY so.option_code, so.id
            LIMIT 20
        """).fetchall()

        for row in zero_rows:
            print(dict(row))

        print("-" * 120)

        print("Muestras con unit_cost > 0:")
        positive_rows = conn.execute("""
            SELECT
                so.id,
                so.sourcing_request_id,
                so.option_code,
                so.supplier_name,
                so.unit_cost
            FROM supplier_options so
            WHERE so.unit_cost > 0
            ORDER BY so.option_code, so.unit_cost
            LIMIT 20
        """).fetchall()

        for row in positive_rows:
            print(dict(row))


if __name__ == "__main__":
    main()