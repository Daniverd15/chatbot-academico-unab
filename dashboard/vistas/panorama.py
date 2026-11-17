"""Página 1 · Panorama del programa."""
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
    "Panorama del programa",
    "Fotografía del programa de Ingeniería de Sistemas: matrícula activa, rendimiento acumulado y estado "
    "académico según el Reglamento Estudiantil de Pregrado UNAB 2019 (art. 24): Normal con PGA > 3,20, "
    "Condicional entre 3,00 y 3,20 y Prueba académica por debajo de 3,00 o tras dos periodos sin recuperarse.",
)

ind = ui.cargar(datos.indicadores)
res = ui.cargar(datos.resumen_estudiantes)
evol = ui.cargar(datos.pga_por_periodo)

activos = res[res["condicion"] == "Activo"]
n_act = int(ind.get("estudiantes_activos") or 0)
pct_prueba = 100 * (ind.get("en_prueba_academica") or 0) / n_act if n_act else None
pct_cond = 100 * (ind.get("condicionales") or 0) / n_act if n_act else None

ui.kpis([
    ui.KPI("Estudiantes activos", ui.num(n_act), f"de {ui.num(len(res))} registrados", ui.AZUL),
    ui.KPI("PGA promedio", ui.num(ind.get("pga_promedio_activos"), 2), "estudiantes activos · escala 0–5", ui.MORADO),
    ui.KPI("En prueba académica", ui.pct(pct_prueba), f"{ui.num(ind.get('en_prueba_academica'))} activos", ui.ROJO),
    ui.KPI("Condicional", ui.pct(pct_cond), f"{ui.num(ind.get('condicionales'))} activos", ui.NARANJA),
    ui.KPI("Tasa de deserción", ui.pct(ind.get("tasa_desercion")),
           f"{ui.num(ind.get('no_activos'))} desertores, retirados o inactivos", ui.VERDE),
])

# ---------------------------------------------------------------------------
c1, c2 = st.columns([1, 1.5], gap="large")
with c1:
    ui.seccion("Estado académico de los activos", "Clasificación del último periodo evaluado.")
    orden = ["Normal", "Condicional", "En prueba académica", "Sin calificaciones"]
    est = activos["estado_academico"].value_counts().reindex(orden).dropna()
    fig = go.Figure(go.Pie(
        labels=est.index, values=est.values, hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=[ui.ESTADO_COLOR[e] for e in est.index], line=dict(color="#FFFFFF", width=2)),
        textinfo="percent", textposition="inside", insidetextorientation="horizontal",
        textfont=dict(color="#FFFFFF", size=12),
        hovertemplate="%{label}: %{value} estudiantes (%{percent})<extra></extra>",
    ))
    fig.update_layout(showlegend=True, uniformtext=dict(minsize=10, mode="hide"),
                      legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"),
                      margin=dict(l=10, r=10, t=10, b=40),
                      annotations=[dict(text=f"<b>{len(activos)}</b><br>activos", showarrow=False,
                                        font=dict(size=16, color=ui.AZUL))])
    ui.grafico(fig, height=360)

with c2:
    ui.seccion("Condición por cohorte", "Composición de cada cohorte de ingreso según su condición actual.")
    coh = res.groupby(["cohorte", "condicion"]).size().reset_index(name="n")
    tot = coh.groupby("cohorte")["n"].transform("sum")
    coh["pct"] = 100 * coh["n"] / tot
    fig = go.Figure()
    for cond in [c for c in ui.CONDICION_COLOR if c in set(coh["condicion"])]:
        d = coh[coh["condicion"] == cond]
        fig.add_bar(x=d["cohorte"], y=d["pct"], name=cond, marker_color=ui.CONDICION_COLOR[cond],
                    customdata=d["n"],
                    hovertemplate=f"{cond}<br>Cohorte %{{x}}: %{{customdata}} est. (%{{y:.1f}} %)<extra></extra>")
    fig.update_layout(barmode="stack", yaxis=dict(title="% de la cohorte", ticksuffix=" %", range=[0, 100]),
                      xaxis=dict(title="Cohorte de ingreso", type="category"))
    ui.grafico(fig, height=360)

