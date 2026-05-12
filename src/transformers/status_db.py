"""
status_db.py
------------
Muestra el estado actual del sistema: conteos por tabla, último import,
y señales de salud del pipeline.

Uso:
    python status_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH  = BASE_DIR / "db" / "steel_mvp.db"


def get_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return -1  # tabla no existe


def get_valid_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE is_valid_row = 1").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return None


def get_last_batch(conn: sqlite3.Connection, table: str) -> str:
    try:
        row = conn.execute(
            f"SELECT import_batch_id, imported_at FROM {table} ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            return f"{row[0]} ({row[1]})"
        return "—"
    except sqlite3.OperationalError:
        return "—"


def get_last_export(conn: sqlite3.Connection) -> str:
    export_path = BASE_DIR / "exports" / "sourcing_report.xlsx"
    if export_path.exists():
        import datetime
        mtime = export_path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = export_path.stat().st_size // 1024
        return f"{dt} ({size_kb} KB)"
    return "—"


def check_pipeline_health(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """
    Devuelve lista de (check, resultado, estado).
    estado: OK | AVISO | ERROR
    """
    checks = []

    # 1. ¿Hay datos en staging?
    stg_count = get_count(conn, "stg_boss_matrix")
    valid_count = get_valid_count(conn, "stg_boss_matrix") or 0
    if stg_count == 0:
        checks.append(("stg_boss_matrix tiene datos", "0 filas", "ERROR"))
    elif valid_count == 0:
        checks.append(("stg_boss_matrix tiene filas válidas", f"{stg_count} filas, 0 válidas", "ERROR"))
    else:
        checks.append(("stg_boss_matrix tiene datos", f"{valid_count} filas válidas de {stg_count}", "OK"))

    # 2. ¿Hay clients?
    clients = get_count(conn, "clients")
    if clients == 0:
        checks.append(("clients cargados", "0 clientes", "AVISO"))
    else:
        checks.append(("clients cargados", f"{clients} clientes", "OK"))

    # 3. ¿Hay sourcing_requests?
    sr = get_count(conn, "sourcing_requests")
    if sr == 0:
        checks.append(("sourcing_requests creadas", "0 requests", "ERROR"))
    else:
        checks.append(("sourcing_requests creadas", f"{sr} requests", "OK"))

    # 4. ¿Hay supplier_options?
    so = get_count(conn, "supplier_options")
    if so == 0:
        checks.append(("supplier_options cargadas", "0 opciones", "ERROR"))
    else:
        checks.append(("supplier_options cargadas", f"{so} opciones", "OK"))

    # 5. ¿Hay opciones comparables?
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM supplier_options WHERE is_comparable = 1"
        ).fetchone()
        comparable = row[0] if row else 0
        if comparable == 0:
            checks.append(("opciones comparables clasificadas", "0 comparables", "AVISO"))
        else:
            checks.append(("opciones comparables clasificadas", f"{comparable} comparables", "OK"))
    except sqlite3.OperationalError:
        checks.append(("opciones comparables clasificadas", "columna no existe", "AVISO"))

    # 6. ¿Hay shortlist?
    sl = get_count(conn, "sourcing_request_shortlist")
    if sl == 0:
        checks.append(("shortlist construida", "0 entradas", "ERROR"))
    else:
        checks.append(("shortlist construida", f"{sl} entradas", "OK"))

    # 7. ¿Hay opciones sin total_cost cuando deberían tenerlo?
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM supplier_options
            WHERE is_comparable = 1 AND total_cost IS NULL
        """).fetchone()
        missing_totals = row[0] if row else 0
        if missing_totals > 0:
            checks.append(("total_cost calculado", f"{missing_totals} comparables sin total_cost", "AVISO"))
        else:
            checks.append(("total_cost calculado", "todo calculado", "OK"))
    except sqlite3.OperationalError:
        pass

    return checks


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: No existe la base de datos: {DB_PATH}")
        print("Ejecuta primero: python src/init_db.py")
        return

    db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        print("=" * 70)
        print("STEEL MVP — ESTADO DEL SISTEMA")
        print("=" * 70)
        print(f"Base de datos : {DB_PATH}")
        print(f"Tamaño        : {db_size_mb:.1f} MB")
        print()

        # --- Staging ---
        print("STAGING")
        print("-" * 70)
        stg = get_count(conn, "stg_boss_matrix")
        stg_valid = get_valid_count(conn, "stg_boss_matrix") or 0
        stg_invalid = stg - stg_valid
        print(f"  stg_boss_matrix      : {stg:>6} filas  ({stg_valid} válidas, {stg_invalid} inválidas)")
        print(f"  Último import BOSS   : {get_last_batch(conn, 'stg_boss_matrix')}")

        sap = get_count(conn, "stg_sap_zsd017_sales")
        sap_valid = get_valid_count(conn, "stg_sap_zsd017_sales") or 0
        print(f"  stg_sap_zsd017_sales : {sap:>6} filas  ({sap_valid} válidas)")
        print(f"  Último import SAP    : {get_last_batch(conn, 'stg_sap_zsd017_sales')}")
        print()

        # --- Core ---
        print("CORE")
        print("-" * 70)
        core_tables = [
            ("clients",                    "Clientes"),
            ("client_aliases",             "Aliases de cliente"),
            ("materials",                  "Materiales"),
            ("request_specs",              "Specs de request"),
            ("sourcing_requests",          "Sourcing requests"),
            ("supplier_options",           "Supplier options"),
            ("provider_capabilities",      "Capabilities de proveedor"),
            ("sourcing_request_shortlist", "Shortlist"),
        ]
        for table, label in core_tables:
            count = get_count(conn, table)
            indicator = f"{count:>6}" if count >= 0 else "  N/A "
            print(f"  {label:30s}: {indicator} filas")

        # Detalle supplier_options
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM supplier_options WHERE is_comparable = 1"
            ).fetchone()
            comparable = row[0] if row else 0
            print(f"  {'  → comparables':30s}: {comparable:>6} filas")
        except sqlite3.OperationalError:
            pass

        print()

        # --- Request intakes (creación manual) ---
        ri = get_count(conn, "request_intakes")
        if ri >= 0:
            print("REQUESTS MANUALES")
            print("-" * 70)
            print(f"  request_intakes              : {ri:>6} filas")
            print()

        # --- Export ---
        print("EXPORTS")
        print("-" * 70)
        print(f"  sourcing_report.xlsx : {get_last_export(conn)}")
        print()

        # --- Health checks ---
        print("DIAGNÓSTICO DEL PIPELINE")
        print("-" * 70)
        checks = check_pipeline_health(conn)
        for check, result, estado in checks:
            icon = "✓" if estado == "OK" else ("⚠" if estado == "AVISO" else "✗")
            print(f"  {icon} [{estado:5s}] {check}: {result}")

        print()
        print("=" * 70)

        n_errors  = sum(1 for _, _, e in checks if e == "ERROR")
        n_avisos  = sum(1 for _, _, e in checks if e == "AVISO")
        n_ok      = sum(1 for _, _, e in checks if e == "OK")
        print(f"  Checks OK: {n_ok}  Avisos: {n_avisos}  Errores: {n_errors}")
        print("=" * 70)

        if n_errors > 0:
            print("\nHay errores. Ejecuta el pipeline para corregirlos:")
            print("  python src/pipeline/run_pipeline.py --with-import")
        elif n_avisos > 0:
            print("\nHay avisos. Revisa los puntos marcados con ⚠.")
        else:
            print("\nEl sistema está en buen estado.")


if __name__ == "__main__":
    main()
