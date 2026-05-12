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
                capability_allowed,
                capability_note,
                COUNT(*) AS total
            FROM supplier_options
            GROUP BY option_code, capability_allowed, capability_note
            ORDER BY option_code, capability_allowed DESC, capability_note
        """).fetchall()

        print("Resumen capability validation:")
        for row in summary:
            print(
                f"- {row['option_code']} | "
                f"capability_allowed={row['capability_allowed']} | "
                f"{row['capability_note']} | total={row['total']}"
            )

        print("-" * 120)

        samples = conn.execute("""
            SELECT
                so.id,
                so.option_code,
                so.supplier_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm,
                so.capability_allowed,
                so.capability_rule_id,
                so.capability_note
            FROM supplier_options so
            JOIN sourcing_requests sr
              ON sr.id = so.sourcing_request_id
            JOIN request_specs rs
              ON rs.id = sr.request_spec_id
            WHERE so.capability_allowed = 0
               OR so.capability_allowed IS NULL
            ORDER BY so.id
            LIMIT 20
        """).fetchall()

        if samples:
            print("Muestras no permitidas o sin regla:")
            for row in samples:
                print(dict(row))
        else:
            print("No hay muestras fuera de capacidad o sin regla.")


if __name__ == "__main__":
    main()