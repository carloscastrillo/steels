from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


OPTION_CONFIG = [
    ("AM_SPOT", "ArcelorMittal", "internal_calculated", "am_spot_cost"),
    ("AM_AUTO", "ArcelorMittal", "internal_calculated", "am_auto_cost"),
    ("SSAB", "SSAB", "internal_calculated", "ssab_cost"),
    ("ADI", "ADI Italia", "internal_calculated", "adi_cost"),
    ("LUSO", "Luso", "internal_calculated", "luso_cost"),
    ("GALMED", "Galmed", "internal_calculated", "galmed_cost"),
    ("LEON", "Leon", "internal_calculated", "leon_cost"),
    ("TATA", "Tata", "internal_calculated", "tata_cost"),
    ("BAO_CFRFO", "Baosteel", "import_option", "bao_cfrfo"),
    ("BAO_DDP_HL", "Baosteel", "import_option", "bao_ddp_hl"),
    ("BASE_EQUIV", "Benchmark interno", "benchmark", "base_equivalent"),
]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM supplier_options")

        source_rows = conn.execute("""
            SELECT
                sr.id AS sourcing_request_id,
                b.am_spot_cost,
                b.am_auto_cost,
                b.ssab_cost,
                b.adi_cost,
                b.luso_cost,
                b.galmed_cost,
                b.leon_cost,
                b.tata_cost,
                b.bao_cfrfo,
                b.bao_ddp_hl,
                b.base_equivalent
            FROM sourcing_requests sr
            JOIN stg_boss_matrix b
              ON b.id = sr.source_row_id
            ORDER BY sr.id
        """).fetchall()

        inserted = 0

        for row in source_rows:
            for option_code, supplier_name, cost_type, source_column in OPTION_CONFIG:
                unit_cost = row[source_column]

                if unit_cost is None:
                    continue

                conn.execute("""
                    INSERT INTO supplier_options (
                        sourcing_request_id,
                        option_code,
                        supplier_name,
                        cost_type,
                        unit_cost,
                        total_cost,
                        currency,
                        notes,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["sourcing_request_id"],
                    option_code,
                    supplier_name,
                    cost_type,
                    float(unit_cost),
                    None,
                    "EUR",
                    "Loaded from stg_boss_matrix",
                    created_at,
                ))
                inserted += 1

        conn.commit()

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM supplier_options
        """).fetchone()["total"]

    print(f"Sourcing requests leídas: {len(source_rows)}")
    print(f"Supplier options insertadas: {inserted}")
    print(f"Total supplier_options: {total}")


if __name__ == "__main__":
    main()