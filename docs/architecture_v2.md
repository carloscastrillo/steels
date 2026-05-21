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

## Capa 1 — Raw data

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

## Capa 2 — Staging

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

## Capa 3 — Core

Modelo de negocio limpio. Solo se alimenta desde staging mediante transformers.

### Catálogo

- `clients`  
  Catálogo de clientes normalizados.

- `client_aliases`  
  Aliases de nombres de cliente para mejorar matching desde BOSS.

### Especificaciones técnicas

- `materials`  
  Catálogo de materiales deduplicados mediante `material_key`.

- `request_specs`  
  Combinaciones técnicas únicas de producto, calidad y dimensiones.

### Ciclo mensual de sourcing

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

### Ciclo de cotización y decisión

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

## Capa 4 — Reporting e interfaces

### CLI

El punto de entrada principal es:

```bash
python src/app_cli.py