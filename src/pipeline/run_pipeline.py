"""
run_pipeline.py  (Sprint 2 — actualizado)
------------------------------------------
Ejecuta el pipeline completo de transformación.
Incorpora protección de sourcing_quotes y sourcing_decisions: si existen datos
de cotizaciones antes del re-import, avisa y ofrece backup CSV.

Uso:
    python src/pipeline/run_pipeline.py                       # sin import
    python src/pipeline/run_pipeline.py --with-import         # pide hoja
    python src/pipeline/run_pipeline.py --with-import --sheet "ABRIL 2026"
    python src/pipeline/run_pipeline.py --with-import --sheet "ABRIL 2026" --force
"""



from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from sourcing_state_backup import backup_sourcing_state, restore_sourcing_state

BASE_DIR         = Path(__file__).resolve().parent.parent.parent
DB_PATH          = BASE_DIR / "db" / "steel_mvp.db"
SRC_DIR          = BASE_DIR / "src"
IMPORTERS_DIR    = SRC_DIR / "importers"
TRANSFORMERS_DIR = SRC_DIR / "transformers"
EXPORTS_DIR      = BASE_DIR / "exports"


# ---------------------------------------------------------------------------
# FUNCIONES ACTUALES DEL PIPELINE
# ---------------------------------------------------------------------------
'''
build_steps(...): ...
get_count(...): ...
table_exists(...): ...
confirm_reimport(...): ...
run_step(...): ...
print_summary(...): ...
_print_db_counts(...): ...
parse_args(...): ...
main(...): ...
'''


# ---------------------------------------------------------------------------
# Pasos del pipeline
# ---------------------------------------------------------------------------

def build_steps(sheet_name: str | None = None) -> list[dict]:
    import_args = ["--sheet", sheet_name] if sheet_name else []

    return [
        {
            "label":        "Importar BOSS a staging",
            "script":       IMPORTERS_DIR / "import_boss_to_staging.py",
            "verify_table": "stg_boss_matrix",
            "verify_min":   1,
            "args":         import_args,
            "optional":     True,
        },
        {
            "label":        "Cargar request_specs desde BOSS",
            "script":       TRANSFORMERS_DIR / "load_request_specs_from_boss.py",
            "verify_table": "request_specs",
            "verify_min":   1,
            "args":         [],
        },
        {
            "label":        "Cargar sourcing_requests desde BOSS",
            "script":       TRANSFORMERS_DIR / "load_sourcing_requests_from_boss.py",
            "verify_table": "sourcing_requests",
            "verify_min":   1,
            "args":         [],
        },
        {
            "label":        "Cargar supplier_options desde BOSS",
            "script":       TRANSFORMERS_DIR / "load_supplier_options_from_boss.py",
            "verify_table": "supplier_options",
            "verify_min":   1,
            "args":         [],
        },
        {
            "label":        "Calibrar capabilities de proveedor",
            "script":       TRANSFORMERS_DIR / "calibrate_provider_capabilities.py",
            "verify_table": "provider_capabilities",
            "verify_min":   1,
            "args":         [],
        },
        {
            "label":        "Validar opciones contra capabilities",
            "script":       TRANSFORMERS_DIR / "validate_supplier_options_against_capabilities.py",
            "verify_table": None,
            "verify_min":   0,
            "args":         [],
        },
        {
            "label":        "Validar opciones (campos requeridos)",
            "script":       TRANSFORMERS_DIR / "validate_supplier_options.py",
            "verify_table": None,
            "verify_min":   0,
            "args":         [],
        },
        {
            "label":        "Calcular costes totales",
            "script":       TRANSFORMERS_DIR / "update_supplier_option_total_costs.py",
            "verify_table": None,
            "verify_min":   0,
            "args":         [],
        },
        {
            "label":        "Clasificar comparabilidad de opciones",
            "script":       TRANSFORMERS_DIR / "classify_supplier_option_comparability.py",
            "verify_table": None,
            "verify_min":   0,
            "args":         [],
        },
        {
            "label":        "Construir shortlist de proveedores",
            "script":       TRANSFORMERS_DIR / "build_sourcing_request_shortlist.py",
            "verify_table": "sourcing_request_shortlist",
            "verify_min":   1,
            "args":         [],
        },
        {
            "label":        "Exportar sourcing report a Excel",
            "script":       TRANSFORMERS_DIR / "export_sourcing_report_to_excel.py",
            "verify_table": None,
            "verify_min":   0,
            "args":         [],
        },
    ]


# ---------------------------------------------------------------------------
# Helpers de BD
# ---------------------------------------------------------------------------

def get_count(table: str) -> int:
    if not DB_PATH.exists():
        return -1
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return -1


