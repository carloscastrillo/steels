# Arquitectura corregida del proyecto - v2

## 1. Objetivo real del sistema
Construir un sistema híbrido que sustituya progresivamente el Excel operativo actual mediante:
- captura de datos desde fuentes reales
- almacenamiento centralizado
- trazabilidad
- comparación operativa
- soporte a decisión

El sistema NO se construirá inicialmente como una app de escritorio completa.
Primero se construirá el backend de datos y la capa de transformación.

---

## 2. Fuentes reales del sistema

### Fuente A - SAP ZSD017
Naturaleza:
- histórico de ventas
- datos comerciales y de materiales ya vendidos

Uso en el sistema:
- alimentar staging SAP
- derivar clientes
- derivar materiales históricos
- aportar contexto comercial e histórico

No se usará directamente para crear requests de compra en esta fase.

---

### Fuente B - Excel operativo del jefe
Naturaleza:
- archivo híbrido de trabajo
- mezcla de datos exportados, fórmulas y entradas manuales

Uso en el sistema:
- alimentar staging Excel operativo
- detectar necesidades operativas reales
- identificar lógica manual actual
- descubrir qué columnas representan comparación, materiales nuevos y reglas de negocio

No se considerará fuente maestra final.

---

### Fuente C - Documentos de proveedor
Naturaleza:
- PDFs
- Excels
- mails
- listas de precios

Uso en el sistema:
- alimentar documents
- generar quotes en fases posteriores

---

## 3. Capas del sistema

### Capa 1 - Raw
Archivos originales sin modificar.

Ubicación:
- data/raw/sap/
- data/raw/excel/
- data/raw/pdfs/
- data/raw/mails/

Regla:
- nunca se sobreescriben
- se conservan como evidencia de origen

---

### Capa 2 - Staging
Tablas que representan las fuentes tal como llegan, con mínima limpieza técnica.

Tablas previstas:
- stg_sap_zsd017_sales
- stg_boss_matrix

Objetivo:
- conservar datos fuente
- facilitar depuración
- separar extracción de transformación
- permitir rehacer procesos sin perder trazabilidad

---

### Capa 3 - Core
Modelo de negocio limpio del sistema.

Tablas actuales:
- clients
- materials
- requests
- providers
- documents
- quotes
- decisions

Regla:
- estas tablas no se alimentan directamente desde archivos brutos
- se alimentan desde staging mediante reglas controladas

---

### Capa 4 - Interfaces
Herramientas de uso humano.

Inicialmente:
- scripts Python
- Excel de revisión
- Power BI opcional

Más adelante:
- automatización SAP GUI
- OCR
- app propia

---

## 4. Principio central del proyecto

La fuente de verdad del sistema será SQLite.

Esto implica:
- SAP no será la fuente maestra directa
- Excel no será la fuente maestra
- Power BI no será la fuente maestra
- Python será el motor de transformación
- SQLite será el repositorio central del estado limpio del sistema

---

## 5. Flujo general del proyecto

### Flujo corregido
Fuentes brutas
-> staging
-> transformación controlada
-> modelo core
-> revisión / análisis
-> automatización posterior

### Traducción práctica
SAP export / Excel jefe / PDFs
-> Python
-> SQLite staging
-> reglas de transformación
-> SQLite core
-> Excel revisión / Power BI
-> futura app o automatización

---

## 6. Decisiones congeladas

- ZSD017 se tratará como histórico SAP, no como request actual.
- El Excel del jefe se tratará como fuente operativa híbrida, no como base maestra.
- Se introducirán tablas staging antes de construir importadores finales.
- El modelo core actual se mantiene.
- La app de escritorio queda pospuesta hasta que el backend esté estabilizado.
- SAP GUI scripting se considera capacidad futura, no prioridad inmediata.

---

## 7. Consecuencia práctica para el desarrollo

El siguiente trabajo no será:
- importar SAP directamente a requests

El siguiente trabajo será:
- añadir tablas staging al esquema
- cargar ZSD017 a staging
- cargar el Excel operativo a staging
- entender cómo derivar core desde ambas fuentes

---

## 8. Estado del proyecto tras esta corrección

### Backend
- correcto y bien orientado

### Modelo core
- válido, pero todavía no alimentado por la fuente correcta

### Estrategia MVP
- sigue siendo híbrida
- ahora con arquitectura más sólida y más escalable

### Riesgo principal actual
- entender exactamente qué parte del Excel del jefe representa operativa real y qué parte es solo apoyo manual