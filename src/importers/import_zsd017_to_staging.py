from __future__ import annotations

from pathlib import Path
from datetime import datetime, date
import json
import sqlite3
import unicodedata
import uuid

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"
SAP_DIR = BASE_DIR / "data" / "raw" / "sap"

EXPECTED_HEADERS = {
    "organizacion ventas",
    "texto:organizacion ventas",
    "centro",
    "texto:centro",
    "numero de documento del documento modelo",
    "posicion documento ventas",
    "clase de documento de ventas",
    "texto:clase de documento de ventas",
    "grupo de vendedores",
    "texto:grupo de vendedores",
    "solicitante",
    "texto:solicitante",
    "destinatario de mercancias",
    "texto:destinatario de mercancias",
    "numero de material",
    "texto:numero de material",
    "tipo de material",
    "texto:tipo de material",
    "fecha movimiento de mercancias real",
    "peso neto",
    "peso bruto",
    "subtotal 1 de la condicion proveniente d",
    "valor neto en moneda de documento",
    "valor unitario f",
    "numero de lote",
    "familia",
    "texto:familia",
    "codigo interno de calidad",
    "espesor",
    "ancho",
    "largo",
    "nº de cliente",
    "texto:nº de cliente",
    "descripcion codigo calidad.",
    "metros",
    "fecha entrega solicitada",
    "periodo",
    "precio untario de ventas",
    "numero de pedido del cliente",
    "numero de lote de proveedor",
    "num. bobina",
}

COLUMN_MAPPING = {
    "organizacion ventas": "sales_org_text",
    "orgv": "sales_org_code",
    "centro": "center_text",
    "cen.": "center_code",
    "doc.modelo": "model_doc_number",
    "pos.": "sales_doc_position",
    "clvt": "sales_doc_type_code",
    "clase doc. ventas": "sales_doc_type_text",
    "gve": "seller_group_code",
    "grupo de vendedores": "seller_group_text",
    "solicitan.": "requester_code",
    "solicitante": "requester_name",
    "destinat.": "ship_to_code",
    "destinatario de mercancias": "ship_to_name",
    "material": "material_number",
    "numero de material": "material_text",
    "tpma": "material_type_code",
    "tipo de material": "material_type_text",
    "numero de material del cliente": "customer_material_number",
    "entrega": "delivery_number",
    "clen": "delivery_type_code",
    "clase de entrega": "delivery_type_text",
    "fe.sm real": "movement_date",
    "fechadispo": "availability_date",
    "cantidad de pedido": "ordered_qty",
    "cantidad de pedido.1": "sales_uom",
    "cantidad entrega": "delivered_qty",
    "peso neto": "net_weight",
    "peso bruto": "gross_weight",
    "valor total final": "net_value",
    "valor unitario f": "unit_sales_value",
    "lote": "lot_number",
    "fa": "family_code",
    "familia": "family_text",
    "cali": "internal_quality_code",
    "descripcion codigo calidad.": "quality_description",
    "espeso": "thickness_mm",
    "ancho": "width_mm",
    "largo": "length_mm",
    "cliente": "customer_number",
    "numero de cliente": "customer_name",
    "no unidade": "units_count",
    "metros": "meters",
    "fecha entr": "requested_delivery_date",
    "periodo": "period",
    "precio untario de": "sales_unit_price",
    "no pedido cliente": "customer_order_number",
    "lote-proveedor": "supplier_lot_number",
    "bobina": "coil_number",
}


NUMERIC_FIELDS = {
    "ordered_qty",
    "delivered_qty",
    "net_weight",
    "gross_weight",
    "net_value",
    "unit_sales_value",
    "thickness_mm",
    "width_mm",
    "length_mm",
    "units_count",
    "meters",
    "sales_unit_price",
}


DATE_FIELDS = {
    "movement_date",
    "availability_date",
    "requested_delivery_date",
}


def normalize_text(value: object) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = " ".join(text.split())
    return text


def parse_number(value: object) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def parse_date_to_iso(value: object) -> str | None:
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

    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def json_safe(value: object) -> object:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    return str(value).strip()


def find_excel_file() -> Path:
    allowed_suffixes = {".xlsx", ".xlsm"}
    files = sorted(
        [p for p in SAP_DIR.iterdir() if p.is_file() and p.suffix.lower() in allowed_suffixes]
    )

    if not files:
        raise FileNotFoundError(f"No se ha encontrado ningún Excel válido en: {SAP_DIR}")

    return files[0]


def score_header_row(df: pd.DataFrame) -> tuple[int | None, int]:
    best_row = None
    best_score = -1
    max_rows = min(len(df), 25)

    for row_idx in range(max_rows):
        row_values = [normalize_text(v) for v in df.iloc[row_idx].tolist()]
        row_values = [v for v in row_values if v]
        if not row_values:
            continue

        score = sum(1 for v in row_values if v in EXPECTED_HEADERS)

        if score > best_score:
            best_score = score
            best_row = row_idx

    return best_row, best_score


