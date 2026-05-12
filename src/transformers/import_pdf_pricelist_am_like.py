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
        description="Parser AM-like para PDFs de extras (AM / ILVA / EN_*)."
    )
    parser.add_argument("--pdf", required=True, help="Ruta al PDF")
    parser.add_argument("--supplier-code", default="AM", help="Código proveedor")
    parser.add_argument("--supplier-name", default="ArcelorMittal", help="Nombre proveedor")
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
            "AUTO_REGISTERED_BY_AM_LIKE_PDF_IMPORT",
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


def looks_like_heading(line: str) -> bool:
    heading_patterns = [
        r"price extras",
        r"effective",
        r"valid as from",
        r"user guidelines",
        r"price calculation",
        r"the following document only lists extras",
        r"the price as invoiced includes",
        r"general$",
        r"dimensions$",
        r"thickness",
        r"width",
        r"coil weight",
        r"welds",
        r"coating",
        r"€/tonne",
        r"eur/tonne",
        r"unless otherwise agreed",
        r"all prices",
        r"this document",
    ]
    low = line.lower()
    return any(re.search(p, low) for p in heading_patterns)


def looks_like_dimension_row(line: str) -> bool:
    if re.match(r"^[0-9]+[.,][0-9]+\s+[0-9]+[.,][0-9]+", line):
        return True
    if re.match(r"^[<>≥≤-]", line):
        return True
    return False

def has_letters(text: str) -> bool:
    return bool(re.search(r"[A-Z]", text.upper()))


def count_pure_numeric_tokens(text: str) -> int:
    tokens = text.split()
    return sum(
        1
        for tok in tokens
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?", tok)
    )


def looks_like_numeric_matrix_row(line: str) -> bool:
    tokens = line.split()

    pure_numeric_tokens = [
        tok for tok in tokens
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?", tok)
    ]

    # Casos tipo:
    # "600 700 800 900 1100"
    # "64 61 53 48 48 68"
    if len(pure_numeric_tokens) >= 4 and not has_letters(line):
        return True

    # Casos tipo:
    # "1.00 - 1.24 64 61 53 48 48 68"
    if len(pure_numeric_tokens) >= 4 and re.search(r"\d+[.,]\d+\s*-\s*\d+[.,]\d+", line):
        return True

    return False


def is_valid_grade_piece(piece: str) -> bool:
    cleaned = " ".join(piece.strip().split())

    if not cleaned:
        return False

    # Un grade válido debe contener letras
    if not has_letters(cleaned):
        return False

    # Si tiene demasiados tokens numéricos sueltos, parece matriz, no grade
    if count_pure_numeric_tokens(cleaned) >= 3:
        return False

    return True

def extract_am_like_rows(raw_text: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, float]] = set()

    pattern_two_grades = re.compile(
        r"^([A-Z0-9][A-Z0-9/ .+\-]{1,50}?[A-Z0-9])\s+([A-Z0-9][A-Z0-9/ .+\-]{1,50}?[A-Z0-9])\s+(-?\d+(?:[.,]\d+)?)$"
    )
    pattern_one_grade = re.compile(
        r"^([A-Z0-9][A-Z0-9/ .+\-]{1,50}?[A-Z0-9])\s+(-?\d+(?:[.,]\d+)?)$"
    )

    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue

        if len(line) > 80:
            continue
        
        if looks_like_heading(line):
            continue

        if looks_like_dimension_row(line):
            continue

        if looks_like_numeric_matrix_row(line):
            continue

        m1 = pattern_two_grades.match(line)
        if m1:
            grade_1 = m1.group(1).strip()
            grade_2 = m1.group(2).strip()
            price = float(m1.group(3).replace(",", "."))

            if not is_valid_grade_piece(grade_1):
                continue
            if not is_valid_grade_piece(grade_2):
                continue

            extracted_grade = f"{grade_1} | {grade_2}"
            key = (extracted_grade, price)
            if key not in seen:
                seen.add(key)
                rows.append({
                    "extracted_grade": extracted_grade,
                    "price_per_ton": price,
                    "raw_text_snippet": line,
                })
            continue

        m2 = pattern_one_grade.match(line)
        if m2:
            grade = m2.group(1).strip()
            price = float(m2.group(2).replace(",", "."))

            if not is_valid_grade_piece(grade):
                continue

            key = (grade, price)
            if key not in seen:
                seen.add(key)
                rows.append({
                    "extracted_grade": grade,
                    "price_per_ton": price,
                    "raw_text_snippet": line,
                })
            continue
    return rows


def main() -> None:
    args = parse_args()
    pdf_path = resolve_pdf_path(args.pdf)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        raw_text = extract_all_text(pdf_path)
        document_id = ensure_document_row(
            conn=conn,
            pdf_path=pdf_path,
            supplier_code=args.supplier_code,
            raw_text=raw_text,
        )

        extracted_rows = extract_am_like_rows(raw_text)

        conn.execute("""
            DELETE FROM stg_supplier_quotes
            WHERE supplier_document_id = ?
              AND source_type = 'pdf'
              AND supplier_code = ?
        """, (document_id, args.supplier_code))

        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        for row in extracted_rows:
            payload = {
                "extracted_grade": row["extracted_grade"],
                "price_per_ton": row["price_per_ton"],
            }

            conn.execute("""
                INSERT INTO stg_supplier_quotes (
                    supplier_document_id,
                    source_type,
                    supplier_code,
                    supplier_name,
                    extracted_grade,
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
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                "pdf",
                args.supplier_code,
                args.supplier_name,
                row["extracted_grade"],
                None,
                None,
                row["price_per_ton"],
                "EUR",
                None,
                None,
                None,
                json.dumps(payload, ensure_ascii=False),
                row["raw_text_snippet"],
                None,
                "pending",
                "AUTO_EXTRACTED_FROM_PDF|AM_LIKE_GRADE_EXTRA",
                created_at,
            ))

        conn.execute("""
            UPDATE stg_supplier_documents
            SET n_quotes_extracted = ?
            WHERE id = ?
        """, (len(extracted_rows), document_id))

        conn.commit()

    print("Importación AM-like completada.")
    print(f"document_id: {document_id}")
    print(f"quotes_extraídas: {len(extracted_rows)}")

    if extracted_rows:
        print("Primeras 10 filas extraídas:")
        for row in extracted_rows[:10]:
            print(row)
    else:
        print("No se extrajeron filas. Habrá que ajustar regex o estrategia.")


if __name__ == "__main__":
    main()