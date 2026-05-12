from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


CANDIDATE_WHERE = """
    material_type_text IS NOT NULL
    AND TRIM(material_type_text) <> ''
    AND quality_description IS NOT NULL
    AND TRIM(quality_description) <> ''
    AND thickness_mm > 0
    AND width_mm > 0
"""


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        total_rows = conn.execute("""
            SELECT COUNT(*) AS total
            FROM stg_sap_zsd017_sales
        """).fetchone()["total"]

        candidate_rows = conn.execute(f"""
            SELECT COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            WHERE {CANDIDATE_WHERE}
        """).fetchone()["total"]

        distinct_candidate_materials = conn.execute(f"""
            SELECT COUNT(*) AS total
            FROM (
                SELECT DISTINCT
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
                    length_mm
                FROM stg_sap_zsd017_sales
                WHERE {CANDIDATE_WHERE}
            )
        """).fetchone()["total"]

        print(f"Total filas staging: {total_rows}")
        print(f"Filas candidatas a material real: {candidate_rows}")
        print(f"Materiales distintos candidatos: {distinct_candidate_materials}")
        print("-" * 100)

        print("Muestra de materiales candidatos:")
        sample_rows = conn.execute(f"""
            SELECT DISTINCT
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
                length_mm
            FROM stg_sap_zsd017_sales
            WHERE {CANDIDATE_WHERE}
            ORDER BY requester_name, material_number
            LIMIT 15
        """).fetchall()

        for row in sample_rows:
            print(dict(row))
            print("-" * 100)

        print("\nTop 15 material_type_text candidatas:")
        top_types = conn.execute(f"""
            SELECT material_type_text, COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            WHERE {CANDIDATE_WHERE}
            GROUP BY material_type_text
            ORDER BY total DESC
            LIMIT 15
        """).fetchall()

        for row in top_types:
            print(f"- {row['material_type_text']}: {row['total']}")

        print("\nTop 15 quality_description candidatas:")
        top_quality = conn.execute(f"""
            SELECT quality_description, COUNT(*) AS total
            FROM stg_sap_zsd017_sales
            WHERE {CANDIDATE_WHERE}
            GROUP BY quality_description
            ORDER BY total DESC
            LIMIT 15
        """).fetchall()

        for row in top_quality:
            print(f"- {row['quality_description']}: {row['total']}")


if __name__ == "__main__":
    main()