from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        summary = conn.execute("""
            SELECT
                option_code,
                COUNT(*) AS total_rows,
                SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) AS available_rows,
                SUM(CASE WHEN is_zero_placeholder = 1 THEN 1 ELSE 0 END) AS zero_placeholder_rows,
                SUM(CASE WHEN is_suspicious = 1 THEN 1 ELSE 0 END) AS suspicious_rows,
                SUM(CASE WHEN is_rankable = 1 THEN 1 ELSE 0 END) AS rankable_rows
            FROM supplier_options
            GROUP BY option_code
            ORDER BY option_code
        """).fetchall()

        print("Resumen validado por option_code:")
        for row in summary:
            print(
                f"- {row['option_code']}: "
                f"total={row['total_rows']}, "
                f"available={row['available_rows']}, "
                f"zero_placeholder={row['zero_placeholder_rows']}, "
                f"suspicious={row['suspicious_rows']}, "
                f"rankable={row['rankable_rows']}"
            )

        print("-" * 140)

        suspicious_rows = conn.execute("""
            SELECT
                id,
                sourcing_request_id,
                option_code,
                supplier_name,
                unit_cost,
                validation_note
            FROM supplier_options
            WHERE is_suspicious = 1
            ORDER BY option_code, unit_cost
            LIMIT 20
        """).fetchall()

        print("Muestras sospechosas:")
        for row in suspicious_rows:
            print(dict(row))


if __name__ == "__main__":
    main()