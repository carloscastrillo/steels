from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def norm_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def norm_num(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_num(value):
    if value is None:
        return "NULL"
    return f"{float(value):.3f}"


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
    return "|".join([
        product.strip(),
        grade.strip(),
        fmt_num(thickness_mm),
        fmt_num(width_mm),
        thickness_tolerance_text.strip() if thickness_tolerance_text else "NULL",
        width_tolerance_text.strip() if width_tolerance_text else "NULL",
        fmt_num(cw_min),
        fmt_num(cw_max),
    ])


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        source_rows = conn.execute("""
            SELECT DISTINCT
                product,
                grade,
                thickness_mm,
                width_mm,
                thickness_tolerance_text,
                width_tolerance_text,
                cw_min,
                cw_max
            FROM stg_boss_matrix
            WHERE is_valid_row = 1
              AND product IS NOT NULL AND TRIM(product) <> ''
              AND grade IS NOT NULL AND TRIM(grade) <> ''
              AND thickness_mm IS NOT NULL
              AND width_mm IS NOT NULL
              AND tn IS NOT NULL
              AND tn > 0
            ORDER BY product, grade, thickness_mm, width_mm
        """).fetchall()

        inserted = 0
        skipped = 0

        for row in source_rows:
            product = norm_text(row["product"])
            grade = norm_text(row["grade"])
            thickness_mm = norm_num(row["thickness_mm"])
            width_mm = norm_num(row["width_mm"])
            thickness_tolerance_text = norm_text(row["thickness_tolerance_text"])
            width_tolerance_text = norm_text(row["width_tolerance_text"])
            cw_min = norm_num(row["cw_min"])
            cw_max = norm_num(row["cw_max"])

            spec_key = build_spec_key(
                product=product,
                grade=grade,
                thickness_mm=thickness_mm,
                width_mm=width_mm,
                thickness_tolerance_text=thickness_tolerance_text,
                width_tolerance_text=width_tolerance_text,
                cw_min=cw_min,
                cw_max=cw_max,
            )

            existing = conn.execute("""
                SELECT id
                FROM request_specs
                WHERE spec_key = ?
            """, (spec_key,)).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO request_specs (
                    product,
                    grade,
                    thickness_mm,
                    width_mm,
                    thickness_tolerance_text,
                    width_tolerance_text,
                    cw_min,
                    cw_max,
                    spec_key,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product,
                grade,
                thickness_mm,
                width_mm,
                thickness_tolerance_text,
                width_tolerance_text,
                cw_min,
                cw_max,
                spec_key,
                "Loaded from stg_boss_matrix",
                created_at,
            ))
            inserted += 1

        conn.commit()

        total_specs = conn.execute("""
            SELECT COUNT(*) AS total
            FROM request_specs
        """).fetchone()["total"]

    print(f"Specs fuente detectadas: {len(source_rows)}")
    print(f"Specs insertadas: {inserted}")
    print(f"Specs omitidas por duplicado: {skipped}")
    print(f"Total request_specs en core: {total_specs}")


if __name__ == "__main__":
    main()