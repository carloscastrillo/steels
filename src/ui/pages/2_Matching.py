from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


st.set_page_config(page_title="Matching", page_icon="🔗", layout="wide")

st.title("Matching quote → request")
st.info("Pantalla pendiente: aquí se asignarán quotes aprobadas a requests.")