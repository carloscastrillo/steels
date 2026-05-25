from __future__ import annotations

import argparse
from pathlib import Path
import os
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))


VALID_DECISIONS = {"approved", "rejected"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa revisión Excel del staging de proveedor."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Ruta al Excel supplier_staging_report_YYYY-MM-DD.xlsx revisado por el operador",
    )
    return parser.parse_args()


def resolve_file(file_arg: str) -> Path:
    path = Path(file_arg)
    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    return path


def normalize_decision(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    if text in {"approve", "aprobado", "aprobada"}:
        return "approved"

    if text in {"reject", "rechazado", "rechazada"}:
        return "rejected"

    return text


def quote_exists(conn: sqlite3.Connection, quote_id: int) -> bool:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM stg_supplier_quotes
        WHERE id = ?
    """, (quote_id,)).fetchone()

    return bool(row and row[0])


def run(file_path: Path) -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    xf = pd.ExcelFile(file_path)

    updated = 0
    skipped_blank = 0
    skipped_invalid = 0
    skipped_missing_id = 0
    skipped_missing_quote = 0

    with sqlite3.connect(DB_PATH) as conn:
        for sheet in xf.sheet_names:
            if sheet.upper() == "SUMMARY":
                continue

            df = pd.read_excel(file_path, sheet_name=sheet)

            if "APROBACION_OPERADOR" not in df.columns or "id" not in df.columns:
                continue

            for _, row in df.iterrows():
                raw_id = row.get("id")
                decision = normalize_decision(row.get("APROBACION_OPERADOR", ""))

                if decision == "":
                    skipped_blank += 1
                    continue

                if decision not in VALID_DECISIONS:
                    skipped_invalid += 1
                    continue

                try:
                    quote_id = int(raw_id)
                except (TypeError, ValueError):
                    skipped_missing_id += 1
                    continue

                if not quote_exists(conn, quote_id):
                    skipped_missing_quote += 1
                    continue

                conn.execute("""
                    UPDATE stg_supplier_quotes
                    SET review_status = ?
                    WHERE id = ?
                """, (decision, quote_id))

                updated += 1

        conn.commit()

    print("Revisión staging importada.")
    print(f"Archivo: {file_path}")
    print(f"Quotes actualizadas: {updated}")
    print(f"Filas sin decisión: {skipped_blank}")
    print(f"Filas con decisión inválida: {skipped_invalid}")
    print(f"Filas sin id válido: {skipped_missing_id}")
    print(f"Filas con id inexistente: {skipped_missing_quote}")


def main() -> None:
    args = parse_args()
    file_path = resolve_file(args.file)
    run(file_path)


if __name__ == "__main__":
    main()