def table_exists(table: str) -> bool:
    if not DB_PATH.exists():
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            ).fetchone()
            return bool(row and row[0])
    except sqlite3.OperationalError:
        return False




# # ---------------------------------------------------------------------------
# # Protección de sourcing_quotes y sourcing_decisions antes del re-import
# # ---------------------------------------------------------------------------

# def backup_sourcing_quotes_to_csv(conn: sqlite3.Connection) -> Path | None:
#     """Exporta sourcing_quotes y sourcing_decisions a CSV de backup. Devuelve la ruta."""
#     EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     path = EXPORTS_DIR / f"backup_sourcing_quotes_sourcing_decisions_{ts}.csv"

#     rows = conn.execute("""
#         SELECT
#             sr.our_ref,
#             c.name          AS client_name,
#             q.supplier_code,
#             q.supplier_name,
#             q.quoted_price_per_ton,
#             q.transport_cost_per_ton,
#             q.surcharges_per_ton,
#             q.total_price_per_ton,
#             q.total_estimated_cost,
#             q.currency,
#             q.quoted_tons,
#             q.lead_time_days,
#             q.transport_type,
#             q.quality_confirmed,
#             q.source_type,
#             q.notes         AS quote_notes,
#             q.created_at    AS quote_created_at,
#             d.decision_reason,
#             d.decided_by,
#             d.decided_at
#         FROM sourcing_quotes q
#         JOIN sourcing_requests sr ON sr.id = q.sourcing_request_id
#         JOIN clients c            ON c.id  = sr.client_id
#         LEFT JOIN sourcing_decisions d     ON d.selected_quote_id = q.id
#         ORDER BY sr.our_ref, q.supplier_code
#     """).fetchall()

#     if not rows:
#         return None

#     fieldnames = [desc[0] for desc in conn.execute("""
#         SELECT
#             sr.our_ref, c.name, q.supplier_code, q.supplier_name,
#             q.quoted_price_per_ton, q.transport_cost_per_ton, q.surcharges_per_ton,
#             q.total_price_per_ton, q.total_estimated_cost, q.currency,
#             q.quoted_tons, q.lead_time_days, q.transport_type, q.quality_confirmed,
#             q.source_type, q.notes, q.created_at,
#             d.decision_reason, d.decided_by, d.decided_at
#         FROM sourcing_quotes q
#         JOIN sourcing_requests sr ON sr.id = q.sourcing_request_id
#         JOIN clients c            ON c.id  = sr.client_id
#         LEFT JOIN sourcing_decisions d     ON d.selected_quote_id = q.id
#         LIMIT 0
#     """).description]

#     with open(path, "w", newline="", encoding="utf-8-sig") as f:
#         writer = csv.writer(f)
#         writer.writerow(fieldnames)
#         writer.writerows(rows)

#     return path


# def check_and_warn_sourcing_quotes(force: bool = False) -> bool:
#     """
#     Verifica si hay sourcing_quotes/sourcing_decisions que se perderán con el re-import.
#     Si force=True, continúa sin preguntar (pero avisa).
#     Devuelve True si se puede continuar, False si el usuario cancela.
#     """
#     n_sourcing_quotes    = get_count("sourcing_quotes")    if table_exists("sourcing_quotes")    else 0
#     n_sourcing_decisions = get_count("sourcing_decisions") if table_exists("sourcing_decisions") else 0

#     if n_sourcing_quotes == 0 and n_sourcing_decisions == 0:
#         return True

#     print(f"\n  [AVISO] El re-import borrará datos existentes:")
#     print(f"    Quotes registradas   : {n_sourcing_quotes}")
#     print(f"    Decisiones tomadas   : {n_sourcing_decisions}")
#     print()

#     if force:
#         print("  --force activo. Continuando sin confirmación.")
#         if n_sourcing_quotes > 0:
#             with sqlite3.connect(DB_PATH) as conn:
#                 conn.row_factory = sqlite3.Row
#                 backup_path = backup_sourcing_quotes_to_csv(conn)
#                 if backup_path:
#                     print(f"  Backup guardado: {backup_path}")
#         return True

#     print("  Se creará un backup CSV automáticamente antes de borrar.")
#     raw = input("  ¿Continuar con el re-import? (s/N): ").strip().upper()
#     if raw not in ("S", "SI", "Y", "YES"):
#         print("  Re-import cancelado. Los datos existentes no se han modificado.")
#         return False

#     # Hacer backup
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.row_factory = sqlite3.Row
#         backup_path = backup_sourcing_quotes_to_csv(conn)
#         if backup_path:
#             print(f"  Backup guardado en: {backup_path}")
#         else:
#             print("  (No se generó backup porque no había sourcing_quotes con datos exportables.)")

#     return True

