from pathlib import Path
from datetime import datetime
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


PLAUSIBLE_THICKNESS_MIN = 0.1
PLAUSIBLE_THICKNESS_MAX = 30.0
PLAUSIBLE_WIDTH_MIN = 50.0
PLAUSIBLE_WIDTH_MAX = 2500.0


def safe_float(value):
    if value is None:
        return None
    return float(value)


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip().upper()
    return text if text else None


def parse_iso_date(value: str | None) -> bool:
    if value is None:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def compare_input_vs_spec(input_data: dict, chosen_spec: sqlite3.Row):
    mismatches = []

    input_product = normalize_text(input_data.get("product"))
    spec_product = normalize_text(chosen_spec["product"])
    if input_product != spec_product:
        mismatches.append(
            f"PRODUCT_MISMATCH: input={input_data.get('product')} | spec={chosen_spec['product']}"
        )

    input_grade = normalize_text(input_data.get("grade"))
    spec_grade = normalize_text(chosen_spec["grade"])
    if input_grade != spec_grade:
        mismatches.append(
            f"GRADE_MISMATCH: input={input_data.get('grade')} | spec={chosen_spec['grade']}"
        )

    input_thickness = safe_float(input_data.get("thickness_mm"))
    spec_thickness = safe_float(chosen_spec["thickness_mm"])
    if input_thickness is not None and spec_thickness is not None:
        diff = abs(input_thickness - spec_thickness)
        if diff > 0.01:
            mismatches.append(
                f"THICKNESS_DIFF: input={input_thickness} | spec={spec_thickness} | diff={round(diff, 3)}"
            )

    input_width = safe_float(input_data.get("width_mm"))
    spec_width = safe_float(chosen_spec["width_mm"])
    if input_width is not None and spec_width is not None:
        diff = abs(input_width - spec_width)
        if diff > 0.5:
            mismatches.append(
                f"WIDTH_DIFF: input={input_width} | spec={spec_width} | diff={round(diff, 3)}"
            )

    input_cw_min = safe_float(input_data.get("cw_min"))
    spec_cw_min = safe_float(chosen_spec["cw_min"])
    if input_cw_min is not None and spec_cw_min is not None:
        diff = abs(input_cw_min - spec_cw_min)
        if diff > 1:
            mismatches.append(
                f"CW_MIN_DIFF: input={input_cw_min} | spec={spec_cw_min} | diff={round(diff, 3)}"
            )

    input_cw_max = safe_float(input_data.get("cw_max"))
    spec_cw_max = safe_float(chosen_spec["cw_max"])
    if input_cw_max is not None and spec_cw_max is not None:
        diff = abs(input_cw_max - spec_cw_max)
        if diff > 1:
            mismatches.append(
                f"CW_MAX_DIFF: input={input_cw_max} | spec={spec_cw_max} | diff={round(diff, 3)}"
            )

    if not mismatches:
        match_quality = "exact"
    else:
        serious = any(
            m.startswith("PRODUCT_MISMATCH")
            or m.startswith("GRADE_MISMATCH")
            or m.startswith("THICKNESS_DIFF")
            for m in mismatches
        )
        if serious:
            match_quality = "rescued_with_warnings"
        else:
            match_quality = "close"

    return match_quality, mismatches


def assess_input_quality(input_spec: dict):
    warnings = []
    status = "ok"

    thickness = safe_float(input_spec.get("thickness_mm"))
    width = safe_float(input_spec.get("width_mm"))
    cw_min = safe_float(input_spec.get("cw_min"))
    cw_max = safe_float(input_spec.get("cw_max"))
    tons = safe_float(input_spec.get("requested_tons"))
    sheet_date = input_spec.get("sheet_date")

    if thickness is not None:
        if thickness < PLAUSIBLE_THICKNESS_MIN or thickness > PLAUSIBLE_THICKNESS_MAX:
            warnings.append(f"THICKNESS_OUT_OF_RANGE: {thickness} mm")
            status = "suspicious"

    if width is not None:
        if width < PLAUSIBLE_WIDTH_MIN or width > PLAUSIBLE_WIDTH_MAX:
            warnings.append(f"WIDTH_OUT_OF_RANGE: {width} mm")
            status = "suspicious"

    if thickness is not None and width is not None and thickness == width:
        warnings.append(f"THICKNESS_EQUALS_WIDTH: {thickness}")
        status = "suspicious"

    if cw_min is not None and cw_max is not None and cw_min > cw_max:
        warnings.append(f"CW_RANGE_INVERTED: cw_min={cw_min} > cw_max={cw_max}")
        status = "invalid"

    if tons is None or tons <= 0:
        warnings.append(f"REQUESTED_TONS_INVALID: {tons}")
        status = "invalid"

    if not parse_iso_date(sheet_date):
        warnings.append(f"SHEET_DATE_INVALID_FORMAT: {sheet_date} | expected YYYY-MM-DD")
        status = "invalid"

    return status, warnings


