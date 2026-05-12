from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


INPUT_REQUEST = {
    "client_name": "HIJOS DE ANGEL BALLESTER S.L.",
    "our_ref": "NUEVA_PRUEBA_001",
    "spec_id": 4,
    "requested_tons": 80.0,
    "missing_tons": 80.0,
    "sheet_date": "2026-04-16",
    "notes": "Alta manual rápida desde script",
}


def resolve_client(conn: sqlite3.Connection, client_name: str):
    client = conn.execute("""
        SELECT id, name
        FROM clients
        WHERE name = ?
    """, (client_name,)).fetchone()

    if client:
        return client

    client = conn.execute("""
        SELECT c.id, c.name
        FROM client_aliases a
        JOIN clients c ON c.id = a.client_id
        WHERE a.alias_name = ?
    """, (client_name,)).fetchone()

    return client


def create_sourcing_request(
    conn: sqlite3.Connection,
    client_id: int,
    request_spec_id: int,
    our_ref: str,
    requested_tons: float,
    missing_tons: float | None,
    sheet_date: str | None,
    notes: str | None,
    created_at: str,
) -> int:
    cursor = conn.execute("""
        INSERT INTO sourcing_requests (
            source_row_id,
            client_id,
            request_spec_id,
            our_ref,
            requested_tons,
            missing_tons,
            sheet_date,
            notes,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        -1,
        client_id,
        request_spec_id,
        our_ref,
        requested_tons,
        missing_tons,
        sheet_date,
        notes,
        "manual_seeded",
        created_at,
    ))
    return cursor.lastrowid


def seed_supplier_options_from_history(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    request_spec_id: int,
    requested_tons: float,
    created_at: str,
) -> int:
    historical_options = conn.execute("""
        SELECT
            so.option_code,
            so.supplier_name,
            so.cost_type,
            AVG(so.unit_cost) AS avg_unit_cost,
            COUNT(*) AS sample_count
        FROM supplier_options so
        JOIN sourcing_requests sr
          ON sr.id = so.sourcing_request_id
        WHERE sr.request_spec_id = ?
          AND so.is_comparable = 1
          AND so.is_rankable = 1
          AND so.unit_cost IS NOT NULL
        GROUP BY so.option_code, so.supplier_name, so.cost_type
        ORDER BY avg_unit_cost ASC, so.option_code ASC
    """, (request_spec_id,)).fetchall()

    inserted = 0

    for row in historical_options:
        unit_cost = float(row["avg_unit_cost"])
        total_cost = unit_cost * float(requested_tons)

        notes = (
            f"Seeded from historical spec averages | "
            f"sample_count={row['sample_count']}"
        )

        conn.execute("""
            INSERT INTO supplier_options (
                sourcing_request_id,
                option_code,
                supplier_name,
                cost_type,
                unit_cost,
                total_cost,
                currency,
                notes,
                created_at,
                is_available,
                is_zero_placeholder,
                is_suspicious,
                is_rankable,
                validation_note,
                is_comparable,
                comparability_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sourcing_request_id,
            row["option_code"],
            row["supplier_name"],
            row["cost_type"],
            unit_cost,
            total_cost,
            "EUR",
            notes,
            created_at,
            1,
            0,
            0,
            1,
            "OK",
            1,
            "COMPARABLE",
        ))
        inserted += 1

    return inserted


