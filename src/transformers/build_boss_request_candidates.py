from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM stg_boss_request_candidates")

        source_rows = conn.execute("""
            SELECT
                id,
                our_ref,
                client_name,
                product,
                grade,
                thickness_mm,
                width_mm,
                tn,
                missing_tons,
                sheet_date
            FROM stg_boss_matrix
            WHERE is_valid_row = 1
              AND our_ref IS NOT NULL
              AND TRIM(our_ref) <> ''
              AND client_name IS NOT NULL
              AND TRIM(client_name) <> ''
              AND grade IS NOT NULL
              AND TRIM(grade) <> ''
              AND thickness_mm IS NOT NULL
              AND width_mm IS NOT NULL
              AND tn IS NOT NULL
              AND tn > 0
            ORDER BY id
        """).fetchall()

        inserted = 0
        exact_match = 0
        no_material_match = 0
        multiple_material_match = 0
        no_client_match = 0

        for row in source_rows:
            client = conn.execute("""
                SELECT id
                FROM clients
                WHERE name = ?
            """, (row["client_name"],)).fetchone()

            if not client:
                client = conn.execute("""
                    SELECT c.id
                    FROM client_aliases a
                    JOIN clients c ON c.id = a.client_id
                    WHERE a.alias_name = ?
                """, (row["client_name"],)).fetchone()

            if not client:
                conn.execute("""
                    INSERT INTO stg_boss_request_candidates (
                        boss_row_id, our_ref, client_name, client_id,
                        product, grade, thickness_mm, width_mm, tn, missing_tons,
                        sheet_date, matched_material_count, matched_material_id,
                        match_status, notes, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["id"], row["our_ref"], row["client_name"], None,
                    row["product"], row["grade"], row["thickness_mm"], row["width_mm"],
                    row["tn"], row["missing_tons"], row["sheet_date"],
                    0, None, "no_client_match", None, created_at
                ))
                inserted += 1
                no_client_match += 1
                continue

            client_id = client["id"]

            materials = conn.execute("""
                SELECT id
                FROM materials
                WHERE client_id = ?
                  AND quality = ?
                  AND thickness_mm = ?
                  AND width_mm = ?
            """, (
                client_id,
                row["grade"],
                row["thickness_mm"],
                row["width_mm"],
            )).fetchall()

            material_count = len(materials)

            if material_count == 0:
                match_status = "no_material_match"
                matched_material_id = None
                no_material_match += 1
            elif material_count == 1:
                match_status = "exact_match"
                matched_material_id = materials[0]["id"]
                exact_match += 1
            else:
                match_status = "multiple_material_match"
                matched_material_id = None
                multiple_material_match += 1

            conn.execute("""
                INSERT INTO stg_boss_request_candidates (
                    boss_row_id, our_ref, client_name, client_id,
                    product, grade, thickness_mm, width_mm, tn, missing_tons,
                    sheet_date, matched_material_count, matched_material_id,
                    match_status, notes, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"], row["our_ref"], row["client_name"], client_id,
                row["product"], row["grade"], row["thickness_mm"], row["width_mm"],
                row["tn"], row["missing_tons"], row["sheet_date"],
                material_count, matched_material_id, match_status, None, created_at
            ))
            inserted += 1

        conn.commit()

    print(f"Filas procesadas: {len(source_rows)}")
    print(f"Candidatos insertados: {inserted}")
    print(f"Exact match: {exact_match}")
    print(f"No material match: {no_material_match}")
    print(f"Multiple material match: {multiple_material_match}")
    print(f"No client match: {no_client_match}")


if __name__ == "__main__":
    main()