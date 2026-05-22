from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3

import pdfplumber


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parser Galmed para PDF de extras Zn/ZnMg."
    )
    parser.add_argument("--pdf", required=True, help="Ruta al PDF")
    parser.add_argument("--supplier-code", default="GALMED", help="Código proveedor")
    parser.add_argument("--supplier-name", default="Galmed", help="Nombre proveedor")
    return parser.parse_args()


def resolve_pdf_path(pdf_arg: str) -> Path:
    path = Path(pdf_arg)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"No existe el PDF: {path}")
    return path


def extract_all_text(pdf_path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def extract_tables(pdf_path: Path) -> list[list[list[str | None]]]:
    all_tables: list[list[list[str | None]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
    return all_tables


def ensure_document_row(
    conn: sqlite3.Connection,
    pdf_path: Path,
    supplier_code: str,
    raw_text: str,
) -> int:
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    existing = conn.execute("""
        SELECT id
        FROM stg_supplier_documents
        WHERE file_path = ?
        LIMIT 1
    """, (str(pdf_path),)).fetchone()

    if existing is None:
        conn.execute("""
            INSERT INTO stg_supplier_documents (
                file_name,
                file_type,
                supplier_code,
                file_path,
                imported_at,
                n_quotes_extracted,
                raw_text,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pdf_path.name,
            "pdf",
            supplier_code,
            str(pdf_path),
            imported_at,
            0,
            raw_text,
            "AUTO_REGISTERED_BY_GALMED_PDF_IMPORT",
        ))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    document_id = existing["id"]
    conn.execute("""
        UPDATE stg_supplier_documents
        SET
            supplier_code = ?,
            imported_at = ?,
            raw_text = ?
        WHERE id = ?
    """, (
        supplier_code,
        imported_at,
        raw_text,
        document_id,
    ))
    return document_id


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").strip().split())


def normalize_coating_raw(header: object) -> tuple[str | None, str, bool]:
    """
    Conserva la cabecera original y genera un coating normalizado único.

    Ejemplos:
        "Z70"              -> ("Z70", "Z70", False)
        "Z120\\nZ70/50"    -> ("Z120__Z70-50", "Z120\\nZ70/50", True)
        "Z140 Z100/40"     -> ("Z140__Z100-40", "Z140 Z100/40", True)

    El objetivo es NO colapsar recubrimientos diferenciales como Z70/50 en Z70.
    """
    if header is None:
        return None, "", False

    raw = str(header).strip()
    if not raw:
        return None, "", False

    compact = " ".join(raw.replace("\r", "\n").split())
    upper = compact.upper()

    tokens = re.findall(r"\bZ\s*\d{2,3}(?:\s*/\s*\d{1,3})?\b|\bZM\s*\d{2,3}\b", upper)

    cleaned_tokens: list[str] = []
    for token in tokens:
        cleaned = token.replace(" ", "").replace("/", "-")
        if cleaned not in cleaned_tokens:
            cleaned_tokens.append(cleaned)

    if not cleaned_tokens:
        return None, raw, False

    is_compound = len(cleaned_tokens) > 1 or "\n" in raw or "/" in raw

    normalized = "__".join(cleaned_tokens)
    return normalized, raw, is_compound


def parse_number(value: object) -> float | None:
    text = clean_cell(value)
    if not text or text in {"-", "—"}:
        return None

    text = text.replace(".", "").replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_thickness_range(value: object) -> tuple[float | None, float | None, float | None, str]:
    text = clean_cell(value)
    normalized = text.replace(",", ".")

    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", normalized)]
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        mid = round((lo + hi) / 2, 3)
        return round(lo, 3), round(hi, 3), mid, text

    if len(nums) == 1:
        val = round(nums[0], 3)
        return val, val, val, text

    return None, None, None, text


def looks_like_galmed_main_table(table: list[list[object]]) -> bool:
    if not table or len(table) < 2:
        return False

    header = [clean_cell(c).upper() for c in table[0]]
    joined = " | ".join(header)

    return "ESPESOR" in joined and "Z60" in joined and "Z275" in joined


def extract_galmed_rows(tables: list[list[list[str | None]]]) -> list[dict]:
    main_table = None

    for table in tables:
        if looks_like_galmed_main_table(table):
            main_table = table
            break

    if main_table is None:
        raise RuntimeError(
            "No se encontró la tabla principal Galmed Espesor × Recubrimiento."
        )

    header = main_table[0]
    coatings_by_col: dict[int, str] = {}

    coating_meta_by_col: dict[int, dict] = {}

    for idx, cell in enumerate(header):
        coating, coating_raw, is_compound = normalize_coating_raw(cell)
        if coating:
            coating_meta_by_col[idx] = {
                "coating": coating,
                "coating_raw": coating_raw,
                "is_compound": is_compound,
            }

    rows: list[dict] = []
    seen: set[tuple[str, str, float]] = set()

    for raw_row in main_table[1:]:
        if not raw_row or len(raw_row) < 2:
            continue

        thickness_min, thickness_max, thickness_mid, thickness_label = parse_thickness_range(raw_row[0])

        if thickness_mid is None:
            continue

        for col_idx, meta in coating_meta_by_col.items():
            if col_idx >= len(raw_row):
                continue

            coating = meta["coating"]
            coating_raw = meta["coating_raw"]
            is_compound = meta["is_compound"]

            extra = parse_number(raw_row[col_idx])
            if extra is None:
                continue

            extracted_grade = f"GALMED {coating} | espesor {thickness_label}"

            key = (extracted_grade, thickness_mid)
            if key in seen:
                continue
            seen.add(key)

            notes_flags = ["AUTO_EXTRACTED_FROM_PDF", "GALMED_ZINC_MATRIX", "NEEDS_REVIEW"]
            if is_compound:
                notes_flags.append("COMPOUND_COATING")

            rows.append({
                "extracted_grade": extracted_grade,
                "coating_raw": coating_raw,
                "is_compound": is_compound,
                "extracted_thickness_mm": thickness_mid,
                "extracted_width_mm": None,
                "extracted_price_per_ton": extra,
                "currency": "EUR",
                "notes": "|".join(notes_flags),
                "raw_text_snippet": f"{thickness_label} | {coating_raw} | {extra}",
                "raw_row_json": {
                    "table": "zinc_main_matrix",
                    "thickness_label": thickness_label,
                    "thickness_min_mm": thickness_min,
                    "thickness_max_mm": thickness_max,
                    "thickness_mid_mm": thickness_mid,
                    "coating": coating,
                    "coating_raw": coating_raw,
                    "is_compound": is_compound,
                    "extra_eur_t": extra,
                },
            })

    return rows


def insert_staging_quotes(
    conn: sqlite3.Connection,
    document_id: int,
    supplier_code: str,
    supplier_name: str,
    rows: list[dict],
) -> None:
    conn.execute("""
        DELETE FROM stg_supplier_quotes
        WHERE supplier_document_id = ?
          AND source_type = 'pdf'
          AND supplier_code = ?
    """, (document_id, supplier_code))

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for row in rows:
        conn.execute("""
            INSERT INTO stg_supplier_quotes (
                supplier_document_id,
                source_type,
                supplier_code,
                supplier_name,
                extracted_grade,
                coating_raw,
                extracted_thickness_mm,
                extracted_width_mm,
                extracted_price_per_ton,
                currency,
                incoterm,
                lead_time_days,
                valid_until,
                raw_row_json,
                raw_text_snippet,
                matched_sourcing_request_id,
                review_status,
                needs_manual_review,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            "pdf",
            supplier_code,
            supplier_name,
            row["extracted_grade"],
            row["coating_raw"],            
            row["extracted_thickness_mm"],
            row["extracted_width_mm"],
            row["extracted_price_per_ton"],
            row["currency"],
            None,
            None,
            None,
            json.dumps(row["raw_row_json"], ensure_ascii=False),
            row["raw_text_snippet"],
            None,
            "pending",
            1,
            row["notes"],
            created_at,
        ))


def main() -> None:
    args = parse_args()
    pdf_path = resolve_pdf_path(args.pdf)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        raw_text = extract_all_text(pdf_path)
        tables = extract_tables(pdf_path)

        if not tables:
            raise RuntimeError("pdfplumber no detectó tablas en el PDF Galmed.")

        document_id = ensure_document_row(
            conn=conn,
            pdf_path=pdf_path,
            supplier_code=args.supplier_code,
            raw_text=raw_text,
        )

        extracted_rows = extract_galmed_rows(tables)

        insert_staging_quotes(
            conn=conn,
            document_id=document_id,
            supplier_code=args.supplier_code,
            supplier_name=args.supplier_name,
            rows=extracted_rows,
        )

        conn.execute("""
            UPDATE stg_supplier_documents
            SET n_quotes_extracted = ?
            WHERE id = ?
        """, (len(extracted_rows), document_id))

        conn.commit()

    print("Importación Galmed completada.")
    print(f"document_id: {document_id}")
    print(f"quotes_extraídas: {len(extracted_rows)}")

    if extracted_rows:
        print("Primeras 10 filas extraídas:")
        for row in extracted_rows[:10]:
            print({
                "extracted_grade": row["extracted_grade"],
                "extracted_thickness_mm": row["extracted_thickness_mm"],
                "price_per_ton": row["extracted_price_per_ton"],
                "raw_text_snippet": row["raw_text_snippet"],
            })


if __name__ == "__main__":
    main()