def choose_best_sheet(file_path: Path) -> tuple[str, int]:
    excel_file = pd.ExcelFile(file_path, engine="openpyxl")
    best_sheet = None
    best_header_row = None
    best_score = -1

    for sheet_name in excel_file.sheet_names:
        preview_df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
            dtype=object,
            engine="openpyxl",
        )

        header_row, score = score_header_row(preview_df)

        if score > best_score and header_row is not None:
            best_score = score
            best_sheet = sheet_name
            best_header_row = header_row

    if best_sheet is None or best_header_row is None:
        raise ValueError("No se ha podido detectar una hoja/cabecera válida para ZSD017.")

    return best_sheet, best_header_row


def build_row_payload(
    row: pd.Series,
    source_file_name: str,
    source_sheet_name: str,
    source_row_number: int,
    import_batch_id: str,
    imported_at: str,
) -> dict:
    raw_record = {
        str(column): json_safe(value)
        for column, value in row.items()
    }

    payload = {
        "source_file_name": source_file_name,
        "source_sheet_name": source_sheet_name,
        "source_row_number": source_row_number,
        "import_batch_id": import_batch_id,
        "imported_at": imported_at,
        "raw_record_json": json.dumps(raw_record, ensure_ascii=False),
        "is_valid_row": 1,
        "validation_error": None,
        "processed_to_core": 0,
    }

    normalized_row = {
        normalize_text(column): value
        for column, value in row.items()
    }

    for source_col, target_col in COLUMN_MAPPING.items():
        raw_value = normalized_row.get(source_col)

        if target_col in NUMERIC_FIELDS:
            payload[target_col] = parse_number(raw_value)
        elif target_col in DATE_FIELDS:
            payload[target_col] = parse_date_to_iso(raw_value)
        else:
            payload[target_col] = None if raw_value is None or pd.isna(raw_value) else str(raw_value).strip()

    material_number = payload.get("material_number")
    requester_code = payload.get("requester_code")
    movement_date = payload.get("movement_date")

    if not material_number:
        payload["is_valid_row"] = 0
        payload["validation_error"] = "Falta material_number"
    elif not requester_code:
        payload["is_valid_row"] = 0
        payload["validation_error"] = "Falta requester_code"
    elif not movement_date:
        payload["is_valid_row"] = 0
        payload["validation_error"] = "Falta movement_date"

    return payload


def insert_rows(connection: sqlite3.Connection, rows: list[dict]) -> None:
    if not rows:
        return

    columns = [
        "source_file_name",
        "source_sheet_name",
        "source_row_number",
        "import_batch_id",
        "imported_at",
        "raw_record_json",
        "sales_org_code",
        "sales_org_text",
        "center_code",
        "center_text",
        "model_doc_number",
        "sales_doc_position",
        "sales_doc_type_code",
        "sales_doc_type_text",
        "seller_group_code",
        "seller_group_text",
        "requester_code",
        "requester_name",
        "ship_to_code",
        "ship_to_name",
        "material_number",
        "material_text",
        "material_type_code",
        "material_type_text",
        "customer_material_number",
        "delivery_number",
        "delivery_type_code",
        "delivery_type_text",
        "movement_date",
        "availability_date",
        "ordered_qty",
        "sales_uom",
        "delivered_qty",
        "net_weight",
        "gross_weight",
        "weight_uom",
        "net_value",
        "currency",
        "unit_sales_value",
        "lot_number",
        "family_code",
        "family_text",
        "internal_quality_code",
        "quality_description",
        "thickness_mm",
        "width_mm",
        "length_mm",
        "customer_number",
        "customer_name",
        "units_count",
        "meters",
        "requested_delivery_date",
        "period",
        "sales_unit_price",
        "customer_order_number",
        "supplier_lot_number",
        "coil_number",
        "is_valid_row",
        "validation_error",
        "processed_to_core",
    ]

    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(columns)

    sql = f"""
        INSERT INTO stg_sap_zsd017_sales ({column_sql})
        VALUES ({placeholders})
    """

    values = [
        tuple(row.get(col) for col in columns)
        for row in rows
    ]

    connection.executemany(sql, values)


def import_zsd017_to_staging() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    file_path = find_excel_file()
    sheet_name, header_row = choose_best_sheet(file_path)

    print(f"Archivo detectado: {file_path.name}")
    print(f"Hoja seleccionada: {sheet_name}")
    print(f"Fila de cabecera detectada: {header_row}")

    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=header_row,
        dtype=object,
        engine="openpyxl",
    )

    df.columns = [normalize_text(col) for col in df.columns]
    df = df.loc[:, [col for col in df.columns if col]]
    df = df.dropna(how="all").reset_index(drop=True)

    import_batch_id = f"zsd017_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    imported_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    rows_to_insert = []
    for idx, row in df.iterrows():
        payload = build_row_payload(
            row=row,
            source_file_name=file_path.name,
            source_sheet_name=sheet_name,
            source_row_number=header_row + 2 + idx,
            import_batch_id=import_batch_id,
            imported_at=imported_at,
        )
        rows_to_insert.append(payload)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        insert_rows(connection, rows_to_insert)
        connection.commit()

    valid_rows = sum(1 for row in rows_to_insert if row["is_valid_row"] == 1)
    invalid_rows = len(rows_to_insert) - valid_rows

    print("\nImportación a staging completada.")
    print(f"Batch ID: {import_batch_id}")
    print(f"Filas leídas: {len(rows_to_insert)}")
    print(f"Filas válidas: {valid_rows}")
    print(f"Filas inválidas: {invalid_rows}")


if __name__ == "__main__":
    import_zsd017_to_staging()