# ---------------------------------------------------------------------------
# Sustituto de lo de arriba - una función simple de confirmación
# ---------------------------------------------------------------------------
def confirm_reimport(force: bool = False) -> bool:
    n_sourcing_quotes = get_count("sourcing_quotes") if table_exists("sourcing_quotes") else 0
    n_sourcing_decisions = get_count("sourcing_decisions") if table_exists("sourcing_decisions") else 0

    if n_sourcing_quotes == 0 and n_sourcing_decisions == 0:
        return True

    print("\n  [AVISO] El re-import va a reconstruir el bloque BOSS.")
    print(f"    sourcing_quotes existentes   : {n_sourcing_quotes}")
    print(f"    sourcing_decisions existentes: {n_sourcing_decisions}")
    print("  Se hará backup JSON y se intentará restaurar al final del pipeline.\n")

    if force:
        print("  --force activo. Continuando sin confirmación.")
        return True

    raw = input("  ¿Continuar con el re-import? (s/N): ").strip().upper()
    if raw not in ("S", "SI", "Y", "YES"):
        print("  Re-import cancelado. No se ha modificado nada.")
        return False

    return True

# ---------------------------------------------------------------------------
# Ejecución de un paso
# ---------------------------------------------------------------------------

def run_step(step: dict, step_num: int, total: int) -> bool:
    label  = step["label"]
    script = step["script"]
    args   = step.get("args", [])

    print(f"\n{'='*70}")
    print(f"Paso {step_num}/{total}: {label}")
    print(f"Script: {script.name}")
    print("=" * 70)

    if not script.exists():
        print(f"[ERROR] Script no encontrado: {script}")
        return False

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        cwd=str(BASE_DIR),
    )
    elapsed = time.time() - t0

    ok = result.returncode == 0
    print(f"\n[{'OK' if ok else 'FALLO'}] Tiempo: {elapsed:.1f}s | Código: {result.returncode}")

    if not ok:
        return False

    verify_table = step.get("verify_table")
    verify_min   = step.get("verify_min", 0)

    if verify_table:
        count = get_count(verify_table)
        print(f"[VERIFY] {verify_table}: {count} filas")
        if verify_min > 0 and count < verify_min:
            print(f"[AVISO] Se esperaba al menos {verify_min} fila(s), hay {count}")
            return False

    return True


# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------

def print_summary(results: list[tuple[str, bool, int]]) -> None:
    print(f"\n{'='*70}")
    print("RESUMEN DEL PIPELINE")
    print("=" * 70)

    all_ok = True
    for label, ok, step_num in results:
        status = "✓" if ok else "✗ FALLO"
        print(f"  {step_num:2}. {status}  {label}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        _print_db_counts()
        print("\nPipeline completado sin errores.")
    else:
        print("Pipeline completado CON ERRORES.")


def _print_db_counts() -> None:
    tables = [
        "stg_boss_matrix",
        "clients",
        "request_specs",
        "sourcing_requests",
        "supplier_options",
        "provider_capabilities",
        "sourcing_request_shortlist",
        "sourcing_quotes",
        "sourcing_decisions",
    ]
    print("Estado final de la base de datos:")
    for t in tables:
        count = get_count(t)
        indicator = f"{count:>6}" if count >= 0 else "  N/A "
        print(f"  {t:40s}: {indicator} filas")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline completo de Steel MVP.")
    parser.add_argument("--with-import", action="store_true",
                        help="Importar el BOSS antes del pipeline")
    parser.add_argument("--sheet", type=str, default=None,
                        help='Hoja del BOSS, ej: "ABRIL 2026"')
    parser.add_argument("--force", action="store_true",
                        help="No pedir confirmación aunque haya sourcing_quotes/sourcing_decisions existentes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: No existe la base de datos: {DB_PATH}")
        print("Ejecuta: python src/init_db.py")
        sys.exit(1)

    steps = build_steps(sheet_name=args.sheet)

    backup_file = None

    if not args.with_import:
        steps = [s for s in steps if not s.get("optional")]
    else:
        if not confirm_reimport(force=args.force):
            sys.exit(0)

        backup_file = backup_sourcing_state(DB_PATH)

    total = len(steps)
    results = []

    for i, step in enumerate(steps, 1):
        ok = run_step(step, i, total)
        results.append((step["label"], ok, i))
        if not ok:
            print(f"\n[ABORT] Pipeline detenido en el paso {i}.\n")
            for j, remaining in enumerate(steps[i:], i + 1):
                results.append((remaining["label"], False, j))
            break

    if args.with_import:
        print(f"\n{'='*70}")
        print("RESTAURANDO SOURCING STATE")
        print("=" * 70)
        restore_sourcing_state(DB_PATH, backup_file)

    print_summary(results)

    all_ok = all(ok for _, ok, _ in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":

    main()
