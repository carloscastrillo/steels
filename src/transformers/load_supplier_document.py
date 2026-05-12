from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sqlite3

import pdfplumber


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Carga un documento de proveedor en stg_supplier_documents.")
    parser.add_argument("--file", required=True, help="Ruta al documento")
    parser.add_argument("--supplier-code", default=None, help="Código proveedor, ej: AM")
    parser.add_argument("--notes", default=None, help="Notas opcionales")
    return parser.parse_args()


def infer_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in (".xlsx", ".xlsm", ".xls"):
        return "excel"
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "email"
    return "unknown"


def extract_raw_text(path: Path, file_type: str) -> str | None:
    if file_type != "pdf":
        return None

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)

    return "\n\n".join(parts) if parts else None


def main() -> None:
    args = parse_args()

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = BASE_DIR / file_path

    if not file_path.exists():
        raise FileNotFoundError(f"No existe el fichero: {file_path}")

    file_type = infer_file_type(file_path)
    raw_text = extract_raw_text(file_path, file_type)
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        existing = conn.execute("""
            SELECT id
            FROM stg_supplier_documents
            WHERE file_path = ?
            LIMIT 1
        """, (str(file_path),)).fetchone()

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
                file_path.name,
                file_type,
                args.supplier_code,
                str(file_path),
                imported_at,
                0,
                raw_text,
                args.notes,
            ))
            document_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            action = "insertado"
        else:
            document_id = existing["id"]
            conn.execute("""
                UPDATE stg_supplier_documents
                SET
                    file_name = ?,
                    file_type = ?,
                    supplier_code = ?,
                    imported_at = ?,
                    raw_text = ?,
                    notes = ?
                WHERE id = ?
            """, (
                file_path.name,
                file_type,
                args.supplier_code,
                imported_at,
                raw_text,
                args.notes,
                document_id,
            ))
            action = "actualizado"

        conn.commit()

    print("Documento cargado correctamente.")
    print(f"document_id: {document_id}")
    print(f"acción: {action}")
    print(f"file_name: {file_path.name}")
    print(f"file_type: {file_type}")
    print(f"supplier_code: {args.supplier_code}")
    print(f"file_path: {file_path}")
    print(f"raw_text_chars: {0 if raw_text is None else len(raw_text)}")


if __name__ == "__main__":
    main()