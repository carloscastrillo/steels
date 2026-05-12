from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def build_spec_key(
    product,
    grade,
    thickness_mm,
    width_mm,
    thickness_tolerance_text,
    width_tolerance_text,
    cw_min,
    cw_max,
):
    def fmt_num(value):
        if value is None:
            return "NULL"
        return f"{float(value):.3f}"

    return "|".join([
        str(product).strip(),
        str(grade).strip(),
        fmt_num(thickness_mm),
        fmt_num(width_mm),
        str(thickness_tolerance_text).strip() if thickness_tolerance_text else "NULL",
        str(width_tolerance_text).strip() if width_tolerance_text else "NULL",
        fmt_num(cw_min),
        fmt_num(cw_max),
    ])


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM sourcing_requests")

        source_rows = conn.execute("""
            SELECT
                b.id,
                b.our_ref,
                b.client_name,
                b.product,
                b.grade,
                b.thickness_mm,
                b.width_mm,
                b.thickness_tolerance_text,
                b.width_tolerance_text,
                b.cw_min,
                b.cw_max,
                b.tn,
                b.missing_tons,
                b.sheet_date,
                b.notes
            FROM stg_boss_matrix b
            WHERE b.is_valid_row = 1
              AND b.our_ref IS NOT NULL AND TRIM(b.our_ref) <> ''
              AND b.client_name IS NOT NULL AND TRIM(b.client_name) <> ''
              AND b.product IS NOT NULL AND TRIM(b.product) <> ''
              AND b.grade IS NOT NULL AND TRIM(b.grade) <> ''
              AND b.thickness_mm IS NOT NULL
              AND b.width_mm IS NOT NULL
              AND b.tn IS NOT NULL
              AND b.tn > 0
            ORDER BY b.id
        """).fetchall()

        inserted = 0
        no_client = 0
        no_spec = 0

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
                no_client += 1
                continue

            spec_key = build_spec_key(
                product=row["product"],
                grade=row["grade"],
                thickness_mm=row["thickness_mm"],
                width_mm=row["width_mm"],
                thickness_tolerance_text=row["thickness_tolerance_text"],
                width_tolerance_text=row["width_tolerance_text"],
                cw_min=row["cw_min"],
                cw_max=row["cw_max"],
            )

            spec = conn.execute("""
                SELECT id
                FROM request_specs
                WHERE spec_key = ?
            """, (spec_key,)).fetchone()

            if not spec:
                no_spec += 1
                continue

            conn.execute("""
                INSERT INTO sourcing_requests (
                    source_row_id,
                    client_id,
                    request_spec_id,
                    our_ref,
                    requested_tons,
                    missing_tons,
                    sheet_date,
                    notes,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"],
                client["id"],
                spec["id"],
                row["our_ref"],
                row["tn"],
                row["missing_tons"],
                row["sheet_date"],
                row["notes"],
                "pending_review",
                created_at,
            ))
            inserted += 1

        conn.commit()

        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM sourcing_requests
        """).fetchone()["total"]

    print(f"Filas fuente procesadas: {len(source_rows)}")
    print(f"Sourcing requests insertadas: {inserted}")
    print(f"Filas sin client: {no_client}")
    print(f"Filas sin spec: {no_spec}")
    print(f"Total sourcing_requests: {total}")


if __name__ == "__main__":
    main()