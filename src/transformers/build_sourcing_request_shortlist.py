from __future__ import annotations

from pathlib import Path
from datetime import datetime
import os
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("STEEL_DB_PATH", BASE_DIR / "db" / "steel_mvp.db"))


UNIT_COST_CANDIDATES = [
    "unit_cost",
    "total_cost_per_ton",
    "total_price_per_ton",
    "estimated_unit_cost",
    "option_unit_cost",
    "supplier_unit_cost",
]

TOTAL_COST_CANDIDATES = [
    "total_cost",
    "total_estimated_cost",
    "estimated_total_cost",
    "option_total_cost",
]


def get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def pick_column(columns: set[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def fetch_rankable_options(conn: sqlite3.Connection, request_id: int) -> list[dict]:
    """
    Devuelve opciones rankeables combinando:
      - supplier_options procedentes del BOSS
      - sourcing_quotes aprobadas en core

    Solo entran quotes core con needs_manual_review = 0.
    """

    supplier_option_cols = get_columns(conn, "supplier_options")

    unit_col = pick_column(supplier_option_cols, UNIT_COST_CANDIDATES)
    total_col = pick_column(supplier_option_cols, TOTAL_COST_CANDIDATES)

    if unit_col is None:
        raise RuntimeError(
            "No se encontró columna de coste unitario en supplier_options. "
            f"Columnas disponibles: {sorted(supplier_option_cols)}"
        )

    if "option_code" not in supplier_option_cols:
        raise RuntimeError("supplier_options no tiene option_code")

    if "supplier_name" not in supplier_option_cols:
        raise RuntimeError("supplier_options no tiene supplier_name")

    where_parts = [
        "so.sourcing_request_id = ?",
        f"so.{unit_col} IS NOT NULL",
    ]

    if "is_comparable" in supplier_option_cols:
        where_parts.append("COALESCE(so.is_comparable, 0) = 1")

    if "is_rankable" in supplier_option_cols:
        where_parts.append("COALESCE(so.is_rankable, 0) = 1")

    if "capability_allowed" in supplier_option_cols:
        where_parts.append("COALESCE(so.capability_allowed, 0) = 1")

    total_expr = (
        f"so.{total_col}"
        if total_col is not None
        else f"so.{unit_col} * COALESCE(sr.requested_tons, 0)"
    )

    boss_query = f"""
        SELECT
            so.option_code AS option_code,
            so.supplier_name AS supplier_name,
            so.{unit_col} AS unit_cost,
            {total_expr} AS total_cost,
            'BOSS' AS source
        FROM supplier_options so
        JOIN sourcing_requests sr
            ON sr.id = so.sourcing_request_id
        WHERE {" AND ".join(where_parts)}
        ORDER BY so.{unit_col} ASC
    """

    boss_options = conn.execute(boss_query, (request_id,)).fetchall()

    core_quotes = conn.execute("""
        SELECT
            supplier_code AS option_code,
            supplier_name AS supplier_name,
            total_price_per_ton AS unit_cost,
            COALESCE(
                total_estimated_cost,
                CASE
                    WHEN quoted_tons IS NOT NULL
                    THEN total_price_per_ton * quoted_tons
                    ELSE NULL
                END
            ) AS total_cost,
            'QUOTE' AS source
        FROM sourcing_quotes
        WHERE sourcing_request_id = ?
          AND COALESCE(needs_manual_review, 1) = 0
          AND total_price_per_ton IS NOT NULL
        ORDER BY total_price_per_ton ASC
    """, (request_id,)).fetchall()

    all_options: list[dict] = []

    for row in boss_options:
        all_options.append({
            "option_code": row["option_code"],
            "supplier_name": row["supplier_name"],
            "unit_cost": row["unit_cost"],
            "total_cost": row["total_cost"],
            "source": row["source"],
        })

    for row in core_quotes:
        all_options.append({
            "option_code": row["option_code"],
            "supplier_name": row["supplier_name"],
            "unit_cost": row["unit_cost"],
            "total_cost": row["total_cost"],
            "source": row["source"],
        })

    all_options.sort(
        key=lambda x: (
            float("inf") if x["unit_cost"] is None else float(x["unit_cost"]),
            x["source"],
            x["option_code"] or "",
        )
    )

    return all_options


def get_option_total_cost(option: dict | None, requested_tons: float | None) -> float | None:
    if option is None:
        return None

    if option.get("total_cost") is not None:
        return float(option["total_cost"])

    if option.get("unit_cost") is not None and requested_tons is not None:
        return float(option["unit_cost"]) * float(requested_tons)

    return None


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        conn.execute("DELETE FROM sourcing_request_shortlist")

        requests = conn.execute("""
            SELECT
                id,
                requested_tons
            FROM sourcing_requests
            ORDER BY id
        """).fetchall()

        inserted = 0

        for req in requests:
            request_id = req["id"]
            requested_tons = req["requested_tons"]

            all_options = fetch_rankable_options(conn, request_id)

            am_spot = next(
                (option for option in all_options if option["option_code"] == "AM_SPOT"),
                None,
            )

            rankable = [
                option
                for option in all_options
                if option["option_code"] != "AM_SPOT"
            ]

            best = rankable[0] if len(rankable) > 0 else None
            second = rankable[1] if len(rankable) > 1 else None
            third = rankable[2] if len(rankable) > 2 else None

            best_total_cost = get_option_total_cost(best, requested_tons)
            second_total_cost = get_option_total_cost(second, requested_tons)
            third_total_cost = get_option_total_cost(third, requested_tons)
            am_spot_total_cost = get_option_total_cost(am_spot, requested_tons)

            am_spot_unit_cost = am_spot["unit_cost"] if am_spot else None

            delta_best_vs_am_spot = None
            savings_total_vs_am_spot = None

            if best and am_spot_unit_cost is not None and best["unit_cost"] is not None:
                delta_best_vs_am_spot = float(best["unit_cost"]) - float(am_spot_unit_cost)

            if best_total_cost is not None and am_spot_total_cost is not None:
                savings_total_vs_am_spot = float(am_spot_total_cost) - float(best_total_cost)

            conn.execute("""
                INSERT INTO sourcing_request_shortlist (
                    sourcing_request_id,
                    best_option_code,
                    best_supplier_name,
                    best_source,
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                best["option_code"] if best else None,
                best["supplier_name"] if best else None,
                best["source"] if best else None,
                best["unit_cost"] if best else None,
                best_total_cost,
                second["option_code"] if second else None,
                second["supplier_name"] if second else None,
                second["unit_cost"] if second else None,
                second_total_cost,
                third["option_code"] if third else None,
                third["supplier_name"] if third else None,
                third["unit_cost"] if third else None,
                third_total_cost,
                am_spot_unit_cost,
                am_spot_total_cost,
                delta_best_vs_am_spot,
                savings_total_vs_am_spot,
                created_at,
            ))

            inserted += 1

        conn.commit()

    print(f"Shortlists generadas: {inserted}")


if __name__ == "__main__":
    main()