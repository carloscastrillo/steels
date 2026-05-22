from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
import unicodedata

import pdfplumber


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parser Luso/Lusosider para PDFs de listas de precios por tablas."
    )
    parser.add_argument("--pdf", required=True, help="Ruta al PDF")
    parser.add_argument("--supplier-code", default="LUSO", help="Código proveedor")
    parser.add_argument("--supplier-name", default="Lusosider", help="Nombre proveedor")
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
            "AUTO_REGISTERED_BY_LUSO_PDF_IMPORT",
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


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def collapse_duplicated_chars(text: str) -> str:
    """Corrige casos tipo LLIISSTTAA -> LISTA cuando todo viene duplicado."""
    if len(text) < 4 or len(text) % 2 != 0:
        return text

    pairs = [text[i:i + 2] for i in range(0, len(text), 2)]
    if not pairs:
        return text

    duplicated = sum(1 for pair in pairs if len(pair) == 2 and pair[0] == pair[1])
    if duplicated / len(pairs) >= 0.75:
        return "".join(pair[0] for pair in pairs)

    return text


def normalize_text(text: str) -> str:
    text = clean_cell(text)
    text = collapse_duplicated_chars(text)
    text = remove_accents(text)
    return text.upper()


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
        return lo, hi, (lo + hi) / 2, text

    if len(nums) == 1:
        return nums[0], nums[0], nums[0], text

    return None, None, None, text


def normalize_coating(header: str) -> str | None:
    cleaned = normalize_text(header)
    match = re.search(r"\bZ\s*([0-9]{2,3})\b", cleaned)
    if match:
        return f"Z{match.group(1)}"
    return None


def detect_luso_document_type(pdf_path: Path, tables: list[list[list[str | None]]]) -> str:
    name = pdf_path.name.upper()
    if "CG" in name:
        return "galvanized"
    if "DK" in name:
        return "pickled"
    if "LF" in name:
        return "cold_rolled"

    joined = " ".join(
        normalize_text(cell)
        for table in tables[:3]
        for row in table[:5]
        for cell in row
        if cell
    )

    if "REVESTIMENTO" in joined or "GALVAN" in joined:
        return "galvanized"
    if "DECAP" in joined:
        return "pickled"
    if "LAMIN" in joined or "FRIO" in joined:
        return "cold_rolled"

    return "unknown"


def extract_matrix_rows(
    table: list[list[object]],
    document_type: str,
) -> list[dict]:
    if not table or len(table) < 2:
        return []

    header = table[0]
    coatings_by_col: dict[int, str] = {}

    for idx, cell in enumerate(header):
        coating = normalize_coating(clean_cell(cell))
        if coating:
            coatings_by_col[idx] = coating

    if len(coatings_by_col) < 2:
        return []

    rows: list[dict] = []
    seen: set[tuple[str, str, float]] = set()

    for raw_row in table[1:]:
        if not raw_row or len(raw_row) < 2:
            continue

        thickness_min, thickness_max, thickness_mid, thickness_label = parse_thickness_range(raw_row[0])
        if thickness_mid is None:
            continue

        for col_idx, coating in coatings_by_col.items():
            if col_idx >= len(raw_row):
                continue

            extra = parse_number(raw_row[col_idx])
            if extra is None:
                continue

            key = (thickness_label, coating, extra)
            if key in seen:
                continue
            seen.add(key)

            extracted_grade = f"LUSO {document_type.upper()} {coating} | espessura {thickness_label}"

            rows.append({
                "extracted_grade": extracted_grade,
                "extracted_thickness_mm": thickness_mid,
                "extracted_width_mm": None,
                "extracted_price_per_ton": extra,
                "currency": "EUR",
                "raw_text_snippet": f"{thickness_label} | {coating} | {extra}",
                "raw_row_json": {
                    "table_type": "coating_matrix",
                    "document_type": document_type,
                    "thickness_label": thickness_label,
                    "thickness_min_mm": thickness_min,
                    "thickness_max_mm": thickness_max,
                    "thickness_mid_mm": thickness_mid,
                    "coating": coating,
                    "extra_eur_t": extra,
                },
            })

    return rows


def extract_simple_extra_rows(
    table: list[list[object]],
    document_type: str,
) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, float]] = set()

    skip_tokens = {
        "ESPESSURA", "LARGURA", "REVESTIMENTO", "PRECO", "PRECOS",
        "LISTA", "TABELA", "EUR", "TON", "TONELADA", "MM"
    }

    for raw_row in table:
        cells = [clean_cell(cell) for cell in raw_row if clean_cell(cell)]
        if len(cells) < 2:
            continue

        normalized_cells = [normalize_text(cell) for cell in cells]
        if any(cell in skip_tokens for cell in normalized_cells):
            continue

        numeric_positions = [idx for idx, cell in enumerate(cells) if parse_number(cell) is not None]
        if not numeric_positions:
            continue

        # Evitar filas puramente matriciales. Aquí queremos filas descriptivas + último número.
        if len(numeric_positions) >= max(2, len(cells) - 1):
            continue

        price_idx = numeric_positions[-1]
        price = parse_number(cells[price_idx])
        if price is None:
            continue

        description_parts = [cells[i] for i in range(0, price_idx) if parse_number(cells[i]) is None]
        description = " ".join(description_parts).strip()
        description_norm = normalize_text(description)

        if not description or len(description_norm) < 2:
            continue

        key = (description_norm, price)
        if key in seen:
            continue
        seen.add(key)

        rows.append({
            "extracted_grade": f"LUSO {document_type.upper()} | {description}",
            "extracted_thickness_mm": None,
            "extracted_width_mm": None,
            "extracted_price_per_ton": price,
            "currency": "EUR",
            "raw_text_snippet": " | ".join(cells),
            "raw_row_json": {
                "table_type": "simple_extra",
                "document_type": document_type,
                "description": description,
                "extra_eur_t": price,
                "cells": cells,
            },
        })

    return rows


def extract_luso_rows(pdf_path: Path, tables: list[list[list[str | None]]]) -> list[dict]:
    document_type = detect_luso_document_type(pdf_path, tables)

    rows: list[dict] = []
    seen: set[tuple[str, float, float | None]] = set()

    for table in tables:
        for row in extract_matrix_rows(table, document_type):
            key = (
                row["extracted_grade"],
                row["extracted_price_per_ton"],
                row["extracted_thickness_mm"],
            )
            if key not in seen:
                seen.add(key)
                rows.append(row)

    # Fallback/complemento útil para DK2 y tablas de extras simples.
    for table in tables:
        for row in extract_simple_extra_rows(table, document_type):
            key = (
                row["extracted_grade"],
                row["extracted_price_per_ton"],
                row["extracted_thickness_mm"],
            )
            if key not in seen:
                seen.add(key)
                rows.append(row)

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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            "pdf",
            supplier_code,
            supplier_name,
            row["extracted_grade"],
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
            "AUTO_EXTRACTED_FROM_PDF|LUSO_2014|NEEDS_REVIEW",
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
            raise RuntimeError("pdfplumber no detectó tablas en el PDF Luso.")

        document_id = ensure_document_row(
            conn=conn,
            pdf_path=pdf_path,
            supplier_code=args.supplier_code,
            raw_text=raw_text,
        )

        extracted_rows = extract_luso_rows(pdf_path, tables)

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

    print("Importación Luso completada.")
    print(f"document_id: {document_id}")
    print(f"quotes_extraídas: {len(extracted_rows)}")
    print("Todas las quotes Luso entran con needs_manual_review=1 por antigüedad del PDF.")

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
