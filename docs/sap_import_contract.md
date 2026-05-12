# Contrato de importación SAP export - MVP

## 1. Objetivo
Importar desde un Excel de origen los datos mínimos necesarios para crear:
- materials
- requests

En esta fase NO se importarán quotes ni precios de proveedor.

---

## 2. Columnas de origen esperadas

Columnas esperadas en el archivo de entrada:
- Our Ref.
- Product
- Grade
- Thickness
- Width
- Thickness Tol +/-
- Width Tol + / -
- CW Min.
- CW Max.
- TN

Columnas que pueden existir pero NO se usarán aún:
- columnas de proveedor (AM, LUSO, TATA, SSAB, etc.)
- columnas de coste
- columnas de estado comercial
- columnas auxiliares de revisión

---

## 3. Mapeo origen -> sistema

### Para Material

#### client
Origen:
- pendiente de definir con certeza

Regla provisional:
- si no viene un cliente claro en el export, se dejará como cliente genérico temporal o se resolverá después

#### quality
Origen:
- Grade

#### thickness_mm
Origen:
- Thickness

#### width_mm
Origen:
- Width

#### length_mm
Origen:
- no disponible inicialmente

Valor:
- NULL

#### coating
Origen:
- Product o combinación Product + Grade

Regla provisional:
- se derivará del campo Product hasta definir una tabla de equivalencias más precisa

#### finish
Origen:
- no disponible inicialmente

Valor:
- NULL

---

### Para Request

#### requested_tons
Origen:
- TN

#### request_date
Origen:
- fecha de importación

#### target_delivery_date
Origen:
- no disponible inicialmente

Valor:
- NULL

#### destination
Origen:
- no disponible inicialmente

Valor:
- NULL

#### status
Valor inicial:
- pending

#### notes
Origen:
- Our Ref. + tolerancias + observaciones mínimas si hacen falta

---

## 4. Campos obligatorios para aceptar una fila

Una fila solo se importará si tiene como mínimo:
- Grade
- Thickness
- Width
- TN

Si falta uno de esos campos:
- la fila no se insertará
- la fila quedará marcada para revisión

---

## 5. Normalizaciones necesarias

### thickness_mm
- convertir comas a puntos si hace falta
- convertir a número decimal

### width_mm
- convertir a número decimal o entero usable

### requested_tons
- convertir a número decimal
- debe ser > 0

### quality
- quitar espacios sobrantes
- convertir valores vacíos en NULL

### product / coating
- normalizar mayúsculas y espacios
- preparar para futura tabla de equivalencias

---

## 6. Reglas de negocio provisionales

- Las toneladas pertenecen a request, no a material.
- Si una fila genera un material ya existente, se reutiliza ese material.
- Si una fila no puede generar un material válido, no se importa.
- En esta fase no se crean quotes desde este fichero.
- En esta fase no se usarán columnas de proveedor/precio.

---

## 7. Resultado esperado de una fila válida

Cada fila válida debe producir:
- 1 material nuevo o reutilizado
- 1 request nuevo

---

## 8. Dudas abiertas

- Cómo identificar exactamente el cliente desde el export.
- Cómo derivar coating de forma robusta desde Product.
- Qué hoja concreta del archivo será la hoja oficial de importación.
- Qué filas son cabecera real y qué filas son ruido visual.