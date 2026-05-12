from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3
import json

from parse_request_from_raw_text import (
    parse_request_from_raw_text,
    build_extraction_summary,
)

from create_request_from_input_with_suggestions import (
    assess_input_quality,
    resolve_client,
    find_top_similar_specs,
    choose_spec_interactively,
    compare_input_vs_spec,
    confirm_creation,
    create_sourcing_request,
    seed_supplier_options_from_history,
    build_shortlist_for_request,
)


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


FIELD_ORDER = [
    ("client_name", "Client name", "text"),
    ("our_ref", "Our ref", "text"),
    ("product", "Product", "text"),
    ("grade", "Grade", "text"),
    ("thickness_mm", "Thickness (mm)", "float"),
    ("width_mm", "Width (mm)", "float"),
    ("cw_min", "CW min", "float"),
    ("cw_max", "CW max", "float"),
    ("requested_tons", "Requested tons", "float"),
    ("missing_tons", "Missing tons", "float"),
    ("sheet_date", "Sheet date YYYY-MM-DD", "text"),
    ("notes", "Notes", "text"),
]


def parse_number_input(value: str):
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    text = text.replace(",", ".")
    return float(text)


def collect_raw_text() -> str:
    print("PEGA EL TEXTO BRUTO DE LA PETICION.")
    print("Cuando termines, escribe una línea con solo: END")
    print("-" * 120)

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def edit_parsed_data(parsed: dict) -> dict:
    print("\nREVISION RAPIDA DE CAMPOS")
    print("Pulsa Enter para aceptar el valor detectado.")
    print("-" * 120)

    reviewed = dict(parsed)

    if reviewed.get("sheet_date") is None:
        reviewed["sheet_date"] = datetime.now().strftime("%Y-%m-%d")

    if reviewed.get("missing_tons") is None and reviewed.get("requested_tons") is not None:
        reviewed["missing_tons"] = reviewed["requested_tons"]

    for key, label, field_type in FIELD_ORDER:
        current_value = reviewed.get(key)

        prompt = f"{label}"
        if current_value is not None:
            prompt += f" [{current_value}]"
        prompt += ": "

        raw = input(prompt).strip()

        if raw == "":
            continue

        if field_type == "float":
            reviewed[key] = parse_number_input(raw)
        else:
            reviewed[key] = raw

    if reviewed.get("missing_tons") is None and reviewed.get("requested_tons") is not None:
        reviewed["missing_tons"] = reviewed["requested_tons"]

    return reviewed


def print_parsed_fields(data: dict):
    print("\nPARSED / REVIEWED FIELDS")
    print("-" * 120)
    for key, value in data.items():
        print(f"{key}: {value}")


