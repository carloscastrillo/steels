from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXCEL_DIR = BASE_DIR / "data" / "raw" / "excel"

TARGET_SHEETS = [
    "MARZO 2026",
]

HINTS = {
    "our ref.",
    "product",
    "grade",
    "thickness",
    "width",
    "thickness tol +/-",
    "width tol + / -",
    "cw min.",
    "cw max.",
    "tn",
    "tons",
    "falta",
    "cliente",
    "fecha",
}


def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = " ".join(text.split())
    return text


def make_unique_columns(columns: list[str]) -> list[str]:
    seen = {}
    unique = []

    for col in columns:
        base = normalize_text(col)
        if not base:
            base = "unnamed"

        count = seen.get(base, 0)
        if count == 0:
            unique.append(base)
        else:
            unique.append(f"{base}.{count}")

        seen[base] = count + 1

    return unique


def find_excel_file() -> Path:
    allowed_suffixes = {".xlsx", ".xlsm", ".xls"}
    files = sorted(
        [p for p in EXCEL_DIR.iterdir() if p.is_file() and p.suffix.lower() in allowed_suffixes]
    )

    if not files:
        raise FileNotFoundError(f"No se ha encontrado ningún Excel en: {EXCEL_DIR}")

    return files[0]


def score_header_row(df: pd.DataFrame) -> tuple[int | None, int]:
    best_row = None
    best_score = -1
    max_rows = min(len(df), 30)

    for row_idx in range(max_rows):
        row_values = [normalize_text(v) for v in df.iloc[row_idx].tolist()]
        row_values = [v for v in row_values if v]

        if not row_values:
            continue

        score = sum(1 for v in row_values if v in HINTS)

        if score > best_score:
            best_score = score
            best_row = row_idx

    return best_row, best_score


def inspect_excel_file(file_path: Path) -> None:
    print(f"Archivo detectado: {file_path}")
    print("-" * 100)

    excel_file = pd.ExcelFile(file_path, engine="openpyxl")
    print("Hojas encontradas:")
    for sheet in excel_file.sheet_names:
        print(f"  - {sheet}")

    print("\n" + "=" * 100)

    sheet_names = [s for s in excel_file.sheet_names if s in TARGET_SHEETS]

    for sheet_name in sheet_names:
        print(f"\nHOJA: {sheet_name}")
        print("-" * 100)

        preview_df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
            dtype=object,
            engine="openpyxl",
        )

        print(f"Dimensiones crudas: {preview_df.shape[0]} filas x {preview_df.shape[1]} columnas")

        header_row, header_score = score_header_row(preview_df)
        print(f"Fila candidata de cabecera: {header_row}")
        print(f"Score de cabecera: {header_score}")

        if header_row is None:
            print("No se ha podido detectar una cabecera probable.")
            print("\n" + "=" * 100)
            continue

        data_df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=header_row,
            dtype=object,
            engine="openpyxl",
        )

        data_df.columns = make_unique_columns(list(data_df.columns))

        non_empty_columns = []
        for idx, col in enumerate(data_df.columns):
            series = data_df.iloc[:, idx]
            if col and not series.isna().all():
                non_empty_columns.append(col)

        data_df = data_df[non_empty_columns]

        print("\nColumnas no vacías detectadas:")
        for col in data_df.columns:
            print(f"  - {col}")

        print("\nPreview de datos:")
        print(data_df.head(12).to_string(index=False))

        print("\n" + "=" * 100)


if __name__ == "__main__":
    file_path = find_excel_file()
    inspect_excel_file(file_path)