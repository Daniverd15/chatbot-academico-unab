"""Página · Alertas tempranas (workflow 08 de n8n, mensajes para revisión de consejería)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402

ui.encabezado(
    "Alertas tempranas",
    "Cada día n8n detecta estudiantes activos en estado Condicional, En prueba académica o con alertas de "
    "prioridad alta y redacta con Gemini un mensaje de acompañamiento. Los mensajes quedan pendientes para que "
    "consejería los revise: el sistema no contacta al estudiante por sí solo.",
)

al = ui.cargar(datos.alertas_tempranas)
if al.empty:
    st.info("Aún no hay alertas tempranas. Aplique database/04_alertas_tempranas.sql y active el workflow "
            "08 de n8n (o ejecútelo manualmente) para generarlas.", icon=":material/notifications_active:")
    st.stop()

al = al.copy()
al["estudiante"] = al["codigo"].map(ui.enmascarar_codigo)
al["fecha"] = al["generada_en"].dt.tz_localize(None)
al["motivos_n"] = al["motivos"].map(lambda m: len(m) if isinstance(m, list) else 0)
al["palabras"] = al["mensaje"].str.split().str.len()

hoy = al["fecha"].max().normalize()
ui.kpis([
    ui.KPI("Alertas generadas", ui.num(len(al)), f"desde {al['fecha'].min():%Y-%m-%d}", ui.AZUL),
    ui.KPI("Pendientes de revisión", ui.num(int((al["estado"] == "pendiente").sum())), "para consejería", ui.NARANJA),
    ui.KPI("Nivel alto", ui.num(int((al["nivel"] == "alto").sum())), "prueba académica o varias alertas", ui.ROJO),
    ui.KPI("Última corrida", f"{al['fecha'].max():%Y-%m-%d}", f"{int((al['fecha'] >= hoy).sum())} alertas ese día",
           ui.VERDE),
])

c1, c2 = st.columns(2, gap="large")
for col, campo, titulo, ayuda, colores in (
    (c1, "nivel", "Alertas por nivel", "Alto: prueba académica o dos o más alertas de prioridad alta.", ui.NIVEL_COLOR),
    (c2, "estado", "Alertas por estado", "Seguimiento de consejería.",
     {"pendiente": ui.NARANJA, "revisada": ui.AZUL_MEDIO, "enviada": ui.VERDE}),
):
    with col:
        ui.seccion(titulo, ayuda)
        t = al[campo].value_counts().sort_values()
        fig = go.Figure(go.Bar(x=t.values, y=t.index, orientation="h",
                               marker_color=[colores.get(x, ui.GRIS) for x in t.index],
                               text=t.values, textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x} alertas<extra></extra>"))
        fig.update_layout(xaxis=dict(title="Alertas"), margin=dict(l=10, r=40, t=20, b=10))
        ui.grafico(fig, height=260, key=f"alertas_{campo}")

ui.seccion("Últimas alertas", "Código estudiantil enmascarado; por privacidad no se muestra el texto del mensaje "
                              "(se revisa en chatbot.alerta_temprana).")
estados = sorted(al["estado"].unique().tolist())
sel = st.multiselect("Estados", estados, default=estados, key="estados_alertas")
f = al[al["estado"].isin(sel)] if sel else al.iloc[0:0]
st.dataframe(
    f[["fecha", "estudiante", "nivel", "estado", "motivos_n", "palabras"]].head(100),
    hide_index=True, use_container_width=True,
    column_config={"fecha": "Generada", "estudiante": "Estudiante", "nivel": "Nivel", "estado": "Estado",
                   "motivos_n": "Motivos", "palabras": "Palabras"},
)