def build_shortlist_for_request(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    created_at: str,
) -> None:
    conn.execute("""
        DELETE FROM sourcing_request_shortlist
        WHERE sourcing_request_id = ?
    """, (sourcing_request_id,))

    options = conn.execute("""
        SELECT
            option_code,
            supplier_name,
            unit_cost,
            total_cost
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND is_comparable = 1
        ORDER BY unit_cost ASC, option_code ASC
    """, (sourcing_request_id,)).fetchall()

    am_spot = conn.execute("""
        SELECT unit_cost, total_cost
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND option_code = 'AM_SPOT'
          AND is_comparable = 1
        LIMIT 1
    """, (sourcing_request_id,)).fetchone()

    best = options[0] if len(options) > 0 else None
    second = options[1] if len(options) > 1 else None
    third = options[2] if len(options) > 2 else None

    am_spot_unit_cost = am_spot["unit_cost"] if am_spot else None
    am_spot_total_cost = am_spot["total_cost"] if am_spot else None

    delta_best_vs_am_spot = None
    savings_total_vs_am_spot = None

    if best and am_spot_unit_cost is not None:
        delta_best_vs_am_spot = float(best["unit_cost"]) - float(am_spot_unit_cost)

    if best and am_spot_total_cost is not None and best["total_cost"] is not None:
        savings_total_vs_am_spot = float(am_spot_total_cost) - float(best["total_cost"])

    conn.execute("""
        INSERT INTO sourcing_request_shortlist (
            sourcing_request_id,
            best_option_code,
            best_supplier_name,
            best_unit_cost,
            best_total_cost,
            second_option_code,
            second_supplier_name,
            second_unit_cost,
            second_total_cost,
            third_option_code,
            third_supplier_name,
            third_unit_cost,
            third_total_cost,
            am_spot_unit_cost,
            am_spot_total_cost,
            delta_best_vs_am_spot,
            savings_total_vs_am_spot,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sourcing_request_id,
        best["option_code"] if best else None,
        best["supplier_name"] if best else None,
        best["unit_cost"] if best else None,
        best["total_cost"] if best else None,
        second["option_code"] if second else None,
        second["supplier_name"] if second else None,
        second["unit_cost"] if second else None,
        second["total_cost"] if second else None,
        third["option_code"] if third else None,
        third["supplier_name"] if third else None,
        third["unit_cost"] if third else None,
        third["total_cost"] if third else None,
        am_spot_unit_cost,
        am_spot_total_cost,
        delta_best_vs_am_spot,
        savings_total_vs_am_spot,
        created_at,
    ))


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        spec = conn.execute("""
            SELECT id, product, grade, thickness_mm, width_mm, cw_min, cw_max
            FROM request_specs
            WHERE id = ?
        """, (INPUT_REQUEST["spec_id"],)).fetchone()

        if not spec:
            raise ValueError(f"No existe request_spec con id={INPUT_REQUEST['spec_id']}")

        client = resolve_client(conn, INPUT_REQUEST["client_name"])
        if not client:
            raise ValueError(
                f"No se ha podido resolver client_name='{INPUT_REQUEST['client_name']}' "
                f"ni por clients.name ni por client_aliases"
            )

        sourcing_request_id = create_sourcing_request(
            conn=conn,
            client_id=client["id"],
            request_spec_id=spec["id"],
            our_ref=INPUT_REQUEST["our_ref"],
            requested_tons=float(INPUT_REQUEST["requested_tons"]),
            missing_tons=float(INPUT_REQUEST["missing_tons"]) if INPUT_REQUEST["missing_tons"] is not None else None,
            sheet_date=INPUT_REQUEST["sheet_date"],
            notes=INPUT_REQUEST["notes"],
            created_at=created_at,
        )

        inserted_options = seed_supplier_options_from_history(
            conn=conn,
            sourcing_request_id=sourcing_request_id,
            request_spec_id=spec["id"],
            requested_tons=float(INPUT_REQUEST["requested_tons"]),
            created_at=created_at,
        )

        build_shortlist_for_request(
            conn=conn,
            sourcing_request_id=sourcing_request_id,
            created_at=created_at,
        )

        conn.commit()

    print("Nueva sourcing_request creada correctamente.")
    print(f"sourcing_request_id: {sourcing_request_id}")
    print(f"client_resolved: {client['name']}")
    print(
        f"spec_used: id={spec['id']} | "
        f"{spec['product']} | {spec['grade']} | "
        f"{spec['thickness_mm']} x {spec['width_mm']} | "
        f"cw=({spec['cw_min']}, {spec['cw_max']})"
    )
    print(f"supplier_options_seeded: {inserted_options}")


if __name__ == "__main__":
    main()