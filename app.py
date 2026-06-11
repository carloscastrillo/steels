from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.services.backup_service import create_startup_backup
from src.ui.components.db_session import (
    clear_cache,
    get_database_path_text,
    load_dashboard_snapshot,
)
from src.ui.components.feedback import render_debug_toggle
from src.ui.components.filters import format_eur
from src.ui.components.theme import db_connected_badge, inject_theme, page_header

st.set_page_config(
    page_title="Inicio · Steel MVP",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

if "startup_backup_done" not in st.session_state:
    try:
        backup_path = create_startup_backup(prefix="streamlit_startup")
        st.session_state["startup_backup_done"] = True
        st.session_state["startup_backup_path"] = str(backup_path)
    except Exception as exc:
        st.session_state["startup_backup_done"] = False
        st.session_state["startup_backup_error"] = str(exc)

page_header("Inicio", "Panel operativo de compras de acero")
db_connected_badge()

with st.sidebar:
    st.title("Steel MVP")
    st.caption("Herramienta de compras de acero")

    if st.button("Actualizar datos", width="stretch"):
        clear_cache()
        st.rerun()

    if st.session_state.get("startup_backup_path"):
        st.success("Copia de seguridad creada al iniciar.")
    elif st.session_state.get("startup_backup_error"):
        st.error("No se pudo crear la copia de seguridad inicial.")

    st.divider()
    st.caption("Modo soporte")
    render_debug_toggle()

snapshot = load_dashboard_snapshot()

requests = snapshot.get("requests", {})
staging = snapshot.get("staging", {})
shortlist = snapshot.get("shortlist", {})
latest_report = snapshot.get("latest_monthly_report", {})
staging_by_supplier = snapshot.get("staging_by_supplier", [])

st.write("")
st.subheader("Resumen del mes")

r1c1, r1c2, r1c3, r1c4 = st.columns(4)
r1c1.metric("Solicitudes del mes", int(requests.get("requests_total") or 0))
r1c2.metric("Pendientes de decisión", int(requests.get("requests_pending") or 0))
r1c3.metric("Adjudicadas", int(requests.get("requests_awarded") or 0))
r1c4.metric("Con alternativa", int(shortlist.get("shortlist_with_alternatives") or 0))

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
r2c1.metric("Precios proveedor cargados", int(staging.get("staging_total") or 0))
r2c2.metric("Pendientes de revisar", int(staging.get("staging_pending") or 0))
r2c3.metric(
    "Mejor opción desde PDF",
    int(shortlist.get("best_source_quote") or 0),
    help="Solicitudes cuya mejor opción procede de un PDF de proveedor.",
)
r2c4.metric("Ahorro estimado", format_eur(shortlist.get("estimated_savings_total")))

st.divider()

st.subheader("Proceso del mes")
st.markdown(
    "**1.** Importar matriz &nbsp;→&nbsp; "
    "**2.** Revisar precios de proveedor &nbsp;→&nbsp; "
    "**3.** Comparar ofertas &nbsp;→&nbsp; "
    "**4.** Decidir compra &nbsp;→&nbsp; "
    "**5.** Exportar informe"
)

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Resumen por proveedor")
    if staging_by_supplier:
        supplier_df = pd.DataFrame(staging_by_supplier)
        supplier_df = supplier_df.rename(
            columns={
                "supplier_code": "Proveedor",
                "review_status": "Estado",
                "n_quotes": "Precios",
                "n_manual_review": "Requieren revisión",
                "n_matched": "Asignados",
                "n_documents": "Documentos",
            }
        )
        status_map = {
            "pending": "Pendiente",
            "approved": "Aprobado",
            "rejected": "Rechazado",
        }
        if "Estado" in supplier_df.columns:
            supplier_df["Estado"] = supplier_df["Estado"].map(
                lambda value: status_map.get(str(value), value)
            )
        st.dataframe(supplier_df, width="stretch", hide_index=True)
    else:
        st.info("Todavía no hay precios de proveedor cargados.")

with right:
    st.subheader("Último informe mensual")
    file_name = latest_report.get("file_name")
    modified_at = latest_report.get("modified_at")

    if file_name:
        st.write(f"Archivo: `{file_name}`")
        st.write(f"Generado: `{modified_at}`")
        st.page_link(
            "pages/3_Exportar_Documentos.py",
            label="Ir a Exportar Documentos",
            icon="📤",
        )
    else:
        st.warning("Aún no se ha generado el informe mensual.")

st.divider()

st.subheader("Accesos rápidos")

link_col1, link_col2, link_col3 = st.columns(3)

with link_col1:
    st.page_link("pages/1_Matriz.py", label="Ir a la Matriz", icon="📊")

with link_col2:
    st.page_link(
        "pages/2_Revision_Precios_Proveedores.py",
        label="Revisar precios de proveedor",
        icon="📋",
    )

with link_col3:
    st.page_link(
        "pages/3_Exportar_Documentos.py",
        label="Exportar documentos",
        icon="📤",
    )

with st.expander("Información técnica", expanded=False):
    st.code(get_database_path_text(), language="text")
    if st.session_state.get("startup_backup_path"):
        st.caption(f"Backup: {st.session_state['startup_backup_path']}")
