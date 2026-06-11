from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.ui.components.db_session import (
    load_supplier_documents,
    load_supplier_price_freshness,
    save_supplier_document_upload,
)
from src.ui.components.feedback import run_safe_action


SUPPLIER_OPTIONS = [
    "GALMED",
    "AM",
    "TATA",
    "LUSO",
    "LEON",
    "BAO",
]


def _format_datetime(value: Any) -> str:
    if value is None:
        return "-"

    text = str(value)

    if "T" in text:
        date, time = text.split("T", 1)
        return f"{date} {time[:5]}"

    return text


def _freshness_dataframe() -> pd.DataFrame:
    rows = []

    for item in load_supplier_price_freshness():
        rows.append({
            "Proveedor": item.supplier_code,
            "Último documento": item.latest_file_name or "-",
            "Última actualización": _format_datetime(item.latest_imported_at),
            "Documentos": item.n_documents,
            "Precios detectados": item.n_quotes,
            "Pendientes": item.n_pending,
            "Aprobados": item.n_approved,
            "Requieren revisión": item.n_manual_review,
            "Estado": item.status,
        })

    return pd.DataFrame(rows)


def _documents_dataframe() -> pd.DataFrame:
    rows = []

    for doc in load_supplier_documents(limit=100):
        rows.append({
            "ID": doc.id,
            "Fecha": _format_datetime(doc.imported_at),
            "Proveedor": doc.supplier_code,
            "Archivo": doc.file_name,
            "Tipo": doc.file_type.upper(),
            "Precios detectados": doc.n_quotes_extracted,
            "Notas": doc.notes or "",
            "Ruta": doc.file_path,
        })

    return pd.DataFrame(rows)


def _style_freshness(df: pd.DataFrame):
    def style_row(row):
        styles = [""] * len(row)
        estado = str(row.get("Estado", ""))

        for idx, col in enumerate(row.index):
            if col == "Estado":
                if "Actualizado" in estado:
                    styles[idx] = "background-color: #14532D; color: #DCFCE7; font-weight: 700;"
                elif "Pendiente" in estado:
                    styles[idx] = "background-color: #78350F; color: #FEF3C7; font-weight: 700;"
                elif "Revisión" in estado:
                    styles[idx] = "background-color: #7F1D1D; color: #FEE2E2; font-weight: 700;"

            if col == "Proveedor":
                styles[idx] = "font-weight: 700;"

        return styles

    return df.style.apply(style_row, axis=1)


def render_supplier_documents_section() -> None:
    st.subheader("Documentos y actualización de proveedores")
    st.caption(
        "Sube nuevos PDFs/Excel de proveedor y consulta qué precios están cargados en el sistema."
    )

    with st.container(border=True):
        left, right = st.columns([1, 1.4])

        with left:
            st.markdown("#### Subir nuevo documento")

            uploaded_file = st.file_uploader(
                "Archivo PDF/Excel",
                type=["pdf", "xlsx", "xls", "xlsm", "csv"],
                key="supplier_doc_upload",
            )

            supplier_code = st.selectbox(
                "Proveedor",
                options=SUPPLIER_OPTIONS,
                key="supplier_doc_supplier",
            )

            uploaded_by = st.text_input(
                "Subido por",
                value="",
                placeholder="Nombre del operador",
                key="supplier_doc_uploaded_by",
            )

            notes = st.text_area(
                "Notas",
                value="Documento subido desde la app. Pendiente de procesamiento por parser.",
                key="supplier_doc_notes",
            )

            st.info(
                "El archivo se guarda en el historial. "
                "En esta fase todavía no se procesan automáticamente los precios del PDF/Excel."
            )

            disabled = uploaded_file is None

            if st.button(
                "Guardar documento",
                type="primary",
                disabled=disabled,
                key="supplier_doc_save",
                use_container_width=True,
            ):
                if uploaded_file is None:
                    st.error("Selecciona un archivo primero.")
                else:
                    run_safe_action(
                        lambda: save_supplier_document_upload(
                            file_bytes=uploaded_file.getvalue(),
                            filename=uploaded_file.name,
                            supplier_code=supplier_code,
                            uploaded_by=uploaded_by.strip() or None,
                            notes=notes.strip() or None,
                        ),
                        success_message="Documento guardado correctamente en el historial.",
                        error_message="No se pudo guardar el documento.",
                        rerun=True,
                    )

        with right:
            st.markdown("#### Estado por proveedor")

            freshness_df = _freshness_dataframe()

            if freshness_df.empty:
                st.info("Todavía no hay documentos de proveedor registrados.")
            else:
                st.dataframe(
                    _style_freshness(freshness_df),
                    hide_index=True,
                    use_container_width=True,
                )

    st.markdown("#### Historial de documentos")

    docs_df = _documents_dataframe()

    if docs_df.empty:
        st.info("No hay documentos en el historial.")
    else:
        st.dataframe(
            docs_df,
            hide_index=True,
            use_container_width=True,
        )

    st.caption(
        "Nota: los documentos nuevos quedan registrados con 0 precios detectados hasta que se conecte el procesamiento automático."
    )
