from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import sys
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "exports"
TRANSFORMERS_DIR = BASE_DIR / "src" / "transformers"


def _run_python_script(script_path: Path, args: list[str] | None = None) -> dict[str, Any]:
    if args is None:
        args = []

    if not script_path.exists():
        raise FileNotFoundError(f"No existe el script: {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "script": str(script_path.relative_to(BASE_DIR)),
        "args": args,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
        "ran_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def generate_sourcing_report() -> dict[str, Any]:
    return _run_python_script(
        TRANSFORMERS_DIR / "export_sourcing_report_to_excel.py"
    )


def generate_savings_report() -> dict[str, Any]:
    return _run_python_script(
        TRANSFORMERS_DIR / "export_savings_report_to_excel.py"
    )


def generate_monthly_report(month: str) -> dict[str, Any]:
    if not month or len(month.strip()) != 7:
        raise ValueError("month debe tener formato YYYY-MM, por ejemplo 2026-05.")

    return _run_python_script(
        TRANSFORMERS_DIR / "generate_monthly_report.py",
        ["--month", month.strip()],
    )


def list_export_files() -> list[dict[str, Any]]:
    if not EXPORTS_DIR.exists():
        return []

    rows: list[dict[str, Any]] = []

    for path in sorted(EXPORTS_DIR.glob("*.xlsx"), key=lambda item: item.stat().st_mtime, reverse=True):
        stat = path.stat()
        rows.append({
            "file_name": path.name,
            "path": str(path),
            "size_kb": round(stat.st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return rows
