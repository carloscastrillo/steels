from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


COMPARABLE_CODES = {
    "AM_SPOT",
    "SSAB",
    "ADI",
    "LUSO",
    "GALMED",
    "LEON",
    "TATA",
}


def classify(option_code: str, is_rankable: int):
    if is_rankable != 1:
        return 0, "NOT_RANKABLE"

    if option_code == "BASE_EQUIV":
        return 0, "BENCHMARK_ONLY"

    if option_code == "BAO_DDP_HL":
        return 0, "LOGISTICS_NOT_VALIDATED"

    if option_code == "BAO_CFRFO":
        return 0, "INCOTERM_NOT_COMPARABLE_YET"

    if option_code == "AM_AUTO":
        return 0, "AUTO_PLACEHOLDER_OR_NON_OPERATIVE"

    if option_code in COMPARABLE_CODES:
        return 1, "COMPARABLE"

    return 0, "UNCLASSIFIED"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT id, option_code, is_rankable
            FROM supplier_options
            ORDER BY id
        """).fetchall()

        updated = 0

        for row in rows:
            is_comparable, note = classify(row["option_code"], row["is_rankable"])

            conn.execute("""
                UPDATE supplier_options
                SET is_comparable = ?,
                    comparability_note = ?
                WHERE id = ?
            """, (is_comparable, note, row["id"]))
            updated += 1

        conn.commit()

    print(f"Supplier options clasificadas por comparabilidad: {updated}")


if __name__ == "__main__":
    main()