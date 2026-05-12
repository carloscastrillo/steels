"""
calibrate_provider_capabilities.py
------------------------------------
Lee los datos REALES de stg_boss_matrix y actualiza provider_capabilities
con los rangos min/max de thickness y width observados para cada proveedor.

Un proveedor tiene capacidad para un producto/espesor/ancho si tiene
un precio no nulo en la columna correspondiente del BOSS.

Uso:
    python calibrate_provider_capabilities.py         # actualiza, no borra reglas manuales
    python calibrate_provider_capabilities.py --reset # borra y recarga desde cero

Cuándo ejecutar:
    Después de importar un nuevo BOSS. Los rangos se ajustan solos
    según lo que el mercado real ha ofertado.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH  = BASE_DIR / "db" / "steel_mvp.db"


# Mapeo: (provider_code, provider_name) → columna de coste en stg_boss_matrix
PROVIDER_COST_COLUMNS = {
    ("AM_SPOT",  "ArcelorMittal"):  "am_spot_cost",
    ("SSAB",     "SSAB"):           "ssab_cost",
    ("ADI",      "ADI Italia"):     "adi_cost",
    ("LUSO",     "Luso"):           "luso_cost",
    ("GALMED",   "Galmed"):         "galmed_cost",
    ("LEON",     "Leon"):           "leon_cost",
    ("TATA",     "Tata"):           "tata_cost",
    ("BAO_CFRFO","Baosteel"):       "bao_cfrfo",
}

# Productos reconocidos (tal como aparecen en stg_boss_matrix.product)
PRODUCTS = ["CRC", "HDG", "DKP", "HRC"]


def get_calibrated_rules(conn: sqlite3.Connection) -> list[dict]:
    """
    Para cada proveedor y cada producto, calcula:
      - min/max de thickness_mm donde el proveedor tiene precio no nulo
      - min/max de width_mm donde el proveedor tiene precio no nulo
    """
    rules = []
    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for (provider_code, provider_name), cost_col in PROVIDER_COST_COLUMNS.items():
        # Verificar que la columna existe en la tabla
        col_check = conn.execute(
            "SELECT COUNT(*) FROM pragma_table_info('stg_boss_matrix') WHERE name = ?",
            (cost_col,)
        ).fetchone()
        if not col_check or col_check[0] == 0:
            print(f"  [AVISO] Columna '{cost_col}' no encontrada en stg_boss_matrix. Saltando {provider_code}.")
            continue

        for product in PRODUCTS:
            row = conn.execute(f"""
                SELECT
                    COUNT(*)                    AS n_rows,
                    MIN(thickness_mm)           AS min_thickness,
                    MAX(thickness_mm)           AS max_thickness,
                    MIN(width_mm)               AS min_width,
                    MAX(width_mm)               AS max_width
                FROM stg_boss_matrix
                WHERE is_valid_row = 1
                  AND UPPER(TRIM(product)) = UPPER(?)
                  AND {cost_col} IS NOT NULL
                  AND {cost_col} > 0
                  AND thickness_mm IS NOT NULL
                  AND width_mm IS NOT NULL
            """, (product,)).fetchone()

            if not row or row["n_rows"] == 0:
                # Este proveedor no tiene datos para este producto — no crear regla
                continue

            rules.append({
                "provider_code":    provider_code,
                "provider_name":    provider_name,
                "product":          product,
                "grade_pattern":    None,   # cualquier calidad
                "min_thickness_mm": round(row["min_thickness"], 2),
                "max_thickness_mm": round(row["max_thickness"], 2),
                "min_width_mm":     round(row["min_width"], 0),
                "max_width_mm":     round(row["max_width"], 0),
                "n_rows_source":    row["n_rows"],
                "notes":            f"Auto-calibrado desde stg_boss_matrix ({row['n_rows']} filas) - {created_at[:10]}",
                "created_at":       created_at,
            })

    return rules


def upsert_rules(conn: sqlite3.Connection, rules: list[dict], reset: bool) -> int:
    if reset:
        conn.execute("DELETE FROM provider_capabilities")
        print("  Reglas anteriores borradas (--reset).")

    inserted = 0
    updated  = 0

    for rule in rules:
        existing = conn.execute("""
            SELECT id FROM provider_capabilities
            WHERE provider_code = ? AND product = ?
        """, (rule["provider_code"], rule["product"])).fetchone()

        if existing and not reset:
            conn.execute("""
                UPDATE provider_capabilities
                SET min_thickness_mm = ?,
                    max_thickness_mm = ?,
                    min_width_mm     = ?,
                    max_width_mm     = ?,
                    notes            = ?
                WHERE id = ?
            """, (
                rule["min_thickness_mm"],
                rule["max_thickness_mm"],
                rule["min_width_mm"],
                rule["max_width_mm"],
                rule["notes"],
                existing["id"],
            ))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO provider_capabilities (
                    provider_code, provider_name, product, grade_pattern,
                    min_thickness_mm, max_thickness_mm,
                    min_width_mm, max_width_mm,
                    is_active, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                rule["provider_code"],
                rule["provider_name"],
                rule["product"],
                rule["grade_pattern"],
                rule["min_thickness_mm"],
                rule["max_thickness_mm"],
                rule["min_width_mm"],
                rule["max_width_mm"],
                rule["notes"],
                rule["created_at"],
            ))
            inserted += 1

    conn.commit()
    return inserted + updated


def print_rules_summary(rules: list[dict]) -> None:
    print(f"\n{'PROVEEDOR':<12} {'PRODUCTO':<6} {'ESP.MIN':>7} {'ESP.MAX':>7} {'ANCHO.MIN':>9} {'ANCHO.MAX':>9} {'FILAS':>6}")
    print("-" * 65)
    for r in sorted(rules, key=lambda x: (x["provider_code"], x["product"])):
        print(
            f"{r['provider_code']:<12} {r['product']:<6} "
            f"{r['min_thickness_mm']:>7.2f} {r['max_thickness_mm']:>7.2f} "
            f"{r['min_width_mm']:>9.0f} {r['max_width_mm']:>9.0f} "
            f"{r['n_rows_source']:>6}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibra provider_capabilities desde datos reales del BOSS.")
    parser.add_argument("--reset", action="store_true", help="Borra todas las reglas antes de cargar las nuevas.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: No existe la base de datos: {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Verificar que hay datos en staging
        stg_count = conn.execute(
            "SELECT COUNT(*) FROM stg_boss_matrix WHERE is_valid_row = 1"
        ).fetchone()[0]

        if stg_count == 0:
            print("ERROR: stg_boss_matrix no tiene filas válidas.")
            print("Importa el BOSS primero: python src/importers/import_boss_to_staging.py")
            sys.exit(1)

        print(f"Calibrando desde {stg_count} filas válidas en stg_boss_matrix...")

        rules = get_calibrated_rules(conn)

        if not rules:
            print("No se encontraron reglas que calibrar. Revisa que el BOSS tenga datos de precio.")
            sys.exit(0)

        print_rules_summary(rules)

        total = upsert_rules(conn, rules, reset=args.reset)

    action = "cargadas" if args.reset else "insertadas/actualizadas"
    print(f"\nReglas {action}: {total}")
    print("Calibración completada.")


if __name__ == "__main__":
    main()
