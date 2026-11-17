"""Página 5 · Uso del chatbot (chatbot.conversacion_log)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, ui  # noqa: E402

ui.encabezado(
    "Uso del chatbot",
    "Actividad registrada en la bitácora del asistente (chatbot.conversacion_log): volumen de conversaciones, "
    "intenciones detectadas por el clasificador, latencia de respuesta, intervenciones de los guardrails y "
    "satisfacción declarada por los estudiantes.",
)

log = ui.cargar(datos.conversaciones)
if log.empty:
    st.info("La bitácora aún no tiene conversaciones registradas. Cuando el chatbot empiece a recibir preguntas "
            "(app Android o n8n), aquí aparecerán sus métricas de uso.", icon=":material/forum:")
    st.stop()

log = log.copy()
log["dia"] = log["creado_en"].dt.tz_localize(None).dt.normalize()
log["flags"] = log["guardrail_flags"].apply(lambda v: v if isinstance(v, list) else [])
lat = log["latencia_ms"].dropna().astype(float)
cal = log["calificacion"].dropna().astype(float)

pequeno = len(log) < 30
if pequeno:
    st.caption(f"Muestra pequeña ({len(log)} mensajes): los indicadores son descriptivos y pueden variar mucho.")

ui.kpis([
    ui.KPI("Mensajes", ui.num(len(log)), f"{ui.num(log['session_id'].nunique())} sesiones", ui.AZUL),
    ui.KPI("Latencia p50 · p95", f"{ui.num(lat.quantile(.5) / 1000, 1)} · {ui.num(lat.quantile(.95) / 1000, 1)} s"
           if len(lat) else "—", f"{ui.num(len(lat))} mensajes con latencia", ui.MORADO),
    ui.KPI("Bloqueados por guardrails", ui.pct(100 * log["bloqueado"].mean()),
           f"{ui.num(int(log['bloqueado'].sum()))} mensajes", ui.ROJO),
    ui.KPI("Con alguna alerta", ui.pct(100 * (log["flags"].str.len() > 0).mean()), "entrada o salida marcada", ui.NARANJA),
    ui.KPI("Calificación promedio", f"{ui.num(cal.mean(), 2)} / 5" if len(cal) else "—",
           f"{ui.num(len(cal))} calificaciones" if len(cal) else "sin calificaciones aún", ui.VERDE),
])

# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.5, 1], gap="large")
with c1:
    ui.seccion("Conversaciones por día", "Mensajes recibidos y sesiones distintas por día (hora de Colombia).")
    por_dia = log.groupby("dia").agg(mensajes=("log_id", "size"), sesiones=("session_id", "nunique")).reset_index()
    rango = pd.date_range(por_dia["dia"].min(), por_dia["dia"].max(), freq="D")
    por_dia = por_dia.set_index("dia").reindex(rango, fill_value=0).rename_axis("dia").reset_index()
    fig = go.Figure()
    fig.add_bar(x=por_dia["dia"], y=por_dia["mensajes"], name="Mensajes", marker_color=ui.MORADO,
                hovertemplate="%{x|%d %b %Y}: %{y} mensajes<extra></extra>")
    fig.add_scatter(x=por_dia["dia"], y=por_dia["sesiones"], name="Sesiones", mode="lines+markers",
                    line=dict(color=ui.NARANJA, width=2.5), hovertemplate="%{x|%d %b %Y}: %{y} sesiones<extra></extra>")
    fig.update_layout(xaxis=dict(title="", tickformat="%d %b"), yaxis=dict(title="Cantidad", rangemode="tozero"))
    ui.grafico(fig, height=340)

with c2:
    ui.seccion("Distribución de intención", "Clasificación de cada pregunta por el enrutador del agente.")
    it = log["intencion"].value_counts().sort_values()
    fig = go.Figure(go.Bar(
        x=it.values, y=[s.replace("_", " ") for s in it.index], orientation="h",
        marker_color=[ui.ROJO if "bloque" in s else ui.MORADO for s in it.index],
        text=[f"{v} ({100 * v / len(log):.0f} %)" for v in it.values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x} mensajes<extra></extra>",
    ))
    fig.update_layout(xaxis=dict(title="Mensajes"), margin=dict(l=10, r=60, t=20, b=10))
    ui.grafico(fig, height=340)

# ---------------------------------------------------------------------------
c3, c4 = st.columns([1.5, 1], gap="large")
with c3:
    ui.seccion("Latencia por intención", "Tiempo de respuesta extremo a extremo; la línea punteada marca el p95 global.")
    d = log.dropna(subset=["latencia_ms"])
    if d.empty:
        st.info("No hay mensajes con latencia registrada.")
    else:
        fig = go.Figure()
        orden = d.groupby("intencion")["latencia_ms"].median().sort_values().index
        for i, intencion in enumerate(orden):
            v = d.loc[d["intencion"] == intencion, "latencia_ms"] / 1000
            fig.add_box(y=v, name=intencion.replace("_", " "), boxpoints="all", jitter=0.4, pointpos=0,
                        marker=dict(color=ui.SECUENCIA[i % len(ui.SECUENCIA)], size=6, opacity=0.7),
                        line=dict(width=1.5), fillcolor="rgba(142,0,230,.08)",
                        hovertemplate="%{y:.2f} s<extra></extra>")
        fig.add_hline(y=lat.quantile(.95) / 1000, line=dict(color=ui.ROJO, dash="dot"),
                      annotation_text=f"p95 {ui.num(lat.quantile(.95) / 1000, 1)} s", annotation_position="top right")
        fig.update_layout(showlegend=False, yaxis=dict(title="Segundos", rangemode="tozero"))
        ui.grafico(fig, height=360)

with c4:
    ui.seccion("Guardrails", "Alertas registradas: «entrada» (pregunta filtrada) y «salida:…» (respuesta saneada).")
    flags = log["flags"].explode().dropna()
    if flags.empty:
        st.info("Ningún mensaje ha activado los guardrails.")
    else:
        fc = flags.value_counts()
        fig = go.Figure(go.Pie(labels=fc.index, values=fc.values, hole=0.55, sort=False,
                               marker=dict(colors=ui.SECUENCIA, line=dict(color="#FFFFFF", width=2)),
                               hovertemplate="%{label}: %{value}<extra></extra>"))
        fig.update_layout(legend=dict(orientation="v", x=1.02, y=0.5, yanchor="middle"))
        ui.grafico(fig, height=360)

# ---------------------------------------------------------------------------
if len(cal):
    ui.seccion("Calificaciones de los usuarios", "Escala 1–5 enviada desde la app; los mensajes sin calificar no se cuentan.")
    cc = cal.astype(int).value_counts().reindex(range(1, 6), fill_value=0)
    fig = go.Figure(go.Bar(x=[f"{i} ★" for i in cc.index], y=cc.values,
                           marker_color=[ui.ROJO, ui.NARANJA, ui.GRIS, ui.AZUL_MEDIO, ui.VERDE],
                           text=cc.values, textposition="outside", cliponaxis=False))
    fig.update_layout(yaxis=dict(title="Mensajes"), height=280)
    ui.grafico(fig)

ui.seccion("Últimas 20 interacciones", "Código estudiantil enmascarado; por privacidad no se muestra el texto de la pregunta ni de la respuesta.")
st.caption("El texto de las preguntas no se muestra ni se consulta: puede contener nombres u otros datos personales. "
           "Solo se listan metadatos de la interacción.")
ult = log.sort_values("creado_en", ascending=False).head(20).copy()
ult["fecha"] = ult["creado_en"].dt.strftime("%Y-%m-%d %H:%M")
ult["latencia_s"] = ult["latencia_ms"] / 1000
st.dataframe(
    ult[["fecha", "codigo_enmascarado", "intencion", "bloqueado", "latencia_s", "calificacion"]],
    hide_index=True,
    column_config={
        "fecha": "Fecha y hora", "codigo_enmascarado": "Estudiante", "intencion": "Intención",
        "bloqueado": st.column_config.CheckboxColumn("Bloqueado"),
        "latencia_s": st.column_config.NumberColumn("Latencia (s)", format="%.2f"),
        "calificacion": st.column_config.NumberColumn("Calif.", format="%d"),
    },
)
