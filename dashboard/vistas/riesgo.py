"""Página 3 · Riesgo académico (modelo logístico)."""
import sys
from pathlib import Path

_BASE = str(Path(__file__).resolve().parents[1])
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from lib import datos, riesgo, ui  # noqa: E402

ui.encabezado(
    "Riesgo académico",
    "Probabilidad estimada de que cada estudiante activo quede en prueba académica el próximo periodo, "
    "según el modelo de regresión logística entrenado en notebooks/ y usado por el chatbot (herramienta MCP). "
    "Sirve para priorizar acompañamiento, no para tomar decisiones individuales automáticas.",
)

modelo = riesgo.cargar_modelo()
if modelo is None:
    st.warning("No se encontró modelo_riesgo.json (se busca en DASH_MODELO_RIESGO, /app/modelo_riesgo.json "
               "y ../mcp_server/modelo_riesgo.json).", icon=":material/warning:")
    st.stop()

res = ui.cargar(datos.resumen_estudiantes)
activos = res[res["condicion"] == "Activo"]
p = riesgo.puntuar(activos, modelo)
if p.empty:
    st.info("No hay estudiantes activos con PGA acumulado para puntuar.")
    st.stop()

met = modelo.get("metricas_test", {})
n_alto, n_medio = int((p["nivel"] == "alto").sum()), int((p["nivel"] == "medio").sum())
ui.kpis([
    ui.KPI("Estudiantes puntuados", ui.num(len(p)), f"{ui.num(len(activos) - len(p))} activos sin PGA aún", ui.AZUL),
    ui.KPI("Riesgo alto (p ≥ 0,50)", ui.num(n_alto), ui.pct(100 * n_alto / len(p)) + " de los puntuados", ui.ROJO),
    ui.KPI("Riesgo medio (0,25–0,50)", ui.num(n_medio), ui.pct(100 * n_medio / len(p)) + " de los puntuados", ui.NARANJA),
    ui.KPI("Probabilidad media", ui.num(p["probabilidad"].mean(), 3), f"mediana {ui.num(p['probabilidad'].median(), 3)}", ui.MORADO),
    ui.KPI("AUC (test)", ui.num(met.get("AUC"), 3),
           f"Brier {ui.num(met.get('Brier'), 3)} · n entrenamiento = {ui.num(modelo.get('n_entrenamiento'))}", ui.VERDE),
])

# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.4, 1], gap="large")
with c1:
    ui.seccion("Distribución de probabilidades", "Umbrales del chatbot: medio desde 0,25 y alto desde 0,50.")
    fig = go.Figure()
    for nivel, (a, b) in {"bajo": (0, 0.25), "medio": (0.25, 0.5), "alto": (0.5, 1.0001)}.items():
        d = p[(p["probabilidad"] >= a) & (p["probabilidad"] < b)]
        fig.add_histogram(x=d["probabilidad"], xbins=dict(start=0, end=1, size=0.025), name=f"Riesgo {nivel}",
                          marker_color=ui.NIVEL_COLOR[nivel], marker_line=dict(color="#FFFFFF", width=1),
                          hovertemplate="p ≈ %{x}: %{y} estudiantes<extra></extra>")
    for x in (0.25, 0.5):
        fig.add_vline(x=x, line=dict(color=ui.AZUL, dash="dash", width=1.4))
    fig.update_layout(barmode="overlay", bargap=0.04, xaxis=dict(title="Probabilidad de prueba académica", range=[0, 1]),
                      yaxis=dict(title="Estudiantes"))
    ui.grafico(fig, height=380)

with c2:
    ui.seccion("Coeficientes del modelo", "Coeficientes estandarizados: efecto en el log-odds por 1 desviación estándar.")
    coef = pd.Series(modelo["coeficientes"]).rename(index=riesgo.ETIQUETAS).sort_values()
    fig = go.Figure(go.Bar(
        x=coef.values, y=coef.index, orientation="h",
        marker_color=[ui.ROJO if v > 0 else ui.VERDE for v in coef.values],
        text=[f"{v:+.2f}".replace(".", ",") for v in coef.values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+.3f}<extra></extra>",
    ))
    fig.add_vline(x=0, line=dict(color=ui.AZUL, width=1))
    pad = 0.3 * float(coef.abs().max())
    fig.update_layout(xaxis=dict(title="← reduce el riesgo · aumenta el riesgo →",
                                 range=[min(0.0, float(coef.min())) - pad, max(0.0, float(coef.max())) + pad]),
                      margin=dict(l=10, r=20, t=20, b=10))
    ui.grafico(fig, height=380)

# ---------------------------------------------------------------------------
ui.seccion("Riesgo por grupo", "Probabilidad media y porcentaje en riesgo alto por cohorte, condición laboral y beca.")


