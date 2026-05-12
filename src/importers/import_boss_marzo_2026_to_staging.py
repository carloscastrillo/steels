from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
import json
import sqlite3
import uuid

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"
EXCEL_PATH = BASE_DIR / "data" / "raw" / "excel" / "matriz.xlsm"
SHEET_NAME = "MARZO 2026"
HEADER_ROW = 9


def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = " ".join(text.split())
    return text


def make_unique_columns(columns: list[str]) -> list[str]:
    seen = {}
    result = []

    for col in columns:
        base = normalize_text(col)
        if not base:
            base = "unnamed"

        count = seen.get(base, 0)
        result.append(base if count == 0 else f"{base}.{count}")
        seen[base] = count + 1

    return result


def parse_number(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_date_to_iso(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def json_safe(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    return str(value).strip()


def build_payload(row, source_file_name, source_sheet_name, source_row_number, import_batch_id, imported_at):
    raw_record = {str(column): json_safe(value) for column, value in row.items()}

    payload = {
        "source_file_name": source_file_name,
        "source_sheet_name": source_sheet_name,
        "source_row_number": source_row_number,
        "import_batch_id": import_batch_id,
        "imported_at": imported_at,
        "raw_record_json": json.dumps(raw_record, ensure_ascii=False),

        "our_ref": json_safe(row.get("our ref.")),
        "product": json_safe(row.get("product")),
        "grade": json_safe(row.get("grade")),
        "thickness_mm": parse_number(row.get("thickness")),
        "width_mm": parse_number(row.get("width")),
        "length_mm": None,
        "thickness_tolerance_text": json_safe(row.get("thickness tol +/-")),
        "width_tolerance_text": json_safe(row.get("width tol + / -")),
        "cw_min": parse_number(row.get("cw min.")),
        "cw_max": parse_number(row.get("cw max.")),
        "tn": parse_number(row.get("tn")),
        "notes": json_safe(row.get("observaciones")),

        "am_flag": json_safe(row.get("am")),
        "luso_flag": json_safe(row.get("luso")),
        "import_flag": json_safe(row.get("import")),
        "missing_tons": parse_number(row.get("falta")),
        "client_name": json_safe(row.get("cliente")),
        "sheet_date": parse_date_to_iso(row.get("fecha")),
        "grouping_text": json_safe(row.get("agrup.")),
        "agreement_am": json_safe(row.get("acuerdo am")),
        "sales_price_or_cost": parse_number(row.get("p.vta / coste")),

        "am_spot_cost": parse_number(row.get("cte am spot")),
        "am_spot_cost_net": parse_number(row.get("cte am spot (neto)")),
        "am_auto_cost": parse_number(row.get("cte am auto")),
        "am_auto_cost_net": parse_number(row.get("cte am auto (neto)")),

        "ssab_cost": parse_number(row.get("cte ssab")),
        "ssab_cost_net": parse_number(row.get("cte ssab neto")),

        "adi_cost": parse_number(row.get("cte adi italia")),
        "adi_cost_net": parse_number(row.get("cte adi (neto)")),

        "luso_cost": parse_number(row.get("cte luso")),
        "luso_cost_net": parse_number(row.get("cte luso (neto)")),

        "galmed_cost": parse_number(row.get("galmed")),
        "leon_cost": parse_number(row.get("leon")),

        "tata_cost": parse_number(row.get("tata hdg uk")),
        "tata_cost_net": parse_number(row.get("tata hdg uk neto (1,5%)")),

        "bao_cfrfo": parse_number(row.get("bao cfrfo")),
        "bao_ddp_hl": parse_number(row.get("bao ddp hl")),
        "base_equivalent": parse_number(row.get("base equiv")),

        "am_tons": parse_number(row.get("am")),
        "luso_tons": parse_number(row.get("luso")),
        "import_tons": parse_number(row.get("import")),
        "offer_14": parse_number(row.get("oferta 14")),
        "offer_15": parse_number(row.get("oferta 15")),
        "offer_16": parse_number(row.get("oferta 16")),
        "offer_17": parse_number(row.get("oferta 17")),

        "is_valid_row": 1,
        "validation_error": None,
        "processed_to_core": 0,
    }

    required = [
        payload["our_ref"],
        payload["product"],
        payload["grade"],
        payload["thickness_mm"],
        payload["width_mm"],
    ]

    if any(v is None or v == "" for v in required):
        payload["is_valid_row"] = 0
        payload["validation_error"] = "Faltan campos base obligatorios"

    return payload


def insert_rows(conn, rows):
    if not rows:
        return

    columns = [
        "source_file_name",
        "source_sheet_name",
        "source_row_number",
        "import_batch_id",
        "imported_at",
        "raw_record_json",
        "our_ref",
        "product",
        "grade",
        "thickness_mm",
        "width_mm",
        "length_mm",
        "thickness_tolerance_text",
        "width_tolerance_text",
        "cw_min",
        "cw_max",
        "tn",
        "notes",
        "am_flag",
        "luso_flag",
        "import_flag",
        "missing_tons",
        "client_name",
        "sheet_date",
        "grouping_text",
        "agreement_am",
        "sales_price_or_cost",
        "am_spot_cost",
        "am_spot_cost_net",
        "am_auto_cost",
        "am_auto_cost_net",
        "ssab_cost",
        "ssab_cost_net",
        "adi_cost",
        "adi_cost_net",
        "luso_cost",
        "luso_cost_net",
        "galmed_cost",
        "leon_cost",
        "tata_cost",
        "tata_cost_net",
        "bao_cfrfo",
        "bao_ddp_hl",
        "base_equivalent",
        "am_tons",
        "luso_tons",
        "import_tons",
        "offer_14_total",
        "offer_15_total",
        "offer_16_total",
        "offer_17_total",
        "is_valid_row",
        "validation_error",
        "processed_to_core",
    ]

    placeholders = ", ".join(["?"] * len(columns))
    sql = f"""
        INSERT INTO stg_boss_matrix ({", ".join(columns)})
        VALUES ({placeholders})
    """

    values = [tuple(row.get(col) for col in columns) for row in rows]
    conn.executemany(sql, values)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"No existe el Excel: {EXCEL_PATH}")

    df = pd.read_excel(
        EXCEL_PATH,
        sheet_name=SHEET_NAME,
        header=HEADER_ROW,
        dtype=object,
        engine="openpyxl",
    )

    df.columns = make_unique_columns(list(df.columns))
    df = df.dropna(how="all").reset_index(drop=True)

    import_batch_id = f"boss_marzo_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    rows_to_insert = []
    for idx, row in df.iterrows():
        payload = build_payload(
            row=row,
            source_file_name=EXCEL_PATH.name,
            source_sheet_name=SHEET_NAME,
            source_row_number=HEADER_ROW + 2 + idx,
            import_batch_id=import_batch_id,
            imported_at=imported_at,
        )
        rows_to_insert.append(payload)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DELETE FROM stg_boss_matrix")
        insert_rows(conn, rows_to_insert)
        conn.commit()

    valid_rows = sum(1 for row in rows_to_insert if row["is_valid_row"] == 1)
    invalid_rows = len(rows_to_insert) - valid_rows

    print(f"Batch ID: {import_batch_id}")
    print(f"Filas leídas: {len(rows_to_insert)}")
    print(f"Filas válidas: {valid_rows}")
    print(f"Filas inválidas: {invalid_rows}")


if __name__ == "__main__":
    main()