from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"


LAYERS = [
    (
        "CAPA 1 — STAGING SAP",
        [
            "stg_sap_zsd017_sales",
        ],
    ),
    (
        "CAPA 2 — STAGING BOSS",
        [
            "stg_boss_matrix",
            "stg_boss_request_candidates",
        ],
    ),
    (
        "CAPA 3 — STAGING DOCUMENTOS DE PROVEEDOR",
        [
            "stg_supplier_documents",
            "stg_supplier_quotes",
        ],
    ),
    (
        "CAPA 4 — CORE OPERATIVO",
        [
            "clients",
            "client_aliases",
            "materials",
            "request_specs",
            "sourcing_requests",
            "request_intakes",
            "provider_capabilities",
            "supplier_options",
            "sourcing_request_shortlist",
            "sourcing_quotes",
            "sourcing_decisions",
        ],
    ),
    (
        "CAPA 5 — LEGACY / PRE-SPRINT 2",
        [
            "requests",
            "decisions",
            "providers",
            "documents",
        ],
    ),
]


LEGACY_NOTES = {
    "requests": "LEGACY: no usar en código nuevo. Usar sourcing_requests.",
    "decisions": "LEGACY: no usar en código nuevo. Usar sourcing_decisions.",
    "providers": "LEGACY: tabla vacía del modelo antiguo.",
    "documents": "LEGACY: no usar en flujo nuevo. Usar stg_supplier_documents.",
}


def normalize_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")

    sql = re.sub(
        r"^CREATE TABLE\s+",
        "CREATE TABLE IF NOT EXISTS ",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"^CREATE UNIQUE INDEX\s+",
        "CREATE UNIQUE INDEX IF NOT EXISTS ",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"^CREATE INDEX\s+",
        "CREATE INDEX IF NOT EXISTS ",
        sql,
        flags=re.IGNORECASE,
    )

    return sql + ";"


def get_table_sql(conn: sqlite3.Connection, table_name: str) -> str | None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
          AND name NOT LIKE 'sqlite_%'
        """,
        (table_name,),
    ).fetchone()

    return row["sql"] if row and row["sql"] else None


def get_all_user_tables(conn: sqlite3.Connection) -> list[str]:
    return [
        row["name"]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]


def get_all_indexes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index'
          AND name NOT LIKE 'sqlite_%'
          AND sql IS NOT NULL
        ORDER BY tbl_name, name
        """
    ).fetchall()


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la DB: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        all_tables = get_all_user_tables(conn)
        known_tables = {table for _, tables in LAYERS for table in tables}
        unknown_tables = [table for table in all_tables if table not in known_tables]

        lines: list[str] = []

        lines.append("-- ============================================================")
        lines.append("-- HIERROS Steel MVP — Schema canónico")
        lines.append(f"-- Generado desde: {DB_PATH}")
        lines.append(f"-- Última generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("--")
        lines.append("-- Este fichero debe reflejar la estructura REAL de steel_mvp.db.")
        lines.append("-- Capas: staging SAP, staging BOSS, staging proveedor, core operativo y legacy.")
        lines.append("-- ============================================================")
        lines.append("")
        lines.append("PRAGMA foreign_keys = ON;")
        lines.append("")

        for layer_title, tables in LAYERS:
            existing_layer_tables = [table for table in tables if table in all_tables]
            if not existing_layer_tables:
                continue

            lines.append("")
            lines.append("-- ============================================================")
            lines.append(f"-- {layer_title}")
            lines.append("-- ============================================================")
            lines.append("")

            for table in existing_layer_tables:
                if table in LEGACY_NOTES:
                    lines.append(f"-- {LEGACY_NOTES[table]}")

                sql = get_table_sql(conn, table)
                if sql is None:
                    lines.append(f"-- WARNING: tabla {table} no encontrada o sin SQL.")
                    continue

                lines.append(f"-- table: {table}")
                lines.append(normalize_sql(sql))
                lines.append("")

        if unknown_tables:
            lines.append("")
            lines.append("-- ============================================================")
            lines.append("-- OTRAS TABLAS DETECTADAS NO CLASIFICADAS")
            lines.append("-- ============================================================")
            lines.append("")

            for table in unknown_tables:
                sql = get_table_sql(conn, table)
                if sql:
                    lines.append(f"-- table: {table}")
                    lines.append(normalize_sql(sql))
                    lines.append("")

        indexes = get_all_indexes(conn)
        if indexes:
            lines.append("")
            lines.append("-- ============================================================")
            lines.append("-- ÍNDICES")
            lines.append("-- ============================================================")
            lines.append("")

            for idx in indexes:
                lines.append(f"-- index: {idx['name']} ON {idx['tbl_name']}")
                lines.append(normalize_sql(idx["sql"]))
                lines.append("")

        SCHEMA_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("schema.sql reconstruido correctamente.")
    print(f"Archivo generado: {SCHEMA_PATH}")
    print(f"Tablas detectadas: {len(all_tables)}")
    for table in all_tables:
        print(f" - {table}")


if __name__ == "__main__":
    main()