def create_request_intake(
    conn: sqlite3.Connection,
    input_mode: str,
    raw_input_text: str | None,
    parsed_input_data: dict,
    input_quality_status: str,
    match_quality: str,
    input_warnings: list[str],
    match_warnings: list[str],
    chosen_spec_id: int | None,
    sourcing_request_id: int | None,
    created_at: str,
) -> int:
    payload = {
        "input_warnings": input_warnings,
        "match_warnings": match_warnings,
    }

    cursor = conn.execute("""
        INSERT INTO request_intakes (
            input_mode,
            raw_input_text,
            parsed_input_json,
            input_quality_status,
            match_quality,
            warnings_json,
            chosen_spec_id,
            sourcing_request_id,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        input_mode,
        raw_input_text,
        json.dumps(parsed_input_data, ensure_ascii=False),
        input_quality_status,
        match_quality,
        json.dumps(payload, ensure_ascii=False),
        chosen_spec_id,
        sourcing_request_id,
        created_at,
    ))
    return cursor.lastrowid


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    raw_text = collect_raw_text()
    if not raw_text:
        raise ValueError("No se ha introducido texto.")

    print("\nRAW TEXT")
    print("-" * 120)
    print(raw_text)

    parsed = parse_request_from_raw_text(raw_text)

    print("\nEXTRACTION SUMMARY")
    print("-" * 120)
    print(build_extraction_summary(parsed))

    input_data = edit_parsed_data(parsed)
    print_parsed_fields(input_data)

    input_status, warnings = assess_input_quality(input_data)

    print("\nINPUT QUALITY")
    print("-" * 120)
    print(f"status: {input_status}")
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("No warnings.")

    if input_status == "invalid":
        raise ValueError("La entrada es inválida. Corrígela antes de continuar.")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        client = resolve_client(conn, input_data["client_name"])
        if not client:
            raise ValueError(
                f"No se ha podido resolver client_name='{input_data['client_name']}' "
                f"ni por clients.name ni por client_aliases"
            )

        top_specs = find_top_similar_specs(conn, input_data, input_status=input_status, top_n=8)
        if not top_specs:
            raise ValueError("No se encontraron request_specs candidatas.")

        chosen_spec = choose_spec_interactively(top_specs)

        match_quality, match_warnings = compare_input_vs_spec(input_data, chosen_spec)

        if not confirm_creation(
            input_data=input_data,
            chosen_spec=chosen_spec,
            input_warnings=warnings,
            match_quality=match_quality,
            match_warnings=match_warnings,
        ):
            print("Creación cancelada por el usuario.")
            return

        sourcing_request_id = create_sourcing_request(
            conn=conn,
            client_id=client["id"],
            request_spec_id=chosen_spec["id"],
            our_ref=input_data["our_ref"],
            requested_tons=float(input_data["requested_tons"]),
            missing_tons=float(input_data["missing_tons"]) if input_data["missing_tons"] is not None else None,
            sheet_date=input_data["sheet_date"],
            notes=input_data["notes"],
            created_at=created_at,
        )

        inserted_options = seed_supplier_options_from_history(
            conn=conn,
            sourcing_request_id=sourcing_request_id,
            request_spec_id=chosen_spec["id"],
            requested_tons=float(input_data["requested_tons"]),
            created_at=created_at,
        )

        build_shortlist_for_request(
            conn=conn,
            sourcing_request_id=sourcing_request_id,
            created_at=created_at,
        )

        request_intake_id = create_request_intake(
            conn=conn,
            input_mode="raw_text",
            raw_input_text=raw_text,
            parsed_input_data=input_data,
            input_quality_status=input_status,
            match_quality=match_quality,
            input_warnings=warnings,
            match_warnings=match_warnings,
            chosen_spec_id=chosen_spec["id"],
            sourcing_request_id=sourcing_request_id,
            created_at=created_at,
        )

        shortlist = conn.execute("""
            SELECT
                best_option_code,
                best_supplier_name,
                best_unit_cost,
                best_total_cost,
                second_option_code,
                second_unit_cost,
                third_option_code,
                third_unit_cost,
                am_spot_unit_cost,
                delta_best_vs_am_spot,
                savings_total_vs_am_spot
            FROM sourcing_request_shortlist
            WHERE sourcing_request_id = ?
        """, (sourcing_request_id,)).fetchone()

        conn.commit()

    print("\nREQUEST CREADA CORRECTAMENTE")
    print("-" * 120)
    print(f"request_intake_id: {request_intake_id}")
    print(f"sourcing_request_id: {sourcing_request_id}")
    print(f"client_resolved: {client['name']}")
    print(
        f"spec_used: id={chosen_spec['id']} | "
        f"{chosen_spec['product']} | {chosen_spec['grade']} | "
        f"{chosen_spec['thickness_mm']} x {chosen_spec['width_mm']} | "
        f"cw=({chosen_spec['cw_min']}, {chosen_spec['cw_max']})"
    )
    print(f"supplier_options_seeded: {inserted_options}")

    print("\nSHORTLIST")
    print("-" * 120)
    if shortlist:
        print(dict(shortlist))
    else:
        print("Sin shortlist generada.")


if __name__ == "__main__":
    main()