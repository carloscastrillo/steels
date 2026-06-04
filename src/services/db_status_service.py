from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any

from src.utils.db import get_db_path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "db"
BACKUPS_DIR = BASE_DIR / "backups"
EXPORTS_DIR = BASE_DIR / "exports"
DEVTOOLS_DIR = BASE_DIR / "src" / "devtools"
TESTS_DIR = BASE_DIR / "src" / "tests"


IMPORTANT_TABLES = [
    "sourcing_requests",
    "request_specs",
    "supplier_options",
    "sourcing_request_shortlist",
    "stg_supplier_documents",
    "stg_supplier_quotes",
    "sourcing_quotes",
    "sourcing_decisions",
    "clients",
    "materials",
]


def active_db_info() -> dict[str, Any]:
    db_path = get_db_path()
    exists = db_path.exists()

    info: dict[str, Any] = {
        "db_path": str(db_path),
        "exists": exists,
        "size_mb": None,
        "modified_at": None,
    }

    if exists:
        stat = db_path.stat()
        info["size_mb"] = round(stat.st_size / (1024 * 1024), 2)
        info["modified_at"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    return info


def table_counts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    existing_tables = {
        item[0]
        for item in conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """).fetchall()
    }

    table_records: list[dict[str, Any]] = []

    for table_name in IMPORTANT_TABLES:
        if table_name not in existing_tables:
            table_records.append({
                "table_name": table_name,
                "exists": False,
                "count": None,
            })
            continue

        total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        table_records.append({
            "table_name": table_name,
            "exists": True,
            "count": int(total),
        })

    return table_records


def staging_health(conn: sqlite3.Connection) -> dict[str, Any]:
    item = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN COALESCE(review_status, 'pending') = 'pending' THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN review_status = 'approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN review_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN matched_sourcing_request_id IS NOT NULL THEN 1 ELSE 0 END) AS matched,
            SUM(CASE WHEN needs_manual_review = 1 THEN 1 ELSE 0 END) AS manual_review
        FROM stg_supplier_quotes
    """).fetchone()

    return {
        "total": int(item[0] or 0),
        "pending": int(item[1] or 0),
        "approved": int(item[2] or 0),
        "rejected": int(item[3] or 0),
        "matched": int(item[4] or 0),
        "manual_review": int(item[5] or 0),
    }


def shortlist_health(conn: sqlite3.Connection) -> dict[str, Any]:
    item = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN second_option_code IS NOT NULL THEN 1 ELSE 0 END) AS with_second,
            SUM(CASE WHEN best_source = 'QUOTE' THEN 1 ELSE 0 END) AS best_quote,
            SUM(CASE WHEN savings_total_vs_am_spot IS NOT NULL THEN savings_total_vs_am_spot ELSE 0 END) AS savings
        FROM sourcing_request_shortlist
    """).fetchone()

    return {
        "total": int(item[0] or 0),
        "with_second": int(item[1] or 0),
        "best_quote": int(item[2] or 0),
        "savings": float(item[3] or 0),
    }


def request_health(conn: sqlite3.Connection) -> dict[str, Any]:
    item = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'awarded' THEN 1 ELSE 0 END) AS awarded,
            SUM(CASE WHEN COALESCE(status, '') NOT IN ('awarded', 'cancelled') THEN 1 ELSE 0 END) AS open_requests,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
        FROM sourcing_requests
    """).fetchone()

    return {
        "total": int(item[0] or 0),
        "awarded": int(item[1] or 0),
        "open_requests": int(item[2] or 0),
        "cancelled": int(item[3] or 0),
    }


def list_recent_files(directory: Path, pattern: str, limit: int = 10) -> list[dict[str, Any]]:
    if not directory.exists():
        return []

    file_records: list[dict[str, Any]] = []

    for file_path in sorted(
        directory.glob(pattern),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )[:limit]:
        stat = file_path.stat()
        file_records.append({
            "file_name": file_path.name,
            "path": str(file_path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return file_records


def recent_backups(limit: int = 10) -> list[dict[str, Any]]:
    db_backups = list_recent_files(DB_DIR, "*backup*.db", limit=limit)
    app_backups = list_recent_files(BACKUPS_DIR, "*.db", limit=limit)

    combined = [*db_backups, *app_backups]
    combined.sort(key=lambda item: item["modified_at"], reverse=True)

    return combined[:limit]


def recent_exports(limit: int = 10) -> list[dict[str, Any]]:
    return list_recent_files(EXPORTS_DIR, "*.xlsx", limit=limit)


def run_system_check(check_name: str) -> dict[str, Any]:
    scripts = {
        "architecture": DEVTOOLS_DIR / "check_architecture.py",
        "parsers": TESTS_DIR / "test_parsers.py",
        "schema": DEVTOOLS_DIR / "smoke_test_schema.py",
    }

    if check_name not in scripts:
        raise ValueError(f"Check no soportado: {check_name}")

    script_path = scripts[check_name]

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "check_name": check_name,
        "script": str(script_path.relative_to(BASE_DIR)),
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ran_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def db_status_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "active_db": active_db_info(),
        "table_counts": table_counts(conn),
        "staging": staging_health(conn),
        "shortlist": shortlist_health(conn),
        "requests": request_health(conn),
        "recent_backups": recent_backups(),
        "recent_exports": recent_exports(),
    }
