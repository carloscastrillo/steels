from __future__ import annotations

import streamlit as st

_THEME_CSS = """
<style>
/* ---- Layout general ---- */
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background-color: #101A28;
    border-right: 1px solid #243246;
}
section[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.85rem;
}

/* ---- Métricas como cards ---- */
div[data-testid="stMetric"] {
    background-color: #16202E;
    border: 1px solid #243246;
    border-radius: 10px;
    padding: 14px 16px;
}
div[data-testid="stMetric"] label {
    color: #9FB0C3;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
div[data-testid="stMetricValue"] {
    color: #E6ECF2;
}

/* ---- Tablas ---- */
div[data-testid="stDataFrame"] {
    border: 1px solid #243246;
    border-radius: 10px;
}

/* ---- Botones ---- */
.stButton > button {
    border-radius: 8px;
    border: 1px solid #2C3E55;
}
.stButton > button[kind="primary"] {
    background-color: #3B82C4;
    border-color: #3B82C4;
}

/* ---- Expanders ---- */
details[data-testid="stExpander"] {
    border: 1px solid #243246;
    border-radius: 10px;
    background-color: #131D2A;
}

/* ---- Cabecera de página ---- */
.steel-page-title {
    font-size: 1.85rem;
    font-weight: 700;
    color: #E6ECF2;
    margin-bottom: 0.1rem;
}
.steel-page-subtitle {
    font-size: 0.95rem;
    color: #9FB0C3;
    margin-bottom: 1.2rem;
}
.steel-badge-ok {
    display: inline-block;
    background-color: #15301F;
    color: #6FCF8E;
    border: 1px solid #2C5A3C;
    border-radius: 999px;
    padding: 2px 12px;
    font-size: 0.75rem;
}
</style>
"""


def inject_theme() -> None:
    """Inyecta el CSS global del tema industrial. Llamar una vez por página."""
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None) -> None:
    """Cabecera de página consistente en toda la app."""
    st.markdown(f'<div class="steel-page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f'<div class="steel-page-subtitle">{subtitle}</div>',
            unsafe_allow_html=True,
        )


def db_connected_badge(text: str = "Base de datos conectada") -> None:
    """Pequeño badge de estado de conexión."""
    st.markdown(f'<span class="steel-badge-ok">{text}</span>', unsafe_allow_html=True)
