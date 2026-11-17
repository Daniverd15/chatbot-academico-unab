"""Observatorio académico UNABot — punto de entrada (Streamlit multipágina).

Ejecutar en local:   streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from lib import ui  # noqa: E402

st.set_page_config(
    page_title="Observatorio académico UNABot",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Observatorio académico UNABot · Chatbot de apoyo académico, "
                         "Ingeniería de Sistemas UNAB. Datos sintéticos — simulación Banner/COSMOS."},
)

ui.estilos()
ui.barra_lateral()

V = BASE / "vistas"
paginas = {
    "Programa académico": [
        st.Page(V / "panorama.py", title="Panorama del programa", icon=":material/dashboard:",
                url_path="panorama", default=True),
        st.Page(V / "cursos.py", title="Cursos y cuellos de botella", icon=":material/account_tree:",
                url_path="cursos"),
        st.Page(V / "riesgo.py", title="Riesgo académico", icon=":material/monitoring:", url_path="riesgo"),
        st.Page(V / "competencias.py", title="Competencias digitales", icon=":material/workspace_premium:",
                url_path="competencias"),
    ],
    "Asistente UNABot": [
        st.Page(V / "chatbot.py", title="Uso del chatbot", icon=":material/forum:", url_path="chatbot"),
        st.Page(V / "rag.py", title="Calidad del RAG", icon=":material/fact_check:", url_path="rag"),
        st.Page(V / "noticias.py", title="Noticias", icon=":material/newspaper:", url_path="noticias"),
    ],
}

pagina = st.navigation(paginas, position="sidebar", expanded=True)
ui.barra_lateral_pie()
pagina.run()
ui.pie_pagina()
