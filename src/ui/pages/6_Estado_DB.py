from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st
from src.ui.components.feedback import run_safe_action

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.db_session import (
    clear_cache,
    load_db_status_snapshot,
    run_system_check_action,
)
from src.ui.components.filters import format_eur


st.set_page_config(page_title="Estado DB", page_icon="🗄️", layout="wide")

st.title("Estado DB")
st.caption("Estado tecnico de la base de datos, backups, exports y checks del sistema.")

with st.sidebar:
    st.header("Acciones")

    if st.button("Refrescar estado", width="stretch"):
        clear_cache()
        st.rerun()

    st.warning("No ejecutes checks mientras haya pipelines pesados o migraciones en curso.")


snapshot = load_db_status_snapshot()

active_db = snapshot.get("active_db", {})
staging = snapshot.get("staging", {})
shortlist = snapshot.get("shortlist", {})
requests = snapshot.get("requests", {})

st.subheader("Base de datos activa")

db_col1, db_col2, db_col3 = st.columns(3)
db_col1.metric("Existe", "SI" if active_db.get("exists") else "NO")
db_col2.metric("Tamano MB", active_db.get("size_mb") or "-")
db_col3.metric("Ultima modificacion", active_db.get("modified_at") or "-")

st.code(active_db.get("db_path") or "(sin ruta)", language="text")

st.divider()

st.subheader("KPIs tecnicos")

r1c1, r1c2, r1c3, r1c4 = st.columns(4)
r1c1.metric("Requests", int(requests.get("total") or 0))
r1c2.metric("Requests abiertas", int(requests.get("open_requests") or 0))
r1c3.metric("Awarded", int(requests.get("awarded") or 0))
r1c4.metric("Cancelled", int(requests.get("cancelled") or 0))

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
r2c1.metric("Staging quotes", int(staging.get("total") or 0))
r2c2.metric("Pending", int(staging.get("pending") or 0))
r2c3.metric("Approved", int(staging.get("approved") or 0))
r2c4.metric("Matched", int(staging.get("matched") or 0))

r3c1, r3c2, r3c3, r3c4 = st.columns(4)
r3c1.metric("Shortlists", int(shortlist.get("total") or 0))
r3c2.metric("Con segunda opcion", int(shortlist.get("with_second") or 0))
r3c3.metric("Best QUOTE", int(shortlist.get("best_quote") or 0))
r3c4.metric("Ahorro estimado", format_eur(shortlist.get("savings")))

st.divider()

st.subheader("Conteo de tablas principales")

table_counts = snapshot.get("table_counts", [])

if table_counts:
    st.dataframe(
        pd.DataFrame(table_counts),
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No hay informacion de tablas.")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Backups recientes")
    backups = snapshot.get("recent_backups", [])
    if backups:
        st.dataframe(pd.DataFrame(backups), width="stretch", hide_index=True)
    else:
        st.info("No hay backups detectados.")

with right:
    st.subheader("Exports recientes")
    exports = snapshot.get("recent_exports", [])
    if exports:
        st.dataframe(pd.DataFrame(exports), width="stretch", hide_index=True)
    else:
        st.info("No hay exports detectados.")

st.divider()

st.subheader("Checks tecnicos")

st.write("Ejecuta checks desde la interfaz para validar arquitectura, parsers y schema.")

check_col1, check_col2, check_col3 = st.columns(3)

check_to_run = None

with check_col1:
    if st.button("Check arquitectura", width="stretch"):
        check_to_run = "architecture"

with check_col2:
    if st.button("Test parsers", width="stretch"):
        check_to_run = "parsers"

with check_col3:
    if st.button("Smoke schema", width="stretch"):
        check_to_run = "schema"

if check_to_run:
    with st.spinner(f"Ejecutando check: {check_to_run}..."):
        result = run_safe_action(
            lambda: run_system_check_action(check_to_run),
            success_message=f"Check {check_to_run} ejecutado.",
            error_message=f"No se pudo ejecutar el check {check_to_run}.",
            rerun=False,
        )

    if result:
        if result.get("ok"):
            st.success(f"Check {check_to_run} OK.")
        else:
            st.error(f"Check {check_to_run} falló.")

        with st.expander("Ver salida técnica", expanded=True):
            st.json(result)
            if result.get("stdout"):
                st.markdown("#### stdout")
                st.code(result["stdout"], language="text")
            if result.get("stderr"):
                st.markdown("#### stderr")
                st.code(result["stderr"], language="text")