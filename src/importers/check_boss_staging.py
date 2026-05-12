from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM stg_boss_matrix
        """).fetchone()["total"]

        valid = conn.execute("""
            SELECT COUNT(*) AS total
            FROM stg_boss_matrix
            WHERE is_valid_row = 1
        """).fetchone()["total"]

        print(f"Total filas stg_boss_matrix: {total}")
        print(f"Filas válidas: {valid}")
        print("-" * 120)

        rows = conn.execute("""
            SELECT
                our_ref,
                product,
                grade,
                thickness_mm,
                width_mm,
                tn,
                am_tons,
                luso_tons,
                import_tons,
                missing_tons,
                client_name,
                sheet_date,
                agreement_am,
                am_spot_cost,
                am_auto_cost,
                ssab_cost,
                adi_cost,
                luso_cost,
                galmed_cost,
                leon_cost,
                tata_cost,
                bao_cfrfo,
                bao_ddp_hl,
                base_equivalent,
                offer_14_total,
                offer_15_total,
                offer_16_total,
                offer_17_total,
                validation_error
            FROM stg_boss_matrix
            ORDER BY id
            LIMIT 12
        """).fetchall()

        for row in rows:
            print(dict(row))
            print("-" * 120)


if __name__ == "__main__":
    main()