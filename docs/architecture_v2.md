# Architecture v2 — HIERROS Steel MVP

## 1. Objetivo del sistema

El objetivo del sistema es convertir un flujo operativo basado en Excel, SAP y documentos de proveedor en una base de datos local estructurada, trazable y útil para apoyar decisiones de compra de acero.

El MVP no pretende sustituir SAP ni automatizar completamente la decisión comercial. Su función es:

- importar datos operativos del Excel BOSS;
- normalizar clientes, materiales y necesidades de compra;
- calcular opciones comparables por proveedor;
- construir shortlists de sourcing;
- registrar quotes manuales o extraídas desde documentos;
- revisar manualmente las quotes dudosas;
- registrar decisiones de compra;
- generar reporting operativo y ejecutivo.

La arquitectura sigue una regla central:

> ningún dato bruto entra directamente al core sin pasar por staging y por un transformer controlado.

---

## 2. Fuentes reales del sistema

### Fuente A — SAP ZSD017

Naturaleza:

- Export de SAP con histórico de ventas.
- Fuente estructurada.
- Formato Excel exportado desde SAP.
- Sirve como base histórica de clientes, materiales y ventas.

Uso en el sistema:

- Carga inicial en `stg_sap_zsd017_sales`.
- Normalización posterior hacia tablas core.
- Alimenta el catálogo de clientes y materiales.

Estado actual:

- Fuente integrada en staging.
- Tabla disponible en el schema canónico.
- No es el flujo principal del Sprint 4, pero sigue siendo fuente estructural del sistema.

---

### Fuente B — Excel operativo BOSS

Naturaleza:

- Excel mensual usado por el jefe.
- Archivo principal de trabajo operativo.
- Contiene requests, necesidades de compra, opciones de proveedor y costes comparativos.

Uso en el sistema:

- Importación a `stg_boss_matrix`.
- Generación de `request_specs`.
- Generación de `sourcing_requests`.
- Generación de `supplier_options`.
- Calibración de `provider_capabilities`.
- Construcción de `sourcing_request_shortlist`.
- Exportación a `sourcing_report.xlsx`.

Estado actual:

- Fuente principal del pipeline mensual.
- Pipeline BOSS → staging → core → reporting validado de punta a punta.

---

### Fuente C — Documentos de proveedor

Naturaleza:

- PDFs de listas de precios de extras, formato principal actual.
- Excels de proveedor, soporte futuro.
- Emails de proveedor, soporte futuro.

Uso en el sistema:

- Registrar el documento en `stg_supplier_documents`.
- Extraer quotes en bruto a `stg_supplier_quotes` mediante parsers Python.
- Revisar manualmente las quotes desde el CLI.
- Aprobar, rechazar o asignar manualmente una quote a una `sourcing_request`.
- Promover quotes aprobadas a `sourcing_quotes`.

Cobertura actual de parsers:

- AM-like: ArcelorMittal / ILVA / EN_*.
- Tata Steel.
- Galmed pendiente de parser específico.
- Luso / Lusosider pendiente de parser específico.

Estado actual:

- Fuente operativa parcial.
- El flujo documental funciona con staging + revisión manual.
- El matching automático completo queda fuera del MVP actual.

---

## 3. Capas del sistema

### Capa 1 — Raw data

Contiene los ficheros tal como llegan antes de cualquier transformación.

Ejemplos:

- `data/raw/excel/matriz.xlsm`
- `data/raw/pdfs/*.pdf`
- exports SAP
- futuros textos de email o documentos adjuntos

Regla:

- Los ficheros raw no se modifican.
- Si un dato se transforma, se guarda en staging o core.
- Los raw sirven como referencia y trazabilidad.

---

### Capa 2 — Staging

Tablas que representan las fuentes tal como llegan, con mínima limpieza técnica.

Tablas actuales:

- `stg_sap_zsd017_sales` → fuente SAP ZSD017.
- `stg_boss_matrix` → Excel operativo BOSS.
- `stg_boss_request_candidates` → candidatos de requests desde BOSS antes de promoción.
- `stg_supplier_documents` → registro de documentos de proveedor.
- `stg_supplier_quotes` → quotes extraídas desde PDFs, pendientes de revisión.

