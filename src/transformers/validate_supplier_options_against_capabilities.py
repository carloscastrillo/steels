from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def grade_matches(spec_grade: str | None, rule_pattern: str | None) -> bool:
    if rule_pattern is None or str(rule_pattern).strip() == "":
        return True
    if spec_grade is None:
        return False
    return rule_pattern.strip().upper() in spec_grade.strip().upper()


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    updated = 0

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT
                so.id AS supplier_option_id,
                so.option_code,
                so.supplier_name,
                rs.product,
                rs.grade,
                rs.thickness_mm,
                rs.width_mm
            FROM supplier_options so
            JOIN sourcing_requests sr
              ON sr.id = so.sourcing_request_id
            JOIN request_specs rs
              ON rs.id = sr.request_spec_id
            ORDER BY so.id
        """).fetchall()

        for row in rows:
            supplier_option_id = row["supplier_option_id"]
            option_code = row["option_code"]
            product = row["product"]
            grade = row["grade"]
            thickness = row["thickness_mm"]
            width = row["width_mm"]

            matching_rules = conn.execute("""
                SELECT
                    id,
                    provider_code,
                    provider_name,
                    product,
                    grade_pattern,
                    min_thickness_mm,
                    max_thickness_mm,
                    min_width_mm,
                    max_width_mm,
                    is_active
                FROM provider_capabilities
                WHERE provider_code = ?
                  AND is_active = 1
                  AND (product IS NULL OR product = ?)
                  AND (? IS NULL OR min_thickness_mm IS NULL OR min_thickness_mm <= ?)
                  AND (? IS NULL OR max_thickness_mm IS NULL OR max_thickness_mm >= ?)
                  AND (? IS NULL OR min_width_mm IS NULL OR min_width_mm <= ?)
                  AND (? IS NULL OR max_width_mm IS NULL OR max_width_mm >= ?)
                ORDER BY id
            """, (
                option_code,
                product,
                thickness, thickness,
                thickness, thickness,
                width, width,
                width, width,
            )).fetchall()

            selected_rule = None
            for rule in matching_rules:
                if grade_matches(grade, rule["grade_pattern"]):
                    selected_rule = rule
                    break

            if selected_rule is not None:
                capability_allowed = 1
                capability_rule_id = selected_rule["id"]
                capability_note = "CAPABILITY_MATCH"
            else:
                any_provider_rule = conn.execute("""
                    SELECT COUNT(*) AS cnt
                    FROM provider_capabilities
                    WHERE provider_code = ?
                      AND is_active = 1
                """, (option_code,)).fetchone()["cnt"]

                if any_provider_rule > 0:
                    capability_allowed = 0
                    capability_rule_id = None
                    capability_note = "OUTSIDE_PROVIDER_CAPABILITY"
                else:
                    capability_allowed = None
                    capability_rule_id = None
                    capability_note = "NO_PROVIDER_RULE_DEFINED"

            conn.execute("""
                UPDATE supplier_options
                SET capability_allowed = ?,
                    capability_rule_id = ?,
                    capability_note = ?
                WHERE id = ?
            """, (
                capability_allowed,
                capability_rule_id,
                capability_note,
                supplier_option_id,
            ))
            updated += 1

        conn.commit()

    print(f"Supplier options validadas contra provider_capabilities: {updated}")


if __name__ == "__main__":
    main()