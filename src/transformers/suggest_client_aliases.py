from pathlib import Path
import sqlite3
import unicodedata
import re
from difflib import SequenceMatcher


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


def normalize_name(text: str) -> str:
    if text is None:
        return ""

    text = text.strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    replacements = {
        "S. A.": "SA",
        "S.A.": "SA",
        "S. L.": "SL",
        "S.L.": "SL",
        "S. L": "SL",
        "S. A": "SA",
        "SOCIEDAD ANONIMA": "SA",
        "SOCIEDAD LIMITADA": "SL",
        "TRANSFORMACS.": "TRANSFORMACIONES",
        "CONSTRUCS": "CONSTRUCCIONES",
        "&": "Y",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        unmatched = conn.execute("""
            SELECT
                client_name,
                COUNT(*) AS total_rows
            FROM stg_boss_request_candidates
            WHERE match_status = 'no_client_match'
            GROUP BY client_name
            ORDER BY total_rows DESC, client_name
        """).fetchall()

        clients = conn.execute("""
            SELECT id, name, sap_code
            FROM clients
            ORDER BY name
        """).fetchall()

    normalized_clients = []
    for row in clients:
        normalized_clients.append({
            "id": row["id"],
            "name": row["name"],
            "sap_code": row["sap_code"],
            "norm": normalize_name(row["name"]),
        })

    print("Sugerencias de alias:\n")

    for row in unmatched:
        alias_name = row["client_name"]
        alias_norm = normalize_name(alias_name)

        scored = []
        for client in normalized_clients:
            score = similarity(alias_norm, client["norm"])
            if alias_norm == client["norm"]:
                score = 1.0
            scored.append((score, client))

        scored.sort(key=lambda x: x[0], reverse=True)
        top3 = scored[:3]

        print(f"ALIAS: {alias_name} | filas: {row['total_rows']}")
        print(f"NORMALIZADO: {alias_norm}")
        for score, client in top3:
            print(
                f"  -> score={score:.3f} | client_id={client['id']} | "
                f"sap_code={client['sap_code']} | name={client['name']}"
            )
        print("-" * 120)


if __name__ == "__main__":
    main()