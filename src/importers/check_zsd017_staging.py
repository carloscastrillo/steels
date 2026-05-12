from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total_rows = conn.execute("""
            SELECT COUNT(*) AS total
            FROM stg_sap_zsd017_sales
        """).fetchone()["total"]

        valid_rows = conn.execute("""
            SELECT COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            WHERE is_valid_row = 1
        """).fetchone()["total"]

        print(f"Total filas staging: {total_rows}")
        print(f"Filas válidas: {valid_rows}")
        print("-" * 100)

        sample_rows = conn.execute("""
            SELECT
                id,
                requester_code,
                requester_name,
                material_number,
                material_text,
                material_type_code,
                material_type_text,
                internal_quality_code,
                quality_description,
                thickness_mm,
                width_mm,
                length_mm,
                movement_date,
                net_weight,
                sales_unit_price,
                customer_order_number,
                supplier_lot_number,
                coil_number
            FROM stg_sap_zsd017_sales
            ORDER BY id
            LIMIT 15
        """).fetchall()

        print("Muestra de filas:")
        for row in sample_rows:
            print(dict(row))
            print("-" * 100)

        print("\nChequeos rápidos:")
        checks = {
            "requester_code NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE requester_code IS NULL OR TRIM(requester_code) = ''
            """,
            "material_number NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE material_number IS NULL OR TRIM(material_number) = ''
            """,
            "movement_date NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE movement_date IS NULL OR TRIM(movement_date) = ''
            """,
            "thickness_mm NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE thickness_mm IS NULL
            """,
            "width_mm NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE width_mm IS NULL
            """,
            "length_mm NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE length_mm IS NULL
            """,
            "quality_description NULL": """
                SELECT COUNT(*) AS total
                FROM stg_sap_zsd017_sales
                WHERE quality_description IS NULL OR TRIM(quality_description) = ''
            """,
        }

        for label, sql in checks.items():
            value = conn.execute(sql).fetchone()["total"]
            print(f"- {label}: {value}")

        print("\nTop 10 quality_description:")
        top_quality = conn.execute("""
            SELECT quality_description, COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            GROUP BY quality_description
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

        for row in top_quality:
            print(f"- {row['quality_description']}: {row['total']}")

        print("\nTop 10 material_type_text:")
        top_material_types = conn.execute("""
            SELECT material_type_text, COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            GROUP BY material_type_text
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()

        for row in top_material_types:
            print(f"- {row['material_type_text']}: {row['total']}")


if __name__ == "__main__":
    main()