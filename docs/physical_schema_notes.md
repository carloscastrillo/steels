# Notas del esquema físico SQLite

## Decisiones tomadas
- Se usa `INTEGER PRIMARY KEY` en lugar de `AUTOINCREMENT`.
- Las fechas se guardan como texto en formato ISO.
- Los booleanos se guardan como 0/1.
- Los estados y tipos se guardan como texto con restricciones `CHECK`.
- Se añaden índices solo en columnas de búsqueda frecuente.

## Pendiente para futuras fases
- Tabla de recargos estructurados.
- Tabla de múltiples documentos por quote.
- Tabla de auditoría.
- Tabla de capacidades de proveedor.
- Reglas de borrado y actualización más avanzadas.