from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"

with sqlite3.connect(DB_PATH) as conn:
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = ?",
        ("table",)
    )]

    refs = []
    for t in tables:
        for fk in conn.execute(f"PRAGMA foreign_key_list({t})").fetchall():
            if fk[2] == "stg_boss_matrix":
                refs.append((t, fk))

    print(refs if refs else "SIN REFERENCIAS")