Regla de staging:

- Nunca se escribe directamente desde archivos brutos al core.
- Staging actúa como zona de cuarentena.
- La promoción al core siempre pasa por un transformer controlado.
- `stg_supplier_quotes.review_status` marca el estado de revisión:
  - `pending`
  - `approved`
  - `rejected`
- Las quotes extraídas automáticamente deben entrar como revisables antes de usarse en decisiones.

---

### Capa 3 — Core

Modelo de negocio limpio. Solo se alimenta desde staging mediante transformers.

#### Catálogo

- `clients`  
  Catálogo de clientes normalizados.

- `client_aliases`  
  Aliases de nombres de cliente para mejorar matching desde BOSS.

#### Especificaciones técnicas

- `materials`  
  Catálogo de materiales deduplicados mediante `material_key`.

- `request_specs`  
  Combinaciones técnicas únicas de producto, calidad y dimensiones.

#### Ciclo mensual de sourcing

- `sourcing_requests`  
  Necesidades de compra del mes. Sustituye al modelo legacy `requests`.

- `request_intakes`  
  Trazabilidad de cómo se creó cada request manual o automática.

- `provider_capabilities`  
  Rangos de capacidad por proveedor, producto, espesor y ancho.

- `supplier_options`  
  Opciones de proveedor por request, generadas desde BOSS.

- `sourcing_request_shortlist`  
  Top opciones por request, con delta frente a benchmark AM Spot.

#### Ciclo de cotización y decisión

- `sourcing_quotes`  
  Quotes validadas, ya sean manuales o promovidas desde staging documental.

- `sourcing_decisions`  
  Decisiones de compra adjudicadas.

Reglas del core:

- Ninguna tabla core se escribe directamente desde importers.
- Toda escritura al core pasa por un transformer con validación explícita.
- Las quotes con `needs_manual_review = 1` deben tratarse como dudosas.
- El cálculo de ahorro y next-best quote debe evitar contaminar resultados con quotes no revisadas o claramente anómalas.

---

### Capa 4 — Reporting e interfaces

#### CLI

El punto de entrada principal es:

```bash
python src/app_cli.py
```

El CLI agrupa operaciones de:

- creación de requests;
- reimport BOSS;
- creación de quotes manuales;
- comparación de quotes;
- registro de decisiones;
- importación de PDFs;
- revisión de quotes staging;
- reporting.

#### Excels generados

Archivos principales:

- `exports/sourcing_report.xlsx`
- `exports/savings_report.xlsx`
- `exports/monthly_report_YYYY-MM.xlsx`

#### Reportes

El sistema puede generar:

- shortlist mensual;
- resumen global de ahorro;
- savings report;
- monthly report.

---

## 4. Pipeline mensual BOSS

Flujo principal:

```text
matriz.xlsm
    ↓
stg_boss_matrix
    ↓
request_specs
    ↓
sourcing_requests
    ↓
supplier_options
    ↓
provider_capabilities
    ↓
sourcing_request_shortlist
    ↓
sourcing_report.xlsx
```

Comando principal:

```bash
python src/pipeline/run_pipeline.py --with-import --sheet "MARZO 2026"
```

Características actuales:

- Protege `sourcing_quotes` y `sourcing_decisions` antes de reimportar.
- Hace backup del estado de sourcing.
- Reconstruye el bloque BOSS.
- Restaura quotes y decisiones cuando puede.
- Exporta reporting operativo.

---

## 5. Pipeline documental de proveedor

Flujo actual:

```text
PDF proveedor
    ↓
stg_supplier_documents
    ↓
stg_supplier_quotes
    ↓
review_pending_supplier_quotes.py
    ↓
sourcing_quotes
    ↓
compare_quotes_for_request.py
    ↓
record_decision.py
    ↓
build_savings_report.py
```

Reglas:

- Todo PDF se registra primero como documento.
- Las filas extraídas entran en staging.
- Las quotes extraídas no se usan automáticamente.
- El operador debe aprobar, corregir o rechazar.
- La asignación a `sourcing_request` sigue siendo manual en el MVP.

