from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

from src.ui.components.feedback import run_safe_action, show_user_error

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.ui.components.db_session import (
    clear_cache,
    generate_monthly_report_action,
    generate_savings_report_action,
    generate_sourcing_report_action,
    load_export_files,
)


st.set_page_config(page_title="Reporting", page_icon="📊", layout="wide")

st.title("Reporting")
st.caption("Generación y consulta de informes Excel del sistema.")

with st.sidebar:
    st.header("Acciones")

    if st.button("Refrescar lista", width="stretch"):
        clear_cache()
        st.rerun()

    st.warning(
        "No ejecutes reports mientras haya pipelines pesados o migraciones en curso."
    )


st.subheader("Generar informes")

current_month = datetime.now().strftime("%Y-%m")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Sourcing report")
    st.write("Genera el informe operativo principal de sourcing.")
    if st.button("Generar sourcing report", width="stretch"):
        with st.spinner("Generando sourcing report..."):
            result = run_safe_action(
                generate_sourcing_report_action,
                success_message="Sourcing report generado correctamente.",
                error_message="No se pudo generar el sourcing report.",
                rerun=False,
            )

        if result:
            with st.expander("Ver salida técnica"):
                st.json(result)
with col2:
    st.markdown("#### Savings report")
    st.write("Genera el informe de ahorro y alternativas reales.")
    if st.button("Generar savings report", width="stretch"):
        with st.spinner("Generando savings report..."):
            result = run_safe_action(
                generate_savings_report_action,
                success_message="Savings report generado correctamente.",
                error_message="No se pudo generar el savings report.",
                rerun=False,
            )

        if result:
            with st.expander("Ver salida técnica"):
                st.json(result)

with col3:
    st.markdown("#### Monthly report")
    st.write("Genera el informe mensual completo.")
    month = st.text_input(
        "Mes",
        value=current_month,
        help="Formato esperado: YYYY-MM",
    )

    if st.button("Generar monthly report", width="stretch"):
        with st.spinner("Generando monthly report..."):
            result = run_safe_action(
                lambda: generate_monthly_report_action(month),
                success_message="Monthly report generado correctamente.",
                error_message="No se pudo generar el monthly report.",
                rerun=False,
            )

        if result:
            with st.expander("Ver salida técnica"):
                st.json(result)



st.divider()

st.subheader("Exports disponibles")

exports = load_export_files()

if not exports:
    st.info("No hay archivos Excel en la carpeta exports.")
    st.stop()

exports_df = pd.DataFrame(exports)

st.dataframe(
    exports_df,
    width="stretch",
    hide_index=True,
)

st.divider()

st.subheader("Descargar archivo")

file_names = exports_df["file_name"].tolist()

selected_file = st.selectbox(
    "Archivo",
    file_names,
)

selected_row = exports_df[exports_df["file_name"] == selected_file].iloc[0].to_dict()
selected_path = Path(selected_row["path"])

if not selected_path.exists():
    st.error("El archivo seleccionado ya no existe en disco.")
else:
    st.write(f"Ruta: `{selected_path}`")
    st.write(f"Tamaño: {selected_row['size_kb']} KB")
    st.write(f"Última modificación: {selected_row['modified_at']}")

    st.download_button(
        label="Descargar Excel",
        data=selected_path.read_bytes(),
        file_name=selected_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