def thickness_is_plausible(value: float | None) -> bool:
    if value is None:
        return False
    return PLAUSIBLE_THICKNESS_MIN <= value <= PLAUSIBLE_THICKNESS_MAX


def width_is_plausible(value: float | None) -> bool:
    if value is None:
        return False
    return PLAUSIBLE_WIDTH_MIN <= value <= PLAUSIBLE_WIDTH_MAX


def similarity_score(target: dict, candidate: sqlite3.Row, input_status: str) -> float:
    score = 0.0

    if target["product"] == candidate["product"]:
        score += 45

    if target["grade"] == candidate["grade"]:
        score += 35

    target_width = safe_float(target["width_mm"])
    candidate_width = safe_float(candidate["width_mm"])
    if width_is_plausible(target_width) and width_is_plausible(candidate_width):
        diff = abs(target_width - candidate_width)
        score += max(0, 25 - diff / 8)

    target_thickness = safe_float(target["thickness_mm"])
    candidate_thickness = safe_float(candidate["thickness_mm"])
    if thickness_is_plausible(target_thickness) and thickness_is_plausible(candidate_thickness):
        diff = abs(target_thickness - candidate_thickness)
        score += max(0, 18 - diff * 40)
    elif input_status == "suspicious" and thickness_is_plausible(candidate_thickness):
        score += 6

    target_cw_min = safe_float(target["cw_min"])
    target_cw_max = safe_float(target["cw_max"])
    candidate_cw_min = safe_float(candidate["cw_min"])
    candidate_cw_max = safe_float(candidate["cw_max"])

    if (
        target_cw_min is not None
        and target_cw_max is not None
        and candidate_cw_min is not None
        and candidate_cw_max is not None
    ):
        overlap = min(target_cw_max, candidate_cw_max) - max(target_cw_min, candidate_cw_min)
        if overlap > 0:
            score += 10
        else:
            distance = min(
                abs(target_cw_min - candidate_cw_max),
                abs(target_cw_max - candidate_cw_min),
            )
            score += max(0, 10 - distance / 1000)

    history_count = candidate["sourcing_request_count"] or 0
    score += min(history_count * 2, 10)

    return round(score, 2)


def resolve_client(conn: sqlite3.Connection, client_name: str):
    client = conn.execute("""
        SELECT id, name
        FROM clients
        WHERE name = ?
    """, (client_name,)).fetchone()

    if client:
        return client

    client = conn.execute("""
        SELECT c.id, c.name
        FROM client_aliases a
        JOIN clients c ON c.id = a.client_id
        WHERE a.alias_name = ?
    """, (client_name,)).fetchone()

    return client


def create_sourcing_request(
    conn: sqlite3.Connection,
    client_id: int,
    request_spec_id: int,
    our_ref: str,
    requested_tons: float,
    missing_tons: float | None,
    sheet_date: str | None,
    notes: str | None,
    created_at: str,
) -> int:
    cursor = conn.execute("""
        INSERT INTO sourcing_requests (
            source_row_id,
            client_id,
            request_spec_id,
            our_ref,
            requested_tons,
            missing_tons,
            sheet_date,
            notes,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        -1,
        client_id,
        request_spec_id,
        our_ref,
        requested_tons,
        missing_tons,
        sheet_date,
        notes,
        "manual_seeded",
        created_at,
    ))
    return cursor.lastrowid


def seed_supplier_options_from_history(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    request_spec_id: int,
    requested_tons: float,
    created_at: str,
) -> int:
    historical_options = conn.execute("""
        SELECT
            so.option_code,
            so.supplier_name,
            so.cost_type,
            AVG(so.unit_cost) AS avg_unit_cost,
            COUNT(*) AS sample_count
        FROM supplier_options so
        JOIN sourcing_requests sr
          ON sr.id = so.sourcing_request_id
        WHERE sr.request_spec_id = ?
          AND so.is_comparable = 1
          AND so.is_rankable = 1
          AND so.unit_cost IS NOT NULL
        GROUP BY so.option_code, so.supplier_name, so.cost_type
        ORDER BY avg_unit_cost ASC, so.option_code ASC
    """, (request_spec_id,)).fetchall()

    inserted = 0

    for row in historical_options:
        unit_cost = float(row["avg_unit_cost"])
        total_cost = unit_cost * float(requested_tons)

        notes = (
            f"Seeded from historical spec averages | "
            f"sample_count={row['sample_count']}"
        )

        conn.execute("""
            INSERT INTO supplier_options (
                sourcing_request_id,
                option_code,
                supplier_name,
                cost_type,
                unit_cost,
                total_cost,
                currency,
                notes,
                created_at,
                is_available,
                is_zero_placeholder,
                is_suspicious,
                is_rankable,
                validation_note,
                is_comparable,
                comparability_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sourcing_request_id,
            row["option_code"],
            row["supplier_name"],
            row["cost_type"],
            unit_cost,
            total_cost,
            "EUR",
            notes,
            created_at,
            1,
            0,
            0,
            1,
            "OK",
            1,
            "COMPARABLE",
        ))
        inserted += 1

    return inserted


