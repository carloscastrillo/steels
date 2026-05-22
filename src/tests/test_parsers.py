#!/usr/bin/env python3
"""
Tests de regresión para los parsers de PDF de proveedor.

Ejecutar:
    python src/tests/test_parsers.py

No requiere pytest.
Devuelve 0 si todos los tests pasan.
Devuelve 1 si algún test falla.

Usa:
    - PDFs reales en data/raw/pdfs/
    - DB temporal en db/test_steel_parsers.db
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PDF_DIR = BASE_DIR / "data" / "raw" / "pdfs"
TEST_DB = BASE_DIR / "db" / "test_steel_parsers.db"


PARSER_TESTS = [
    {
        "name": "AM-like alusi",
        "script": "src/transformers/import_pdf_pricelist_am_like.py",
        "pdf": "Auto_alusi_02022016.pdf",
        "supplier_code": "AM_TEST",
        "supplier_name": "ArcelorMittal Test",
        "min_quotes": 6,
        "all_needs_review_1": False,
        "no_null_prices": True,
    },
    {
        "name": "Tata cold rolled",
        "script": "src/transformers/import_pdf_pricelist_tata.py",
        "pdf": "Tata Steel_Price extra list EN - Cold rolled products EURO.pdf",
        "supplier_code": "TATA_TEST",
        "supplier_name": "Tata Steel Test",
        "min_quotes": 20,
        "all_needs_review_1": False,
        "no_null_prices": True,
    },
    {
        "name": "Galmed",
        "script": "src/transformers/import_pdf_pricelist_galmed.py",
        "pdf": "Tabla de Extras Galmed Abril 2026 Zn-ZnMg.pdf",
        "supplier_code": "GALMED_TEST",
        "supplier_name": "Galmed Test",
        "min_quotes": 100,
        "all_needs_review_1": True,
        "no_null_prices": True,
        "no_duplicates": True,
        "no_long_thickness": True,
        "requires_compound_coating": True,
    },
    {
        "name": "Luso CG2 galvanizada",
        "script": "src/transformers/import_pdf_pricelist_luso.py",
        "pdf": "Lista_CG2_R15_01out14.pdf",
        "supplier_code": "LUSO_TEST",
        "supplier_name": "Lusosider Test",
        "min_quotes": 50,
        "all_needs_review_1": True,
        "no_null_prices": True,
        "no_long_thickness": True,
    },
]


def init_test_db() -> None:
    schema_path = BASE_DIR / "db" / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"No existe schema.sql: {schema_path}")

    if TEST_DB.exists():
        TEST_DB.unlink()

    schema_sql = schema_path.read_text(encoding="utf-8")

    with sqlite3.connect(TEST_DB) as conn:
        conn.executescript(schema_sql)
        conn.commit()


def run_parser(test: dict) -> tuple[int, str, str]:
    script_path = BASE_DIR / test["script"]
    pdf_path = PDF_DIR / test["pdf"]

    if not script_path.exists():
        return 1, "", f"No existe script: {script_path}"

    if not pdf_path.exists():
        return 1, "", f"No existe PDF: {pdf_path}"

    env = dict(os.environ)
    env["STEEL_DB_PATH"] = str(TEST_DB)

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--pdf",
            str(pdf_path),
            "--supplier-code",
            test["supplier_code"],
            "--supplier-name",
            test["supplier_name"],
        ],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        env=env,
    )

    return result.returncode, result.stdout, result.stderr


def check_quotes(conn: sqlite3.Connection, test: dict) -> list[str]:
    errors: list[str] = []
    supplier_code = test["supplier_code"]

    n_quotes = conn.execute("""
        SELECT COUNT(*)
        FROM stg_supplier_quotes
        WHERE supplier_code = ?
    """, (supplier_code,)).fetchone()[0]

    if n_quotes < test["min_quotes"]:
        errors.append(f"Expected >= {test['min_quotes']} quotes, got {n_quotes}")

    if test.get("all_needs_review_1"):
        n_bad = conn.execute("""
            SELECT COUNT(*)
            FROM stg_supplier_quotes
            WHERE supplier_code = ?
              AND COALESCE(needs_manual_review, 0) = 0
        """, (supplier_code,)).fetchone()[0]

        if n_bad > 0:
            errors.append(f"{n_bad} quotes with needs_manual_review=0")

    if test.get("no_null_prices"):
        n_null = conn.execute("""
            SELECT COUNT(*)
            FROM stg_supplier_quotes
            WHERE supplier_code = ?
              AND extracted_price_per_ton IS NULL
        """, (supplier_code,)).fetchone()[0]

        if n_null > 0:
            errors.append(f"{n_null} quotes with NULL extracted_price_per_ton")

    if test.get("no_duplicates"):
        dupes = conn.execute("""
            SELECT
                extracted_grade,
                extracted_thickness_mm,
                COUNT(*) AS n
            FROM stg_supplier_quotes
            WHERE supplier_code = ?
            GROUP BY extracted_grade, extracted_thickness_mm
            HAVING COUNT(*) > 1
            LIMIT 5
        """, (supplier_code,)).fetchall()

        if dupes:
            errors.append(f"Duplicates found: {dupes}")

    if test.get("no_long_thickness"):
        long_thickness = conn.execute("""
            SELECT
                id,
                extracted_grade,
                extracted_thickness_mm
            FROM stg_supplier_quotes
            WHERE supplier_code = ?
              AND extracted_thickness_mm IS NOT NULL
              AND LENGTH(CAST(extracted_thickness_mm AS TEXT)) > 8
            LIMIT 5
        """, (supplier_code,)).fetchall()

        if long_thickness:
            errors.append(f"Long thickness values found: {long_thickness}")

    if test.get("requires_compound_coating"):
        n_compound = conn.execute("""
            SELECT COUNT(*)
            FROM stg_supplier_quotes
            WHERE supplier_code = ?
              AND notes LIKE '%COMPOUND_COATING%'
        """, (supplier_code,)).fetchone()[0]

        if n_compound == 0:
            errors.append("Expected at least one COMPOUND_COATING row")

    return errors


def cleanup() -> None:
    try:
        if TEST_DB.exists():
            TEST_DB.unlink()
    except PermissionError:
        print(f"[WARN] No se pudo borrar {TEST_DB}. Windows puede mantenerla bloqueada.")


def main() -> None:
    print("PARSER REGRESSION TESTS")
    print("-" * 100)

    init_test_db()

    all_passed = True

    for test in PARSER_TESTS:
        print(f"Testing: {test['name']} ... ", end="", flush=True)

        returncode, stdout, stderr = run_parser(test)

        if returncode != 0:
            print("FAIL")
            print("  Parser returned non-zero exit code.")
            if stdout.strip():
                print("  STDOUT:")
                print(stdout)
            if stderr.strip():
                print("  STDERR:")
                print(stderr)
            all_passed = False
            continue

        with sqlite3.connect(TEST_DB) as conn:
            errors = check_quotes(conn, test)

        if errors:
            print("FAIL")
            for error in errors:
                print(f"  - {error}")
            all_passed = False
        else:
            print("OK")

    cleanup()

    print()
    if all_passed:
        print("All parser tests passed.")
        sys.exit(0)

    print("Some parser tests FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()
