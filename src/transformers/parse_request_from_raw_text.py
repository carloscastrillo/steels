from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime


SAMPLE_RAW_TEXT = """
Cliente: HIJOS DE ANGEL BALLESTER S.L.
Referencia: PRUEBA 004
Producto: CRC
Calidad: DC01 AM O
Espesor: 0,8
Ancho: 1250
CW min: 15000
CW max: 20000
Toneladas: 80
Fecha: 2026-04-17
Notas: urgente
""".strip()


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def search_first(patterns: list[str], text: str, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match
    return None


def extract_labeled_text(text: str, labels: list[str]) -> str | None:
    label_group = "|".join(re.escape(label) for label in labels)
    pattern = rf"(?:{label_group})\s*[:=-]\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    value = value.splitlines()[0].strip()
    return value or None

def extract_client_name(raw_text: str) -> str | None:
    labeled = extract_labeled_text(raw_text, ["cliente", "client", "empresa"])
    if labeled:
        return labeled

    patterns = [
        r"\d+(?:[.,]\d+)?\s*[xX]\s*\d+(?:[.,]\d+)?\s+para\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,&\-]+?)(?:,|\s+cw\b|\s+ref\b|$)",
        r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,&\-]+?)\s+necesita\b",
        r"para\s+(?!el\b)([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,&\-]+?)(?:\s+\d+(?:[.,]\d+)?\s*(?:tn|tons|toneladas)|\s+CRC\b|\s+HDG\b|\s+DKP\b|,|$)",
        r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 .,&\-]+?)\s*/",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            candidate = normalize_spaces(match.group(1))
            candidate = candidate.strip(" .,:;/")
            if candidate and not candidate.lower().startswith("el "):
                return candidate

    return None


def extract_our_ref(raw_text: str) -> str | None:
    def clean_ref_candidate(candidate: str) -> str | None:
        candidate = candidate.strip(" .,:;")
        parts = candidate.split()

        if not parts:
            return None

        if len(parts) >= 2 and any(ch.isdigit() for ch in parts[1]):
            return f"{parts[0].strip(' .,:;')}" + " " + f"{parts[1].strip(' .,:;')}"

        return parts[0].strip(" .,:;")

    labeled = extract_labeled_text(raw_text, ["referencia", "ref", "our ref", "id"])
    if labeled:
        return clean_ref_candidate(labeled)

    patterns = [
        r"\bref(?:erencia)?[: ]+([A-Z0-9][A-Z0-9_\-./]*(?:\s+[A-Z0-9][A-Z0-9_\-./]*)?)",
        r"\bid[: ]+([A-Z0-9][A-Z0-9_\-./]*(?:\s+[A-Z0-9][A-Z0-9_\-./]*)?)",
    ]
    match = search_first(patterns, raw_text)
    if match:
        return clean_ref_candidate(match.group(1))

    return None

def extract_product(raw_text: str) -> str | None:
    labeled = extract_labeled_text(raw_text, ["producto", "product"])
    if labeled:
        return labeled.upper()

    patterns = [
        r"\b(CRC|HDG|DKP|ALUMINIZADO|GALVA|GALVANIZADO)\b",
    ]
    match = search_first(patterns, raw_text)
    if match:
        return match.group(1).upper()
    return None


def extract_grade(raw_text: str) -> str | None:
    labeled = extract_labeled_text(raw_text, ["calidad", "grade"])
    if labeled:
        return labeled.upper().strip()

    patterns = [
        r"\b(?:CRC|HDG|DKP|ALUMINIZADO|GALVA|GALVANIZADO)\s+([A-Z0-9+/\- ]{4,}?)(?=\s+en\s+\d|\s+\d+(?:[.,]\d+)?\s*[xX]\s*\d|\s*/\s*\d+(?:[.,]\d+)?\s*(?:tn|tons|toneladas)\b|\s+fecha\b|\s+ref\b|,|$)",
        r"\b(?:CRC|HDG|DKP|ALUMINIZADO|GALVA|GALVANIZADO)\s+([A-Z0-9+/\- ]{4,}?)(?=\s+\d+(?:[.,]\d+)?\s*[xX]\s*\d+(?:[.,]\d+)?)",
    ]

    match = search_first(patterns, raw_text)
    if match:
        candidate = normalize_spaces(match.group(1).upper()).strip(" .,:;/")
        candidate = re.sub(r"\s+EN$", "", candidate).strip()
        return candidate if candidate else None

    return None

