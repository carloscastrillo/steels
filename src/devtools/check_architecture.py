from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

SRC_DIR = BASE_DIR / "src"
SERVICES_DIR = SRC_DIR / "services"
UI_DIR = SRC_DIR / "ui"
TESTS_DIR = SRC_DIR / "tests"
README_PATH = BASE_DIR / "README.md"


SQL_CALL_PATTERNS = [
    r"\.execute\s*\(",
    r"\.executemany\s*\(",
]

SQL_KEYWORD_PATTERNS = [
    r"\bSELECT\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bALTER\b",
    r"\bDROP\b",
    r"\bCREATE\b",
]

WRITE_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bALTER\b",
    r"\bDROP\b",
    r"\bCREATE\b",
]


def iter_py_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*.py") if p.is_file())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def check_services_do_not_import_streamlit() -> list[str]:
    errors: list[str] = []

    for path in iter_py_files(SERVICES_DIR):
        text = read_text(path)
        if re.search(r"^\s*import\s+streamlit\b|^\s*from\s+streamlit\b", text, flags=re.MULTILINE):
            errors.append(f"{rel(path)} importa streamlit. Los servicios no pueden depender de la UI.")

    return errors


def check_ui_has_no_sql() -> list[str]:
    errors: list[str] = []

    for path in iter_py_files(UI_DIR):
        text = read_text(path)

        for pattern in SQL_CALL_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(
                    f"{rel(path)} contiene acceso DB directo: {pattern}. "
                    "La UI debe llamar a src/services/, no ejecutar SQL."
                )
                break

        for pattern in SQL_KEYWORD_PATTERNS:
            if re.search(pattern, text):
                errors.append(
                    f"{rel(path)} contiene keyword SQL explícita: {pattern}. "
                    "La UI debe llamar a src/services/, no ejecutar SQL."
                )
                break

    return errors
def check_tests_do_not_import_ui() -> list[str]:
    errors: list[str] = []

    for path in iter_py_files(TESTS_DIR):
        text = read_text(path)

        if re.search(r"^\s*import\s+src\.ui\b|^\s*from\s+src\.ui\b", text, flags=re.MULTILINE):
            errors.append(f"{rel(path)} importa src.ui. Los tests de backend no deben depender de la UI.")

        if re.search(r"^\s*import\s+streamlit\b|^\s*from\s+streamlit\b", text, flags=re.MULTILINE):
            errors.append(f"{rel(path)} importa streamlit. Los tests actuales no deben depender de Streamlit.")

    return errors


def has_write_sql(text: str) -> bool:
    if not re.search(r"\.execute\s*\(|\.executemany\s*\(", text):
        return False

    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in WRITE_SQL_PATTERNS)


def check_service_writes_have_commit() -> list[str]:
    errors: list[str] = []

    for path in iter_py_files(SERVICES_DIR):
        text = read_text(path)

        if not has_write_sql(text):
            continue

        if ".commit(" not in text:
            errors.append(
                f"{rel(path)} parece hacer escrituras SQL pero no contiene commit(). "
                "Cada servicio de escritura debe confirmar transacciones explícitamente."
            )

    return errors


def annotation_to_text(annotation: ast.AST | None) -> str:
    if annotation is None:
        return ""

    try:
        return ast.unparse(annotation)
    except Exception:
        return ""


def is_public_function(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False

    if node.name.startswith("_"):
        return False

    return True


def contains_bad_row_return(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """
    Heurística: una función pública de services no debe devolver directamente
    variables llamadas row/rows ni llamadas fetchone/fetchall.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.Return):
            continue

        value = child.value

        if isinstance(value, ast.Name) and value.id in {"row", "rows"}:
            return True

        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            if value.func.attr in {"fetchone", "fetchall"}:
                return True

    return False


def check_service_public_returns_are_not_rows() -> list[str]:
    errors: list[str] = []

    for path in iter_py_files(SERVICES_DIR):
        text = read_text(path)

        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            errors.append(f"{rel(path)} no se puede parsear con ast: {exc}")
            continue

        for node in ast.walk(tree):
            if not is_public_function(node):
                continue

            annotation = annotation_to_text(node.returns)
            bad_row_annotations = {
                "Row",
                "sqlite3.Row",
                "list[Row]",
                "list[sqlite3.Row]",
                "tuple[Row]",
                "tuple[sqlite3.Row]",
            }

            if annotation in bad_row_annotations:
                errors.append(
                    f"{rel(path)}::{node.name} devuelve {annotation}. "
                    "Los servicios deben devolver dataclasses o primitivos, no sqlite3.Row."
                )

            if contains_bad_row_return(node):
                errors.append(
                    f"{rel(path)}::{node.name} parece devolver row/rows/fetch directamente. "
                    "Convierte a dataclasses/primitivos antes de retornar."
                )

    return errors


def check_readme_mentions_architecture_check() -> list[str]:
    if not README_PATH.exists():
        return ["README.md no existe. Hay que documentar cómo ejecutar check_architecture.py."]

    text = read_text(README_PATH)

    if "python src/devtools/check_architecture.py" not in text:
        return [
            "README.md no documenta el comando: python src/devtools/check_architecture.py"
        ]

    return []


def run_check(name: str, fn) -> tuple[bool, list[str]]:
    errors = fn()
    if errors:
        return False, errors
    return True, []


def main() -> None:
    checks = [
        ("services no importan streamlit", check_services_do_not_import_streamlit),
        ("ui no contiene SQL/acceso DB directo", check_ui_has_no_sql),
        ("tests no importan ui/streamlit", check_tests_do_not_import_ui),
        ("servicios de escritura hacen commit", check_service_writes_have_commit),
        ("servicios no devuelven sqlite3.Row", check_service_public_returns_are_not_rows),
        ("README documenta check_architecture", check_readme_mentions_architecture_check),
    ]

    all_ok = True

    print("ARCHITECTURE CHECKS")
    print("-" * 100)

    for name, fn in checks:
        ok, errors = run_check(name, fn)

        if ok:
            print(f"OK   | {name}")
            continue

        all_ok = False
        print(f"FAIL | {name}")
        for error in errors:
            print(f"     - {error}")

    print("-" * 100)

    if all_ok:
        print("Architecture checks passed.")
        sys.exit(0)

    print("Architecture checks FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()