def build_shortlist_for_request(
    conn: sqlite3.Connection,
    sourcing_request_id: int,
    created_at: str,
) -> None:
    conn.execute("""
        DELETE FROM sourcing_request_shortlist
        WHERE sourcing_request_id = ?
    """, (sourcing_request_id,))

    options = conn.execute("""
        SELECT
            option_code,
            supplier_name,
            unit_cost,
            total_cost
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND is_comparable = 1
          AND is_rankable = 1
          AND capability_allowed = 1
        ORDER BY unit_cost ASC, option_code ASC
    """, (sourcing_request_id,)).fetchall()

    am_spot = conn.execute("""
        SELECT unit_cost, total_cost
        FROM supplier_options
        WHERE sourcing_request_id = ?
          AND option_code = 'AM_SPOT'
          AND is_comparable = 1
          AND is_rankable = 1
          AND capability_allowed = 1
        LIMIT 1
    """, (sourcing_request_id,)).fetchone()

    best = options[0] if len(options) > 0 else None
    second = options[1] if len(options) > 1 else None
    third = options[2] if len(options) > 2 else None

    am_spot_unit_cost = am_spot["unit_cost"] if am_spot else None
    am_spot_total_cost = am_spot["total_cost"] if am_spot else None

    delta_best_vs_am_spot = None
    savings_total_vs_am_spot = None

    if best and am_spot_unit_cost is not None:
        delta_best_vs_am_spot = float(best["unit_cost"]) - float(am_spot_unit_cost)

    if best and am_spot_total_cost is not None and best["total_cost"] is not None:
        savings_total_vs_am_spot = float(am_spot_total_cost) - float(best["total_cost"])

    conn.execute("""
        INSERT INTO sourcing_request_shortlist (
            sourcing_request_id,
            best_option_code,
            best_supplier_name,
            best_unit_cost,
            best_total_cost,
            second_option_code,
            second_supplier_name,
            second_unit_cost,
            second_total_cost,
            third_option_code,
            third_supplier_name,
            third_unit_cost,
            third_total_cost,
            am_spot_unit_cost,
            am_spot_total_cost,
            delta_best_vs_am_spot,
            savings_total_vs_am_spot,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sourcing_request_id,
        best["option_code"] if best else None,
        best["supplier_name"] if best else None,
        best["unit_cost"] if best else None,
        best["total_cost"] if best else None,
        second["option_code"] if second else None,
        second["supplier_name"] if second else None,
        second["unit_cost"] if second else None,
        second["total_cost"] if second else None,
        third["option_code"] if third else None,
        third["supplier_name"] if third else None,
        third["unit_cost"] if third else None,
        third["total_cost"] if third else None,
        am_spot_unit_cost,
        am_spot_total_cost,
        delta_best_vs_am_spot,
        savings_total_vs_am_spot,
        created_at,
    ))


def ask_text(label: str, required: bool = True, default: str | None = None) -> str | None:
    while True:
        prompt = f"{label}"
        if default is not None:
            prompt += f" [{default}]"
        prompt += ": "

        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value:
            return value
        if not required:
            return None
        print("Valor obligatorio.")


def ask_float(label: str, required: bool = True, default: float | None = None) -> float | None:
    while True:
        prompt = f"{label}"
        if default is not None:
            prompt += f" [{default}]"
        prompt += ": "

        value = input(prompt).strip()
        if not value and default is not None:
            return float(default)
        if not value and not required:
            return None

        try:
            return float(value.replace(",", "."))
        except ValueError:
            print("Introduce un número válido.")

def ask_confirmation(prompt: str) -> bool:
    yes_values = {"s", "si", "sí", "y", "yes", "1"}
    no_values = {"n", "no", "0"}

    while True:
        value = input(prompt).strip().lower()

        if value in yes_values:
            return True
        if value in no_values:
            return False

        print("Respuesta no válida. Usa s/n, si/no, y/yes, 1/0.")

def collect_input_spec():
    print("INTRODUCE LA NUEVA NECESIDAD")
    print("-" * 120)

    client_name = ask_text("Client name")
    our_ref = ask_text("Our ref")
    product = ask_text("Product")
    grade = ask_text("Grade")
    thickness_mm = ask_float("Thickness (mm)")
    width_mm = ask_float("Width (mm)")
    cw_min = ask_float("CW min", required=False)
    cw_max = ask_float("CW max", required=False)
    requested_tons = ask_float("Requested tons")
    missing_tons = ask_float("Missing tons", required=False, default=requested_tons)
    sheet_date = ask_text("Sheet date YYYY-MM-DD", required=False, default=datetime.now().strftime("%Y-%m-%d"))
    notes = ask_text("Notes", required=False)

    return {
        "client_name": client_name,
        "our_ref": our_ref,
        "product": product,
        "grade": grade,
        "thickness_mm": thickness_mm,
        "width_mm": width_mm,
        "cw_min": cw_min,
        "cw_max": cw_max,
        "requested_tons": requested_tons,
        "missing_tons": missing_tons,
        "sheet_date": sheet_date,
        "notes": notes,
    }


def find_top_similar_specs(conn: sqlite3.Connection, input_spec: dict, input_status: str, top_n: int = 8):
    specs = conn.execute("""
        SELECT
            rs.id,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            rs.thickness_tolerance_text,
            rs.width_tolerance_text,
            rs.cw_min,
            rs.cw_max,
            rs.spec_key,
            COUNT(sr.id) AS sourcing_request_count
        FROM request_specs rs
        LEFT JOIN sourcing_requests sr
          ON sr.request_spec_id = rs.id
        GROUP BY
            rs.id,
            rs.product,
            rs.grade,
            rs.thickness_mm,
            rs.width_mm,
            rs.thickness_tolerance_text,
            rs.width_tolerance_text,
            rs.cw_min,
            rs.cw_max,
            rs.spec_key
    """).fetchall()

    ranked = []
    for spec in specs:
        score = similarity_score(input_spec, spec, input_status)
        ranked.append((score, spec))

    ranked.sort(
        key=lambda x: (
            x[0],
            x[1]["sourcing_request_count"],
        ),
        reverse=True,
    )
    return ranked[:top_n]


def choose_spec_interactively(top_specs):
    print("\nTOP SPECS SIMILARES")
    print("-" * 120)

    for idx, (score, spec) in enumerate(top_specs, start=1):
        print(
            f"{idx}. spec_id={spec['id']} | score={score} | "
            f"{spec['product']} | {spec['grade']} | "
            f"{spec['thickness_mm']} x {spec['width_mm']} | "
            f"cw=({spec['cw_min']}, {spec['cw_max']}) | "
            f"requests={spec['sourcing_request_count']}"
        )

    while True:
        value = input("\nElige número de spec: ").strip()
        try:
            choice = int(value)
            if 1 <= choice <= len(top_specs):
                return top_specs[choice - 1][1]
        except ValueError:
            pass
        print("Elección no válida.")


def confirm_creation(
    input_data: dict,
    chosen_spec: sqlite3.Row,
    input_warnings: list[str],
    match_quality: str,
    match_warnings: list[str],
) -> bool:
    print("\nCONFIRMACION FINAL")
    print("-" * 120)
    print("INPUT ORIGINAL:")
    print(input_data)

    print("\nINPUT WARNINGS:")
    if input_warnings:
        for warning in input_warnings:
            print(f"- {warning}")
    else:
        print("none")

    print("\nSPEC ELEGIDA:")
    print(
        f"id={chosen_spec['id']} | "
        f"{chosen_spec['product']} | {chosen_spec['grade']} | "
        f"{chosen_spec['thickness_mm']} x {chosen_spec['width_mm']} | "
        f"cw=({chosen_spec['cw_min']}, {chosen_spec['cw_max']})"
    )

    print(f"\nMATCH QUALITY: {match_quality}")

    print("\nMATCH WARNINGS:")
    if match_warnings:
        for warning in match_warnings:
            print(f"- {warning}")
    else:
        print("none")

    if match_quality == "rescued_with_warnings":
        return ask_confirmation("\nConfirmar creación pese a diferencias importantes (s/n, y/n, 1/0): ")
    else:
        return ask_confirmation("\nConfirmar creación (s/n, y/n, 1/0): ")


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    input_data = collect_input_spec()

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