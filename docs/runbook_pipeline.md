# Runbook del operador — Steel MVP

**Estado:** Sprint 4 — Mayo 2026  
**Base de datos:** `db/steel_mvp.db`  
**Entrada principal:** `python src/app_cli.py`  
**Schema canónico:** `db/schema.sql`

---

## 1. Qué hace el sistema

Steel MVP convierte el flujo operativo de compra de acero, basado en Excel BOSS, SAP y documentos de proveedor, en un sistema local trazable sobre SQLite.

El sistema permite:

- importar la matriz BOSS mensual;
- transformar datos de staging a core;
- generar `sourcing_requests`;
- construir opciones y shortlists por proveedor;
- registrar quotes manuales;
- extraer quotes desde PDFs de proveedor;
- revisar quotes extraídas antes de usarlas;
- registrar decisiones de compra;
- calcular ahorro frente a AM Spot y frente a alternativas reales;
- generar reportes Excel operativos, ejecutivos y mensuales.

La fuente de verdad operativa es:

```text
db/steel_mvp.db
```

---

## 2. Estructura de carpetas

```text
steel/
├── data/
│   └── raw/
│       ├── excel/       → matriz BOSS, por ejemplo matriz.xlsm
│       ├── pdfs/        → PDFs reales de proveedor
│       └── sap/         → exports SAP ZSD017
├── db/
│   ├── steel_mvp.db     → base SQLite operativa local
│   └── schema.sql       → schema canónico reconstruido desde la DB real
├── docs/
│   ├── architecture_v2.md
│   ├── runbook_pipeline.md
│   └── supplier_format_inventory.md
├── exports/
│   ├── sourcing_report.xlsx
│   ├── savings_report.xlsx
│   └── monthly_report_YYYY-MM.xlsx
└── src/
    ├── app_cli.py
    ├── devtools/
    ├── importers/
    ├── migrations/
    ├── pipeline/
    ├── transformers/
    └── utils/
```

---

## 3. Menú principal del CLI

Ejecutar:

```bash
python src/app_cli.py
```

Menú real extraído de `app_cli.py`:

| Opción | Grupo | Acción | Script |
|---:|---|---|---|
| 1 | Sourcing requests | Nueva request desde texto bruto | `create_request_from_raw_text_with_suggestions.py` |
| 2 | Sourcing requests | Nueva request manual guiada | `create_request_from_input_with_suggestions.py` |
| 3 | Sourcing requests | Ver último request intake | `check_last_request_intake.py` |
| 4 | Sourcing requests | Ver última request creada y shortlist | `check_last_manual_sourcing_request.py` |
| 5 | Reporting | Ver resumen global de ahorro | `build_sourcing_summary_report.py` |
| 6 | Reporting | Exportar sourcing report a Excel | `export_sourcing_report_to_excel.py` |
| 7 | Sistema | Re-importar BOSS del mes, pipeline completo | `run_pipeline.py` |
| 8 | Sistema | Ver estado del sistema | `status_db.py` |
| 9 | Quotes y decisiones | Crear quote manual para una request | `create_quote_from_input.py` |
| 10 | Quotes y decisiones | Comparar quotes de una request | `compare_quotes_for_request.py` |
| 11 | Quotes y decisiones | Registrar decisión de compra | `record_decision.py` |
| 12 | Quotes y decisiones | Ver savings report | `build_savings_report.py` |
| 13 | Quotes y decisiones | Exportar savings report a Excel | `export_savings_report_to_excel.py` |
| 14 | Documentos proveedor | Cargar documento de proveedor | `load_supplier_document.py` |
| 15 | Documentos proveedor | Inspeccionar PDF de proveedor | `inspect_supplier_pdf.py` |
| 16 | Documentos proveedor | Importar PDF AM-like, AM / ILVA / EN_* | `import_pdf_pricelist_am_like.py` |
| 17 | Documentos proveedor | Revisar quotes staging pendientes | `review_pending_supplier_quotes.py` |
| 18 | Documentos proveedor | Ver estado de staging de proveedor | `status_supplier_staging.py` |

Nota: el backup/restore del estado de `sourcing_quotes` y `sourcing_decisions` no aparece como opción independiente en el menú actual. Está integrado en el flujo del pipeline completo cuando se ejecuta el re-import BOSS con opción 7.

---

## 4. Operación mensual normal — pipeline BOSS

### 4.1 Preparar la matriz BOSS

