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
    parser = argparse.ArgumentParser(description="Parser piloto de price list PDF de ArcelorMittal.")
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
            "AUTO_REGISTERED_BY_ARCELOR_PDF_IMPORT",
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


def extract_all_text(pdf_path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def extract_grade_extra_rows(raw_text: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str, float]] = set()

    pattern = re.compile(
        r"^([A-Z0-9][A-Z0-9/ .+-]*?\+AS)\s+([A-Z0-9-]+(?:-AS)?)\s+(-?\d+(?:\.\d+)?)$"
    )

    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue

        match = pattern.match(line)
        if not match:
            continue

        grade_1 = match.group(1).strip()
        grade_2 = match.group(2).strip()
        price = float(match.group(3))

        key = (grade_1, grade_2, price)
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "grade_1": grade_1,
            "grade_2": grade_2,
            "price_per_ton": price,
            "raw_text_snippet": line,
        })

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

        extracted_rows = extract_grade_extra_rows(raw_text)

        conn.execute("""
            DELETE FROM stg_supplier_quotes
            WHERE supplier_document_id = ?
              AND source_type = 'pdf'
              AND supplier_code = ?
        """, (document_id, args.supplier_code))

        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        for row in extracted_rows:
            payload = {
                "grade_1": row["grade_1"],
                "grade_2": row["grade_2"],
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
                f"{row['grade_1']} | {row['grade_2']}",
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
                "AUTO_EXTRACTED_FROM_PDF|ARCELO_GRADE_EXTRA",
                created_at,
            ))

        conn.execute("""
            UPDATE stg_supplier_documents
            SET n_quotes_extracted = ?
            WHERE id = ?
        """, (len(extracted_rows), document_id))

        conn.commit()

    print("Importación piloto de PDF Arcelor completada.")
    print(f"document_id: {document_id}")
    print(f"quotes_extraídas: {len(extracted_rows)}")

    if extracted_rows:
        print("Primeras 5 filas extraídas:")
        for row in extracted_rows[:5]:
            print(row)
    else:
        print("No se extrajeron filas. Habrá que ajustar regex o estrategia.")
        

if __name__ == "__main__":
    main()