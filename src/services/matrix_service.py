from __future__ import annotations

import sqlite3
from typing import Any


PREFERRED_SUPPLIER_ORDER = [
    "AM_SPOT",
    "AM_AUTO",
    "AM",
    "GALMED",
    "LEON",
    "BAO_DDP_HL",
    "BAO_CFRFO",
    "BASE_EQUIV",
    "TATA",
    "LUSO",
]


SUPPLIER_LABELS = {
    "AM_SPOT": "AM Spot",
    "AM_AUTO": "AM Auto",
    "AM": "AM PDF",
    "GALMED": "GALMED",
    "LEON": "LEON",
    "BAO_DDP_HL": "BAO DDP HL",
    "BAO_CFRFO": "BAO CFRFO",
    "BASE_EQUIV": "Base equiv.",
    "TATA": "TATA",
    "LUSO": "LUSO",
}


STATUS_LABELS = {
    "pending_review": "Pendiente de decisión",
    "pending": "Pendiente",
    "awarded": "Adjudicado",
    "cancelled": "Cancelado",
}


SOURCE_LABELS = {
    "BOSS": "Matriz",
    "QUOTE": "PDF proveedor",
    "manual": "Manual",
    "pdf": "PDF proveedor",
    None: "",
}


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(item[1])
        for item in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _client_name_expression(conn: sqlite3.Connection) -> str:
    columns = _table_columns(conn, "clients")

    candidates = [
        "client_name",
        "name",
        "customer_name",
        "business_name",
        "legal_name",
        "company_name",
    ]

    for column in candidates:
        if column in columns:
            return f"c.{column}"

    return "CAST(sr.client_id AS TEXT)"


def _normalise_source(value: Any) -> str:
    if value is None:
        return ""

    raw = str(value).strip()
    return SOURCE_LABELS.get(raw, raw)


def _normalise_status(value: Any) -> str:
    if value is None:
        return ""

    raw = str(value).strip()
    return STATUS_LABELS.get(raw, raw)


def _supplier_label(code: str) -> str:
    return SUPPLIER_LABELS.get(code, code.replace("_", " ").title())


