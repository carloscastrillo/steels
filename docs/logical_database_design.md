# Diseño lógico de base de datos - MVP híbrido

## 1. Principios del diseño

- Todas las tablas tendrán un campo `id` como clave primaria.
- Las relaciones entre tablas se harán con claves foráneas usando esos `id`.
- Los estados y tipos se guardarán como texto en esta fase.
- No se usarán tablas auxiliares de catálogos todavía.
- Se prioriza simplicidad, trazabilidad y facilidad de mantenimiento.

---

## 2. Tablas del MVP

### 2.1 clients

Propósito:
Guardar los clientes finales o empresas asociadas a la necesidad de compra.

Columnas:
- id
- name
- sap_code
- notes
- created_at

Reglas:
- `id` es PK.
- `name` es obligatorio.
- `sap_code` es opcional.
- `name` debe ser único si en la práctica no tenéis duplicados reales.

---

### 2.2 materials

Propósito:
Guardar la especificación técnica del material.

Columnas:
- id
- client_id
- quality
- thickness_mm
- width_mm
- length_mm
- coating
- finish
- technical_notes
- material_key
- is_active
- created_at

Reglas:
- `id` es PK.
- `client_id` referencia a `clients.id`.
- `quality`, `thickness_mm`, `width_mm`, `coating`, `is_active` son obligatorios.
- `length_mm`, `finish`, `technical_notes` son opcionales.
- `material_key` será obligatorio y único.
- `material_key` servirá para evitar duplicados del mismo material.

Definición de `material_key`:
Concatenación normalizada de:
- client_id
- quality
- thickness_mm
- width_mm
- length_mm
- coating
- finish

Ejemplo:
`12|DX53D|1.50|1250|NULL|Z140|NULL`

---

### 2.3 requests

Propósito:
Guardar cada necesidad concreta de compra.

Columnas:
- id
- material_id
- requested_tons
- request_date
- target_delivery_date
- destination
- status
- notes
- created_at

Reglas:
- `id` es PK.
- `material_id` referencia a `materials.id`.
- `requested_tons`, `request_date`, `status` son obligatorios.
- `target_delivery_date`, `destination`, `notes` son opcionales.
- `requested_tons` debe ser mayor que 0.

Valores iniciales permitidos para `status`:
- pending
- quoted
- awarded
- rejected
- cancelled

---

### 2.4 providers

Propósito:
Guardar los proveedores.

Columnas:
- id
- name
- email
- phone
- notes
- is_active
- created_at

Reglas:
- `id` es PK.
- `name` es obligatorio.
- `is_active` es obligatorio.
- `email`, `phone`, `notes` son opcionales.

---

### 2.5 documents

Propósito:
Guardar la trazabilidad de todos los archivos importados o registrados.

Columnas:
- id
- file_name
- file_type
- source_path
- source_system
- import_date
- raw_reference
- notes
- created_at

Reglas:
- `id` es PK.
- `file_name`, `file_type`, `source_path`, `source_system`, `import_date` son obligatorios.
- `raw_reference` y `notes` son opcionales.

Valores permitidos para `file_type`:
- sap_export
- excel
- pdf
- mail
- clickview_export

---

### 2.6 quotes

Propósito:
Guardar las ofertas de proveedores para cada request.

Columnas:
- id
- request_id
- provider_id
- primary_document_id
- quoted_price
- currency
- quoted_tons
- lead_time_days
- transport_type
- transport_cost
- surcharges_text
- quality_confirmed
- total_estimated_cost
- source_type
- needs_manual_review
- notes
- created_at

Reglas:
- `id` es PK.
- `request_id` referencia a `requests.id`.
- `provider_id` referencia a `providers.id`.
- `primary_document_id` referencia a `documents.id` y puede ser NULL.
- `quoted_price`, `currency`, `source_type`, `needs_manual_review` son obligatorios.
- `quoted_tons`, `lead_time_days`, `transport_type`, `transport_cost`, `surcharges_text`, `quality_confirmed`, `total_estimated_cost`, `notes` son opcionales.
- `quoted_price` debe ser mayor o igual que 0.
- `transport_cost` debe ser mayor o igual que 0 si existe.

Valores permitidos para `source_type`:
- manual
- excel
- pdf
- mail
- sap

Nota MVP:
- En esta fase, una quote tendrá como máximo un `primary_document_id`.
- Si más adelante una quote necesita varios documentos relacionados, se añadirá una tabla intermedia.

---

### 2.7 decisions

Propósito:
Guardar la decisión final de adjudicación.

Columnas:
- id
- request_id
- selected_quote_id
- decision_reason
- decided_at
- decided_by
- created_at

Reglas:
- `id` es PK.
- `request_id` referencia a `requests.id`.
- `selected_quote_id` referencia a `quotes.id`.
- `decided_at` es obligatorio.
- `decision_reason` y `decided_by` son opcionales.
- Un request solo podrá tener una decisión final activa.

---

## 3. Restricciones clave del MVP

### materials
- PK: `id`
- FK: `client_id -> clients.id`
- UNIQUE: `material_key`

### requests
- PK: `id`
- FK: `material_id -> materials.id`

### quotes
- PK: `id`
- FK: `request_id -> requests.id`
- FK: `provider_id -> providers.id`
- FK: `primary_document_id -> documents.id`

### decisions
- PK: `id`
- FK: `request_id -> requests.id`
- FK: `selected_quote_id -> quotes.id`
- UNIQUE: `request_id`

---

## 4. Índices recomendados desde el principio

Crear índices sobre:
- `materials.material_key`
- `requests.material_id`
- `requests.status`
- `quotes.request_id`
- `quotes.provider_id`
- `quotes.primary_document_id`
- `documents.file_type`

Motivo:
- Mejorar búsquedas y comparaciones frecuentes.

---

## 5. Decisiones deliberadas de simplificación

- No habrá tabla de recargos todavía.
- No habrá tabla de capacidades de proveedor todavía.
- No habrá tabla de auditoría todavía.
- No habrá tabla de correcciones manuales todavía.
- No habrá tabla de múltiples documentos por quote todavía.
- Los valores tipo `status`, `file_type` y `source_type` se guardarán como texto.

---

## 6. Riesgos conocidos aceptados en el MVP

- `surcharges_text` es texto libre y no estructurado.
- `quality_confirmed` puede venir incompleto o ambiguo.
- `primary_document_id` puede ser insuficiente en fases futuras con mails + adjuntos.
- `material_key` depende de una buena normalización previa de valores.

---

## 7. Diseño congelado por ahora

Tablas aprobadas para el MVP:
- clients
- materials
- requests
- providers
- documents
- quotes
- decisions