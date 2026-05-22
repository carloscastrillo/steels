from __future__ import annotations

import re
from typing import Any


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\r", "\n").replace("\n", " ").strip().split())


def parse_decimal(value: Any, decimals: int | None = None) -> float | None:
    """
    Convierte texto numérico europeo/inglés a float.

    Ejemplos:
        "0,37" -> 0.37
        "1.250,50" -> 1250.5
        "1,250.50" -> 1250.5
        "-" -> None
    """
    text = clean_text(value)

    if not text or text in {"-", "—", "–", "N/A", "n/a"}:
        return None

    match = re.search(r"-?\d+(?:[.,]\d+)?(?:[.,]\d+)?", text)
    if not match:
        return None

    raw = match.group(0)

    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", ".")

    try:
        number = float(raw)
    except ValueError:
        return None

    if decimals is not None:
        return round(number, decimals)

    return number


def parse_price(value: Any) -> float | None:
    return parse_decimal(value, decimals=2)


def parse_thickness(value: Any) -> float | None:
    return parse_decimal(value, decimals=3)


def parse_width(value: Any) -> float | None:
    return parse_decimal(value, decimals=3)

def parse_range_midpoint(value: Any, decimals: int = 3) -> tuple[float | None, float | None, float | None, str]:
    """
    Extrae rango numérico y devuelve min, max, midpoint, etiqueta original.

    Ejemplos:
        "0,37 - 0,39" -> (0.37, 0.39, 0.38, "0,37 - 0,39")
        "1250"        -> (1250.0, 1250.0, 1250.0, "1250")
        "1.250,50"    -> (1250.5, 1250.5, 1250.5, "1.250,50")
    """
    text = clean_text(value)

    if not text:
        return None, None, None, text

    number_pattern = r"-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?"
    matches = re.findall(number_pattern, text)

    nums: list[float] = []
    for match in matches:
        parsed = parse_decimal(match, decimals=decimals)
        if parsed is not None:
            nums.append(parsed)

    if len(nums) >= 2:
        lo = round(nums[0], decimals)
        hi = round(nums[1], decimals)
        mid = round((lo + hi) / 2, decimals)
        return lo, hi, mid, text

    if len(nums) == 1:
        val = round(nums[0], decimals)
        return val, val, val, text

    return None, None, None, text


def round_optional(value: float | None, decimals: int) -> float | None:
    if value is None:
        return None
    return round(float(value), decimals)
