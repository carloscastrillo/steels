# Supplier Format Inventory

## Objetivo
Inventariar los documentos reales de proveedor antes de construir parsers.
Este documento se rellena usando el script `inspect_supplier_pdf.py`.

## Campos
- **provider_code**: código corto del proveedor
- **file_name**: nombre del fichero
- **file_type**: pdf | excel | email | docx
- **language**: en | es | pt | it | de | other
- **selectable_text**: yes | no
- **tables_detected**: número de tablas detectadas
- **document_kind**: pricelist | extras | conditions | mixed | unknown
- **parseable_mvp**: yes | no | maybe
- **notes**: observaciones útiles para el parser

## Inventario

| provider_code | file_name | file_type | language | selectable_text | tables_detected | document_kind | parseable_mvp | notes |


## Reglas
- Si el PDF tiene **texto seleccionable** y **tablas legibles**, entra en el MVP.
- Si el PDF es **escaneado** o sin estructura útil, queda fuera del MVP y se marca como `parseable_mvp = no`.
- Si el documento tiene texto pero estructura dudosa, se marca como `maybe` y se decide después de inspeccionar 2-3 páginas.

Arcelor
provider_code: AM
file_name: Auto_alusi_02022016.pdf
file_type: pdf
language: en
selectable_text: yes
tables_detected: 6+
document_kind: extras
parseable_mvp: yes
notes: price extras list, texto seleccionable, parser piloto validado
Tata
provider_code: TATA
file_name: Tata Steel_Price extra list EN - Cold rolled products EURO.pdf
file_type: pdf
language: en
selectable_text: yes
tables_detected: 1 en pág.1, 0 en pág.2-3
document_kind: extras
parseable_mvp: yes
notes: texto libre parseable, parser piloto validado