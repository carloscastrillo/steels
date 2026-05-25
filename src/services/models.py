from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    """
    Lee una columna de sqlite3.Row, dict o similar sin romper si no existe.
    """
    if row is None:
        return default

    if isinstance(row, dict):
        return row.get(key, default)

    try:
        keys = row.keys()
    except AttributeError:
        keys = []

    if key in keys:
        return row[key]

    try:
        return getattr(row, key)
    except AttributeError:
        return default


def _row_get_any(row: Any, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = _row_get(row, key, None)
        if value is not None:
            return value
    return default


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return 1 if int(value) == 1 else 0
    except (TypeError, ValueError):
        return 1 if bool(value) else 0


@dataclass(frozen=True)
class StagingQuote:
    id: int
    supplier_code: str | None
    extracted_grade: str | None
    coating_raw: str | None
    thickness_mm: float | None
    width_mm: float | None
    price_per_ton: float | None
    review_status: str | None
    needs_manual_review: int
    matched_request_id: int | None
    document: str | None
    raw_snippet: str | None

    @classmethod
    def from_row(cls, row: Any) -> "StagingQuote":
        return cls(
            id=_to_int(_row_get(row, "id")) or 0,
            supplier_code=_row_get(row, "supplier_code"),
            extracted_grade=_row_get(row, "extracted_grade"),
            coating_raw=_row_get(row, "coating_raw"),
            thickness_mm=_to_float(_row_get_any(row, ["thickness_mm", "extracted_thickness_mm"])),
            width_mm=_to_float(_row_get_any(row, ["width_mm", "extracted_width_mm"])),
            price_per_ton=_to_float(_row_get_any(row, ["price_per_ton", "extracted_price_per_ton"])),
            review_status=_row_get(row, "review_status"),
            needs_manual_review=_to_bool_int(_row_get(row, "needs_manual_review")),
            matched_request_id=_to_int(_row_get_any(row, ["matched_request_id", "matched_sourcing_request_id"])),
            document=_row_get_any(row, ["document", "documento", "file_name"]),
            raw_snippet=_row_get_any(row, ["raw_snippet", "raw_text_snippet"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatchCandidate:
    score: float
    breakdown: dict[str, Any]
    request_id: int
    our_ref: str | None
    client_name: str | None
    product: str | None
    grade: str | None
    thickness_mm: float | None
    width_mm: float | None
    tons: float | None
    status: str | None

    @classmethod
    def from_row(cls, row: Any) -> "MatchCandidate":
        return cls(
            score=_to_float(_row_get(row, "score")) or 0.0,
            breakdown=_row_get(row, "breakdown", {}) or {},
            request_id=_to_int(_row_get_any(row, ["request_id", "id"])) or 0,
            our_ref=_row_get(row, "our_ref"),
            client_name=_row_get(row, "client_name"),
            product=_row_get(row, "product"),
            grade=_row_get(row, "grade"),
            thickness_mm=_to_float(_row_get(row, "thickness_mm")),
            width_mm=_to_float(_row_get(row, "width_mm")),
            tons=_to_float(_row_get_any(row, ["tons", "requested_tons"])),
            status=_row_get(row, "status"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShortlistRow:
    request_id: int
    our_ref: str | None
    client_name: str | None
    product: str | None
    grade: str | None
    thickness_mm: float | None
    width_mm: float | None
    requested_tons: float | None
    status: str | None
    best_option_code: str | None
    best_supplier_name: str | None
    best_unit_cost: float | None
    best_source: str | None
    second_option_code: str | None
    second_unit_cost: float | None
    third_option_code: str | None
    am_spot_unit_cost: float | None
    delta_best_vs_am_spot: float | None
    savings_total_vs_am_spot: float | None

    @classmethod
    def from_row(cls, row: Any) -> "ShortlistRow":
        return cls(
            request_id=_to_int(_row_get_any(row, ["request_id", "sourcing_request_id", "id"])) or 0,
            our_ref=_row_get(row, "our_ref"),
            client_name=_row_get(row, "client_name"),
            product=_row_get(row, "product"),
            grade=_row_get(row, "grade"),
            thickness_mm=_to_float(_row_get(row, "thickness_mm")),
            width_mm=_to_float(_row_get(row, "width_mm")),
            requested_tons=_to_float(_row_get(row, "requested_tons")),
            status=_row_get(row, "status"),
            best_option_code=_row_get(row, "best_option_code"),
            best_supplier_name=_row_get(row, "best_supplier_name"),
            best_unit_cost=_to_float(_row_get(row, "best_unit_cost")),
            best_source=_row_get(row, "best_source"),
            second_option_code=_row_get(row, "second_option_code"),
            second_unit_cost=_to_float(_row_get(row, "second_unit_cost")),
            third_option_code=_row_get(row, "third_option_code"),
            am_spot_unit_cost=_to_float(_row_get(row, "am_spot_unit_cost")),
            delta_best_vs_am_spot=_to_float(_row_get(row, "delta_best_vs_am_spot")),
            savings_total_vs_am_spot=_to_float(_row_get(row, "savings_total_vs_am_spot")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoreQuote:
    id: int
    supplier_code: str | None
    supplier_name: str | None
    total_price_per_ton: float | None
    total_estimated_cost: float | None
    quoted_tons: float | None
    needs_manual_review: int
    source_type: str | None

    @classmethod
    def from_row(cls, row: Any) -> "CoreQuote":
        return cls(
            id=_to_int(_row_get(row, "id")) or 0,
            supplier_code=_row_get(row, "supplier_code"),
            supplier_name=_row_get(row, "supplier_name"),
            total_price_per_ton=_to_float(_row_get(row, "total_price_per_ton")),
            total_estimated_cost=_to_float(_row_get(row, "total_estimated_cost")),
            quoted_tons=_to_float(_row_get(row, "quoted_tons")),
            needs_manual_review=_to_bool_int(_row_get(row, "needs_manual_review")),
            source_type=_row_get(row, "source_type"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
