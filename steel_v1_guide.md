# Steel MVP — Guía de uso de la aplicación

**Versión:** Streamlit Operator App v0.1  
**Sprint:** Sprint 6 — Interfaz operativa local  
**Fecha:** 26/05/2026  
**Uso previsto:** aplicación local para el jefe de compras / usuario operativo de sourcing.

---

## 1. Qué es esta aplicación

Steel MVP es una aplicación local para gestionar el flujo de compras de acero a partir de tres fuentes principales:

1. **BOSS / matriz mensual**: Excel operativo con necesidades de compra, proveedores posibles y costes comparativos.
2. **PDFs de proveedor**: listas de extras y precios extraídas automáticamente.
3. **Base de datos interna**: donde se consolidan requests, quotes, shortlist y decisiones.

La aplicación permite revisar datos extraídos, asignarlos a necesidades reales de compra, comparar alternativas y registrar decisiones sin tener que usar comandos técnicos.

---

## 2. Cómo se arranca

La aplicación se abre con doble clic sobre:

```text
run_app.bat
```

Al arrancar:

1. Se activa automáticamente el entorno Python del proyecto.
2. Se lanza la aplicación Streamlit.
3. Se abre en el navegador en:

```text
http://localhost:8501
```

4. Se crea automáticamente un backup de la base de datos en:

```text
backups/
```

---

## 3. Avisos importantes de uso

Esta aplicación está pensada para **uso local y monousuario**.

Mientras la app esté abierta, no se recomienda ejecutar a la vez:

- pipelines pesados;
- migraciones de base de datos;
- reconstrucciones de `schema.sql`;
- importaciones masivas.

Modo recomendado:

1. Cerrar la app.
2. Ejecutar importaciones o procesos pesados.
3. Volver a abrir la app con `run_app.bat`.

---

# 4. Pantallas de la aplicación

## 4.1 Dashboard

Es la pantalla de resumen inicial. Sirve para ver rápidamente cómo está el mes.

Muestra KPIs como:

- total de requests;
- requests pendientes;
- requests adjudicadas (`awarded`);
- quotes en staging;
- quotes pendientes de revisar;
- quotes aprobadas;
- quotes rechazadas;
- quotes con match;
- ahorro estimado;
- último monthly report generado.

También incluye una tabla resumen por proveedor y accesos directos a las pantallas principales.

**Uso práctico:** abrir la app y saber en 10 segundos si hay trabajo pendiente, si hay quotes sin revisar o si ya existen decisiones registradas.

---

## 4.2 Revisión staging

Esta pantalla sirve para revisar las quotes extraídas automáticamente desde PDFs de proveedor.

Permite filtrar por:

- proveedor;
- estado de revisión;
- coating o grade;
- rango de espesor;
- precio máximo.

La tabla muestra las quotes filtradas con información como:

- ID;
- proveedor;
- documento de origen;
- coating detectado;
- grade extraído;
- espesor;
- ancho;
- precio €/t;
- estado de revisión;
- si necesita revisión manual;
- request asignada, si existe.

También permite:

- seleccionar filas;
- aprobar seleccionadas;
- rechazar seleccionadas;
- aprobar todo el filtro actual;
- rechazar todo el filtro actual;
- ver el texto o fragmento original del PDF del que salió el dato.

**Uso práctico:** validar rápidamente si los precios extraídos de un PDF son correctos antes de usarlos en comparativas.

---

## 4.3 Matching quote → request

Esta pantalla conecta una quote aprobada con una necesidad real de compra.

La aplicación busca candidatos compatibles usando:

- coating / grade;
- espesor;
- ancho;
- score de compatibilidad.

Para cada candidato muestra:

- request sugerida;
- cliente;
- producto;
- grade;
- dimensiones;
- toneladas;
- score total;
- desglose del score.

El matching aplica una regla crítica:

> Si no hay compatibilidad de grade/coating, el candidato queda bloqueado y no debe usarse.

Desde esta pantalla se puede:

- asignar una quote a una request;
- asignar y promover la quote al core;
- promover una quote ya matcheada;
- recalcular shortlist después de promover.

**Uso práctico:** convertir una quote de PDF validada en una alternativa real para una request concreta.

---

## 4.4 Shortlist y decisión

Esta pantalla permite consultar la comparativa final por request.

Muestra las shortlists generadas con:

- referencia;
- cliente;
- material;
- toneladas;
- mejor opción;
- proveedor;
- origen de la mejor opción;
- coste mejor;
- segunda opción;
- AM Spot;
- delta frente a AM Spot;
- ahorro total estimado.

El campo **best_source** indica de dónde viene la mejor opción:

- `BOSS`: viene de la matriz mensual.
- `QUOTE`: viene de una quote real promovida desde PDF.

Las filas donde la mejor opción viene de `QUOTE` aparecen resaltadas, porque indican que el pipeline de PDFs ha aportado una alternativa real.

La pantalla también permite:

- filtrar solo requests con alternativa real;
- recalcular shortlist;
- ver detalle de una request;
- ver quotes core asociadas;
- registrar una decisión de compra;
- marcar la request como `awarded`.

**Uso práctico:** decidir qué proveedor gana cada request y dejar la decisión registrada.

---

## 4.5 Reporting

Pantalla reservada para informes.

Actualmente está preparada como sección futura para centralizar:

- sourcing report;
- savings report;
- monthly report;
- exportaciones Excel.

**Uso práctico esperado:** generar informes sin tener que ejecutar scripts manuales.

---

## 4.6 Estado DB

