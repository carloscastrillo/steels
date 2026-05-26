from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.db_session import clear_cache, load_dashboard_snapshot
from src.ui.components.filters import format_eur


st.set_page_config(page_title="Dashboard", page_icon="📌", layout="wide")

st.title("Dashboard")
st.caption("Estado operativo del mes: requests, staging proveedor, shortlist y reporting.")

with st.sidebar:
    st.header("Acciones")
    if st.button("Refrescar datos", width="stretch"):
        clear_cache()
        st.rerun()

snapshot = load_dashboard_snapshot()

requests = snapshot.get("requests", {})
staging = snapshot.get("staging", {})
shortlist = snapshot.get("shortlist", {})
latest_report = snapshot.get("latest_monthly_report", {})
staging_by_supplier = snapshot.get("staging_by_supplier", [])

st.subheader("KPIs del mes")

r1c1, r1c2, r1c3, r1c4 = st.columns(4)
r1c1.metric("Requests totales", int(requests.get("requests_total") or 0))
r1c2.metric("Pendientes", int(requests.get("requests_pending") or 0))
r1c3.metric("Awarded", int(requests.get("requests_awarded") or 0))
r1c4.metric("Con alternativa", int(shortlist.get("shortlist_with_alternatives") or 0))

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
r2c1.metric("Quotes staging", int(staging.get("staging_total") or 0))
r2c2.metric("Staging pending", int(staging.get("staging_pending") or 0))
r2c3.metric("Staging approved", int(staging.get("staging_approved") or 0))
r2c4.metric("Staging rejected", int(staging.get("staging_rejected") or 0))

r3c1, r3c2, r3c3, r3c4 = st.columns(4)
r3c1.metric("Quotes con match", int(staging.get("staging_matched") or 0))
r3c2.metric("Quotes sin match", int(staging.get("staging_unmatched") or 0))
r3c3.metric("Best source QUOTE", int(shortlist.get("best_source_quote") or 0))
r3c4.metric("Ahorro estimado", format_eur(shortlist.get("estimated_savings_total")))

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Staging por proveedor")
    if staging_by_supplier:
        staging_df = pd.DataFrame(staging_by_supplier)
        st.dataframe(staging_df, width="stretch", hide_index=True)
    else:
        st.info("No hay datos de staging proveedor.")

with right:
    st.subheader("Último monthly report")
    file_name = latest_report.get("file_name")
    modified_at = latest_report.get("modified_at")

    if file_name:
        st.write(f"Archivo: `{file_name}`")
        st.write(f"Última modificación: `{modified_at}`")
    else:
        st.warning("No hay monthly report generado todavía.")

st.divider()

st.subheader("Accesos directos")

link_col1, link_col2, link_col3 = st.columns(3)

with link_col1:
    st.page_link(
        "pages/2_Revision_Staging.py",
        label="Revisar staging",
        icon="📋",
    )

with link_col2:
    st.page_link(
        "pages/3_Matching.py",
        label="Matching quote-request",
        icon="🔗",
    )

with link_col3:
    st.page_link(
        "pages/4_Shortlist.py",
        label="Shortlist y decisión",
        icon="🏁",
    )