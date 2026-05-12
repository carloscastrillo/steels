from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "steel_mvp.db"


INPUT_SPEC = {
    "product": "CRC",
    "grade": "DC01 AM O",
    "thickness_mm": 0.8,
    "width_mm": 1250.0,
    "cw_min": 15000.0,
    "cw_max": 20000.0,
}


def safe_float(value):
    if value is None:
        return None
    return float(value)


def similarity_score(target: dict, candidate: sqlite3.Row) -> float:
    score = 0.0

    if target["product"] == candidate["product"]:
        score += 40

    if target["grade"] == candidate["grade"]:
        score += 35

    target_thickness = safe_float(target["thickness_mm"])
    candidate_thickness = safe_float(candidate["thickness_mm"])
    if target_thickness is not None and candidate_thickness is not None:
        diff = abs(target_thickness - candidate_thickness)
        score += max(0, 15 - diff * 50)

    target_width = safe_float(target["width_mm"])
    candidate_width = safe_float(candidate["width_mm"])
    if target_width is not None and candidate_width is not None:
        diff = abs(target_width - candidate_width)
        score += max(0, 15 - diff / 10)

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

    return round(score, 2)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

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
            score = similarity_score(INPUT_SPEC, spec)
            ranked.append((score, spec))

        ranked.sort(
            key=lambda x: (
                x[0],
                x[1]["sourcing_request_count"],
            ),
            reverse=True,
        )

        print("INPUT SPEC")
        print("-" * 120)
        print(INPUT_SPEC)
        print("\nTOP 10 SPECS SIMILARES")
        print("-" * 120)

        top_specs = ranked[:10]

        for idx, (score, spec) in enumerate(top_specs, start=1):
            print(
                f"{idx}. spec_id={spec['id']} | "
                f"score={score} | "
                f"{spec['product']} | {spec['grade']} | "
                f"{spec['thickness_mm']} x {spec['width_mm']} | "
                f"cw=({spec['cw_min']}, {spec['cw_max']}) | "
                f"requests={spec['sourcing_request_count']}"
            )

            winners = conn.execute("""
                SELECT
                    srs.best_option_code,
                    srs.best_supplier_name,
                    COUNT(*) AS wins
                FROM sourcing_requests sr
                JOIN sourcing_request_shortlist srs
                  ON srs.sourcing_request_id = sr.id
                WHERE sr.request_spec_id = ?
                  AND srs.best_option_code IS NOT NULL
                GROUP BY srs.best_option_code, srs.best_supplier_name
                ORDER BY wins DESC, srs.best_option_code
                LIMIT 3
            """, (spec["id"],)).fetchall()

            if winners:
                print("   Ganadores históricos:")
                for winner in winners:
                    print(
                        f"   - {winner['best_option_code']} | "
                        f"{winner['best_supplier_name']} | wins={winner['wins']}"
                    )
            else:
                print("   Ganadores históricos: sin datos")

            sample_requests = conn.execute("""
                SELECT
                    sr.id,
                    sr.our_ref,
                    c.name AS client_name,
                    sr.requested_tons,
                    sr.sheet_date
                FROM sourcing_requests sr
                JOIN clients c ON c.id = sr.client_id
                WHERE sr.request_spec_id = ?
                ORDER BY sr.id
                LIMIT 3
            """, (spec["id"],)).fetchall()

            if sample_requests:
                print("   Ejemplos de requests:")
                for req in sample_requests:
                    print(
                        f"   - request_id={req['id']} | "
                        f"our_ref={req['our_ref']} | "
                        f"client={req['client_name']} | "
                        f"tn={req['requested_tons']} | "
                        f"date={req['sheet_date']}"
                    )
            else:
                print("   Ejemplos de requests: sin datos")

            print("-" * 120)


if __name__ == "__main__":
    main()