def _grupo(col: str, etiquetas: dict | None = None) -> pd.DataFrame:
    g = p.groupby(col).agg(prob=("probabilidad", "mean"), alto=("nivel", lambda s: 100 * (s == "alto").mean()),
                           n=("codigo", "size")).reset_index()
    if etiquetas:
        g[col] = g[col].map(etiquetas)
    return g


def _barras(g: pd.DataFrame, col: str, titulo_x: str, categoria: bool = True) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=g[col].astype(str), y=g["prob"], name="Probabilidad media", marker_color=ui.MORADO,
                customdata=g["n"], hovertemplate="%{x}: p media %{y:.3f} (%{customdata} est.)<extra></extra>")
    fig.add_scatter(x=g[col].astype(str), y=g["alto"] / 100, name="% en riesgo alto", mode="markers",
                    marker=dict(color=ui.NARANJA, size=12, symbol="diamond", line=dict(color="#FFFFFF", width=1)),
                    hovertemplate="%{x}: %{y:.1%} en riesgo alto<extra></extra>")
    fig.update_layout(xaxis=dict(title=titulo_x, type="category" if categoria else None),
                      yaxis=dict(title="Proporción", tickformat=".0%", rangemode="tozero"))
    return fig


g1, g2, g3 = st.columns([1.5, 0.8, 1.2], gap="medium")
with g1:
    ui.grafico(_barras(_grupo("cohorte").sort_values("cohorte"), "cohorte", "Cohorte de ingreso"), height=340)
with g2:
    ui.grafico(_barras(_grupo("trabaja", {True: "Trabaja", False: "No trabaja"}), "trabaja", "Condición laboral"), height=340)
with g3:
    ui.grafico(_barras(_grupo("beca").sort_values("prob", ascending=False), "beca", "Beca"), height=340)

# ---------------------------------------------------------------------------
ui.seccion("Estudiantes con mayor riesgo", "Nombres enmascarados en la base de datos; se muestra el código institucional.")
n_top = st.slider("Número de estudiantes", 10, 50, 20, step=5, key="n_top_riesgo")
top = p.sort_values("probabilidad", ascending=False).head(n_top)
st.dataframe(
    top[["codigo", "nombre_enmascarado", "cohorte", "pga_acumulado", "pga_ultimo_periodo", "estado_academico",
         "total_reprobados", "f_creditos_por_periodo", "trabaja", "probabilidad", "nivel"]],
    hide_index=True,
    column_config={
        "codigo": "Código", "nombre_enmascarado": "Estudiante", "cohorte": "Cohorte",
        "pga_acumulado": st.column_config.NumberColumn("PGA acum.", format="%.2f"),
        "pga_ultimo_periodo": st.column_config.NumberColumn("PGA últ. periodo", format="%.2f"),
        "estado_academico": "Estado actual", "total_reprobados": "Reprobados",
        "f_creditos_por_periodo": st.column_config.NumberColumn("Créd./periodo", format="%.1f"),
        "trabaja": st.column_config.CheckboxColumn("Trabaja"),
        "probabilidad": st.column_config.ProgressColumn("P(prueba)", format="%.3f", min_value=0, max_value=1),
        "nivel": "Nivel",
    },
)

ui.nota("Los datos son sintéticos (simulación Banner/COSMOS): el modelo y sus métricas (AUC "
        f"{ui.num(met.get('AUC'), 3)}, Brier {ui.num(met.get('Brier'), 3)} en el conjunto de prueba) ilustran la "
        "metodología y no deben interpretarse como evidencia sobre estudiantes reales.")

with st.expander("Detalle del modelo"):
    st.markdown(
        f"**{modelo.get('descripcion', 'Regresión logística')}**\n\n"
        "Variables (estandarizadas con las medias y desviaciones del entrenamiento):\n"
        "- PGA acumulado y PGA del último periodo evaluado (si falta, se usa el acumulado).\n"
        "- Reprobados por periodo y créditos aprobados por periodo (periodos matriculados, mínimo 1).\n"
        "- Trabaja (1/0).\n\n"
        "`p = 1 / (1 + e^(−z))`, con `z = intercepto + Σ coef · (x − media) / desviación`. "
        "Es la misma función que expone el servidor MCP (`_riesgo_academico`)."
    )
    st.dataframe(pd.DataFrame({
        "Variable": [riesgo.ETIQUETAS.get(k, k) for k in modelo["coeficientes"]],
        "Coeficiente": list(modelo["coeficientes"].values()),
        "Media": [modelo["medias"][k] for k in modelo["coeficientes"]],
        "Desviación": [modelo["desviaciones"][k] for k in modelo["coeficientes"]],
    }), hide_index=True)
