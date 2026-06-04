# Sprint 7 — Validación E2E

## Objetivo

Validar el flujo completo de Steel MVP sobre una copia de la DB real, sin tocar producción directamente.

## Base de datos usada

- DB producción original: `db/steel_mvp.db`
- DB de prueba E2E: `db/steel_mvp_e2e_sprint7.db`

## Fecha de prueba

Pendiente.

## Flujo a validar

1. Importar PDF de proveedor.
2. Revisar y aprobar quotes en Pantalla 2 — Revisión Staging.
3. Hacer matching y promover al core en Pantalla 3 — Matching.
4. Recalcular shortlist.
5. Verificar quote en Pantalla 4 — Shortlist.
6. Registrar decisión.
7. Verificar request `awarded` y decisión registrada.

## Estado inicial

E2E SPRINT 7 — ESTADO INICIAL
----------------------------------------------------------------------------------------------------
DB: db\steel_mvp_e2e_sprint7.db
sourcing_requests_total: 73
sourcing_requests_awarded: 3
stg_supplier_quotes_total: 517
stg_supplier_quotes_pending: 516
stg_supplier_quotes_approved: 1
stg_supplier_quotes_approved_unmatched: 0
sourcing_quotes_total: 9
sourcing_decisions_total: 3
shortlist_total: 73
shortlist_best_source_quote: 2

Staging por proveedor/estado
----------------------------------------------------------------------------------------------------
('AM', 'pending', 6)
('GALMED', 'approved', 1)
('GALMED', 'pending', 285)
('LUSO', 'pending', 205)
('TATA', 'pending', 20)

## Evidencias por paso
Incidencia A1-E2E-001:
Durante la prueba E2E se detectó que todas las quotes candidatas para matching tenían needs_manual_review=1. Aunque podían aprobarse y promoverse, no podían entrar en shortlist/savings porque el constructor excluye quotes con revisión manual pendiente. Se añadió en la pantalla Revisión Staging una acción explícita para marcar quotes como "validadas para cálculo", que actualiza needs_manual_review=0.
### Paso 1 — Importar PDF

Pendiente.

### Paso 2 — Revisar/aprobar quote en UI

Pendiente.

### Paso 3 — Matching y promoción a core

Pendiente.

### Paso 4 — Recalcular shortlist

Pendiente.

### Paso 5 — Verificar aparición en shortlist

Pendiente.

### Paso 6 — Registrar decisión

Pendiente.

### Paso 7 — Verificación final DB

Pendiente.

## Resultado final

Pendiente.

## Incidencias encontradas

Pendiente.

## Decisión

Pendiente.



---

## Resultado E2E — PASS

### Fecha

2026-06-04

### DB usada

`db/steel_mvp_e2e_sprint7.db`

### Flujo validado

Se validó el flujo completo:

1. Quote staging de GALMED aprobada.
2. Quote validada para cálculo (`needs_manual_review=0`).
3. Matching quote → request ejecutado.
4. Quote promovida al core (`sourcing_quotes`).
5. Shortlist recalculada.
6. Quote PDF aparece como mejor opción con `best_source='QUOTE'`.
7. Decisión registrada.
8. Request marcada como `awarded`.

### Evidencia final

Request validada:

```text
request_id = 67
our_ref = 176188
status = awarded

Quote core validada:

id = 10
sourcing_request_id = 67
supplier_code = GALMED
supplier_name = Galmed
total_price_per_ton = 17.0
total_estimated_cost = 425.0
quoted_tons = 25.0
needs_manual_review = 0
source_type = pdf

Shortlist validada:

sourcing_request_id = 67
best_option_code = GALMED
best_supplier_name = Galmed
best_source = QUOTE
best_unit_cost = 17.0
second_option_code = GALMED
second_unit_cost = 853.0
third_option_code = LEON
third_unit_cost = 941.0
am_spot_unit_cost = 937.0
delta_best_vs_am_spot = -920.0
savings_total_vs_am_spot = 23000.0

Decisión registrada:

id = 4
sourcing_request_id = 67
selected_quote_id = 10
decision_reason = best_price
decided_by = carlos
decided_at = 2026-06-04T19:37:14
Validaciones automáticas
request_awarded: True
decision_exists: True
core_quote_clean: True
shortlist_best_quote: True

RESULTADO E2E: PASS
Incidencia detectada A1-E2E-001

Durante la prueba se detectó que todas las quotes candidatas tenían needs_manual_review=1, por lo que podían aprobarse y promoverse, pero no entraban en shortlist/savings. Se añadió una acción en Revisión Staging para marcar quotes como válidas para cálculo (needs_manual_review=0).

Incidencia detectada A1-E2E-002

Durante el registro de decisión se detectó que la UI permitía intentar registrar una segunda decisión sobre una request ya awarded. SQLite protegió la integridad con un UNIQUE constraint, pero la UI mostró traceback. Se corrige haciendo register_decision idempotente y deshabilitando el botón cuando la request ya está adjudicada.

Resultado

PASS funcional. El flujo completo es operable desde la interfaz sobre copia de DB real.

