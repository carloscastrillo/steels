from pathlib import Path
from datetime import datetime
import sqlite3
import re


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


def normalize_length(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if value <= 0:
        return None
    return value


def format_num(value):
    if value is None:
        return "NULL"
    return f"{float(value):.3f}"


def derive_coating(quality: str) -> str:
    if not quality:
        return "UNCOATED"

    text = quality.upper()

    if "+ZM" in text:
        return "ZM"
    if "+ZF" in text:
        return "ZF"
    if "+ZA" in text:
        return "ZA"
    if "+ZE" in text:
        return "ZE"
    if "+AS" in text:
        return "AS"
    if "+Z" in text:
        return "Z"
    if " GI" in f" {text} ":
        return "GI"

    return "UNCOATED"


def build_material_key(
    client_id,
    quality,
    thickness_mm,
    width_mm,
    length_mm,
    coating,
    product_form_code,
):
    return "|".join([
        str(client_id),
        quality.strip(),
        format_num(thickness_mm),
        format_num(width_mm),
        format_num(length_mm),
        coating,
        product_form_code.strip() if product_form_code else "NULL",
    ])


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        source_rows = conn.execute(f"""
            SELECT DISTINCT
                s.requester_code,
                s.requester_name,
                s.material_number,
                s.material_text,
                s.material_type_code,
                s.material_type_text,
                s.internal_quality_code,
                s.quality_description,
                s.thickness_mm,
                s.width_mm,
                s.length_mm
            FROM stg_sap_zsd017_sales s
            WHERE {CANDIDATE_WHERE}
            ORDER BY s.requester_name, s.material_number
        """).fetchall()

        inserted = 0
        skipped = 0
        missing_client = 0

        for row in source_rows:
            client = conn.execute("""
                SELECT id
                FROM clients
                WHERE sap_code = ?
            """, (row["requester_code"],)).fetchone()

            if not client:
                missing_client += 1
                continue

            client_id = client["id"]
            quality = row["quality_description"].strip()
            thickness_mm = float(row["thickness_mm"])
            width_mm = float(row["width_mm"])
            length_mm = normalize_length(row["length_mm"])
            product_form_code = row["material_type_code"]
            product_form_text = row["material_type_text"]
            coating = derive_coating(quality)

            technical_parts = []
            if row["internal_quality_code"]:
                technical_parts.append(f"internal_quality_code={row['internal_quality_code']}")
            if row["material_number"]:
                technical_parts.append(f"example_material_number={row['material_number']}")
            if row["material_text"]:
                technical_parts.append(f"example_material_text={row['material_text']}")

            technical_notes = " | ".join(technical_parts) if technical_parts else None

            material_key = build_material_key(
                client_id=client_id,
                quality=quality,
                thickness_mm=thickness_mm,
                width_mm=width_mm,
                length_mm=length_mm,
                coating=coating,
                product_form_code=product_form_code,
            )

            existing = conn.execute("""
                SELECT id
                FROM materials
                WHERE material_key = ?
            """, (material_key,)).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute("""
                INSERT INTO materials (
                    client_id,
                    quality,
                    thickness_mm,
                    width_mm,
                    length_mm,
                    coating,
                    finish,
                    technical_notes,
                    material_key,
                    is_active,
                    created_at,
                    product_form_code,
                    product_form_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                quality,
                thickness_mm,
                width_mm,
                length_mm,
                coating,
                None,
                technical_notes,
                material_key,
                1,
                created_at,
                product_form_code,
                product_form_text,
            ))
            inserted += 1

        conn.commit()

        total_materials = conn.execute("""
            SELECT COUNT(*) AS total
            FROM materials
        """).fetchone()["total"]

    print(f"Filas fuente candidatas: {len(source_rows)}")
    print(f"Materiales insertados: {inserted}")
    print(f"Materiales omitidos por duplicado: {skipped}")
    print(f"Filas sin client encontrado: {missing_client}")
    print(f"Total materials en core: {total_materials}")


if __name__ == "__main__":
    main()