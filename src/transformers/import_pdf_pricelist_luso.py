from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3

import pdfplumber
from parser_utils import parse_price, parse_range_midpoint

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parser Luso/Lusosider para PDFs de listas de extras.")
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
    tables_out: list[list[list[str | None]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                tables_out.extend(tables)
    return tables_out


def ensure_document_row(conn: sqlite3.Connection, pdf_path: Path, supplier_code: str, raw_text: str) -> int:
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    existing = conn.execute(
        """
        SELECT id
        FROM stg_supplier_documents
        WHERE file_path = ?
        LIMIT 1
        """,
        (str(pdf_path),),
    ).fetchone()

    if existing is None:
        conn.execute(
            """
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
            """,
            (
                pdf_path.name,
                "pdf",
                supplier_code,
                str(pdf_path),
                imported_at,
                0,
                raw_text,
                "AUTO_REGISTERED_BY_LUSO_PDF_IMPORT",
            ),
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    document_id = existing["id"]
    conn.execute(
        """
        UPDATE stg_supplier_documents
        SET supplier_code = ?, imported_at = ?, raw_text = ?
        WHERE id = ?
        """,
        (supplier_code, imported_at, raw_text, document_id),
    )
    return document_id


def clean_cell(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").strip().split())


def normalize_decimal_text(text: str) -> str:
    return text.replace(".", "").replace(",", ".")


def parse_number(value: object) -> float | None:
    return parse_price(value)


def parse_range_label(value: object) -> tuple[float | None, float | None, float | None, str]:
    return parse_range_midpoint(value, decimals=3)

def parse_width_range(value: object) -> tuple[float | None, str]:
    _, _, mid, label = parse_range_label(value)
    return mid, label


def detect_document_type(pdf_path: Path, tables: list[list[list[str | None]]]) -> str:
    name = pdf_path.name.lower()
    if "cg" in name:
        return "galvanized"
    if "dk" in name:
        return "pickled"
    if "lf" in name:
        return "cold_rolled"

    joined = " ".join(clean_cell(cell).lower() for table in tables for row in table for cell in row)
    if "revestimento" in joined:
        return "galvanized"
    if "decap" in joined:
        return "pickled"
    if "frio" in joined or "dc01" in joined:
        return "cold_rolled"
    return "unknown"


def has_header_terms(table: list[list[object]], *terms: str) -> bool:
    if not table:
        return False
    joined = " ".join(clean_cell(cell).lower() for row in table[:4] for cell in row)
    return all(term.lower() in joined for term in terms)


def add_row(
    rows: list[dict],
    *,
    document_type: str,
    category: str,
    label: str,
    price: float,
    thickness_label: str | None = None,
    thickness_mid: float | None = None,
    width_label: str | None = None,
    width_mid: float | None = None,
    raw_json: dict,
) -> None:
    parts = [f"LUSO {document_type.upper()}", category, label]
    if thickness_label:
        parts.append(f"espessura {thickness_label}")
    if width_label:
        parts.append(f"largura {width_label}")

    rows.append(
        {
            "extracted_grade": " | ".join(parts),
            "extracted_thickness_mm": thickness_mid,
            "extracted_width_mm": width_mid,
            "extracted_price_per_ton": price,
            "currency": "EUR",
            "raw_text_snippet": " | ".join(
                str(x) for x in [category, label, thickness_label, width_label, price] if x not in (None, "")
            ),
            "raw_row_json": raw_json,
        }
    )


def extract_cg2_rows(tables: list[list[list[str | None]]]) -> list[dict]:
    rows: list[dict] = []
    coating_table = None
    width_table = None

    for table in tables:
        if has_header_terms(table, "espessura", "revestimento"):
            coating_table = table
        elif has_header_terms(table, "espessura", "largura"):
            width_table = table

    if coating_table:
        header = coating_table[1] if len(coating_table) > 1 else []
        coatings_by_col = {
            idx: clean_cell(cell).upper()
            for idx, cell in enumerate(header)
            if clean_cell(cell).upper().startswith("Z")
        }

        for row in coating_table[2:]:
            _, _, thickness_mid, thickness_label = parse_range_label(row[0] if row else None)
            if thickness_mid is None:
                continue
            for col_idx, coating in coatings_by_col.items():
                if col_idx >= len(row):
                    continue
                price = parse_number(row[col_idx])
                if price is None:
                    continue
                add_row(
                    rows,
                    document_type="galvanized",
                    category="revestimento",
                    label=coating,
                    price=price,
                    thickness_label=thickness_label,
                    thickness_mid=thickness_mid,
                    raw_json={
                        "document_type": "galvanized",
                        "table": "revestimento",
                        "thickness_label": thickness_label,
                        "coating": coating,
                        "extra_eur_t": price,
                    },
                )

    if width_table:
        header = width_table[1] if len(width_table) > 1 else []
        widths_by_col = {idx: clean_cell(cell).replace(" ", "") for idx, cell in enumerate(header) if clean_cell(cell)}

        for row in width_table[2:]:
            _, _, thickness_mid, thickness_label = parse_range_label(row[0] if row else None)
            if thickness_mid is None:
                continue
            for col_idx, width_label in widths_by_col.items():
                if col_idx >= len(row):
                    continue
                price = parse_number(row[col_idx])
                width_mid, width_label_original = parse_width_range(width_label)
                if price is None:
                    continue
                add_row(
                    rows,
                    document_type="galvanized",
                    category="largura",
                    label=width_label_original,
                    price=price,
                    thickness_label=thickness_label,
                    thickness_mid=thickness_mid,
                    width_label=width_label_original,
                    width_mid=width_mid,
                    raw_json={
                        "document_type": "galvanized",
                        "table": "largura",
                        "thickness_label": thickness_label,
                        "width_label": width_label_original,
                        "extra_eur_t": price,
                    },
                )

    return rows


def extract_dk2_rows(tables: list[list[list[str | None]]]) -> list[dict]:
    rows: list[dict] = []

    for table in tables:
        if not table:
            continue

        if has_header_terms(table, "espessura", "extras") and len(table[0]) >= 2:
            for row in table[2:]:
                if not row or len(row) < 2:
                    continue
                _, _, thickness_mid, thickness_label = parse_range_label(row[0])
                price = parse_number(row[1])
                if thickness_mid is None or price is None:
                    continue
                add_row(
                    rows,
                    document_type="pickled",
                    category="espessura",
                    label="extra",
                    price=price,
                    thickness_label=thickness_label,
                    thickness_mid=thickness_mid,
                    raw_json={
                        "document_type": "pickled",
                        "table": "espessura_extra",
                        "thickness_label": thickness_label,
                        "extra_eur_t": price,
                    },
                )

        elif has_header_terms(table, "qualidade", "extras") and len(table[0]) >= 2:
            for row in table[1:]:
                if not row or len(row) < 2:
                    continue
                quality = clean_cell(row[0]).upper()
                price = parse_number(row[1])
                if not quality or price is None:
                    continue
                add_row(
                    rows,
                    document_type="pickled",
                    category="qualidade",
                    label=quality,
                    price=price,
                    raw_json={
                        "document_type": "pickled",
                        "table": "quality_extra",
                        "quality": quality,
                        "extra_eur_t": price,
                    },
                )

        elif has_header_terms(table, "espessura", "largura"):
            header = table[1] if len(table) > 1 else []
            widths_by_col = {idx: clean_cell(cell) for idx, cell in enumerate(header) if clean_cell(cell)}
            for row in table[2:]:
                if not row:
                    continue
                _, _, thickness_mid, thickness_label = parse_range_label(row[0])
                if thickness_mid is None:
                    continue
                for col_idx, width_label in widths_by_col.items():
                    if col_idx >= len(row):
                        continue
                    price = parse_number(row[col_idx])
                    width_mid = parse_number(width_label)
                    if price is None:
                        continue
                    add_row(
                        rows,
                        document_type="pickled",
                        category="largura",
                        label=width_label,
                        price=price,
                        thickness_label=thickness_label,
                        thickness_mid=thickness_mid,
                        width_label=width_label,
                        width_mid=width_mid,
                        raw_json={
                            "document_type": "pickled",
                            "table": "width_extra",
                            "thickness_label": thickness_label,
                            "width_label": width_label,
                            "extra_eur_t": price,
                        },
                    )

    return rows


def extract_lf2_rows(tables: list[list[list[str | None]]]) -> list[dict]:
    rows: list[dict] = []

    for table in tables:
        if not table:
            continue

        if has_header_terms(table, "qualidade", "extra") and len(table[0]) >= 2:
            for row in table[1:]:
                if not row or len(row) < 2:
                    continue
                quality = clean_cell(row[0]).upper()
                price = parse_number(row[1])
                if not quality or price is None:
                    continue
                add_row(
                    rows,
                    document_type="cold_rolled",
                    category="qualidade",
                    label=quality,
                    price=price,
                    raw_json={
                        "document_type": "cold_rolled",
                        "table": "quality_extra",
                        "quality": quality,
                        "extra_eur_t": price,
                    },
                )

        elif has_header_terms(table, "espessura", "largura"):
            width_labels = ["900-1099", "1100-1299"]
            for row in table:
                if not row or len(row) < 3:
                    continue
                _, _, thickness_mid, thickness_label = parse_range_label(row[0])
                if thickness_mid is None:
                    continue
                for col_idx, width_label in zip([1, 2], width_labels):
                    if col_idx >= len(row):
                        continue
                    price = parse_number(row[col_idx])
                    if price is None:
                        continue
                    width_mid, width_label_original = parse_width_range(width_label)
                    add_row(
                        rows,
                        document_type="cold_rolled",
                        category="largura",
                        label=width_label_original,
                        price=price,
                        thickness_label=thickness_label,
                        thickness_mid=thickness_mid,
                        width_label=width_label_original,
                        width_mid=width_mid,
                        raw_json={
                            "document_type": "cold_rolled",
                            "table": "width_extra",
                            "thickness_label": thickness_label,
                            "width_label": width_label_original,
                            "extra_eur_t": price,
                        },
                    )

    return rows


def extract_luso_rows(pdf_path: Path, tables: list[list[list[str | None]]]) -> list[dict]:
    doc_type = detect_document_type(pdf_path, tables)
    if doc_type == "galvanized":
        return extract_cg2_rows(tables)
    if doc_type == "pickled":
        return extract_dk2_rows(tables)
    if doc_type == "cold_rolled":
        return extract_lf2_rows(tables)
    raise RuntimeError(f"No se pudo detectar el tipo de documento Luso para: {pdf_path.name}")


def insert_staging_quotes(
    conn: sqlite3.Connection,
    document_id: int,
    supplier_code: str,
    supplier_name: str,
    rows: list[dict],
) -> None:
    conn.execute(
        """
        DELETE FROM stg_supplier_quotes
        WHERE supplier_document_id = ?
          AND source_type = 'pdf'
          AND supplier_code = ?
        """,
        (document_id, supplier_code),
    )

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for row in rows:
        conn.execute(
            """
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
            """,
            (
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
            ),
        )


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

        conn.execute(
            """
            UPDATE stg_supplier_documents
            SET n_quotes_extracted = ?
            WHERE id = ?
            """,
            (len(extracted_rows), document_id),
        )

        conn.commit()

    print("Importación Luso completada.")
    print(f"document_id: {document_id}")
    print(f"quotes_extraídas: {len(extracted_rows)}")
    print("Todas las quotes Luso entran con needs_manual_review=1 por antigüedad del PDF.")

    if extracted_rows:
        print("Primeras 10 filas extraídas:")
        for row in extracted_rows[:10]:
            print(
                {
                    "extracted_grade": row["extracted_grade"],
                    "extracted_thickness_mm": row["extracted_thickness_mm"],
                    "extracted_width_mm": row["extracted_width_mm"],
                    "price_per_ton": row["extracted_price_per_ton"],
                    "raw_text_snippet": row["raw_text_snippet"],
                }
            )


if __name__ == "__main__":
    main()
