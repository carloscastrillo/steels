from pathlib import Path
import pdfplumber

BASE_DIR = Path(".").resolve()

pdfs = [
    "data/raw/pdfs/Lista_CG2_R15_01out14.pdf",
    "data/raw/pdfs/Lista_DK2_R6_01out14.pdf",
    "data/raw/pdfs/Lista_LF2_R6_01out14.pdf",
]

for pdf_rel in pdfs:
    pdf_path = BASE_DIR / pdf_rel
    print("=" * 120)
    print(pdf_rel)
    print("=" * 120)

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            print(f"Página {page_idx} | tablas detectadas: {len(tables)}")

            for table_idx, table in enumerate(tables):
                if not table:
                    continue

                n_rows = len(table)
                n_cols = max(len(row) for row in table if row) if table else 0
                print("-" * 120)
                print(f"Tabla {table_idx} | filas={n_rows} | cols={n_cols}")

                for row in table[:8]:
                    print(row)

            print()
