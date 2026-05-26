from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.ui.components.db_session import get_database_path_text


st.set_page_config(page_title="Estado DB", page_icon="🗄️", layout="wide")

st.title("Estado DB")
st.code(get_database_path_text(), language="text")
st.info("Pantalla pendiente: aquí se mostrarán checks rápidos de salud del sistema.")