Parsers actuales:

- `import_pdf_pricelist_am_like.py`
- `import_pdf_pricelist_tata.py`
- `import_pdf_pricelist_arcelor.py`

Estado de cobertura:

- AM / ILVA / EN_*: operativo mediante parser AM-like.
- Tata Steel: operativo.
- Galmed: pendiente.
- Luso: pendiente.

---

## 6. Decisiones de compra y ahorro

El ciclo de decisión usa:

- `sourcing_quotes`
- `sourcing_decisions`
- `sourcing_request_shortlist`

Flujo:

```text
sourcing_request
    ↓
quotes disponibles
    ↓
comparativa
    ↓
selección de quote ganadora
    ↓
sourcing_decisions
    ↓
savings_report
```

Métricas calculadas:

- spend seleccionado;
- ahorro frente a next-best real quote;
- ahorro frente a benchmark AM Spot;
- ahorro medio por decisión;
- trazabilidad de proveedor ganador;
- trazabilidad de usuario que decide.

Regla de calidad:

- Las quotes con `needs_manual_review = 1` quedan excluidas del cálculo de `next-best real quote`.
- Una quote adjudicada con `needs_manual_review = 1` puede seguir apareciendo como seleccionada si fue aceptada manualmente.
- La exclusión aplica solo al cálculo comparativo de alternativas.

---

## 7. Tablas legacy

El modelo antiguo tenía estas tablas:

- `requests`
- `decisions`
- `providers`
- `documents`
- `quotes`

Estado actual:

- `quotes`: eliminada mediante `drop_legacy_quotes_table.py`.
- `requests`: eliminada mediante `drop_legacy_sprint1_tables.py`.
- `decisions`: eliminada mediante `drop_legacy_sprint1_tables.py`.
- `providers`: eliminada mediante `drop_legacy_sprint1_tables.py`.
- `documents`: eliminada mediante `drop_legacy_sprint1_tables.py`.

Sustituciones operativas:

- `requests` → `sourcing_requests`
- `decisions` → `sourcing_decisions`
- `quotes` → `sourcing_quotes`
- `documents` → `stg_supplier_documents`
- `providers` → funcionalidad cubierta por `supplier_options` y `provider_capabilities`

Regla:

> Las tablas legacy no deben aparecer como tablas operativas en documentación, scripts nuevos ni reporting.

---

## 8. Estado del proyecto

### Backend

Operativo. El pipeline mensual BOSS → staging → core → Excel está validado de punta a punta.

### Modelo core

Operativo sobre:

- `sourcing_requests`
- `sourcing_quotes`
- `sourcing_decisions`
- `supplier_options`
- `sourcing_request_shortlist`

Las tablas legacy ya fueron eliminadas de la DB operativa mediante migraciones formales.

### Pipeline documental

Operativo en modo staging + revisión manual.

Parsers validados:

- AM-like / ArcelorMittal / ILVA / EN_*
- Tata Steel

Pendientes:

- Galmed
- Luso / Lusosider

### Reporting

Operativo:

- `sourcing_report.xlsx`
- `savings_report.xlsx`
- `monthly_report_YYYY-MM.xlsx`

### Saneamiento técnico

P0 completado:

- `.gitignore` añadido.
- `.venv` fuera del tracking.
- scripts sueltos eliminados de raíz.
- `schema.sql` reconstruido desde la DB real.
- smoke test de schema validado.

### Limpieza legacy

P1-2 completado a nivel de DB:

- `drop_legacy_quotes_table.py`
- `drop_legacy_sprint1_tables.py`

El schema canónico debe reflejar solo las tablas reales actualmente existentes en `steel_mvp.db`.

### Riesgos actuales

- Cobertura incompleta de parsers de proveedor.
- Documentación restante pendiente de alinear:
  - `runbook_pipeline.md`
  - `supplier_format_inventory.md`
  - documentación lógica/antigua que aún mencione `quotes`, `requests` o `decisions` como modelo operativo.
