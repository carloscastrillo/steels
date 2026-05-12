from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


SEED_RULES = [
    # SSAB
    {"provider_code": "SSAB", "provider_name": "SSAB", "product": "CRC", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "SSAB", "provider_name": "SSAB", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "SSAB", "provider_name": "SSAB", "product": "DKP", "grade_pattern": None, "min_thickness_mm": 0.5, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # ADI
    {"provider_code": "ADI", "provider_name": "ADI Italia", "product": "CRC", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "ADI", "provider_name": "ADI Italia", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "ADI", "provider_name": "ADI Italia", "product": "DKP", "grade_pattern": None, "min_thickness_mm": 0.5, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # LUSO
    {"provider_code": "LUSO", "provider_name": "Luso", "product": "CRC", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "LUSO", "provider_name": "Luso", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # GALMED
    {"provider_code": "GALMED", "provider_name": "Galmed", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # LEON
    {"provider_code": "LEON", "provider_name": "Leon", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # TATA
    {"provider_code": "TATA", "provider_name": "Tata", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},

    # AM_SPOT / baseline AM
    {"provider_code": "AM_SPOT", "provider_name": "ArcelorMittal", "product": "CRC", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "AM_SPOT", "provider_name": "ArcelorMittal", "product": "HDG", "grade_pattern": None, "min_thickness_mm": 0.3, "max_thickness_mm": 4.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
    {"provider_code": "AM_SPOT", "provider_name": "ArcelorMittal", "product": "DKP", "grade_pattern": None, "min_thickness_mm": 0.5, "max_thickness_mm": 6.0, "min_width_mm": 800.0, "max_width_mm": 1600.0, "notes": "Seed rule"},
]


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM provider_capabilities")

        inserted = 0
        for rule in SEED_RULES:
            conn.execute("""
                INSERT INTO provider_capabilities (
                    provider_code,
                    provider_name,
                    product,
                    grade_pattern,
                    min_thickness_mm,
                    max_thickness_mm,
                    min_width_mm,
                    max_width_mm,
                    is_active,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule["provider_code"],
                rule["provider_name"],
                rule["product"],
                rule["grade_pattern"],
                rule["min_thickness_mm"],
                rule["max_thickness_mm"],
                rule["min_width_mm"],
                rule["max_width_mm"],
                1,
                rule["notes"],
                created_at,
            ))
            inserted += 1

        conn.commit()

    print(f"Reglas cargadas en provider_capabilities: {inserted}")


if __name__ == "__main__":
    main()