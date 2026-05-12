from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


SUSPICIOUS_LOW_COST_THRESHOLD = 300.0


def classify_option(option_code: str, unit_cost):
    if unit_cost is None:
        return {
            "is_available": 0,
            "is_zero_placeholder": 0,
            "is_suspicious": 0,
            "is_rankable": 0,
            "validation_note": "NULL_COST",
        }

    if unit_cost == 0:
        return {
            "is_available": 0,
            "is_zero_placeholder": 1,
            "is_suspicious": 0,
            "is_rankable": 0,
            "validation_note": "ZERO_PLACEHOLDER",
        }

    if unit_cost < SUSPICIOUS_LOW_COST_THRESHOLD:
        return {
            "is_available": 1,
            "is_zero_placeholder": 0,
            "is_suspicious": 1,
            "is_rankable": 0,
            "validation_note": f"SUSPICIOUS_LOW_COST_LT_{int(SUSPICIOUS_LOW_COST_THRESHOLD)}",
        }

    return {
        "is_available": 1,
        "is_zero_placeholder": 0,
        "is_suspicious": 0,
        "is_rankable": 1,
        "validation_note": "OK",
    }


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT id, option_code, unit_cost
            FROM supplier_options
            ORDER BY id
        """).fetchall()

        updated = 0

        for row in rows:
            result = classify_option(row["option_code"], row["unit_cost"])

            conn.execute("""
                UPDATE supplier_options
                SET
                    is_available = ?,
                    is_zero_placeholder = ?,
                    is_suspicious = ?,
                    is_rankable = ?,
                    validation_note = ?
                WHERE id = ?
            """, (
                result["is_available"],
                result["is_zero_placeholder"],
                result["is_suspicious"],
                result["is_rankable"],
                result["validation_note"],
                row["id"],
            ))
            updated += 1

        conn.commit()

    print(f"Supplier options validadas: {updated}")


if __name__ == "__main__":
    main()