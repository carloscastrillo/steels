from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import os
import re
import sqlite3

import pdfplumber
from parser_utils import parse_price


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parser piloto de price list PDF de Tata.")
    parser.add_argument("--pdf", required=True, help="Ruta al PDF")
    parser.add_argument("--supplier-code", default="TATA", help="Código proveedor")
    parser.add_argument("--supplier-name", default="Tata Steel", help="Nombre proveedor")
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
            "AUTO_REGISTERED_BY_TATA_PDF_IMPORT",
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
        r"^Cold-rolled strip products",
        r"^Price extras",
        r"^Effective ",
        r"^General$",
        r"^This document",
        r"^The invoiced price",
        r"^Material is charged",
        r"^Unless otherwise agreed",
        r"^All prices",
        r"^\d+\.\d+ ",
        r"^Dual Phase$",
        r"^Boron steel$",
        r"^Dimensions$",
        r"^Thickness ",
        r"^Width ",
        r"^≥",
        r"^<",
        r"^€/tonne$",
    ]
    return any(re.search(p, line, flags=re.IGNORECASE) for p in heading_patterns)


def extract_tata_grade_price_rows(raw_text: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, float]] = set()

    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue

        if looks_like_heading(line):
            continue

        # Ignorar líneas de dimensión tipo "0,35 0,40 105 102 90 ..."
        if re.match(r"^[0-9]+,[0-9]+\s+[0-9]+,[0-9]+", line):
            continue

        # Caso 1: "DP600 HCT600X 150"
        m1 = re.match(r"^([A-Z0-9+\-]+)\s+([A-Z0-9][A-Z0-9 .+\-/]+?)\s+(-?\d+(?:[.,]\d+)?)$", line)
        if m1:
            grade_1 = m1.group(1).strip()
            grade_2 = m1.group(2).strip()
            price = parse_price(m1.group(3))
            if price is None:
                continue
            key = (f"{grade_1} | {grade_2}", price)
            if key not in seen:
                seen.add(key)
                rows.append({
                    "extracted_grade": f"{grade_1} | {grade_2}",
                    "price_per_ton": price,
                    "raw_text_snippet": line,
                })
            continue

        # Caso 2: "HQ1500CR 100"
        m2 = re.match(r"^([A-Z0-9+\-]+)\s+(-?\d+(?:[.,]\d+)?)$", line)
        if m2:
            grade = m2.group(1).strip()
            price = parse_price(m2.group(2))
            if price is None:
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

        extracted_rows = extract_tata_grade_price_rows(raw_text)

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
                "AUTO_EXTRACTED_FROM_PDF|TATA_GRADE_EXTRA",
                created_at,
            ))

        conn.execute("""
            UPDATE stg_supplier_documents
            SET n_quotes_extracted = ?
            WHERE id = ?
        """, (len(extracted_rows), document_id))

        conn.commit()

    print("Importación piloto de PDF Tata completada.")
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