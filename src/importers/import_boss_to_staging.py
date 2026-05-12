"""
import_boss_to_staging.py
--------------------------
Importador genérico de la matriz BOSS (Excel operativo del jefe) a la tabla
de staging stg_boss_matrix.

Uso:
    python import_boss_to_staging.py                        # elige hoja interactivamente
    python import_boss_to_staging.py --sheet "MARZO 2026"  # hoja directa

Antes de importar, borra en cascada en el orden correcto (FK-safe):
    sourcing_request_shortlist → supplier_options → sourcing_requests
    → request_specs → stg_boss_matrix

Así se garantiza que el re-import es idempotente y nunca viola constraints.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH  = BASE_DIR / "db" / "steel_mvp.db"
EXCEL_PATH = BASE_DIR / "data" / "raw" / "excel" / "matriz.xlsm"
HEADER_ROW = 9   # fila 0-indexed donde están los nombres de columna


# ---------------------------------------------------------------------------
# Helpers de normalización (idénticos al importer de marzo para consistencia)
# ---------------------------------------------------------------------------

def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return " ".join(text.split())


def make_unique_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for col in columns:
        base = normalize_text(col) or "unnamed"
        count = seen.get(base, 0)
        result.append(base if count == 0 else f"{base}.{count}")
        seen[base] = count + 1
    return result


def parse_number(value):
    if value is None or (isinstance(value, float) and str(value) == "nan"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_date_to_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return str(value)[:10]
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def json_safe(value):
    if value is None:
        return None
    if isinstance(value, float) and str(value) == "nan":
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value).strip() if isinstance(value, str) else value


# ---------------------------------------------------------------------------
# Selección de hoja
# ---------------------------------------------------------------------------

def list_sheets(excel_path: Path) -> list[str]:
    xl = pd.ExcelFile(excel_path, engine="openpyxl")
    return xl.sheet_names


def pick_sheet_interactively(sheets: list[str]) -> str:
    print("\nHojas disponibles en el Excel:")
    for i, name in enumerate(sheets, 1):
        print(f"  {i}. {name}")
    while True:
        choice = input("\nElige el número de la hoja a importar: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sheets):
                return sheets[idx]
        except ValueError:
            pass
        print("Opción no válida, intenta de nuevo.")


# ---------------------------------------------------------------------------
# Construcción del payload por fila
# ---------------------------------------------------------------------------

def build_payload(
    row,
    source_file_name: str,
    source_sheet_name: str,
    source_row_number: int,
    import_batch_id: str,
    imported_at: str,
) -> dict:
    raw_record = {str(k): json_safe(v) for k, v in row.items()}

    payload = {
        "source_file_name":   source_file_name,
        "source_sheet_name":  source_sheet_name,
        "source_row_number":  source_row_number,
        "import_batch_id":    import_batch_id,
        "imported_at":        imported_at,
        "raw_record_json": json.dumps(raw_record, ensure_ascii=False, default=str),

        # Campos de especificación técnica
        "our_ref":                    json_safe(row.get("our ref.")),
        "product":                    json_safe(row.get("product")),
        "grade":                      json_safe(row.get("grade")),
        "thickness_mm":               parse_number(row.get("thickness")),
        "width_mm":                   parse_number(row.get("width")),
        "length_mm":                  None,
        "thickness_tolerance_text":   json_safe(row.get("thickness tol +/-")),
        "width_tolerance_text":       json_safe(row.get("width tol + / -")),
        "cw_min":                     parse_number(row.get("cw min.")),
        "cw_max":                     parse_number(row.get("cw max.")),
        "tn":                         parse_number(row.get("tn")),
        "notes":                      json_safe(row.get("observaciones")),

        # Flags operativos
        "am_flag":        json_safe(row.get("am")),
        "luso_flag":      json_safe(row.get("luso")),
        "import_flag":    json_safe(row.get("import")),
        "missing_tons":   parse_number(row.get("faltante")),
        "client_name":    json_safe(row.get("cliente")),
        "sheet_date":     parse_date_to_iso(row.get("fecha")),
        "grouping_text":  json_safe(row.get("agrup.")),
        "agreement_am":   json_safe(row.get("acuerdo am")),
        "sales_price_or_cost": parse_number(row.get("p.vta / coste")),

        # Costes por proveedor
        "am_spot_cost":      parse_number(row.get("cte am spot")),
        "am_spot_cost_net":  parse_number(row.get("cte am spot neto")),
        "am_auto_cost":      parse_number(row.get("cte am auto")),
        "am_auto_cost_net":  parse_number(row.get("cte am auto neto")),
        "ssab_cost":         parse_number(row.get("ssab")),
        "ssab_cost_net":     parse_number(row.get("ssab neto")),
        "adi_cost":          parse_number(row.get("adi")),
        "adi_cost_net":      parse_number(row.get("adi neto")),
        "luso_cost":         parse_number(row.get("luso.1")) or parse_number(row.get("luso cost")),
        "luso_cost_net":     parse_number(row.get("luso neto")),
        "galmed_cost":       parse_number(row.get("galmed")),
        "leon_cost":         parse_number(row.get("leon")),
        "tata_cost":         parse_number(row.get("tata")),
        "tata_cost_net":     parse_number(row.get("tata neto")),
        "bao_cfrfo":         parse_number(row.get("bao cfrfo")),
        "bao_ddp_hl":        parse_number(row.get("bao ddp hl")),
        "base_equivalent":   parse_number(row.get("base equiv")),

        # Tons por canal y ofertas
        "am_tons":          parse_number(row.get("am.1")),
        "luso_tons":        parse_number(row.get("luso.2")),
        "import_tons":      parse_number(row.get("import.1")),
        "offer_14_total":   parse_number(row.get("oferta 14")),
        "offer_15_total":   parse_number(row.get("oferta 15")),
        "offer_16_total":   parse_number(row.get("oferta 16")),
        "offer_17_total":   parse_number(row.get("oferta 17")),

        "is_valid_row":       1,
        "validation_error":   None,
        "processed_to_core":  0,
    }

    required_fields = [
        payload["our_ref"],
        payload["product"],
        payload["grade"],
        payload["thickness_mm"],
        payload["width_mm"],
    ]
    if any(v is None or v == "" for v in required_fields):
        payload["is_valid_row"]     = 0
        payload["validation_error"] = "Faltan campos base obligatorios"

    return payload


# ---------------------------------------------------------------------------
# Inserción batch
# ---------------------------------------------------------------------------

COLUMNS = [
    "source_file_name", "source_sheet_name", "source_row_number",
    "import_batch_id", "imported_at", "raw_record_json",
    "our_ref", "product", "grade", "thickness_mm", "width_mm", "length_mm",
    "thickness_tolerance_text", "width_tolerance_text",
    "cw_min", "cw_max", "tn", "notes",
    "am_flag", "luso_flag", "import_flag", "missing_tons",
    "client_name", "sheet_date", "grouping_text", "agreement_am",
    "sales_price_or_cost",
    "am_spot_cost", "am_spot_cost_net", "am_auto_cost", "am_auto_cost_net",
    "ssab_cost", "ssab_cost_net", "adi_cost", "adi_cost_net",
    "luso_cost", "luso_cost_net", "galmed_cost", "leon_cost",
    "tata_cost", "tata_cost_net", "bao_cfrfo", "bao_ddp_hl", "base_equivalent",
    "am_tons", "luso_tons", "import_tons",
    "offer_14_total", "offer_15_total", "offer_16_total", "offer_17_total",
    "is_valid_row", "validation_error", "processed_to_core",
]


def insert_rows(conn: sqlite3.Connection, rows: list[dict]) -> None:
    if not rows:
        return
    placeholders = ", ".join(["?"] * len(COLUMNS))
    sql = f"INSERT INTO stg_boss_matrix ({', '.join(COLUMNS)}) VALUES ({placeholders})"
    values = [tuple(row.get(col) for col in COLUMNS) for row in rows]
    conn.executemany(sql, values)


# ---------------------------------------------------------------------------
# Cascade delete (FK-safe, orden inverso de dependencias)
# ---------------------------------------------------------------------------

def cascade_delete_core(conn: sqlite3.Connection) -> None:
   

    print("  [cascade] Borrando sourcing_request_shortlist...")
    conn.execute("DELETE FROM sourcing_request_shortlist")

    print("  [cascade] Borrando supplier_options...")
    conn.execute("DELETE FROM supplier_options")
    
    print("  [cascade] Borrando sourcing_decisions (si existe)...")
    try:
        conn.execute("DELETE FROM sourcing_decisions")
        
    except sqlite3.OperationalError:
        pass
    
    print("  [cascade] Borrando sourcing_quotes (si existe)...")
    try:
        conn.execute("DELETE FROM sourcing_quotes")
    except sqlite3.OperationalError:
        pass
    print("  [cascade] Borrando request_intakes (si existe)...")
    try:
        conn.execute("DELETE FROM request_intakes")
    except sqlite3.OperationalError:
        pass

    print("  [cascade] Borrando sourcing_requests...")
    conn.execute("DELETE FROM sourcing_requests")

    print("  [cascade] Borrando stg_boss_request_candidates (si existe)...")
    try:
        conn.execute("DELETE FROM stg_boss_request_candidates")
    except sqlite3.OperationalError:
        pass

    print("  [cascade] Borrando request_specs...")
    conn.execute("DELETE FROM request_specs")

    print("  [cascade] Borrando stg_boss_matrix...")
    conn.execute("DELETE FROM stg_boss_matrix")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa la matriz BOSS a staging. Sin --sheet, elige hoja interactivamente."
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help='Nombre exacto de la hoja a importar, ej: "ABRIL 2026"',
    )
    parser.add_argument(
        "--excel",
        type=str,
        default=None,
        help="Ruta al archivo Excel (por defecto data/raw/excel/matriz.xlsm)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    excel_path = Path(args.excel) if args.excel else EXCEL_PATH
    if not excel_path.exists():
        print(f"ERROR: No existe el Excel: {excel_path}")
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"ERROR: No existe la base de datos: {DB_PATH}")
        sys.exit(1)

    sheets = list_sheets(excel_path)
    if not sheets:
        print("ERROR: El Excel no tiene hojas.")
        sys.exit(1)

    if args.sheet:
        if args.sheet not in sheets:
            print(f"ERROR: La hoja '{args.sheet}' no existe en el Excel.")
            print(f"Hojas disponibles: {sheets}")
            sys.exit(1)
        sheet_name = args.sheet
    else:
        sheet_name = pick_sheet_interactively(sheets)

    print(f"\nImportando hoja: '{sheet_name}'")
    print(f"Archivo: {excel_path.name}")

    df = pd.read_excel(
        excel_path,
        sheet_name=sheet_name,
        header=HEADER_ROW,
        dtype=object,
        engine="openpyxl",
    )
    df.columns = make_unique_columns(list(df.columns))
    df = df.dropna(how="all").reset_index(drop=True)

    import_batch_id = f"boss_{sheet_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    rows_to_insert = [
        build_payload(
            row=row,
            source_file_name=excel_path.name,
            source_sheet_name=sheet_name,
            source_row_number=HEADER_ROW + 2 + idx,
            import_batch_id=import_batch_id,
            imported_at=imported_at,
        )
        for idx, row in df.iterrows()
    ]

    print("\nEliminando datos previos (cascade)...")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cascade_delete_core(conn)
        print(f"\nInsertando {len(rows_to_insert)} filas en stg_boss_matrix...")
        insert_rows(conn, rows_to_insert)
        conn.commit()

    valid   = sum(1 for r in rows_to_insert if r["is_valid_row"] == 1)
    invalid = len(rows_to_insert) - valid

    print(f"\nBatch ID  : {import_batch_id}")
    print(f"Filas leídas  : {len(rows_to_insert)}")
    print(f"Filas válidas : {valid}")
    print(f"Filas inválidas: {invalid}")

    if valid == 0:
        print("\n[AVISO] 0 filas válidas. Revisa que el nombre de la hoja y HEADER_ROW sean correctos.")
        sys.exit(2)

    print("\nImport completado correctamente.")


if __name__ == "__main__":
    main()
