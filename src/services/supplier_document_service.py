from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "raw" / "supplier_uploads"


@dataclass(frozen=True)
class SupplierDocument:
    id: int
    file_name: str
    file_type: str
    supplier_code: str
    file_path: str
    imported_at: str
    n_quotes_extracted: int
    notes: str | None


@dataclass(frozen=True)
class SupplierFreshness:
    supplier_code: str
    latest_file_name: str | None
    latest_imported_at: str | None
    n_documents: int
    n_quotes: int
    n_pending: int
    n_approved: int
    n_manual_review: int
    status: str


def _row_to_document(row: sqlite3.Row) -> SupplierDocument:
    return SupplierDocument(
        id=int(row["id"]),
        file_name=str(row["file_name"] or ""),
        file_type=str(row["file_type"] or ""),
        supplier_code=str(row["supplier_code"] or ""),
        file_path=str(row["file_path"] or ""),
        imported_at=str(row["imported_at"] or ""),
        n_quotes_extracted=int(row["n_quotes_extracted"] or 0),
        notes=row["notes"],
    )


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")

    if suffix in {"pdf", "xlsx", "xls", "xlsm", "csv"}:
        return suffix

    return "bin"


def _safe_filename(filename: str) -> str:
    original = Path(filename).name
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", ".", " "} else "_"
        for char in original
    ).strip()

    return cleaned or "supplier_document.bin"


def _read_preview_text(path: Path, file_type: str) -> str:
    if file_type in {"csv", "txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")[:5000]

    return ""


def list_supplier_documents(conn: sqlite3.Connection, limit: int = 100) -> list[SupplierDocument]:
    rows = conn.execute(
        """
        SELECT
            id,
            file_name,
            file_type,
            supplier_code,
            file_path,
            imported_at,
            COALESCE(n_quotes_extracted, 0) AS n_quotes_extracted,
            notes
        FROM stg_supplier_documents
        ORDER BY imported_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return [_row_to_document(row) for row in rows]


def supplier_price_freshness(conn: sqlite3.Connection) -> list[SupplierFreshness]:
    rows = conn.execute(
        """
        WITH latest_doc AS (
            SELECT
                d.supplier_code,
                d.file_name,
                d.imported_at,
                ROW_NUMBER() OVER (
                    PARTITION BY d.supplier_code
                    ORDER BY d.imported_at DESC, d.id DESC
                ) AS rn
            FROM stg_supplier_documents d
        ),
        doc_counts AS (
            SELECT
                supplier_code,
                COUNT(*) AS n_documents
            FROM stg_supplier_documents
            GROUP BY supplier_code
        ),
        quote_counts AS (
            SELECT
                supplier_code,
                COUNT(*) AS n_quotes,
                SUM(CASE WHEN review_status = 'pending' THEN 1 ELSE 0 END) AS n_pending,
                SUM(CASE WHEN review_status = 'approved' THEN 1 ELSE 0 END) AS n_approved,
                SUM(CASE WHEN COALESCE(needs_manual_review, 1) = 1 THEN 1 ELSE 0 END) AS n_manual_review
            FROM stg_supplier_quotes
            GROUP BY supplier_code
        )
        SELECT
            COALESCE(dc.supplier_code, qc.supplier_code) AS supplier_code,
            ld.file_name AS latest_file_name,
            ld.imported_at AS latest_imported_at,
            COALESCE(dc.n_documents, 0) AS n_documents,
            COALESCE(qc.n_quotes, 0) AS n_quotes,
            COALESCE(qc.n_pending, 0) AS n_pending,
            COALESCE(qc.n_approved, 0) AS n_approved,
            COALESCE(qc.n_manual_review, 0) AS n_manual_review
        FROM doc_counts dc
        LEFT JOIN quote_counts qc
            ON qc.supplier_code = dc.supplier_code
        LEFT JOIN latest_doc ld
            ON ld.supplier_code = dc.supplier_code
           AND ld.rn = 1

        UNION

        SELECT
            qc.supplier_code,
            NULL AS latest_file_name,
            NULL AS latest_imported_at,
            0 AS n_documents,
            COALESCE(qc.n_quotes, 0) AS n_quotes,
            COALESCE(qc.n_pending, 0) AS n_pending,
            COALESCE(qc.n_approved, 0) AS n_approved,
            COALESCE(qc.n_manual_review, 0) AS n_manual_review
        FROM quote_counts qc
        WHERE qc.supplier_code NOT IN (
            SELECT supplier_code FROM doc_counts
        )

        ORDER BY supplier_code
        """
    ).fetchall()

    result: list[SupplierFreshness] = []

    for row in rows:
        n_manual_review = int(row["n_manual_review"] or 0)
        n_pending = int(row["n_pending"] or 0)

        if n_manual_review > 0:
            status = "Revisión recomendada"
        elif n_pending > 0:
            status = "Pendiente de revisar"
        else:
            status = "Actualizado"

        result.append(
            SupplierFreshness(
                supplier_code=str(row["supplier_code"] or ""),
                latest_file_name=row["latest_file_name"],
                latest_imported_at=row["latest_imported_at"],
                n_documents=int(row["n_documents"] or 0),
                n_quotes=int(row["n_quotes"] or 0),
                n_pending=n_pending,
                n_approved=int(row["n_approved"] or 0),
                n_manual_review=n_manual_review,
                status=status,
            )
        )

    return result


def save_uploaded_supplier_document(
    conn: sqlite3.Connection,
    file_bytes: bytes,
    filename: str,
    supplier_code: str,
    uploaded_by: str | None = None,
    notes: str | None = None,
) -> int:
    if not file_bytes:
        raise ValueError("El archivo está vacío.")

    supplier = supplier_code.strip().upper()

    if not supplier:
        raise ValueError("El proveedor es obligatorio.")

    safe_name = _safe_filename(filename)
    file_type = _safe_suffix(safe_name)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    supplier_dir = UPLOAD_DIR / supplier
    supplier_dir.mkdir(parents=True, exist_ok=True)

    target_path = supplier_dir / f"{timestamp}_{safe_name}"

    with target_path.open("wb") as handle:
        handle.write(file_bytes)

    imported_at = datetime.now().replace(microsecond=0).isoformat()

    user_note = f"UPLOADED_FROM_APP"
    if uploaded_by:
        user_note += f"|BY={uploaded_by.strip()}"
    if notes:
        user_note += f"|{notes.strip()}"

    raw_text = _read_preview_text(target_path, file_type)

    cursor = conn.execute(
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
            safe_name,
            file_type,
            supplier,
            str(target_path),
            imported_at,
            0,
            raw_text,
            user_note,
        ),
    )

    conn.commit()

    return int(cursor.lastrowid)


def delete_supplier_document_file(document: SupplierDocument) -> None:
    path = Path(document.file_path)

    if path.exists() and UPLOAD_DIR in path.parents:
        path.unlink()