def _money(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def list_matrix_supplier_codes(conn: sqlite3.Connection) -> list[str]:
    boss_codes = [
        str(item[0])
        for item in conn.execute("""
            SELECT DISTINCT option_code
            FROM supplier_options
            WHERE option_code IS NOT NULL
              AND unit_cost IS NOT NULL
              AND unit_cost > 0
        """).fetchall()
    ]

    quote_codes = [
        str(item[0])
        for item in conn.execute("""
            SELECT DISTINCT supplier_code
            FROM sourcing_quotes
            WHERE supplier_code IS NOT NULL
              AND total_price_per_ton IS NOT NULL
              AND total_price_per_ton > 0
              AND COALESCE(needs_manual_review, 1) = 0
        """).fetchall()
    ]

    all_codes = sorted(set(boss_codes + quote_codes))

    ordered = [
        code
        for code in PREFERRED_SUPPLIER_ORDER
        if code in all_codes
    ]

    remaining = [
        code
        for code in all_codes
        if code not in ordered
    ]

    return ordered + remaining


def _base_request_records(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    client_expr = _client_name_expression(conn)

    query = f"""
        SELECT
            sr.id AS request_id,
            sr.our_ref,
            {client_expr} AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            sr.requested_tons,
            COALESCE(sr.missing_tons, sr.requested_tons) AS missing_tons,
            sr.sheet_date,
            sr.status,
            sl.best_option_code,
            sl.best_supplier_name,
            sl.best_source,
            sl.best_unit_cost,
            sl.best_total_cost,
            sl.second_option_code,
            sl.second_supplier_name,
            sl.second_unit_cost,
            sl.third_option_code,
            sl.third_supplier_name,
            sl.third_unit_cost,
            sl.am_spot_unit_cost,
            sl.am_spot_total_cost,
            sl.delta_best_vs_am_spot,
            sl.savings_total_vs_am_spot
        FROM sourcing_requests sr
        LEFT JOIN request_specs rs
            ON rs.id = sr.request_spec_id
        LEFT JOIN clients c
            ON c.id = sr.client_id
        LEFT JOIN sourcing_request_shortlist sl
            ON sl.sourcing_request_id = sr.id
        ORDER BY
            sr.sheet_date,
            sr.our_ref,
            sr.id
    """

    raw_items = conn.execute(query).fetchall()

    request_records: list[dict[str, Any]] = []

    for item in raw_items:
        request_records.append({
            "request_id": item["request_id"],
            "ref": item["our_ref"],
            "cliente": item["client_name"],
            "producto": item["product"],
            "grado": item["grade"],
            "espesor_mm": item["thickness_mm"],
            "ancho_mm": item["width_mm"],
            "toneladas": item["requested_tons"],
            "falta_comprar_t": item["missing_tons"],
            "fecha": item["sheet_date"],
            "estado": _normalise_status(item["status"]),
            "estado_raw": item["status"],
            "mejor_codigo": item["best_option_code"],
            "mejor_proveedor": item["best_supplier_name"],
            "origen_mejor": _normalise_source(item["best_source"]),
            "origen_mejor_raw": item["best_source"],
            "mejor_eur_t": item["best_unit_cost"],
            "mejor_total": item["best_total_cost"],
            "segunda_opcion": item["second_option_code"],
            "segunda_eur_t": item["second_unit_cost"],
            "tercera_opcion": item["third_option_code"],
            "tercera_eur_t": item["third_unit_cost"],
            "am_spot_eur_t": item["am_spot_unit_cost"],
            "am_spot_total": item["am_spot_total_cost"],
            "ahorro_eur_t": item["delta_best_vs_am_spot"],
            "ahorro_total": item["savings_total_vs_am_spot"],
        })

    return request_records


def _price_options_by_request(conn: sqlite3.Connection) -> dict[int, dict[str, dict[str, Any]]]:
    price_map: dict[int, dict[str, dict[str, Any]]] = {}

    boss_items = conn.execute("""
        SELECT
            sourcing_request_id,
            option_code,
            supplier_name,
            unit_cost,
            total_cost
        FROM supplier_options
        WHERE option_code IS NOT NULL
          AND unit_cost IS NOT NULL
          AND unit_cost > 0
          AND COALESCE(is_available, 1) = 1
          AND COALESCE(is_zero_placeholder, 0) = 0
    """).fetchall()

    for item in boss_items:
        request_id = int(item["sourcing_request_id"])
        code = str(item["option_code"])
        unit_cost = _money(item["unit_cost"])

        if unit_cost is None:
            continue

        price_map.setdefault(request_id, {})

        current = price_map[request_id].get(code)

        if current is None or unit_cost < float(current["unit_cost"]):
            price_map[request_id][code] = {
                "supplier_code": code,
                "supplier_name": item["supplier_name"],
                "unit_cost": unit_cost,
                "total_cost": _money(item["total_cost"]),
                "source": "Matriz",
                "source_raw": "BOSS",
            }

    quote_items = conn.execute("""
        SELECT
            sourcing_request_id,
            supplier_code,
            supplier_name,
            total_price_per_ton,
            total_estimated_cost,
            source_type
        FROM sourcing_quotes
        WHERE sourcing_request_id IS NOT NULL
          AND supplier_code IS NOT NULL
          AND total_price_per_ton IS NOT NULL
          AND total_price_per_ton > 0
          AND COALESCE(needs_manual_review, 1) = 0
    """).fetchall()

    for item in quote_items:
        request_id = int(item["sourcing_request_id"])
        code = str(item["supplier_code"])
        unit_cost = _money(item["total_price_per_ton"])

        if unit_cost is None:
            continue

        price_map.setdefault(request_id, {})

        current = price_map[request_id].get(code)

        if current is None or unit_cost < float(current["unit_cost"]):
            price_map[request_id][code] = {
                "supplier_code": code,
                "supplier_name": item["supplier_name"],
                "unit_cost": unit_cost,
                "total_cost": _money(item["total_estimated_cost"]),
                "source": _normalise_source(item["source_type"]),
                "source_raw": item["source_type"],
            }

    return price_map


def list_monthly_matrix(
    conn: sqlite3.Connection,
    only_with_alternatives: bool = False,
    only_pdf_best: bool = False,
    status: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    supplier_codes = list_matrix_supplier_codes(conn)
    request_records = _base_request_records(conn)
    price_map = _price_options_by_request(conn)

    search_text = (search or "").strip().lower()

    matrix_records: list[dict[str, Any]] = []

    for record in request_records:
        request_id = int(record["request_id"])
        request_prices = price_map.get(request_id, {})

        enriched = dict(record)

        for code in supplier_codes:
            label = _supplier_label(code)
            option = request_prices.get(code)

            enriched[f"{label} €/t"] = option["unit_cost"] if option else None
            enriched[f"{label} origen"] = option["source"] if option else None

        if only_with_alternatives and not enriched.get("segunda_opcion"):
            continue

        if only_pdf_best and enriched.get("origen_mejor_raw") != "QUOTE":
            continue

        if status and status != "Todos" and enriched.get("estado_raw") != status:
            continue

        if search_text:
            searchable = " ".join(
                str(enriched.get(key) or "")
                for key in [
                    "ref",
                    "cliente",
                    "producto",
                    "grado",
                    "mejor_proveedor",
                    "mejor_codigo",
                ]
            ).lower()

            if search_text not in searchable:
                continue

        matrix_records.append(enriched)

    matrix_records.sort(
        key=lambda item: (
            item.get("ahorro_total") is None,
            -float(item.get("ahorro_total") or 0),
            str(item.get("cliente") or ""),
            str(item.get("ref") or ""),
        )
    )

    return matrix_records


def matrix_summary(matrix_records: list[dict[str, Any]]) -> dict[str, Any]:
    total_tons = sum(float(item.get("toneladas") or 0) for item in matrix_records)
    missing_tons = sum(float(item.get("falta_comprar_t") or 0) for item in matrix_records)
    total_savings = sum(float(item.get("ahorro_total") or 0) for item in matrix_records)

    return {
        "requests": len(matrix_records),
        "total_tons": total_tons,
        "missing_tons": missing_tons,
        "with_alternatives": sum(1 for item in matrix_records if item.get("segunda_opcion")),
        "pdf_best": sum(1 for item in matrix_records if item.get("origen_mejor_raw") == "QUOTE"),
        "awarded": sum(1 for item in matrix_records if item.get("estado_raw") == "awarded"),
        "total_savings": total_savings,
    }
