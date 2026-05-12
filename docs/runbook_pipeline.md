# Runbook del operador — Steel MVP

Fecha: Mayo 2026  
Estado: Sprint 1 completado

---

## 1. Qué hace el sistema

Steel MVP toma el Excel operativo del jefe (BOSS) y el export de SAP (ZSD017),
los procesa, y genera un sourcing report en Excel con:

- Las requests del mes ordenadas por cliente y material
- Las opciones de cada proveedor por request
- El proveedor más barato (shortlist) y el ahorro vs AM Spot
- Un resumen global de ahorro

La fuente de verdad es SQLite (`db/steel_mvp.db`).

---

## 2. Estructura de carpetas

```
steel/
├── data/
│   └── raw/
│       ├── excel/   → aquí va la matriz.xlsm del jefe
│       └── sap/     → aquí van los exports ZSD017 (.xlsx)
├── db/
│   └── steel_mvp.db   → la base de datos SQLite
├── exports/
│   └── sourcing_report.xlsx   → el informe generado
└── src/
    ├── app_cli.py             → punto de entrada (menú)
    ├── pipeline/
    │   └── run_pipeline.py    → pipeline completo
    ├── importers/
    │   └── import_boss_to_staging.py
    └── transformers/
        ├── status_db.py       → estado del sistema
        └── ... (resto de transformers)
```

---

## 3. Operación mensual normal

### Paso 1 — Actualizar el Excel del jefe

Copiar la nueva versión de la matriz BOSS en:
```
data/raw/excel/matriz.xlsm
```

El archivo debe mantener el mismo nombre. La hoja del mes nuevo debe seguir
el formato `MES YYYY`, por ejemplo `ABRIL 2026`.

---

### Paso 2 — Procesar el mes nuevo (opción recomendada)

Desde el menú principal:

```bash
python src/app_cli.py
```

Elegir opción **7 — Re-importar BOSS del mes (pipeline completo)**.

Cuando pregunte el nombre de la hoja, escribir exactamente:
```
ABRIL 2026
```

El pipeline hace automáticamente, en orden:
1. Borra datos del mes anterior (cascade)
2. Importa el BOSS nuevo a staging
3. Carga specs, requests, opciones de proveedor
4. Valida opciones contra capabilities
5. Calcula costes totales
6. Clasifica opciones comparables
7. Construye la shortlist
8. Exporta el Excel

Si todo va bien, verás al final `Pipeline completado sin errores.`

---

### Paso 3 — Verificar el estado

Opción **8 — Ver estado del sistema** del menú, o directamente:

```bash
python src/transformers/status_db.py
```

Debe mostrar todos los checks en OK y los conteos razonables.

---

### Paso 4 — Abrir el Excel generado

El informe se genera en:
```
exports/sourcing_report.xlsx
```

Abrirlo con Excel. Contiene:
- Una hoja con el resumen global
- Una hoja con todas las requests y su shortlist
- Una hoja con el detalle de todas las supplier_options

---

## 4. Si algo falla

### El pipeline se detiene en un paso

El pipeline muestra el paso exacto que falló y el código de error.
Los pasos más comunes que fallan:

| Paso | Problema habitual | Solución |
|------|------------------|----------|
| import_boss_to_staging | Nombre de hoja incorrecto | Abrir el Excel y copiar exactamente el nombre de la pestaña |
| import_boss_to_staging | 0 filas válidas | Verificar que HEADER_ROW=9 sigue siendo correcto |
| load_sourcing_requests | 0 requests creadas | Hay clients del BOSS que no están en la tabla clients |
| build_shortlist | 0 entradas | No hay opciones comparables; revisar classify_supplier_option_comparability |

---

### Ver qué clientes del BOSS no están en clients

```bash
python src/transformers/check_unmatched_boss_clients.py
```

Si hay clientes no reconocidos, añadir sus aliases:
```bash
python src/transformers/suggest_client_aliases.py
python src/transformers/load_client_aliases_manual.py
```

---

### Ejecutar sólo parte del pipeline

Si el import ya está hecho y sólo quieres re-procesar las transformaciones:

```bash
python src/pipeline/run_pipeline.py
```

(Sin `--with-import`, el pipeline empieza desde load_request_specs.)

---

### Re-importar sólo el BOSS sin procesar

```bash
python src/importers/import_boss_to_staging.py --sheet "ABRIL 2026"
```

---

## 5. Calibrar rangos de capabilities de proveedor

Cuando hay un mes nuevo con precios de proveedores que antes no aparecían:

```bash
python src/transformers/calibrate_provider_capabilities.py
```

Esto actualiza automáticamente los rangos min/max de espesor y ancho
para cada proveedor, basándose en lo que aparece en el BOSS.

Para resetear completamente y cargar desde cero:
```bash
python src/transformers/calibrate_provider_capabilities.py --reset
```

---

## 6. Primera vez (setup inicial)

Si la base de datos no existe todavía:

```bash
python src/init_db.py
```

Si es la primera vez que se cargan datos de SAP:
```bash
python src/importers/import_zsd017_to_staging.py
python src/transformers/load_clients_from_zsd017.py
python src/transformers/load_materials_from_zsd017.py
python src/transformers/load_client_aliases_manual.py
```

Después, seguir con los pasos de la operación mensual normal.

---

## 7. Secuencia completa de transformers (referencia técnica)

```
import_boss_to_staging.py
  → load_request_specs_from_boss.py
  → load_sourcing_requests_from_boss.py
  → load_supplier_options_from_boss.py
  → load_provider_capabilities_seed.py  [o calibrate_provider_capabilities.py]
  → validate_supplier_options_against_capabilities.py
  → validate_supplier_options.py
  → update_supplier_option_total_costs.py
  → classify_supplier_option_comparability.py
  → build_sourcing_request_shortlist.py
  → export_sourcing_report_to_excel.py
```

Todo esto se ejecuta automáticamente con `run_pipeline.py --with-import`.

---

## 8. Ficheros que NO debes modificar manualmente

- `db/steel_mvp.db` — nunca abrir con Excel ni herramientas externas
- `db/schema.sql` — sólo modificar si se añade una migración
- Cualquier fichero en `data/raw/` — son los originales, nunca se sobreescriben

---

*Última actualización: Sprint 1 — Mayo 2026*

---

# Flujo de documentos de proveedor (Sprint 3 / Sprint 4)

## Objetivo
Permitir cargar documentos reales de proveedor (principalmente PDFs), extraer quotes a staging, revisarlas manualmente y promoverlas al core `sourcing_quotes` antes de entrar en el flujo de comparación, decisión y reporting.

## Flujo operativo completo

### 1. Inspeccionar un PDF de proveedor
Permite ver si el documento tiene texto seleccionable, si se detectan tablas y qué estructura tiene.

```bash
python src/transformers/inspect_supplier_pdf.py --pdf "data/raw/pdfs/NOMBRE_DEL_PDF.pdf" --pages 3

---

## Regla de calidad para reporting de ahorro

A partir del Sprint 4, el cálculo de **next best quote** en:
- `build_savings_report.py`
- `export_savings_report_to_excel.py`
- `generate_monthly_report.py`

solo considera alternativas de `sourcing_quotes` con:

- `needs_manual_review = 0`

Las quotes con:
- `needs_manual_review = 1`

quedan excluidas del cálculo de “next best real quote”, para evitar que quotes dudosas, de prueba o aprobadas con warning distorsionen los KPIs de ahorro.

Esto no impide que una quote adjudicada con `needs_manual_review = 1` siga figurando como quote seleccionada si ya fue aceptada manualmente; la restricción solo aplica al cálculo comparativo de alternativas.