# ---------------------------------------------------------------------------
c3, c4 = st.columns([1, 1.5], gap="large")
with c3:
    ui.seccion("Embudo de avance", "Estudiantes activos que han alcanzado cada semestre según créditos aprobados.")
    sem = activos["semestre_por_creditos"].dropna().astype(int)
    niveles = list(range(1, 10))
    alcanzan = [int((sem >= s).sum()) for s in niveles]
    fig = go.Figure(go.Funnel(
        y=[f"Semestre {s}" for s in niveles], x=alcanzan, textinfo="value+percent initial",
        marker=dict(color=[ui.MORADO if s <= 3 else ui.AZUL_MEDIO if s <= 6 else ui.VERDE for s in niveles]),
        connector=dict(line=dict(color=ui.GRIS_CLARO)),
        hovertemplate="%{y}: %{x} estudiantes<extra></extra>",
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    ui.grafico(fig, height=420)

with c4:
    ui.seccion("Distribución del PGA acumulado",
               "Líneas de referencia del art. 24: 3,00 (límite de prueba académica) y 3,20 (estado Normal).")
    pga = activos["pga_acumulado"].dropna()
    fig = go.Figure()
    fig.add_vrect(x0=0, x1=3.0, fillcolor=ui.ROJO, opacity=0.06, line_width=0)
    fig.add_vrect(x0=3.0, x1=3.2, fillcolor=ui.NARANJA, opacity=0.12, line_width=0)
    fig.add_histogram(x=pga, xbins=dict(start=1.5, end=5.0, size=0.1), marker_color=ui.MORADO,
                      marker_line=dict(color="#FFFFFF", width=1), opacity=0.9,
                      hovertemplate="PGA %{x}: %{y} estudiantes<extra></extra>", name="Estudiantes")
    for x, txt, col in [(3.0, "3,00 · prueba", ui.ROJO), (3.2, "3,20 · normal", ui.VERDE)]:
        fig.add_vline(x=x, line=dict(color=col, width=2, dash="dash"))
        fig.add_annotation(x=x, y=1, yref="paper", text=txt, showarrow=False, xanchor="left", xshift=4,
                           font=dict(color=col, size=12), bgcolor="rgba(255,255,255,.85)")
    if len(pga):
        fig.add_annotation(x=0.99, y=0.92, xref="paper", yref="paper", xanchor="right", showarrow=False,
                           text=f"Mediana {ui.num(pga.median(), 2)} · {ui.pct(100 * (pga < 3).mean())} bajo 3,00",
                           font=dict(color=ui.AZUL))
    fig.update_layout(showlegend=False, xaxis=dict(title="PGA acumulado", range=[1.5, 5.0]),
                      yaxis=dict(title="Estudiantes"), bargap=0.05)
    ui.grafico(fig, height=420)

# ---------------------------------------------------------------------------
ui.seccion("Evolución por periodo académico",
           "PGA promedio del periodo (eje izquierdo) y porcentaje de estudiantes evaluados en prueba académica.")
if not evol.empty:
    fig = go.Figure()
    fig.add_bar(x=evol["periodo_id"], y=evol["pct_prueba"], name="% en prueba académica", yaxis="y2",
                marker_color=ui.ROJO, opacity=0.25, hovertemplate="%{x}: %{y:.1f} % en prueba<extra></extra>")
    fig.add_bar(x=evol["periodo_id"], y=evol["pct_condicional"], name="% condicional", yaxis="y2",
                marker_color=ui.NARANJA, opacity=0.35, hovertemplate="%{x}: %{y:.1f} % condicional<extra></extra>")
    fig.add_scatter(x=evol["periodo_id"], y=evol["pga_promedio"], name="PGA promedio del periodo",
                    mode="lines+markers", line=dict(color=ui.MORADO, width=3), marker=dict(size=8),
                    customdata=evol["estudiantes"],
                    hovertemplate="%{x}: PGA %{y:.2f} (%{customdata} evaluados)<extra></extra>")
    fig.update_layout(
        barmode="stack",
        xaxis=dict(type="category", title="Periodo"),
        yaxis=dict(title="PGA promedio", range=[2.5, 4.5]),
        yaxis2=dict(title="% de evaluados", overlaying="y", side="right", ticksuffix=" %",
                    showgrid=False, range=[0, max(60, float((evol["pct_prueba"] + evol["pct_condicional"]).max()) * 1.2)]),
    )
    ui.grafico(fig, height=360)

with st.expander("¿Cómo se calculan estos indicadores?"):
    st.markdown(
        "- **Fuente:** vistas `v_indicadores_programa`, `v_estudiante_resumen` y `v_pga_periodo` (esquema `academico`).\n"
        "- **Tasa de deserción:** desertores, retirados e inactivos sobre el total de estudiantes registrados.\n"
        "- **Semestre por créditos:** criterio de Registro Académico, `1 + ⌊créditos aprobados / (créditos del plan / 9)⌋`.\n"
        "- **PGA:** promedio ponderado por créditos de las notas finales (escala 0,0–5,0)."
    )
