from __future__ import annotations



from pathlib import Path

from datetime import datetime

import sqlite3





BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_PATH = BASE_DIR / "db" / "steel_mvp.db"





def ask_text(label: str, default: str | None = None) -> str | None:

    suffix = f" [{default}]" if default not in (None, "") else ""

    raw = input(f"{label}{suffix}: ").strip()

    if raw == "":

        return default

    return raw





def ask_float(label: str, default: float | None = None) -> float | None:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip().replace(",", ".")
        if raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            print("Valor numérico no válido. Inténtalo otra vez.")




def ask_int(label: str, default: int | None = None) -> int | None:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            print("Valor entero no válido. Inténtalo otra vez.")



def show_recent_requests(conn: sqlite3.Connection) -> None:

    rows = conn.execute("""

        SELECT
            sr.id,
            sr.our_ref,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            sr.requested_tons,
            sr.status
        FROM sourcing_requests sr
        JOIN clients c       ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        ORDER BY sr.id DESC
        LIMIT 15
    """).fetchall()



    print("-" * 120)

    print("ULTIMAS SOURCING_REQUESTS")

    for row in rows:

        print(

            f"id={row['id']} | ref={row['our_ref']} | client={row['client_name']} | "

            f"{row['product']} | {row['grade']} | {row['thickness_mm']} x {row['width_mm']} | "

            f"tn={row['requested_tons']} | status={row['status']}"

        )

    print("-" * 120)





def show_request_context(conn: sqlite3.Connection, sourcing_request_id: int) -> sqlite3.Row | None:

    row = conn.execute("""

        SELECT 
            sr.id,
            sr.our_ref,
            sr.requested_tons,
            sr.status,
            c.name AS client_name,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            rs.cw_min,
            rs.cw_max
        FROM sourcing_requests sr
        JOIN clients c        ON c.id = sr.client_id
        JOIN request_specs rs ON rs.id = sr.request_spec_id
        WHERE sr.id = ?
    """, (sourcing_request_id,)).fetchone()



    if row:

        print("REQUEST SELECCIONADA")

        print("-" * 120)

        print(dict(row))

        print("-" * 120)



    return row





def show_allowed_suppliers(conn: sqlite3.Connection, sourcing_request_id: int) -> None:

    rows = conn.execute("""

        SELECT DISTINCT

            option_code,

            supplier_name,

            capability_allowed,

            is_comparable,

            is_rankable

        FROM supplier_options

        WHERE sourcing_request_id = ?

        ORDER BY option_code

    """, (sourcing_request_id,)).fetchall()



    print("PROVEEDORES / OPCIONES OBSERVADAS EN ESTA REQUEST")

    print("-" * 120)

    for row in rows:

        print(dict(row))

    print("-" * 120)

def ask_yes_no(label: str, default_no: bool = True) -> bool:
    suffix = " [s/N]" if default_no else " [S/n]"
    while True:
        raw = input(f"{label}{suffix}: ").strip().upper()
        if raw == "":
            return not default_no
        if raw in ("S", "SI", "Y", "YES", "1"):
            return True
        if raw in ("N", "NO", "0"):
            return False
        print("Respuesta no válida. Usa s/n, y/n o 1/0.")

def get_supplier_option_context(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    supplier_code: str,
) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT
            option_code,
            supplier_name,
            capability_allowed,
            is_comparable,
            is_rankable
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND UPPER(option_code) = ?
        LIMIT 1
    """, (sourcing_request_id, supplier_code)).fetchone()

def get_expected_supplier_name(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    supplier_code: str,
) -> str | None:
    row = conn.execute("""
        SELECT supplier_name
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND UPPER(option_code) = ?
        LIMIT 1
    """, (sourcing_request_id, supplier_code)).fetchone()

    if row and row["supplier_name"]:
        return row["supplier_name"].strip()

    row = conn.execute("""
        SELECT provider_name
        FROM provider_capabilities
        WHERE UPPER(provider_code) = ?
          AND is_active = 1
        LIMIT 1
    """, (supplier_code,)).fetchone()

    if row and row["provider_name"]:
        return row["provider_name"].strip()

    canonical_map = {
        "SSAB": "SSAB",
        "ADI": "ADI Italia",
        "AM_SPOT": "ArcelorMittal",
        "AM_AUTO": "ArcelorMittal",
        "LUSO": "Luso",
        "GALMED": "Galmed",
        "LEON": "Leon",
        "TATA": "Tata",
        "BAO_CFRFO": "Baosteel",
        "BAO_DDP_HL": "Baosteel",
        "BASE_EQUIV": "Benchmark interno",
    }
    return canonical_map.get(supplier_code)

def normalize_transport_type(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().upper()
    if raw == "":
        return None

    mapping = {
        "TRUCK": "TRUCK",
        "CAMION": "TRUCK",
        "CAMIÓN": "TRUCK",
        "ROAD": "TRUCK",
        "BOAT": "BOAT",
        "SHIP": "BOAT",
        "SEA": "BOAT",
        "MARITIMO": "BOAT",
        "MARÍTIMO": "BOAT",
        "TRAIN": "TRAIN",
        "RAIL": "TRAIN",
    }
    return mapping.get(raw, raw)


def normalize_quality_confirmed(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().upper()
    if raw == "":
        return None

    if raw in ("YES", "Y", "S", "SI", "1"):
        return "YES"
    if raw in ("NO", "N", "0"):
        return "NO"
    return raw


def find_duplicate_quote(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    supplier_code: str,
    total_price_per_ton: float,
    quoted_tons: float,
) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT
            id,
            supplier_code,
            supplier_name,
            total_price_per_ton,
            quoted_tons,
            created_at
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
          AND UPPER(supplier_code) = ?
          AND ABS(COALESCE(total_price_per_ton, 0) - COALESCE(?, 0)) < 0.000001
          AND ABS(COALESCE(quoted_tons, 0) - COALESCE(?, 0)) < 0.000001
        LIMIT 1
    """, (sourcing_request_id, supplier_code, total_price_per_ton, quoted_tons)).fetchone()

