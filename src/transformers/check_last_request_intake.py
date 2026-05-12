from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT
                id,
                input_mode,
                raw_input_text,
                parsed_input_json,
                input_quality_status,
                match_quality,
                warnings_json,
                chosen_spec_id,
                sourcing_request_id,
                created_at
            FROM request_intakes
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if not row:
            print("No hay request_intakes.")
            return

        print("ULTIMO REQUEST_INTAKE")
        print("-" * 120)
        print(dict(row))


if __name__ == "__main__":
    main()