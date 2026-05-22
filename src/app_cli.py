"""
app_cli.py
----------
Menú principal del Steel MVP.
Punto de entrada único para todas las operaciones del sistema.

Uso:
    python src/app_cli.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
TRANSFORMERS_DIR = SRC_DIR / "transformers"
PIPELINE_DIR = SRC_DIR / "pipeline"
RAW_PDFS_DIR = BASE_DIR / "data" / "raw" / "pdfs"


# ---------------------------------------------------------------------------
# Función de args para la opción 7 (re-import BOSS)
# ---------------------------------------------------------------------------
def _build_reimport_args() -> list[str]:
    print()
    print("Re-importar BOSS del mes")
    print("-" * 50)
    sheet = input("Nombre de la hoja (ENTER para elegir interactivamente): ").strip()
    args = ["--with-import"]
    if sheet:
        args += ["--sheet", sheet]
    return args

def _build_load_supplier_document_args() -> list[str]:
    print()
    print("Cargar documento de proveedor")
    print("-" * 50)
    file_path = input("Ruta al fichero: ").strip()
    supplier_code = input("Supplier code (ENTER si vacío): ").strip()
    notes = input("Notes (ENTER si vacío): ").strip()

    args = ["--file", file_path]
    if supplier_code:
        args += ["--supplier-code", supplier_code]
    if notes:
        args += ["--notes", notes]
    return args


def _pick_pdf_from_raw_folder(title: str) -> str:
    print()
    print(title)
    print("-" * 50)

    pdf_files = sorted(RAW_PDFS_DIR.glob("*.pdf")) if RAW_PDFS_DIR.exists() else []

    if pdf_files:
        print("PDFs detectados en data/raw/pdfs:")
        for i, pdf_path in enumerate(pdf_files, start=1):
            print(f"  {i}. {pdf_path.name}")
        print("  0. Escribir ruta manual")
    else:
        print("(No se han encontrado PDFs en data/raw/pdfs)")
        print("  0. Escribir ruta manual")

    while True:
        raw = input("Elige PDF por número [0]: ").strip()
        if raw == "":
            raw = "0"

        if raw == "0":
            manual_path = input("Ruta al PDF: ").strip()
            if manual_path:
                return manual_path
            print("Debes indicar una ruta.")
            continue

        try:
            idx = int(raw)
        except ValueError:
            print("Introduce un número válido.")
            continue

        if 1 <= idx <= len(pdf_files):
            rel_path = pdf_files[idx - 1].relative_to(BASE_DIR)
            return str(rel_path)

        print("Número fuera de rango.")


def _build_inspect_supplier_pdf_args() -> list[str]:
    file_path = _pick_pdf_from_raw_folder("Inspeccionar PDF de proveedor")
    pages = input("Número de páginas a inspeccionar [2]: ").strip()

    args = ["--pdf", file_path]
    if pages:
        args += ["--pages", pages]
    return args


def _build_import_pdf_am_like_args() -> list[str]:
    file_path = _pick_pdf_from_raw_folder("Importar PDF AM-like (AM / ILVA / EN_*)")
    supplier_code = input("Supplier code [AM]: ").strip()
    supplier_name = input("Supplier name [ArcelorMittal]: ").strip()

    args = ["--pdf", file_path]
    args += ["--supplier-code", supplier_code or "AM"]
    args += ["--supplier-name", supplier_name or "ArcelorMittal"]
    return args

def _build_galmed_pdf_import_args() -> list[str]:
    print()
    print("Importar PDF Galmed")
    print("-" * 50)

    pdfs_dir = BASE_DIR / "data" / "raw" / "pdfs"
    pdfs = sorted(pdfs_dir.glob("*.pdf"))

    galmed_pdfs = [
        p for p in pdfs
        if "galmed" in p.name.lower()
    ]

    candidates = galmed_pdfs or pdfs

    if not candidates:
        pdf_path = input("Ruta del PDF: ").strip()
    else:
        print("PDFs detectados:")
        for idx, pdf in enumerate(candidates, start=1):
            print(f"  {idx}. {pdf.name}")
        print("  0. Escribir ruta manual")

        raw = input("Elige PDF por número [1]: ").strip() or "1"

        if raw == "0":
            pdf_path = input("Ruta del PDF: ").strip()
        else:
            selected = candidates[int(raw) - 1]
            pdf_path = str(selected.relative_to(BASE_DIR))

    supplier_code = input("Supplier code [GALMED]: ").strip() or "GALMED"
    supplier_name = input("Supplier name [Galmed]: ").strip() or "Galmed"

    return [
        "--pdf", pdf_path,
        "--supplier-code", supplier_code,
        "--supplier-name", supplier_name,
    ]


def _build_luso_pdf_import_args() -> list[str]:
    print()
    print("Importar PDF Luso")
    print("-" * 50)

    pdfs_dir = BASE_DIR / "data" / "raw" / "pdfs"
    pdfs = sorted(pdfs_dir.glob("*.pdf"))

    luso_pdfs = [
        p for p in pdfs
        if p.name.lower().startswith("lista_")
    ]

    candidates = luso_pdfs or pdfs

    if not candidates:
        pdf_path = input("Ruta del PDF: ").strip()
    else:
        print("PDFs detectados:")
        for idx, pdf in enumerate(candidates, start=1):
            print(f"  {idx}. {pdf.name}")
        print("  0. Escribir ruta manual")

        raw = input("Elige PDF por número [1]: ").strip() or "1"

        if raw == "0":
            pdf_path = input("Ruta del PDF: ").strip()
        else:
            selected = candidates[int(raw) - 1]
            pdf_path = str(selected.relative_to(BASE_DIR))

    supplier_code = input("Supplier code [LUSO]: ").strip() or "LUSO"
    supplier_name = input("Supplier name [Lusosider]: ").strip() or "Lusosider"

    return [
        "--pdf", pdf_path,
        "--supplier-code", supplier_code,
        "--supplier-name", supplier_name,
    ]

MENU_OPTIONS = {
    # --- Sourcing requests ---
    "1": {
        "label": "Nueva request desde texto bruto",
        "script": TRANSFORMERS_DIR / "create_request_from_raw_text_with_suggestions.py",
        "group": "sourcing_requests",
    },
    "2": {
        "label": "Nueva request manual guiada",
        "script": TRANSFORMERS_DIR / "create_request_from_input_with_suggestions.py",
        "group": "sourcing_requests",
    },
    "3": {
        "label": "Ver último request intake",
        "script": TRANSFORMERS_DIR / "check_last_request_intake.py",
        "group": "sourcing_requests",
    },
    "4": {
        "label": "Ver última request creada y shortlist",
        "script": TRANSFORMERS_DIR / "check_last_manual_sourcing_request.py",
        "group": "sourcing_requests",
    },

    # --- Reporting base ---
    "5": {
        "label": "Ver resumen global de ahorro",
        "script": TRANSFORMERS_DIR / "build_sourcing_summary_report.py",
        "group": "reporting",
    },
    "6": {
        "label": "Exportar sourcing report a Excel",
        "script": TRANSFORMERS_DIR / "export_sourcing_report_to_excel.py",
        "group": "reporting",
    },

    # --- Sistema ---
    "7": {
        "label": "Re-importar BOSS del mes (pipeline completo)",
        "script": PIPELINE_DIR / "run_pipeline.py",
        "group": "system",
        "args_fn": _build_reimport_args,
    },
    "8": {
        "label": "Ver estado del sistema",
        "script": TRANSFORMERS_DIR / "status_db.py",
        "group": "system",
    },

    # --- Sprint 2: Quotes & Decisions ---
    "9": {
        "label": "Crear quote manual para una request",
        "script": TRANSFORMERS_DIR / "create_quote_from_input.py",
        "group": "quotes_decisions",
    },
    "10": {
        "label": "Comparar quotes de una request",
        "script": TRANSFORMERS_DIR / "compare_quotes_for_request.py",
        "group": "quotes_decisions",
    },
    "11": {
        "label": "Registrar decisión de compra",
        "script": TRANSFORMERS_DIR / "record_decision.py",
        "group": "quotes_decisions",
    },
    "12": {
        "label": "Ver savings report",
        "script": TRANSFORMERS_DIR / "build_savings_report.py",
        "group": "quotes_decisions",
    },
    "13": {
        "label": "Exportar savings report a Excel",
        "script": TRANSFORMERS_DIR / "export_savings_report_to_excel.py",
        "group": "quotes_decisions",
    },

    # --- Sprint 3: Supplier Documents ---
    "14": {
        "label": "Cargar documento de proveedor",
        "script": TRANSFORMERS_DIR / "load_supplier_document.py",
        "group": "supplier_docs",
        "args_fn": _build_load_supplier_document_args,
    },
    "15": {
        "label": "Inspeccionar PDF de proveedor",
        "script": TRANSFORMERS_DIR / "inspect_supplier_pdf.py",
        "group": "supplier_docs",
        "args_fn": _build_inspect_supplier_pdf_args,
    },
    "16": {
        "label": "Importar PDF AM-like (AM / ILVA / EN_*)",
        "script": TRANSFORMERS_DIR / "import_pdf_pricelist_am_like.py",
        "group": "supplier_docs",
        "args_fn": _build_import_pdf_am_like_args,
    },
    "17": {
        "label": "Revisar quotes staging pendientes",
        "script": TRANSFORMERS_DIR / "review_pending_supplier_quotes.py",
        "group": "supplier_docs",
    },
    "18": {
        "label": "Ver estado de staging de proveedor",
        "script": TRANSFORMERS_DIR / "status_supplier_staging.py",
        "group": "supplier_docs",
    },
        "19": {
        "label":   "Importar PDF Galmed",
        "script":  TRANSFORMERS_DIR / "import_pdf_pricelist_galmed.py",
        "group":   "supplier_docs",
        "args_fn": _build_galmed_pdf_import_args,
    },

        "20": {
        "label":   "Importar PDF Luso",
        "script":  TRANSFORMERS_DIR / "import_pdf_pricelist_luso.py",
        "group":   "supplier_docs",
        "args_fn": _build_luso_pdf_import_args,
    },
}

GROUP_LABELS = {
    "sourcing_requests": "SOURCING REQUESTS",
    "reporting": "REPORTING",
    "system": "SISTEMA",
    "quotes_decisions": "QUOTES Y DECISIONES",
    "supplier_docs": "DOCUMENTOS DE PROVEEDOR",
}


# ---------------------------------------------------------------------------
# Renderizado del menú
# ---------------------------------------------------------------------------

def print_menu() -> None:
    print("\n" + "=" * 80)
    print("STEEL MVP — MENU PRINCIPAL")
    print("=" * 80)

    current_group = None
    for key, option in MENU_OPTIONS.items():
        group = option.get("group", "")
        if group != current_group:
            current_group = group
            print(f"\n  -- {GROUP_LABELS.get(group, group)} --")
        print(f"  {key}. {option['label']}")

    print("\n  0. Salir")
    print("-" * 80)


# ---------------------------------------------------------------------------
# Ejecución de scripts
# ---------------------------------------------------------------------------

def run_script(script_path: Path, extra_args: list[str] | None = None) -> None:
    if not script_path.exists():
        print(f"\nERROR: no existe el script:\n{script_path}")
        return

    args = extra_args or []

    print("\n" + "-" * 80)
    print(f"Ejecutando: {script_path.name}")
    if args:
        print(f"Argumentos: {' '.join(args)}")
    print("-" * 80)

    result = subprocess.run(
        [sys.executable, str(script_path)] + args,
        cwd=str(BASE_DIR),
    )

    print("-" * 80)
    print(f"Proceso terminado con código: {result.returncode}")
    print("-" * 80)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    while True:
        print_menu()
        choice = input("Elige una opción: ").strip()

        if choice == "0":
            print("Saliendo.")
            break

        option = MENU_OPTIONS.get(choice)
        if option is None:
            print("Opción no válida.")
            continue

        args_fn = option.get("args_fn")
        extra_args = args_fn() if args_fn else []

        run_script(option["script"], extra_args)


if __name__ == "__main__":
    main()