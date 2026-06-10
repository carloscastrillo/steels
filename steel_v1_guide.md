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
# 3.1. Glosario del proyecto HIERROS

BOSS
El fichero Excel operativo del jefe de compras. Es el nombre interno que la empresa da a su hoja de cálculo con macros (.xlsm). Contiene las necesidades de compra del mes: qué materiales se necesitan, para qué clientes, cuántas toneladas y a qué precio oferta cada proveedor. Es la Fuente B del sistema, la más importante operativamente.

Staging
Zona intermedia de cuarentena entre las fuentes de datos brutas y el modelo de negocio limpio. Cuando se importa un fichero (el BOSS, el SAP, un PDF), los datos no van directamente a la base de datos principal: van primero al staging. Allí se pueden revisar, corregir o rechazar antes de que "suban" al sistema real. El concepto viene del inglés staging area (zona de preparación), término estándar en ingeniería de datos. En el proyecto hay tablas de staging para SAP (stg_sap_zsd017_sales), para el BOSS (stg_boss_matrix) y para los documentos de proveedor (stg_supplier_quotes).

Quote (cotización)
Una oferta de precio de un proveedor para un material concreto, con sus condiciones (precio por tonelada, recubrimiento, espesor, ancho). Puede venir de tres sitios: introducida manualmente por el jefe, extraída automáticamente de un PDF de proveedor, o heredada del BOSS. En el sistema hay dos tipos: las quotes que están en staging (pendientes de revisión) y las quotes validadas que ya están en el núcleo (sourcing_quotes).

Matching
El proceso de conectar una quote de proveedor con la solicitud de compra que le corresponde. El problema es que una quote dice "para acero galvanizado Z140, espesor entre 0.5 y 0.7mm, el extra es 15€/t" y una solicitud dice "necesito 50 toneladas de DX51D+Z140 MA C, espesor exacto 0.6mm para el cliente X". El sistema calcula una puntuación de compatibilidad entre ambas y sugiere las mejores candidatas, pero la asignación final la confirma siempre el operador.

Shortlist (lista corta)
Para cada solicitud de compra del mes, la lista de las tres mejores opciones de proveedor ordenadas por precio, con el ahorro calculado respecto al precio de referencia de mercado (AM Spot). Es el elemento central del soporte a la decisión: el jefe de compras mira la shortlist y decide a quién adjudicar. En el sistema, la shortlist combina opciones del BOSS y quotes validadas de PDF.

Sourcing (aprovisionamiento)
El proceso de compra: identificar qué se necesita, buscar proveedores, comparar precios y decidir a quién comprar. En el proyecto, "sourcing requests" son las solicitudes de compra del mes, "sourcing quotes" son las cotizaciones validadas y "sourcing decisions" son las decisiones tomadas. Es terminología estándar del sector de compras industriales.

Pipeline
La cadena de pasos que se ejecuta cada mes para procesar el BOSS y generar la shortlist. En el proyecto son 11 pasos en orden: importar el BOSS, cargar especificaciones, cargar solicitudes, generar opciones de proveedor, calibrar capacidades, validar, calcular costes, clasificar comparabilidad, construir la shortlist y exportar el informe. Si un paso falla, el pipeline se detiene y reporta el error.

Core (núcleo)
Las tablas de la base de datos que contienen los datos limpios y validados del modelo de negocio. Es lo opuesto al staging: aquí solo llegan datos que han pasado por una transformación controlada. Nadie escribe directamente en el core desde un fichero bruto.

Needs manual review (necesita revisión manual)
Un indicador (0 o 1) en las quotes que señala si esa cotización es fiable para usarse en cálculos automáticos. Se pone a 1 automáticamente cuando hay motivos para desconfiar del dato: por ejemplo, las quotes de Luso tienen precios de 2014 y se marcan así para que no distorsionen el cálculo de ahorro. Una quote marcada así puede seguir usándose manualmente, pero el sistema la excluye de las comparaciones automáticas.

AM Spot (precio de referencia ArcelorMittal)
El precio de mercado de referencia de ArcelorMittal para cada material. Se usa como denominador común para calcular el ahorro: "si compramos a Galmed en vez de AM Spot, ahorramos X€/tonelada". No es un precio negociado: es la tarifa pública de mercado que sirve de referencia objetiva.

Parser (analizador)
El módulo de código que lee un PDF de proveedor y extrae los datos de precios de él. Cada proveedor tiene su formato de documento, así que hay parsers específicos: uno para ArcelorMittal/ILVA/EN_*, otro para Tata Steel, otro para Galmed y otro para Luso. El reto técnico es que los PDF no son tablas estructuradas sino documentos con texto y tablas en posiciones variables.

ZSD017
El nombre interno del informe de ventas del ERP SAP. Es una exportación del módulo de distribución (SD) que contiene el histórico comercial: clientes, materiales, cantidades y valores. En el proyecto se usa para construir el catálogo de clientes y materiales, no para precios.

Best source (mejor fuente)
Un campo de la shortlist que indica si la mejor opción para una solicitud viene del BOSS (BOSS) o de una quote extraída de un PDF de proveedor (QUOTE). Es la evidencia visible de que el pipeline documental aporta valor real: cuando aparece QUOTE, significa que el sistema encontró una alternativa más barata que las opciones del BOSS.

Reporting
La pantalla y los procesos de generación de informes. El sistema genera tres: el sourcing report (opciones por solicitud), el savings report (ahorro calculado) y el monthly report (resumen ejecutivo del mes completo). En la app, la pantalla de Reporting es donde el jefe genera y descarga estos ficheros Excel.

Estado DB
La pantalla de salud del sistema. Muestra el estado de la base de datos: cuántos clientes, materiales, solicitudes y quotes hay; si el esquema está bien; cuándo fue el último backup. Es el panel de "todo está bien" para el operador.
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