Colocar o actualizar el Excel operativo en la carpeta configurada por el importador, normalmente:

```text
data/raw/excel/matriz.xlsm
```

La hoja mensual debe existir dentro del Excel, por ejemplo:

```text
MARZO 2026
ABRIL 2026
MAYO 2026
```

---

### 4.2 Ejecutar el pipeline completo

Desde CLI:

```bash
python src/app_cli.py
```

Elegir:

```text
7. Re-importar BOSS del mes (pipeline completo)
```

Si se ejecuta por comando directo:

```bash
python src/pipeline/run_pipeline.py --with-import --sheet "MARZO 2026"
```

Este pipeline ejecuta el flujo completo:

```text
import_boss_to_staging.py
  → load_request_specs_from_boss.py
  → load_sourcing_requests_from_boss.py
  → load_supplier_options_from_boss.py
  → calibrate_provider_capabilities.py
  → validate_supplier_options_against_capabilities.py
  → validate_supplier_options.py
  → update_supplier_option_total_costs.py
  → classify_supplier_option_comparability.py
  → build_sourcing_request_shortlist.py
  → export_sourcing_report_to_excel.py
```

---

### 4.3 Backup/restore automático del estado de sourcing

Antes de reconstruir el bloque BOSS, el pipeline comprueba si existen:

- `sourcing_quotes`
- `sourcing_decisions`

Si existen, avisa y crea backup JSON del estado de sourcing. Tras reconstruir BOSS, intenta restaurar quotes y decisiones.

Este mecanismo protege las decisiones manuales y quotes registradas frente a re-imports mensuales.

---

### 4.4 Verificar estado del sistema

Desde CLI:

```text
8. Ver estado del sistema
```

O por comando directo:

```bash
python src/transformers/status_db.py
```

Debe mostrar:

- filas válidas en `stg_boss_matrix`;
- `sourcing_requests` creadas;
- `supplier_options` cargadas;
- shortlist construida;
- costes calculados;
- ausencia de errores en diagnóstico.

---

### 4.5 Abrir informe generado

Archivo principal:

```text
exports/sourcing_report.xlsx
```

Hojas esperadas:

- `executive_summary`
- `shortlist_requests`
- `summary`

---

## 5. Flujo de documentos de proveedor

El flujo documental permite cargar PDFs de proveedor, extraer quotes a staging, revisarlas manualmente y promoverlas al core operativo.

Flujo completo:

```text
PDF proveedor
  → stg_supplier_documents
  → stg_supplier_quotes
  → revisión manual
  → sourcing_quotes
  → comparación
  → decisión
  → savings report
```

---

### 5.1 Cargar documento de proveedor

Desde CLI:

```text
14. Cargar documento de proveedor
```

Comando directo:

```bash
python src/transformers/load_supplier_document.py --file "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --supplier-code AM --notes "PDF proveedor"
```

Esto registra el documento en:

```text
stg_supplier_documents
```

---

### 5.2 Inspeccionar PDF de proveedor

Desde CLI:

```text
15. Inspeccionar PDF de proveedor
```

Comando directo:

```bash
python src/transformers/inspect_supplier_pdf.py --pdf "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --pages 3
```

Uso:

- comprobar si el texto es seleccionable;
- detectar si existen tablas;
- ver los primeros caracteres de texto libre;
- decidir si el PDF puede parsearse sin OCR.

Si el PDF no devuelve texto, queda fuera del MVP actual y requerirá OCR en una fase posterior.

---

### 5.3 Importar PDF AM-like

Desde CLI:

```text
16. Importar PDF AM-like (AM / ILVA / EN_*)
```

Comando directo:

```bash
python src/transformers/import_pdf_pricelist_am_like.py --pdf "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --supplier-code AM --supplier-name "ArcelorMittal"
```

Este parser se usa para formatos similares a:

- ArcelorMittal;
- ILVA;
- documentos EN_*.

Las filas extraídas se insertan en:

```text
stg_supplier_quotes
```

con:

```text
review_status = pending
source_type = pdf
```

---

### 5.4 Parser Tata

El parser Tata existe como script operativo:

```bash
python src/transformers/import_pdf_pricelist_tata.py --pdf "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --supplier-code TATA --supplier-name "Tata Steel"
```

Actualmente no aparece como opción independiente en el CLI real. Si se usa con frecuencia, conviene añadirlo al menú en una iteración posterior.