def extract_dimensions(raw_text: str) -> tuple[float | None, float | None]:
    labeled_thickness = extract_labeled_text(raw_text, ["espesor", "thickness"])
    labeled_width = extract_labeled_text(raw_text, ["ancho", "width"])

    thickness = parse_number(labeled_thickness)
    width = parse_number(labeled_width)

    if thickness is not None or width is not None:
        return thickness, width

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)",
        r"(\d+(?:[.,]\d+)?)\s*mm\s*[xX]\s*(\d+(?:[.,]\d+)?)",
    ]
    match = search_first(patterns, raw_text)
    if match:
        return parse_number(match.group(1)), parse_number(match.group(2))

    return None, None


def extract_cw_range(raw_text: str) -> tuple[float | None, float | None]:
    labeled_min = extract_labeled_text(raw_text, ["cw min", "coil min", "peso min", "min coil"])
    labeled_max = extract_labeled_text(raw_text, ["cw max", "coil max", "peso max", "max coil"])

    cw_min = parse_number(labeled_min)
    cw_max = parse_number(labeled_max)

    if cw_min is not None or cw_max is not None:
        return cw_min, cw_max

    patterns = [
        r"coil\s+entre\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)",
        r"coil\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)",
        r"cw\s+entre\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)",
        r"cw\s+(\d+(?:[.,]\d+)?)\s*[-/]\s*(\d+(?:[.,]\d+)?)",
        r"entre\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)\s*tn",
    ]
    match = search_first(patterns, raw_text)
    if match:
        left = parse_number(match.group(1))
        right = parse_number(match.group(2))
        if left is not None and right is not None:
            return left * 1000 if left < 1000 else left, right * 1000 if right < 1000 else right

    return None, None


def extract_requested_tons(raw_text: str) -> float | None:
    labeled = extract_labeled_text(raw_text, ["toneladas", "tons", "tn", "requested tons"])
    if labeled:
        return parse_number(labeled)

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:tn|tons|toneladas)\b",
        r"necesita\s+(\d+(?:[.,]\d+)?)\s*(?:tn|tons|toneladas)\b",
    ]
    match = search_first(patterns, raw_text)
    if match:
        return parse_number(match.group(1))
    return None


def extract_sheet_date(raw_text: str) -> str | None:
    labeled = extract_labeled_text(raw_text, ["fecha", "date"])
    if labeled:
        labeled = labeled.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(labeled, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass

    patterns = [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{2}/\d{2}/\d{4})\b",
        r"\b(\d{2}-\d{2}-\d{4})\b",
    ]
    match = search_first(patterns, raw_text)
    if match:
        token = match.group(1)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(token, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def extract_notes(raw_text: str) -> str | None:
    labeled = extract_labeled_text(raw_text, ["notas", "notes", "obs", "observaciones"])
    if labeled:
        return labeled
    return None


def parse_request_from_raw_text(raw_text: str) -> dict:
    text = raw_text.strip()

    thickness, width = extract_dimensions(text)
    cw_min, cw_max = extract_cw_range(text)

    result = {
        "client_name": extract_client_name(text),
        "our_ref": extract_our_ref(text),
        "product": extract_product(text),
        "grade": extract_grade(text),
        "thickness_mm": thickness,
        "width_mm": width,
        "cw_min": cw_min,
        "cw_max": cw_max,
        "requested_tons": extract_requested_tons(text),
        "missing_tons": None,
        "sheet_date": extract_sheet_date(text),
        "notes": extract_notes(text),
    }

    if result["requested_tons"] is not None and result["missing_tons"] is None:
        result["missing_tons"] = result["requested_tons"]

    return result


def build_extraction_summary(data: dict) -> dict:
    filled = [k for k, v in data.items() if v is not None and v != ""]
    missing = [k for k, v in data.items() if v is None or v == ""]
    return {
        "filled_fields": len(filled),
        "missing_fields": missing,
    }


def main():
    raw_text = SAMPLE_RAW_TEXT
    print("RAW TEXT")
    print("-" * 120)
    print(raw_text)

    parsed = parse_request_from_raw_text(raw_text)

    print("\nPARSED FIELDS")
    print("-" * 120)
    for key, value in parsed.items():
        print(f"{key}: {value}")

    summary = build_extraction_summary(parsed)
    print("\nEXTRACTION SUMMARY")
    print("-" * 120)
    print(summary)


if __name__ == "__main__":
    main()