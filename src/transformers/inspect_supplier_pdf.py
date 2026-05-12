from __future__ import annotations

import argparse
from pathlib import Path
import pdfplumber


BASE_DIR = Path(__file__).resolve().parent.parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspecciona un PDF de proveedor.")
    parser.add_argument("--pdf", required=True, help="Ruta al PDF a inspeccionar")
    parser.add_argument("--pages", type=int, default=2, help="Número de páginas a inspeccionar")
    return parser.parse_args()


def safe_preview(text: str | None, n: int = 500) -> str:
    if not text:
        return "(sin texto)"
    return text[:n]


def main() -> None:
    args = parse_args()
    pdf_path = Path(args.pdf)

    if not pdf_path.is_absolute():
        pdf_path = BASE_DIR / pdf_path

    if not pdf_path.exists():
        raise FileNotFoundError(f"No existe el PDF: {pdf_path}")

    print("=" * 120)
    print(f"PDF: {pdf_path}")
    print("=" * 120)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total páginas: {total_pages}")
        print("-" * 120)

        for i, page in enumerate(pdf.pages[:args.pages], start=1):
            print(f"=== Página {i} ===")

            tables = page.extract_tables()
            print(f"Tablas detectadas: {len(tables)}")

            if tables:
                print("Primera tabla (primeras 3 filas):")
                first_table = tables[0]
                for row in first_table[:3]:
                    print(row)
            else:
                print("Primera tabla (primeras 3 filas): (sin tablas detectadas)")

            text = page.extract_text()
            print("Texto libre (primeros 500 chars):")
            print(safe_preview(text, 500))
            print("-" * 120)


if __name__ == "__main__":
    main()