---

### 5.5 Parser Arcelor específico

También existe:

```bash
python src/transformers/import_pdf_pricelist_arcelor.py --pdf "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --supplier-code AM --supplier-name "ArcelorMittal"
```

El parser general preferente para AM / ILVA / EN_* es:

```text
import_pdf_pricelist_am_like.py
```

---

### 5.6 Revisar quotes staging pendientes

Desde CLI:

```text
17. Revisar quotes staging pendientes
```

Comando directo:

```bash
python src/transformers/review_pending_supplier_quotes.py
```

El operador puede:

- aprobar;
- rechazar;
- saltar;
- asignar a una `sourcing_request`;
- corregir precio, toneladas, proveedor, transporte, recargos y notas.

Al aprobar, la quote se promueve al core:

```text
sourcing_quotes
```

---

### 5.7 Ver estado de staging proveedor

Desde CLI:

```text
18. Ver estado de staging de proveedor
```

Comando directo:

```bash
python src/transformers/status_supplier_staging.py
```

Sirve para revisar:

- documentos cargados;
- quotes extraídas;
- quotes pendientes;
- quotes aprobadas;
- quotes rechazadas.

---

## 6. Ciclo de quotes y decisiones manuales

### 6.1 Crear quote manual

Desde CLI:

```text
9. Crear quote manual para una request
```

Comando directo:

```bash
python src/transformers/create_quote_from_input.py
```

Uso:

- introducir precio base;
- transporte;
- recargos;
- toneladas;
- plazo;
- calidad confirmada;
- notas.

La quote se guarda en:

```text
sourcing_quotes
```

---

### 6.2 Comparar quotes de una request

Desde CLI:

```text
10. Comparar quotes de una request
```

Comando directo:

```bash
python src/transformers/compare_quotes_for_request.py
```

Muestra:

- quotes disponibles para la request;
- precio total por tonelada;
- coste total estimado;
- lead time;
- estado de revisión;
- quote seleccionada si existe decisión.

---

### 6.3 Registrar decisión de compra

Desde CLI:

```text
11. Registrar decisión de compra
```

Comando directo:

```bash
python src/transformers/record_decision.py
```

La decisión se guarda en:

```text
sourcing_decisions
```

Y actualiza el estado de la request a:

```text
awarded
```

---

## 7. Reporting de ahorro

### 7.1 Ver savings report

Desde CLI:

```text
12. Ver savings report
```

Comando directo:

```bash
python src/transformers/build_savings_report.py
```

El reporte muestra:

- quote seleccionada;
- next best real quote;
- benchmark AM Spot;
- ahorro total;
- usuario decisor;
- fecha de decisión.

---

### 7.2 Exportar savings report

Desde CLI:

```text
13. Exportar savings report a Excel
```

Comando directo:

```bash
python src/transformers/export_savings_report_to_excel.py
```

Archivo generado:

```text
exports/savings_report.xlsx
```

---

### 7.3 Generar monthly report completo

Comando directo:

```bash
python src/transformers/generate_monthly_report.py --month 2026-05
```

Archivos generados o regenerados:

```text
exports/sourcing_report.xlsx
exports/savings_report.xlsx
exports/monthly_report_2026-05.xlsx
```

---

### 7.4 Regla de calidad: `needs_manual_review`

El campo `needs_manual_review` en `sourcing_quotes` controla qué quotes entran en el cálculo de "next best real quote".

Regla:

- `needs_manual_review = 0` → la quote entra en el cálculo comparativo.
- `needs_manual_review = 1` → la quote queda excluida del cálculo de alternativas.

Esta regla aplica en:

- `build_savings_report.py`
- `export_savings_report_to_excel.py`
- `generate_monthly_report.py`

Una quote con `needs_manual_review = 1` que ya fue adjudicada como decisión sigue apareciendo como quote seleccionada. La restricción solo aplica al cálculo de alternativas comparativas.

---

## 8. Devtools y mantenimiento

### 8.1 Reconstruir schema canónico

Tras cambios estructurales de DB:

```bash
python src/devtools/rebuild_schema_from_db.py
```

Luego validar:

```bash
python src/devtools/smoke_test_schema.py
```

Resultado esperado:

```text
OK: schema.sql crea las mismas tablas y columnas que la DB real.
```

---

### 8.2 Migraciones relevantes

Migraciones de limpieza importantes:

```text
src/migrations/drop_legacy_quotes_table.py
src/migrations/drop_legacy_sprint1_tables.py
```

La DB actual ya no contiene:

- `quotes`
- `requests`
- `decisions`
- `providers`
- `documents`

---

## 9. Troubleshooting

### 9.1 El pipeline falla en un paso

Acciones:

1. leer el paso exacto que falló;
2. ejecutar individualmente el script indicado;
3. revisar `status_db.py`;
4. comprobar que la hoja BOSS existe;
5. comprobar que la DB no está abierta en otro programa.

Comandos útiles:

```bash
python src/transformers/status_db.py
python src/pipeline/run_pipeline.py --with-import --sheet "MARZO 2026"
```

---

### 9.2 Error de foreign key durante re-import

Causa habitual:

- alguna tabla dependiente no fue borrada antes que su tabla padre.

Solución:

- revisar el orden de cascade delete en `import_boss_to_staging.py`;
- confirmar que se borran primero tablas hijas como `sourcing_request_shortlist`, `supplier_options`, `sourcing_quotes`, `sourcing_decisions` si aplica.

---

### 9.3 El PDF no extrae texto

Síntoma:

```text
Texto libre: sin texto
Tablas detectadas: 0
```

Causa probable:

- PDF escaneado como imagen.

Decisión MVP:

- no hacer OCR en esta fase;
- documentar el proveedor como pendiente de OCR;
- introducir quote manual si es necesaria.

---

### 9.4 Una quote da ahorro absurdo

Revisar:

- `needs_manual_review`;
- precio total por tonelada;
- toneladas cotizadas;
- matching con request;
- si la quote era de prueba.

Comandos:

```bash
python src/transformers/compare_quotes_for_request.py
python src/transformers/build_savings_report.py
```

---

### 9.5 Windows bloquea una DB temporal

Puede ocurrir con:

```text
db/test_schema_tmp.db
```

Solución:

```powershell
Remove-Item db/test_schema_tmp.db -Force
```

Si falla:

- cerrar VS Code;
- cerrar terminales;
- repetir.

---

## 10. Secuencia técnica completa de referencia

### Pipeline BOSS

```text
import_boss_to_staging.py
load_request_specs_from_boss.py
load_sourcing_requests_from_boss.py
load_supplier_options_from_boss.py
calibrate_provider_capabilities.py
validate_supplier_options_against_capabilities.py
validate_supplier_options.py
update_supplier_option_total_costs.py
classify_supplier_option_comparability.py
build_sourcing_request_shortlist.py
export_sourcing_report_to_excel.py
```

### Flujo PDF

```text
load_supplier_document.py
inspect_supplier_pdf.py
import_pdf_pricelist_am_like.py / import_pdf_pricelist_tata.py
review_pending_supplier_quotes.py
compare_quotes_for_request.py
record_decision.py
build_savings_report.py
```

### Reporting

```text
export_sourcing_report_to_excel.py
export_savings_report_to_excel.py
generate_monthly_report.py
```

---

## 11. Ficheros que no deben modificarse manualmente

No modificar directamente:

- `db/steel_mvp.db`
- `db/schema.sql`, salvo regeneración controlada con devtools
- ficheros en `data/raw/`
- ficheros generados en `exports/`
- backups en `exports/backups/`

Modificar mediante scripts:

- importers;
- transformers;
- migrations;
- devtools.

---

## 12. Comandos rápidos

Estado:

```bash
python src/transformers/status_db.py
```

Pipeline mensual:

```bash
python src/pipeline/run_pipeline.py --with-import --sheet "MARZO 2026"
```

Sourcing report:

```bash
python src/transformers/export_sourcing_report_to_excel.py
```

Savings report:

```bash
python src/transformers/export_savings_report_to_excel.py
```

Monthly report:

```bash
python src/transformers/generate_monthly_report.py --month 2026-05
```

CLI:

```bash
python src/app_cli.py
```

---

## 13. Estado final esperado tras Sprint 4

El sistema debe tener:

- 16 tablas activas en `steel_mvp.db`;
- `schema.sql` sincronizado con la DB real;
- tablas legacy eliminadas;
- pipeline BOSS operativo;
- flujo PDF operativo con revisión manual;
- `sourcing_quotes` y `sourcing_decisions` como modelo operativo;
- reporting operativo y mensual funcionando.

Última actualización: Sprint 4 — Mayo 2026.