def get_benchmark_option(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    supplier_code: str,
) -> sqlite3.Row | None:
    return conn.execute("""
        SELECT
            option_code,
            supplier_name,
            unit_cost,
            capability_allowed,
            is_comparable,
            is_rankable
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND UPPER(option_code) = ?
        LIMIT 1
    """, (sourcing_request_id, supplier_code)).fetchone()


def main() -> None:

    if not DB_PATH.exists():

        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")



    with sqlite3.connect(DB_PATH) as conn:

        conn.row_factory = sqlite3.Row



        show_recent_requests(conn)



        sourcing_request_id = ask_int("Sourcing request ID")

        if sourcing_request_id is None:

            raise ValueError("Debes indicar un sourcing_request_id")



        request_row = show_request_context(conn, sourcing_request_id)
        if request_row is None:
            raise ValueError(f"No existe sourcing_request_id={sourcing_request_id}")

        if request_row["status"] == "awarded":
            print("[AVISO] Esta sourcing_request ya está adjudicada (status = awarded).")
            if not ask_yes_no("¿Continuar igualmente creando una nueva quote?", default_no=True):
                print("Creación cancelada por el usuario.")
                return

        show_allowed_suppliers(conn, sourcing_request_id)



        supplier_code = ask_text("Supplier code (ej: SSAB, ADI, AM_SPOT, LUSO)")
        if not supplier_code:
            raise ValueError("Supplier code es obligatorio")
        supplier_code = supplier_code.strip().upper()

        supplier_ctx = get_supplier_option_context(conn, sourcing_request_id, supplier_code)

        supplier_name_default = supplier_ctx["supplier_name"] if supplier_ctx else None
        supplier_name = ask_text("Supplier name", supplier_name_default)
        if not supplier_name:
            raise ValueError("Supplier name es obligatorio")
        supplier_name = supplier_name.strip()

        print("-" * 120)
        print("VALIDACION DEL PROVEEDOR")

        auto_manual_review = 0
        auto_notes = []

        if supplier_ctx is None:
            print(f"[AVISO] No existe supplier_option previa para supplier_code={supplier_code} en esta request.")
            auto_manual_review = 1
            auto_notes.append("SUPPLIER_NOT_IN_PRECALCULATED_OPTIONS")
            if not ask_yes_no("¿Continuar igualmente?", default_no=True):
                print("Creación cancelada por el usuario.")
                return
        else:
            print(dict(supplier_ctx))

            if supplier_ctx["capability_allowed"] != 1:
                print(f"[AVISO] capability_allowed != 1 para supplier_code={supplier_code}")
                auto_manual_review = 1
                auto_notes.append("CAPABILITY_NOT_ALLOWED")
                if not ask_yes_no("¿Continuar igualmente?", default_no=True):
                    print("Creación cancelada por el usuario.")
                    return

        expected_name = get_expected_supplier_name(conn, sourcing_request_id, supplier_code)
        if expected_name and supplier_name.casefold() != expected_name.casefold():
            print("[AVISO] Supplier name no coincide con el esperado.")
            print(f"Esperado: {expected_name}")
            print(f"Introducido: {supplier_name}")
            auto_manual_review = 1
            auto_notes.append("SUPPLIER_NAME_MISMATCH")
            if not ask_yes_no("¿Continuar igualmente?", default_no=True):
                print("Creación cancelada por el usuario.")
                return



        quoted_price_per_ton = ask_float("Quoted base price per ton")
        if quoted_price_per_ton is None:
            raise ValueError("Quoted base price per ton es obligatorio")

        transport_cost_per_ton = ask_float("Transport cost per ton", 0.0) or 0.0
        surcharges_per_ton = ask_float("Surcharges per ton", 0.0) or 0.0

        total_price_per_ton = quoted_price_per_ton + transport_cost_per_ton + surcharges_per_ton

        quoted_tons = ask_float("Quoted tons", float(request_row["requested_tons"]))
        if quoted_tons is None:
            quoted_tons = float(request_row["requested_tons"])

        total_estimated_cost = total_price_per_ton * quoted_tons

        benchmark = get_benchmark_option(conn, sourcing_request_id, supplier_code)
        if benchmark is not None and benchmark["unit_cost"] is not None:
            benchmark_price = float(benchmark["unit_cost"])
            if benchmark_price > 0:
                delta_pct = abs(total_price_per_ton - benchmark_price) / benchmark_price
                if delta_pct > 0.25:
                    print("[AVISO] La quote se desvía más de un 25% del benchmark precalculado.")
                    print(f"Benchmark {supplier_code}: {benchmark_price:.2f} EUR/t")
                    print(f"Quote actual: {total_price_per_ton:.2f} EUR/t")
                    auto_manual_review = 1
                    auto_notes.append("STRONG_DEVIATION_VS_BENCHMARK")

        requested_tons = float(request_row["requested_tons"] or 0)
        if requested_tons > 0:
            tons_ratio = quoted_tons / requested_tons
            if tons_ratio < 0.5 or tons_ratio > 1.5:
                print("[AVISO] Las toneladas cotizadas se alejan mucho de la request.")
                print(f"Request tons: {requested_tons:.2f} | Quote tons: {quoted_tons:.2f}")
                auto_manual_review = 1
                auto_notes.append("QUOTED_TONS_FAR_FROM_REQUEST")


        duplicate = find_duplicate_quote(
            conn=conn,
            sourcing_request_id=sourcing_request_id,
            supplier_code=supplier_code,
            total_price_per_ton=total_price_per_ton,
            quoted_tons=quoted_tons,
        )

        if duplicate is not None:
            print("[AVISO] Ya existe una quote muy similar para esta request.")
            print(dict(duplicate))
            auto_manual_review = 1
            auto_notes.append("POTENTIAL_DUPLICATE_QUOTE")
            if not ask_yes_no("¿Continuar igualmente?", default_no=True):
                print("Creación cancelada por el usuario.")
                return



        currency = ask_text("Currency", "EUR") or "EUR"
        lead_time_days = ask_int("Lead time days")
        transport_type = normalize_transport_type(ask_text("Transport type"))
        quality_confirmed = normalize_quality_confirmed(ask_text("Quality confirmed", "yes"))
        source_type = ask_text("Source type", "manual") or "manual"


        needs_manual_review_input = ask_int("Needs manual review (0/1)", auto_manual_review)
        needs_manual_review = 1 if (needs_manual_review_input or 0) == 1 or auto_manual_review == 1 else 0

        notes = ask_text("Notes")
        if auto_notes:
            notes = " | ".join(auto_notes + ([notes] if notes else []))



        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")



        conn.execute("""
            INSERT INTO sourcing_quotes (
                sourcing_request_id,
                supplier_code,
                supplier_name,
                quoted_price_per_ton,
                transport_cost_per_ton,
                surcharges_per_ton,
                total_price_per_ton,
                total_estimated_cost,
                currency,
                quoted_tons,
                lead_time_days,
                transport_type,
                quality_confirmed,
                source_type,
                needs_manual_review,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            sourcing_request_id,
            supplier_code,
            supplier_name,
            quoted_price_per_ton,
            transport_cost_per_ton,
            surcharges_per_ton,
            total_price_per_ton,
            total_estimated_cost,
            currency,
            quoted_tons,
            lead_time_days,
            transport_type,
            quality_confirmed,
            source_type,
            needs_manual_review,
            notes,
            created_at,
        ))

        conn.commit()



        quote_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]


        print("QUOTE CREADA CORRECTAMENTE")
        print("-" * 120)
        print(f"sourcing_quote_id: {quote_id}")
        print(f"sourcing_request_id: {sourcing_request_id}")
        print(f"supplier_code: {supplier_code}")
        print(f"supplier_name: {supplier_name}")
        print(f"quoted_price_per_ton: {quoted_price_per_ton}")
        print(f"transport_cost_per_ton: {transport_cost_per_ton}")
        print(f"surcharges_per_ton: {surcharges_per_ton}")
        print(f"total_price_per_ton: {total_price_per_ton}")
        print(f"quoted_tons: {quoted_tons}")
        print(f"total_estimated_cost: {total_estimated_cost}")
        print(f"needs_manual_review: {needs_manual_review}")
        print(f"notes: {notes}")

if __name__ == "__main__":

    main()