Pantalla reservada para comprobar el estado técnico de la base de datos.

Actualmente muestra la ruta de la DB usada por la aplicación.

**Uso práctico esperado:** verificar rápidamente qué base de datos está usando la app y añadir checks de salud en futuras versiones.

---

# 5. Glosario de términos

## DB

Base de datos SQLite del proyecto.

Archivo principal:

```text
db/steel_mvp.db
```

Guarda clientes, materiales, requests, quotes, shortlist, decisiones y staging.

---

## BOSS

Nombre usado para la matriz Excel operativa del jefe.

Contiene necesidades de compra del mes, proveedores posibles, costes y comparativas iniciales.

---

## Request

Una necesidad de compra concreta.

Ejemplo:

> Cliente X necesita 25 toneladas de HDG DX51D+Z275, espesor 2 mm, ancho 1500 mm.

En la base de datos vive principalmente en:

```text
sourcing_requests
```

---

## Quote

Una oferta o precio de proveedor para una request.

Puede venir de:

- entrada manual;
- PDF de proveedor;
- datos ya existentes en la matriz BOSS.

En el core vive en:

```text
sourcing_quotes
```

---

## Staging

Zona intermedia de datos.

Sirve para guardar información extraída automáticamente antes de confiar en ella.

Ejemplo:

> El parser lee un PDF de Galmed y extrae 286 precios. Esos precios no entran directamente en decisiones; primero van a staging.

Tablas principales:

```text
stg_supplier_documents
stg_supplier_quotes
```

---

## Revisión staging

Proceso de revisar manualmente datos extraídos automáticamente.

Estados posibles:

- `pending`: pendiente de revisar.
- `approved`: aprobado.
- `rejected`: rechazado.

Solo las quotes aprobadas pueden avanzar hacia matching y promoción al core.

---

## Matching

Proceso de conectar una quote extraída de un PDF con una request real.

Ejemplo:

- quote detectada: `Z140`, espesor 0,58;
- request real: `DX51D+Z140 MA C`, espesor 0,58.

Si son compatibles, se asigna la quote a esa request.

Campo clave:

```text
matched_sourcing_request_id
```

---

## Promover al core

Significa pasar una quote desde staging a la tabla operativa real:

```text
sourcing_quotes
```

Hasta que una quote no se promueve al core, no participa realmente en shortlist ni decisiones.

---

## Shortlist

Ranking de mejores opciones para cada request.

Combina:

- opciones procedentes del BOSS;
- quotes reales promovidas desde PDFs.

La shortlist guarda:

- mejor opción;
- segunda opción;
- tercera opción;
- AM Spot;
- ahorro estimado.

Tabla principal:

```text
sourcing_request_shortlist
```

---

## AM Spot

Precio de referencia de ArcelorMittal usado como benchmark.

Sirve para calcular:

- delta frente a AM Spot;
- ahorro total estimado.

---

## best_source

Indica de dónde viene la mejor opción de la shortlist.

Valores:

- `BOSS`: mejor opción procedente de la matriz BOSS.
- `QUOTE`: mejor opción procedente de una quote real promovida desde PDF.

Cuando aparece `QUOTE`, significa que la carga de PDFs ha aportado una alternativa real útil.

---

## needs_manual_review

Campo de seguridad.

Valores:

- `0`: la quote puede usarse normalmente en comparativas.
- `1`: la quote existe, pero debe tratarse con cautela y no debería entrar automáticamente en ciertos cálculos críticos.

Es especialmente importante para documentos antiguos o datos que necesitan validación.

---

## Awarded

Estado de una request cuando ya tiene una decisión registrada.

Significa que se ha elegido una quote/proveedor ganador.

---

## Savings / ahorro

Ahorro estimado frente a una referencia, normalmente AM Spot.

Puede expresarse como:

- ahorro €/t;
- ahorro total según toneladas de la request.

---

## Monthly report

Informe mensual generado en Excel.

Resume el estado del mes, incluyendo sourcing, savings y staging proveedor.

---

## Backup

Copia de seguridad de la base de datos.

La app crea un backup al arrancar en:

```text
backups/
```

Esto permite recuperar el estado anterior si se comete un error operativo.

---

# 6. Flujo operativo recomendado

## Flujo normal

1. Abrir la app con `run_app.bat`.
2. Entrar en **Dashboard** para ver estado general.
3. Entrar en **Revisión staging**.
4. Filtrar proveedor/documento.
5. Aprobar o rechazar quotes.
6. Entrar en **Matching**.
7. Asignar quote aprobada a request.
8. Promover quote al core.
9. Entrar en **Shortlist y decisión**.
10. Recalcular shortlist.
11. Registrar decisión.
12. Comprobar que la request queda `awarded`.

---

# 7. Qué no debe hacerse desde la app

No usar la app para:

- ejecutar migraciones;
- reconstruir el schema;
- importar masivamente nuevos datos mientras otro proceso escribe en la DB;
- operar en paralelo con otra persona sobre la misma base de datos.

La app es monousuario. Si dos personas editan a la vez, SQLite puede bloquearse o generar estados inconsistentes.

---

# 8. Estado actual de la versión

Esta versión ya permite operar visualmente el flujo principal:

```text
Revisión staging
→ Matching quote-request
→ Promoción al core
→ Shortlist
→ Decisión
```

Quedan como mejoras futuras:

- completar pantalla Reporting;
- completar pantalla Estado DB;
- añadir validaciones visuales más fuertes;
- mejorar diseño;
- crear instalador o paquete más cómodo si se usa en varios equipos.
