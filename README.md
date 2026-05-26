# Steel MVP Híbrido

Objetivo:
Sustituir el Excel operativo por un sistema híbrido con Python + SQLite + Excel/Power BI.

Fase actual:
Preparación del proyecto y definición del modelo de datos.

Stack inicial:
- Python
- SQLite
- pandas
- openpyxl
- SQLAlchemy
## Architecture checks

Before closing a sprint or merging UI/service changes, run:

python src/devtools/check_architecture.py

This verifies that:

- services do not import Streamlit;
- Streamlit UI does not execute SQL directly;
- backend tests do not depend on the UI;
- service write operations commit transactions;
- service public functions do not return raw sqlite3.Row objects.
