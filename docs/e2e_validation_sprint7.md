# Sprint 7 - E2E validation report

## Objective

Validate the complete Steel MVP operational flow on a copy of the real database, without modifying production directly.

## Database used

| Item | Value |
|---|---|
| Production DB copied from | db/steel_mvp.db |
| E2E validation DB | db/steel_mvp_e2e_sprint7.db |
| Date | 2026-06-04 |

## Validated flow

The following flow was validated from the Streamlit interface:

1. Review a supplier quote in staging.
2. Approve the quote.
3. Mark the quote as valid for calculation by setting needs_manual_review = 0.
4. Run matching quote -> request.
5. Promote the staging quote to core sourcing_quotes.
6. Rebuild shortlist.
7. Verify that the promoted PDF quote appears as best option with best_source = QUOTE.
8. Register a sourcing decision.
9. Verify that the request is marked as awarded.

## E2E data used

### Staging quote

| Field | Value |
|---|---|
| stg_supplier_quote_id | 1129 |
| supplier_code | GALMED |
| extracted_grade | GALMED Z100 \| espesor 0,5-0,54 |
| coating_raw | Z100 |
| extracted_thickness_mm | 0.52 |
| extracted_price_per_ton | 17.0 |
| review_status | approved |
| matched_sourcing_request_id | 67 |
| needs_manual_review | 0 |

### Matched request

| Field | Value |
|---|---|
| request_id | 67 |
| our_ref | 176188 |
| client | VENTILACION Y CONDUCTOS TASEL, S.L. |
| grade | S220GD+Z100 MA C |
| request_thickness_mm | 0.5 |
| status_after_decision | awarded |

### Core quote created

| Field | Value |
|---|---|
| id | 10 |
| sourcing_request_id | 67 |
| supplier_code | GALMED |
| supplier_name | Galmed |
| total_price_per_ton | 17.0 |
| total_estimated_cost | 425.0 |
| quoted_tons | 25.0 |
| needs_manual_review | 0 |
| source_type | pdf |

### Shortlist result

| Field | Value |
|---|---|
| sourcing_request_id | 67 |
| best_option_code | GALMED |
| best_supplier_name | Galmed |
| best_source | QUOTE |
| best_unit_cost | 17.0 |
| second_option_code | GALMED |
| second_unit_cost | 853.0 |
| third_option_code | LEON |
| third_unit_cost | 941.0 |
| am_spot_unit_cost | 937.0 |
| delta_best_vs_am_spot | -920.0 |
| savings_total_vs_am_spot | 23000.0 |

### Decision registered

| Field | Value |
|---|---|
| id | 4 |
| sourcing_request_id | 67 |
| selected_quote_id | 10 |
| decision_reason | best_price |
| decided_by | carlos |
| decided_at | 2026-06-04T19:37:14 |
| created_at | 2026-06-04T19:37:14 |

## Final automatic validation

| Check | Result |
|---|---|
| request_awarded | True |
| decision_exists | True |
| core_quote_clean | True |
| shortlist_best_quote | True |
| Final result | PASS |

## Incidents detected

### A1-E2E-001 - Quotes approved but not usable in shortlist

During the E2E validation, all candidate quotes had needs_manual_review = 1.

This meant that quotes could be approved, matched and promoted to core, but they could not enter shortlist or savings calculations because the shortlist builder excludes quotes that still require manual review.

Resolution:

- Added an explicit action in the Staging Review screen to mark quotes as valid for calculation.
- This action updates needs_manual_review = 0.

### A1-E2E-002 - Duplicate decision attempt

During the decision registration step, the UI allowed trying to register a second decision for a request that was already awarded.

SQLite protected data integrity through the unique constraint on sourcing_decisions.sourcing_request_id, but the UI showed a traceback.

Resolution:

- register_decision was made idempotent.
- The Shortlist screen disables the decision button when the request is already awarded.
- The UI now shows a clear message instead of allowing duplicate submission.

## Result

PASS.

The complete operational flow is now usable from the Streamlit interface on a copy of the real database:

staging -> review -> matching -> core quote -> shortlist -> decision -> awarded request

## Checks executed

| Check | Result |
|---|---|
| python src/devtools/check_architecture.py | PASS |
| python src/tests/test_parsers.py | PASS |
| python src/devtools/smoke_test_schema.py | PASS |
