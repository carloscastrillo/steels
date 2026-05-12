 # Entidades y relaciones
## 1. Entidades del sistema

### Client
Descripción:
Empresa o cliente final al que pertenece la necesidad de compra.

Campos:
- id
- name
- sap_code (opcional)
- notes (opcional)

---

### Material
Descripción:
Especificación técnica del producto.

Campos:
- id
- client_id
- quality
- thickness_mm
- width_mm
- length_mm (opcional)
- coating
- finish (opcional)
- technical_notes (opcional)
- is_active

---

### Request
Descripción:
Necesidad concreta de compra de un material.

Campos:
- id
- material_id
- requested_tons
- request_date
- target_delivery_date (opcional)
- destination (opcional)
- status
- notes (opcional)

---

### Provider
Descripción:
Proveedor que puede ofertar material.

Campos:
- id
- name
- email (opcional)
- phone (opcional)
- notes (opcional)
- is_active

---

### Quote
Descripción:
Oferta concreta de un proveedor para un request.

Campos:
- id
- request_id
- provider_id
- quoted_price
- currency
- quoted_tons (opcional)
- lead_time_days (opcional)
- transport_type (opcional)
- transport_cost (opcional)
- surcharges_text (opcional)
- quality_confirmed (opcional)
- total_estimated_cost (opcional)
- source_type
- needs_manual_review
- notes (opcional)

---

### Document
Descripción:
Archivo o fuente de donde sale información.

Campos:
- id
- file_name
- file_type
- source_path
- import_date
- source_system
- raw_reference (opcional)
- notes (opcional)

---

### Decision
Descripción:
Selección final de una quote para un request.

Campos:
- id
- request_id
- selected_quote_id
- decision_reason (opcional)
- decided_at
- decided_by (opcional)

---

## 2. Relaciones

### Client -> Material
Relación:
- Un client puede tener muchos materials.
- Un material pertenece a un solo client.

Tipo:
- 1 a N

---

### Material -> Request
Relación:
- Un material puede aparecer en muchos requests.
- Un request pertenece a un solo material.

Tipo:
- 1 a N

---

### Request -> Quote
Relación:
- Un request puede tener muchas quotes.
- Una quote pertenece a un solo request.

Tipo:
- 1 a N

---

### Provider -> Quote
Relación:
- Un provider puede tener muchas quotes.
- Una quote pertenece a un solo provider.

Tipo:
- 1 a N

---

### Document -> Quote
Relación:
- Un document puede generar cero, una o varias quotes.
- Una quote puede venir de un document o de carga manual.

Tipo:
- 1 a N (permitiendo quote sin document)

---

### Request -> Decision
Relación:
- Un request puede tener cero o una decisión final activa.
- Una decisión pertenece a un solo request.

Tipo:
- 1 a 0..1

---

### Quote -> Decision
Relación:
- Una decision selecciona una sola quote.
- Una quote puede no ser seleccionada nunca.

Tipo:
- 1 a 0..1

---

## 3. Reglas de obligatoriedad

### Material
Obligatorios:
- client_id
- quality
- thickness_mm
- width_mm
- coating
- is_active

Opcionales:
- length_mm
- finish
- technical_notes

---

### Request
Obligatorios:
- material_id
- requested_tons
- request_date
- status

Opcionales:
- target_delivery_date
- destination
- notes

---

### Quote
Obligatorios:
- request_id
- provider_id
- quoted_price
- currency
- source_type
- needs_manual_review

Opcionales:
- quoted_tons
- lead_time_days
- transport_type
- transport_cost
- surcharges_text
- quality_confirmed
- total_estimated_cost
- notes

---

### Document
Obligatorios:
- file_name
- file_type
- source_path
- import_date
- source_system

Opcionales:
- raw_reference
- notes

---

## 4. Estados iniciales del sistema

### Request.status
Valores permitidos:
- pending
- quoted
- awarded
- rejected
- cancelled

### Document.file_type
Valores permitidos:
- sap_export
- excel
- pdf
- mail
- clickview_export

### Quote.source_type
Valores permitidos:
- manual
- excel
- pdf
- mail
- sap


## 5. Decisiones congeladas por ahora
- Las toneladas pertenecen a Request, no a Material.
- Excel no será la fuente maestra.
- SQLite será la base local del sistema.
- Una quote puede existir aunque todavía no tenga todos los campos completos.
- Un document puede existir aunque todavía no se haya extraído nada útil de él.