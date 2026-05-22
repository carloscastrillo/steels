# Supplier Format Inventory — Steel MVP

Estado: Sprint 4 / P2-1 — Mayo 2026

## Objetivo

Este documento inventaría los PDFs reales disponibles en `data/raw/pdfs/` y resume su estado técnico para extracción de quotes de proveedor.

El objetivo es que el inventario sea:

- legible por un operador;
- útil para priorizar parsers;
- comparable entre proveedores;
- suficientemente estructurado para revisión técnica.

## Criterios de campos

| Campo | Descripción |
|---|---|
| `provider_code` | Código corto del proveedor o familia documental. |
| `file_name` | Nombre exacto del PDF en `data/raw/pdfs/`. |
| `file_type` | Tipo de fichero. Actualmente `pdf`. |
| `language` | Idioma principal detectado en el documento. |
| `selectable_text` | Indica si el PDF tiene texto seleccionable. |
| `tables_detected` | Número aproximado de tablas detectadas por `pdfplumber`. |
| `document_kind` | Tipo de documento. Actualmente se trabaja con listas de extras. |
| `parseable_mvp` | `yes`, `maybe` o `no`, según viabilidad para el MVP. |
| `parser_script` | Script actual o previsto para extracción. |
| `notes` | Observaciones técnicas útiles para parser/revisión. |

## Reglas de decisión

- `parseable_mvp = yes`: el documento puede entrar en el flujo MVP con parser actual o con parser específico razonable.
- `parseable_mvp = maybe`: el documento tiene texto/tablas, pero requiere limpieza especial o parser más delicado.
- `parseable_mvp = no`: documento no apto para MVP sin OCR o intervención manual fuerte.
- `parser_script = PENDIENTE`: el documento aún no tiene parser implementado, aunque pueda ser técnicamente parseable.

## Inventario

| provider_code | file_name | file_type | language | selectable_text | tables_detected | document_kind | parseable_mvp | parser_script | notes |
|---|---|---|---|---|---|---|---|---|---|
| AM | Auto_alusi_02022016.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | alusi extras; parser validado |
| AM | Auto_coldrolled_02022016.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | cold rolled extras |
| AM | Auto_electrogalvanised_02022016.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | electrogalvanised extras |
| AM | Auto_hotdipgalvanised_02022016 (2).pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | HDG extras |
| AM | Auto_hotrolled_02022016.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | hot rolled extras |
| ILVA | ILVA_coldrolledstripproducts.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| ILVA | ILVA_hotdipgalvanizedstripproducts.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| ILVA | ILVA_hotrolledstripsproducts.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| EN | EN_coldrolled_EUR.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| EN | EN_hotdipgalvanised_EUR.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| EN | EN_hotrolled_EUR.pdf | pdf | en | yes | 6+ | extras | yes | import_pdf_pricelist_am_like.py | am_like compatible |
| TATA | Tata Steel_Price extra list EN - Cold rolled products EURO.pdf | pdf | en | yes | 1 | extras | yes | import_pdf_pricelist_tata.py | parser tata validado |
| TATA | Tata Steel_Price extra list EN - HDG EURO.pdf | pdf | en | yes | 1 | extras | yes | import_pdf_pricelist_tata.py | parser tata |
| TATA | Tata Steel_Price extra list EN - Hot rolled products EURO.pdf | pdf | en | yes | 1 | extras | yes | import_pdf_pricelist_tata.py | parser tata |
| TATA | Tata-Steel-MagiZinc price extras euro EN 0323.pdf | pdf | en | yes | 1 | extras | yes | import_pdf_pricelist_tata.py | variante MagiZinc |
| TATA | Tata-Steel-Ymagine price extras euro EN 0323.pdf | pdf | en | yes | 1 | extras | yes | import_pdf_pricelist_tata.py | variante Ymagine |
| GALMED | Tabla de Extras Galmed Abril 2026 Zn-ZnMg.pdf | pdf | es | yes | 10 | extras | yes | PENDIENTE | 1 pág, 10 tablas; matriz zinc + ancho + calidad DX; parser específico requerido |
| LUSO | Lista_CG2_R15_01out14.pdf | pdf | pt | yes | 3 | extras | maybe | PENDIENTE | chapa galvanizada; texto duplicado en PDF (LL II SS TT); tabla Espessura×Revestimento |
| LUSO | Lista_DK2_R6_01out14.pdf | pdf | pt | yes | 5 | extras | yes | PENDIENTE | chapa decapada; estructura más simple |
| LUSO | Lista_LF2_R6_01out14.pdf | pdf | pt | yes | 4 | extras | maybe | PENDIENTE | chapa laminada frío; texto duplicado |

## Cobertura actual por proveedor

| provider_code | PDFs en repo | Parser status | Script |
|---|---:|---|---|
| AM | 5 | Validado | import_pdf_pricelist_am_like.py |
| ILVA | 3 | Validado mediante AM-like | import_pdf_pricelist_am_like.py |
| EN | 3 | Validado mediante AM-like | import_pdf_pricelist_am_like.py |
| TATA | 5 | Validado | import_pdf_pricelist_tata.py |
| GALMED | 1 | Pendiente de parser específico | — |
| LUSO | 3 | Pendiente de parser específico | — |

## Lectura técnica

### Cobertura validada

Los proveedores o familias documentales actualmente cubiertos por parser son:

- AM / ArcelorMittal;
- ILVA;
- EN_*;
- Tata Steel.

### Cobertura pendiente

Los proveedores pendientes son:

- GALMED: técnicamente parseable, pero requiere parser específico por estructura matricial densa.
- LUSO: técnicamente parseable, pero dos documentos tienen texto duplicado o estructura menos limpia.

### Prioridad recomendada

1. GALMED, porque el PDF es reciente y parseable.
2. LUSO DK2, porque parece el más simple de los tres Luso.
3. LUSO CG2 / LF2, porque tienen duplicación textual y requieren limpieza previa.
