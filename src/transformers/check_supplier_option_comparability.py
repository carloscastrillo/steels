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
                is_comparable,
                comparability_note,
                COUNT(*) AS total
            FROM supplier_options
            GROUP BY option_code, is_comparable, comparability_note
            ORDER BY option_code, is_comparable DESC
        """).fetchall()

        print("Resumen de comparabilidad:")
        for row in summary:
            print(
                f"- {row['option_code']} | "
                f"is_comparable={row['is_comparable']} | "
                f"{row['comparability_note']} | total={row['total']}"
            )


if __name__ == "__main__":
    main()